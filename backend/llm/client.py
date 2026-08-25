"""LLM client wrapper providing multi-key load balancing, model fallbacks, and high-speed generation.

Supports Google Gemini (with multi-key rotation and multi-model fallbacks),
Anthropic Claude, and OpenAI backends.
"""

import json
import re
import time
import logging
import threading
from collections import deque
from typing import Any, Dict, List, Optional
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
    """Thread-safe sliding window rate limiter allowing high-throughput bursts while enforcing RPM limits."""

    def __init__(self, max_rpm: int = 30, window_seconds: float = 60.0):
        self.max_rpm = max(1, max_rpm)
        self.window_seconds = window_seconds
        self._timestamps: deque = deque()
        self._lock = threading.Lock()

    def acquire(self) -> float:
        """Acquire a rate limit slot with burst support."""
        total_waited = 0.0
        while True:
            sleep_needed = 0.0
            with self._lock:
                now = time.time()
                while self._timestamps and self._timestamps[0] <= now - self.window_seconds:
                    self._timestamps.popleft()

                if len(self._timestamps) >= self.max_rpm:
                    oldest = self._timestamps[0]
                    sleep_needed = max(0.05, (oldest + self.window_seconds) - now + 0.02)
                else:
                    self._timestamps.append(now)
                    return total_waited

            if sleep_needed > 0:
                time.sleep(sleep_needed)
                total_waited += sleep_needed


class MultiKeyGeminiPool:
    """Load-balances requests across multiple Gemini API keys and fast fallback models."""

    def __init__(self, api_keys: List[str], primary_model: str = "gemini-flash-lite-latest"):
        self.clients = [genai.Client(api_key=key.strip()) for key in api_keys if key.strip()]
        if not self.clients:
            raise ValueError("At least one valid Gemini API key is required.")
        self.primary_model = primary_model
        self.fallback_models = ["gemini-2.5-flash", "gemini-flash-lite-latest"]
        self._index = 0
        self._lock = threading.Lock()

    def get_client_and_index(self, offset: int = 0):
        with self._lock:
            idx = (self._index + offset) % len(self.clients)
            self._index += 1
            return self.clients[idx], idx


class LLMClient:
    """Wrapper for invoking LLMs with structured JSON responses and dual/multi-API load balancing."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        rpm_ceiling = getattr(settings, "GEMINI_MAX_RPM", 30) or getattr(settings, "LLM_MAX_RPM", 30) or 30
        self.rate_limiter = SlidingWindowRateLimiter(max_rpm=rpm_ceiling, window_seconds=60.0)
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize active provider or multi-key pool."""
        if self.provider == "gemini":
            keys = []
            if settings.GEMINI_API_KEY:
                keys.extend([k.strip() for k in settings.GEMINI_API_KEY.split(",") if k.strip()])
            if getattr(settings, "GEMINI_API_KEY_2", None):
                k2 = settings.GEMINI_API_KEY_2.strip()
                if k2 and k2 not in keys:
                    keys.append(k2)

            primary_model = settings.GEMINI_MODEL or "gemini-flash-lite-latest"
            # If an API key was accidentally passed as the model name:
            if primary_model.startswith("AQ.") or primary_model.startswith("AIza") or len(primary_model) > 35:
                if primary_model not in keys:
                    keys.append(primary_model)
                primary_model = "gemini-flash-lite-latest"

            if not keys:
                raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

            self.gemini_pool = MultiKeyGeminiPool(api_keys=keys, primary_model=primary_model)
            logger.info(f"Initialized Gemini Multi-Key Pool with {len(keys)} key(s) on model '{primary_model}'")
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
            self.model_name = "claude-3-5-haiku-20241022"
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Generate a structured JSON response from the LLM."""
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
        max_retries: int = 4,
    ) -> Dict[str, Any]:
        """Invoke Gemini model across keys and fallback models with sub-second execution."""
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        models_to_try = [self.gemini_pool.primary_model] + [
            m for m in self.gemini_pool.fallback_models if m != self.gemini_pool.primary_model
        ]

        last_error = None
        for attempt in range(1, max_retries + 1):
            self.rate_limiter.acquire()
            # Alternate across keys on retries
            client, key_idx = self.gemini_pool.get_client_and_index(offset=attempt - 1)
            model_name = models_to_try[(attempt - 1) % len(models_to_try)]

            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                if not response.text:
                    raise ValueError("Gemini returned empty response")

                cleaned = clean_json_response(response.text)
                return json.loads(cleaned)
            except Exception as e:
                last_error = e
                is_rate_limit = "429" in str(e) or "quota" in str(e).lower() or "resource_exhausted" in str(e).lower()
                logger.warning(
                    f"Gemini error on key #{key_idx+1} model {model_name} (attempt {attempt}/{max_retries}): {e}"
                )
                if is_rate_limit:
                    time.sleep(1.2 * attempt)
                else:
                    time.sleep(0.3 * attempt)

        raise RuntimeError(f"Gemini generation failed after {max_retries} attempts: {last_error}") from last_error

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
