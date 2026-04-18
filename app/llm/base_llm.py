"""Abstract base class for LLM providers.

All concrete LLM providers must implement this interface so they can be
swapped at runtime via dependency injection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseLLM(ABC):
    """Abstract LLM provider interface."""

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        self._api_key = api_key
        self._config: Dict[str, Any] = kwargs

    @property
    def provider_name(self) -> str:
        """Return the human-readable provider name."""
        return self.__class__.__name__

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text completion from the given prompt.

        Args:
            prompt: The input prompt string.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The generated text response.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the provider is configured and reachable.

        Returns:
            True if the provider can accept requests.
        """
