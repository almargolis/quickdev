"""Tests for qdimage.llmdescribe"""

import os
import tempfile

import pytest
from PIL import Image

from qdimage.llmdescribe import describe_image
from qdimage.llmproviders import LLMProvider
from qdimage.infmeta import InfMeta


class FakeProvider(LLMProvider):
    """Fake LLM provider for testing."""

    def __init__(self, response_text="A test description"):
        self._response = response_text
        self._model = "fake-model-v1"
        self._calls = []

    @property
    def model_name(self) -> str:
        return self._model

    def describe_image(self, image_data, media_type, prompt=None):
        self._calls.append({
            'data_len': len(image_data),
            'media_type': media_type,
            'prompt': prompt,
        })
        return self._response


@pytest.fixture
def test_jpg():
    """Create a test JPEG image file."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "test.jpg")
        img = Image.new('RGB', (100, 50), color='red')
        img.save(path, 'JPEG')
        yield path


@pytest.fixture
def test_png():
    """Create a test PNG image file."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "test.png")
        img = Image.new('RGB', (100, 50), color='blue')
        img.save(path, 'PNG')
        yield path


class TestDescribeImage:
    def test_basic_describe(self, test_jpg):
        provider = FakeProvider("A red rectangle")
        result = describe_image(test_jpg, provider, save_to_inf=False)
        assert result['text'] == "A red rectangle"
        assert result['model'] == "fake-model-v1"
        assert result['source'] == 'llm'
        assert 'date' in result

    def test_calls_provider_with_correct_media_type(self, test_jpg):
        provider = FakeProvider()
        describe_image(test_jpg, provider, save_to_inf=False)
        assert len(provider._calls) == 1
        assert provider._calls[0]['media_type'] == 'image/jpeg'

    def test_png_media_type(self, test_png):
        provider = FakeProvider()
        describe_image(test_png, provider, save_to_inf=False)
        assert provider._calls[0]['media_type'] == 'image/png'

    def test_custom_prompt(self, test_jpg):
        provider = FakeProvider()
        describe_image(test_jpg, provider, prompt="What is this?",
                      save_to_inf=False)
        assert provider._calls[0]['prompt'] == "What is this?"

    def test_saves_to_inf(self, test_jpg):
        provider = FakeProvider("Description from LLM")
        result = describe_image(test_jpg, provider, save_to_inf=True)

        inf_path = test_jpg.replace('.jpg', '.inf')
        assert os.path.exists(inf_path)

        meta = InfMeta.load(inf_path)
        descs = meta.get_descriptions()
        assert len(descs) == 1
        # Get the single description
        desc = list(descs.values())[0]
        assert desc['text'] == "Description from LLM"
        assert desc['source'] == 'llm'
        assert desc['model'] == "fake-model-v1"

    def test_appends_to_existing_inf(self, test_jpg):
        # Create initial .inf
        inf_path = test_jpg.replace('.jpg', '.inf')
        meta = InfMeta.from_image_path(test_jpg)
        meta.add_description("Manual desc", source="manual")
        meta.save()

        # Now describe with LLM
        provider = FakeProvider("LLM desc")
        describe_image(test_jpg, provider, save_to_inf=True)

        meta2 = InfMeta.load(inf_path)
        descs = meta2.get_descriptions()
        assert len(descs) == 2

    def test_nonexistent_file(self):
        provider = FakeProvider()
        with pytest.raises(FileNotFoundError):
            describe_image("/nonexistent/image.jpg", provider)

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as f:
            img = Image.new('RGB', (10, 10))
            img.save(f.name, 'BMP')
            provider = FakeProvider()
            try:
                with pytest.raises(ValueError, match="Unsupported"):
                    describe_image(f.name, provider)
            finally:
                os.unlink(f.name)
