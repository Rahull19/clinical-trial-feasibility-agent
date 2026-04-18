"""LLM port interface — contract for language-model providers.

All concrete LLM providers implement this interface so they can be
swapped at runtime via dependency injection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMPort(ABC):
    """Abstract LLM provider interface."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the human-readable provider name."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text completion from the given prompt.

        Args:
            prompt: The input prompt string.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The generated text response.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the provider is configured and reachable."""
