"""Tests for qdimage.llmproviders"""

import pytest
from qdimage.llmproviders import (
    LLMProvider, get_provider, register_provider,
    AnthropicProvider, OpenAIProvider,
)


class MockProvider(LLMProvider):
    """Test provider that returns canned responses."""

    def __init__(self, api_key: str, model: str = None):
        self._api_key = api_key
        self._model = model or "mock-v1"

    @property
    def model_name(self) -> str:
        return self._model

    def describe_image(self, image_data, media_type, prompt=None):
        return f"Mock description of {len(image_data)} bytes"


class TestGetProvider:
    def test_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nonexistent", api_key="key")

    def test_anthropic_type(self):
        p = get_provider("anthropic", api_key="test-key")
        assert isinstance(p, AnthropicProvider)
        assert p.model_name == "claude-sonnet-4-20250514"

    def test_anthropic_custom_model(self):
        p = get_provider("anthropic", api_key="test-key", model="claude-opus-4-20250514")
        assert p.model_name == "claude-opus-4-20250514"

    def test_openai_type(self):
        p = get_provider("openai", api_key="test-key")
        assert isinstance(p, OpenAIProvider)
        assert p.model_name == "gpt-4o"


class TestRegisterProvider:
    def test_register_and_use(self):
        register_provider("mock", MockProvider)
        p = get_provider("mock", api_key="key123")
        assert isinstance(p, MockProvider)
        result = p.describe_image(b"test data", "image/jpeg")
        assert "9 bytes" in result

    def test_register_invalid_class(self):
        with pytest.raises(TypeError, match="must be a subclass"):
            register_provider("bad", str)


class TestMockProvider:
    def test_describe(self):
        p = MockProvider(api_key="k")
        text = p.describe_image(b"hello", "image/jpeg", "Describe this")
        assert isinstance(text, str)
        assert "5 bytes" in text

    def test_custom_model(self):
        p = MockProvider(api_key="k", model="custom-v2")
        assert p.model_name == "custom-v2"


class TestProviderIndependence:
    def test_separate_instances(self):
        """Each get_provider call creates an independent instance."""
        p1 = get_provider("anthropic", api_key="key1")
        p2 = get_provider("anthropic", api_key="key2")
        assert p1 is not p2
        assert p1._api_key == "key1"
        assert p2._api_key == "key2"
