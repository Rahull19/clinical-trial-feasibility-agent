"""xAI (Grok) LLM provider implementation using OpenAI-compatible SDK."""

from __future__ import annotations

from typing import Any, Optional

from openai import OpenAI

from app.llm.base_llm import BaseLLM
from app.core.logging import get_logger

logger = get_logger(__name__)


class XAIProvider(BaseLLM):
    """LLM provider backed by xAI (Grok)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-beta",
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, **kwargs)
        self._model = model
        if self._api_key:
            self._client = OpenAI(
                api_key=self._api_key,
                base_url="https://api.x.ai/v1"
            )
        else:
            self._client = None

    @property
    def provider_name(self) -> str:
        return "xAI"

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a completion via xAI (Grok).

        Args:
            prompt: The input prompt.
            **kwargs: Extra params (temperature, max_tokens, etc.).

        Returns:
            Generated text.
        """
        if not self._client:
            raise ValueError("xAI client not initialized. Check API key.")

        logger.info("[XAIProvider] generate called — model=%s, prompt_len=%d", self._model, len(prompt))

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("[XAIProvider] API call failed: %s", str(e))
            raise

    def is_available(self) -> bool:
        return bool(self._client and self._api_key)
