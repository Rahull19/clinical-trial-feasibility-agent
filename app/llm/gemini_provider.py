"""Google Gemini LLM provider implementation using the official Google Generative AI SDK."""

from __future__ import annotations

from typing import Any, Optional

import google.generativeai as genai

from app.llm.base_llm import BaseLLM
from app.core.logging import get_logger

logger = get_logger(__name__)


class GeminiProvider(BaseLLM):
    """LLM provider backed by Google Gemini."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, **kwargs)
        self._model = model
        if self._api_key:
            genai.configure(api_key=self._api_key)
            self._client = genai.GenerativeModel(self._model)
        else:
            self._client = None

    @property
    def provider_name(self) -> str:
        return "Gemini"

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a completion via Google Gemini.

        Args:
            prompt: The input prompt.
            **kwargs: Extra params (temperature, max_tokens, etc.).

        Returns:
            Generated text.
        """
        if not self._client:
            raise ValueError("Gemini client not initialized. Check API key.")

        logger.info("[GeminiProvider] generate called — model=%s, prompt_len=%d", self._model, len(prompt))

        try:
            generation_config = genai.types.GenerationConfig(
                temperature=kwargs.get("temperature", 0.7),
                max_output_tokens=kwargs.get("max_tokens", 2000),
            )
            response = self._client.generate_content(
                prompt,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            logger.error("[GeminiProvider] API call failed: %s", str(e))
            raise

    def is_available(self) -> bool:
        return bool(self._client and self._api_key)
