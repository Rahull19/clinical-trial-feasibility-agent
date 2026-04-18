"""Groq LLM provider implementation using the official Groq SDK."""

from __future__ import annotations

from typing import Any, Optional

from groq import Groq

from app.llm.base_llm import BaseLLM
from app.core.logging import get_logger

logger = get_logger(__name__)


class GroqProvider(BaseLLM):
    """LLM provider backed by Groq (Llama / Mixtral)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, **kwargs)
        self._model = model
        self._client = Groq(api_key=self._api_key) if self._api_key else None

    @property
    def provider_name(self) -> str:
        return "Groq"

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a completion via Groq.

        Args:
            prompt: The input prompt.
            **kwargs: Extra params (temperature, max_tokens, etc.).

        Returns:
            Generated text.
        """
        if not self._client:
            raise ValueError("Groq client not initialized. Check API key.")

        logger.info("[GroqProvider] generate called — model=%s, prompt_len=%d", self._model, len(prompt))

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("[GroqProvider] API call failed: %s", str(e))
            raise

    def is_available(self) -> bool:
        return bool(self._client and self._api_key)
