"""LLM adapter — wraps existing sync BaseLLM providers into the async LLMPort.

This allows the existing OpenAI/Groq/Gemini/xAI providers to be used
through the new domain interface without rewriting them.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.domain.interfaces.llm import LLMPort
from app.llm.base_llm import BaseLLM


class LLMAdapter(LLMPort):
    """Adapts a synchronous BaseLLM to the async LLMPort interface.

    Runs the sync ``generate()`` call in a thread-pool so it never
    blocks the event loop.

    Args:
        wrapped: The existing sync LLM provider to wrap.
    """

    def __init__(self, wrapped: BaseLLM) -> None:
        self._wrapped = wrapped

    @property
    def provider_name(self) -> str:
        return self._wrapped.provider_name

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return await asyncio.to_thread(self._wrapped.generate, prompt, **kwargs)

    def is_available(self) -> bool:
        return self._wrapped.is_available()
