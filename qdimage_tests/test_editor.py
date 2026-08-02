"""Tests for qdimage.editor"""

import pytest
from PIL import Image
from qdimage.editor import ImageEditor


def make_test_image(width=200, height=100, mode='RGB', color='red'):
    """Create a test image."""
    return Image.new(mode, (width, height), color=color)


class TestCropImage:
    def test_basic_crop(self):
        img = make_test_image(200, 100)
        result = ImageEditor.crop_image(img, (10, 10, 100, 50))
        assert result.size == (90, 40)

    def test_coords_clamped_to_bounds(self):
        img = make_test_image(200, 100)
        result = ImageEditor.crop_image(img, (-10, -10, 300, 200))
        assert result.size == (200, 100)

    def test_invalid_coords_raises(self):
        img = make_test_image(200, 100)
        with pytest.raises(ValueError, match="right must be > left"):
            ImageEditor.crop_image(img, (100, 10, 50, 50))

    def test_float_coords_converted(self):
        img = make_test_image(200, 100)
        result = ImageEditor.crop_image(img, (10.5, 10.5, 100.7, 50.3))
        assert result.size == (90, 40)


class TestAdjustBrilliance:
    def test_no_change(self):
        img = make_test_image()
        result = ImageEditor.adjust_brilliance(img, 1.0, 1.0)
        assert result.size == img.size

    def test_brightness_change(self):
        img = make_test_image()
        result = ImageEditor.adjust_brilliance(img, brightness=1.5)
        assert result.size == img.size

    def test_contrast_change(self):
        img = make_test_image()
        result = ImageEditor.adjust_brilliance(img, contrast=0.8)
        assert result.size == img.size


class TestResizeForPreview:
    def test_small_image_unchanged(self):
        img = make_test_image(100, 50)
        result = ImageEditor.resize_for_preview(img, max_dimension=1200)
        assert result.size == (100, 50)

    def test_large_landscape(self):
        img = make_test_image(2400, 1600)
        result = ImageEditor.resize_for_preview(img, max_dimension=1200)
        assert result.size[0] == 1200
        assert result.size[1] == 800

    def test_large_portrait(self):
        img = make_test_image(1600, 2400)
        result = ImageEditor.resize_for_preview(img, max_dimension=1200)
        assert result.size[0] == 800
        assert result.size[1] == 1200


class TestResize:
    def test_both_dimensions(self):
        img = make_test_image(200, 100)
        result = ImageEditor.resize(img, width=400, height=200)
        assert result.size == (400, 200)

    def test_width_only(self):
        img = make_test_image(200, 100)
        result = ImageEditor.resize(img, width=400)
        assert result.size == (400, 200)

    def test_height_only(self):
        img = make_test_image(200, 100)
        result = ImageEditor.resize(img, height=200)
        assert result.size == (400, 200)

    def test_no_dimensions_raises(self):
        img = make_test_image()
        with pytest.raises(ValueError, match="At least one"):
            ImageEditor.resize(img)


class TestAutoOrient:
    def test_returns_image(self):
        img = make_test_image()
        result = ImageEditor.auto_orient(img)
        assert isinstance(result, Image.Image)
