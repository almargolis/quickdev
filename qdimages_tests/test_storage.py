"""
Tests for qdimages storage module.
"""

import pytest
import os
import tempfile
from PIL import Image
from qdimages.storage import ImageStorage


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for image storage tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_image():
    """Create a sample test image."""
    img = Image.new('RGB', (100, 100), color='red')
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img.save(f.name, 'PNG')
        yield f.name
        os.unlink(f.name)


@pytest.fixture
def storage(temp_storage_dir):
    """Create an ImageStorage instance."""
    return ImageStorage(
        base_path=temp_storage_dir,
        temp_path=os.path.join(temp_storage_dir, 'temp')
    )


def test_storage_initialization(storage, temp_storage_dir):
    """Test that ImageStorage initializes correctly."""
    assert storage.base_path == temp_storage_dir
    assert os.path.exists(storage.base_path)


def test_compute_hash(storage, sample_image):
    """Test hash computation for images."""
    hash_value = storage.compute_hash(sample_image)
    assert hash_value is not None
    assert isinstance(hash_value, str)
    assert len(hash_value) > 0

    # Same file should produce same hash
    hash_value2 = storage.compute_hash(sample_image)
    assert hash_value == hash_value2


def test_hierarchical_path_generation(storage):
    """Test that hierarchical paths are generated correctly."""
    hash_value = "a1b2c3d4e5f6"
    path = storage.get_hierarchical_path(hash_value)

    # Path should contain hash prefix directories
    assert 'a1' in path or 'b2' in path
    assert path.endswith('.jpg') or path.endswith('.png')


def test_save_image(storage, sample_image):
    """Test saving an image to hierarchical storage."""
    result = storage.save_image(sample_image, keywords=['test', 'sample'])

    assert 'path' in result
    assert 'hash' in result
    assert os.path.exists(result['path'])


def test_browse_directories(storage, sample_image):
    """Test browsing storage directories."""
    # Save an image first
    storage.save_image(sample_image)

    # Browse root
    result = storage.browse()
    assert 'directories' in result or 'images' in result
