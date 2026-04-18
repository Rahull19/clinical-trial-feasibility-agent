"""OpenAI LLM provider implementation using the official OpenAI SDK."""

from __future__ import annotations

from typing import Any, Optional

from openai import OpenAI

from app.llm.base_llm import BaseLLM
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(BaseLLM):
    """LLM provider backed by OpenAI (GPT-4o / GPT-4-turbo)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, **kwargs)
        self._model = model
        self._client = OpenAI(api_key=self._api_key) if self._api_key else None

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a completion via OpenAI.

        Args:
            prompt: The input prompt.
            **kwargs: Extra params (temperature, max_tokens, etc.).

        Returns:
            Generated text.
        """
        if not self._client:
            raise ValueError("OpenAI client not initialized. Check API key.")

        logger.info("[OpenAIProvider] generate called — model=%s, prompt_len=%d", self._model, len(prompt))

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("[OpenAIProvider] API call failed: %s", str(e))
            raise

    def is_available(self) -> bool:
        return bool(self._client and self._api_key)
