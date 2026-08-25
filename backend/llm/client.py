"""LLM client wrapper providing a swappable interface with rate pacing.

Supports Google Gemini (via official google-genai SDK), Anthropic Claude,
and OpenAI backends configured by the LLM_PROVIDER environment variable.
Includes a thread-safe sliding window rate limiter and exponential backoff.
"""

import json
import re
import time
import logging
import threading
from collections import deque
from typing import Any, Dict, Optional
from google import genai
from google.genai import types

from backend.config import settings

logger = logging.getLogger(__name__)


def clean_json_response(raw_text: str) -> str:
    """Strip markdown code blocks or wrapping whitespace from LLM output."""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter ensuring requests per minute stay below ceiling."""

    def __init__(self, max_rpm: int = 14, window_seconds: float = 60.0):
        self.max_rpm = max(1, max_rpm)
        self.window_seconds = window_seconds
        self._min_interval = window_seconds / float(self.max_rpm)
        self._timestamps: deque = deque()
        self._lock = threading.Lock()

    def acquire(self) -> float:
        """Block until a slot in the sliding window is available with smooth spacing.
        
        Returns:
            float: Total seconds waited before acquiring slot.
        """
        total_waited = 0.0
        while True:
            sleep_needed = 0.0
            with self._lock:
                now = time.time()
                # Purge timestamps older than the sliding window
                while self._timestamps and self._timestamps[0] <= now - self.window_seconds:
                    self._timestamps.popleft()

                # Check sliding window capacity
                if len(self._timestamps) >= self.max_rpm:
                    oldest = self._timestamps[0]
                    sleep_needed = max(0.1, (oldest + self.window_seconds) - now + 0.05)
                elif self._timestamps:
                    # Apply smooth spacing between consecutive requests
                    time_since_last = now - self._timestamps[-1]
                    if time_since_last < self._min_interval:
                        sleep_needed = max(0.05, self._min_interval - time_since_last)

                if sleep_needed <= 0.0:
                    self._timestamps.append(now)
                    if total_waited > 0:
                        logger.info(f"RateLimiter: Slot acquired after {total_waited:.2f}s wait ({len(self._timestamps)}/{self.max_rpm} in window).")
                    return total_waited

            if sleep_needed > 0:
                time.sleep(sleep_needed)
                total_waited += sleep_needed


class LLMClient:
    """Wrapper for invoking LLMs with structured JSON responses and client-side rate pacing."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        rpm_ceiling = getattr(settings, "GEMINI_MAX_RPM", 12) or getattr(settings, "LLM_MAX_RPM", 12) or 12
        self.rate_limiter = SlidingWindowRateLimiter(max_rpm=rpm_ceiling, window_seconds=60.0)
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize the active provider SDK client."""
        if self.provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
            self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self.model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"
        elif self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
            import openai
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model_name = "gpt-4o-mini"
        elif self.provider == "claude":
            if not settings.CLAUDE_API_KEY:
                raise ValueError("CLAUDE_API_KEY is required when LLM_PROVIDER=claude")
            import anthropic
            self.claude_client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
            self.model_name = "claude-3-5-sonnet-20241022"
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Generate a structured JSON response from the LLM with rate limiting and backoff."""
        if self.provider == "gemini":
            return self._generate_gemini_json(prompt, system_instruction)
        elif self.provider == "openai":
            return self._generate_openai_json(prompt, system_instruction)
        elif self.provider == "claude":
            return self._generate_claude_json(prompt, system_instruction)
        else:
            raise RuntimeError(f"Unknown provider: {self.provider}")

    def _generate_gemini_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_retries: int = 5,
    ) -> Dict[str, Any]:
        """Invoke Gemini model with client-side rate limiting and 429 exponential backoff."""
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        delay = 5.0
        for attempt in range(1, max_retries + 1):
            # 1. Pacing slot acquisition
            self.rate_limiter.acquire()

            try:
                response = self.gemini_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )

                if not response.text:
                    raise ValueError("Gemini returned empty text response")

                cleaned = clean_json_response(response.text)
                return json.loads(cleaned)
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str
                
                if is_rate_limit:
                    if attempt < max_retries:
                        logger.warning(
                            f"Gemini 429/Quota limit hit on attempt {attempt}/{max_retries}. Backing off {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= 1.8
                        continue
                    else:
                        logger.error(f"Gemini rate limit retries exhausted after {max_retries} attempts.")
                        raise RuntimeError(f"Gemini API rate limit exceeded ({max_retries} retries exhausted): {e}") from e

                # For non-rate-limit errors
                logger.error(f"Gemini generation error on attempt {attempt}/{max_retries}: {e}")
                if attempt == max_retries:
                    raise RuntimeError(f"Gemini generation failed: {e}") from e
                time.sleep(1.0)

        raise RuntimeError("Gemini generation retries exhausted")

    def _generate_openai_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Invoke OpenAI model with JSON response format."""
        self.rate_limiter.acquire()
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(clean_json_response(content))
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}", exc_info=True)
            raise RuntimeError(f"OpenAI generation failed: {e}") from e

    def _generate_claude_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Invoke Anthropic Claude model."""
        self.rate_limiter.acquire()
        try:
            kwargs: Dict[str, Any] = {
                "model": self.model_name,
                "max_tokens": 1000,
                "temperature": 0.7,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_instruction:
                kwargs["system"] = system_instruction

            response = self.claude_client.messages.create(**kwargs)
            text = response.content[0].text if response.content else "{}"
            return json.loads(clean_json_response(text))
        except Exception as e:
            logger.error(f"Claude generation error: {e}", exc_info=True)
            raise RuntimeError(f"Claude generation failed: {e}") from e


# Singleton LLM client instance
llm_client = LLMClient()
