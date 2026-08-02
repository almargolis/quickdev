"""
LLM provider system for image description.

Provides a base class and implementations for sending images to LLMs
for description/identification. Each provider instance is independent,
allowing multiple LLMs with different API keys to be used simultaneously.

Usage:
    provider = get_provider("anthropic", api_key="sk-ant-...")
    description = provider.describe_image(image_bytes, "image/jpeg")
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Abstract base class for LLM image description providers."""

    @abstractmethod
    def describe_image(self, image_data: bytes, media_type: str,
                       prompt: Optional[str] = None) -> str:
        """
        Send an image to the LLM and get a text description.

        Args:
            image_data: Raw image bytes
            media_type: MIME type (e.g., "image/jpeg", "image/png")
            prompt: Optional custom prompt (default provided by implementation)

        Returns:
            Description text from the LLM
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string."""


_DEFAULT_PROMPT = (
    "Describe this image in detail. Include the main subject, colors, "
    "composition, and any text visible in the image."
)


class AnthropicProvider(LLMProvider):
    """Image description via Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = None):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model identifier (default: claude-sonnet-4-20250514)
        """
        self._api_key = api_key
        self._model = model or "claude-sonnet-4-20250514"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "anthropic is not installed. Install with: "
                    "pip install qdimage[llm]"
                )
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    @property
    def model_name(self) -> str:
        return self._model

    def describe_image(self, image_data: bytes, media_type: str,
                       prompt: Optional[str] = None) -> str:
        import base64
        client = self._get_client()
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        message = client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt or _DEFAULT_PROMPT,
                    },
                ],
            }],
        )
        return message.content[0].text


class OpenAIProvider(LLMProvider):
    """Image description via OpenAI API."""

    def __init__(self, api_key: str, model: str = None):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model identifier (default: gpt-4o)
        """
        self._api_key = api_key
        self._model = model or "gpt-4o"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
            except ImportError:
                raise ImportError(
                    "openai is not installed. Install with: "
                    "pip install qdimage[llm]"
                )
            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    @property
    def model_name(self) -> str:
        return self._model

    def describe_image(self, image_data: bytes, media_type: str,
                       prompt: Optional[str] = None) -> str:
        import base64
        client = self._get_client()
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:{media_type};base64,{image_b64}"

        response = client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt or _DEFAULT_PROMPT,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                ],
            }],
        )
        return response.choices[0].message.content


# Provider registry
_PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


def register_provider(name: str, cls):
    """
    Register a custom LLM provider.

    Args:
        name: Provider name (used with get_provider)
        cls: Provider class (must subclass LLMProvider)
    """
    if not issubclass(cls, LLMProvider):
        raise TypeError(f"{cls} must be a subclass of LLMProvider")
    _PROVIDERS[name] = cls


def get_provider(name: str, api_key: str, model: str = None) -> LLMProvider:
    """
    Create an LLM provider instance.

    Args:
        name: Provider name ("anthropic", "openai", or custom registered name)
        api_key: API key for the provider
        model: Optional model identifier override

    Returns:
        LLMProvider instance
    """
    if name not in _PROVIDERS:
        available = ", ".join(sorted(_PROVIDERS.keys()))
        raise ValueError(
            f"Unknown provider '{name}'. Available: {available}"
        )
    cls = _PROVIDERS[name]
    return cls(api_key=api_key, model=model)
