"""LLM client wrapper providing a swappable interface.

Supports Google Gemini (via official google-genai SDK), Anthropic Claude,
and OpenAI backends configured by the LLM_PROVIDER environment variable.
"""

import json
import re
import logging
from typing import Any, Dict, Optional
from google import genai
from google.genai import types

from backend.config import settings

logger = logging.getLogger(__name__)


def clean_json_response(raw_text: str) -> str:
    """Strip markdown code blocks or wrapping whitespace from LLM output."""
    text = raw_text.strip()
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


class LLMClient:
    """Wrapper for invoking LLMs with structured JSON responses."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
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
        """Generate a structured JSON response from the LLM.

        Args:
            prompt: User prompt containing instructions, context, and schema details.
            system_instruction: Optional system instruction for grounding or behavior.

        Returns:
            Dict containing parsed JSON payload from LLM.

        Raises:
            RuntimeError: If LLM call fails or returns malformed JSON.
        """
        if self.provider == "gemini":
            return self._generate_gemini_json(prompt, system_instruction)
        elif self.provider == "openai":
            return self._generate_openai_json(prompt, system_instruction)
        elif self.provider == "claude":
            return self._generate_claude_json(prompt, system_instruction)
        else:
            raise RuntimeError(f"Unknown provider: {self.provider}")

    def _generate_gemini_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Invoke Gemini model with JSON response configuration."""
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            )
            if system_instruction:
                config.system_instruction = system_instruction

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
            logger.error(f"Gemini generation error: {e}", exc_info=True)
            raise RuntimeError(f"Gemini generation failed: {e}") from e

    def _generate_openai_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Invoke OpenAI model with JSON response format."""
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
