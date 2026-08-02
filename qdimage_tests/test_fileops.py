"""Tests for qdimage.fileops"""

import os
import pytest
import tempfile
from PIL import Image
from qdimage.fileops import ImageFileHandler


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_image(tmp_dir):
    """Create a sample image file and return its path."""
    img = Image.new('RGB', (100, 50), color='blue')
    path = os.path.join(tmp_dir, 'test.jpg')
    img.save(path, 'JPEG')
    return path


class TestLoadImage:
    def test_load_existing(self, sample_image):
        img = ImageFileHandler.load_image(sample_image)
        assert isinstance(img, Image.Image)
        assert img.size == (100, 50)

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            ImageFileHandler.load_image('/nonexistent/path.jpg')


class TestSaveImage:
    def test_save_jpeg(self, tmp_dir):
        img = Image.new('RGB', (100, 50), color='green')
        original = os.path.join(tmp_dir, 'photo.jpg')
        img.save(original, 'JPEG')
        output = ImageFileHandler.save_image(img, original, suffix="_edited")
        assert output.endswith('photo_edited.jpg')
        assert os.path.exists(output)

    def test_save_rgba_as_png(self, tmp_dir):
        img = Image.new('RGBA', (100, 50), color=(255, 0, 0, 128))
        original = os.path.join(tmp_dir, 'photo.jpg')
        output = ImageFileHandler.save_image(img, original, suffix="_bg")
        assert output.endswith('.png')
        assert os.path.exists(output)


class TestListImages:
    def test_list_with_images(self, tmp_dir):
        for name in ['a.jpg', 'b.png', 'c.gif', 'not_image.txt']:
            path = os.path.join(tmp_dir, name)
            if name.endswith('.txt'):
                with open(path, 'w') as f:
                    f.write('hello')
            else:
                Image.new('RGB', (10, 10)).save(path)

        handler = ImageFileHandler(default_directory=tmp_dir)
        images = handler.list_images()
        names = {img['name'] for img in images}
        assert 'a.jpg' in names
        assert 'b.png' in names
        assert 'c.gif' in names
        assert 'not_image.txt' not in names

    def test_list_empty_dir(self, tmp_dir):
        handler = ImageFileHandler(default_directory=tmp_dir)
        assert handler.list_images() == []

    def test_list_nonexistent_dir(self):
        handler = ImageFileHandler()
        assert handler.list_images('/nonexistent/dir') == []

    def test_list_no_default(self):
        handler = ImageFileHandler()
        assert handler.list_images() == []


class TestValidatePath:
    def test_valid_path(self, tmp_dir, sample_image):
        assert ImageFileHandler.validate_path(sample_image, tmp_dir) is True

    def test_path_traversal(self, tmp_dir):
        bad_path = os.path.join(tmp_dir, '..', '..', 'etc', 'passwd')
        assert ImageFileHandler.validate_path(bad_path, tmp_dir) is False


class TestGenerateOutputFilename:
    def test_default_suffix(self):
        result = ImageFileHandler.generate_output_filename('/path/to/image.jpg')
        assert result == '/path/to/image_new.jpg'

    def test_custom_suffix(self):
        result = ImageFileHandler.generate_output_filename('/path/to/photo.png', '_edited')
        assert result == '/path/to/photo_edited.png'
