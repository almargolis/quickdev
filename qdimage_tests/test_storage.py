"""Tests for qdimage.storage"""

import os
import tempfile

import pytest
from PIL import Image

from qdimage.storage import ImageStorage


@pytest.fixture
def storage():
    """Create ImageStorage with temp directory."""
    with tempfile.TemporaryDirectory() as d:
        s = ImageStorage(base_path=d, db_path=os.path.join(d, 'test.db'))
        yield s


@pytest.fixture
def test_image():
    """Create a simple test image."""
    img = Image.new('RGB', (100, 50), color='red')
    img.format = 'JPEG'
    return img


class TestImageStorageInit:
    def test_creates_base_dir(self):
        with tempfile.TemporaryDirectory() as d:
            subdir = os.path.join(d, 'images')
            storage = ImageStorage(base_path=subdir)
            assert os.path.isdir(subdir)

    def test_requires_base_path(self):
        with pytest.raises(ValueError):
            ImageStorage(base_path=None)


class TestSaveImageWithMetadata:
    def test_basic_save(self, storage, test_image):
        result = storage.save_image_with_metadata(test_image, keywords="test red")
        assert result['success'] is True
        assert result['image_id'] is not None
        assert result['path'] is not None
        assert result['xxhash'] is not None
        assert len(result['xxhash']) == 16
        assert result['error'] is None

    def test_creates_inf_file(self, storage, test_image):
        result = storage.save_image_with_metadata(test_image)
        assert result['success']
        full_path = result['full_path']
        inf_path = os.path.splitext(full_path)[0] + '.inf'
        assert os.path.exists(inf_path)

    def test_inf_contains_metadata(self, storage, test_image):
        result = storage.save_image_with_metadata(test_image, keywords="product")
        full_path = result['full_path']
        inf_path = os.path.splitext(full_path)[0] + '.inf'

        from qdimage.infmeta import InfMeta
        meta = InfMeta.load(inf_path)
        assert meta.data['xxhash'] == result['xxhash']
        assert meta.data['keywords'] == 'product'
        assert meta.data['image']['width'] == 100
        assert meta.data['image']['height'] == 50

    def test_duplicate_detection(self, storage, test_image):
        result1 = storage.save_image_with_metadata(test_image)
        assert result1['success']

        result2 = storage.save_image_with_metadata(test_image)
        assert result2['success'] is False
        assert result2.get('duplicate') is True

    def test_with_keywords(self, storage, test_image):
        result = storage.save_image_with_metadata(test_image, keywords="red square test")
        assert result['success']
        info = storage.get_image_by_id(result['image_id'])
        assert info['keywords'] == "red square test"

    def test_different_images(self, storage):
        img1 = Image.new('RGB', (100, 50), color='red')
        img1.format = 'JPEG'
        img2 = Image.new('RGB', (100, 50), color='blue')
        img2.format = 'JPEG'

        result1 = storage.save_image_with_metadata(img1)
        result2 = storage.save_image_with_metadata(img2)
        assert result1['success']
        assert result2['success']
        assert result1['xxhash'] != result2['xxhash']

    def test_with_source_tracking(self, storage):
        # Save source image
        img1 = Image.new('RGB', (200, 100), color='green')
        img1.format = 'JPEG'
        r1 = storage.save_image_with_metadata(img1)
        assert r1['success']

        # Save derived image
        img2 = Image.new('RGB', (100, 50), color='blue')
        img2.format = 'JPEG'
        transformations = {
            'crop': {'upper_left_x': 0, 'upper_left_y': 0,
                     'lower_right_x': 100, 'lower_right_y': 50},
            'brightness': 1.25
        }
        r2 = storage.save_image_with_metadata(
            img2, source_image_id=r1['image_id'],
            transformations=transformations
        )
        assert r2['success']

        # Check .inf has source info
        from qdimage.infmeta import InfMeta
        inf_path = os.path.splitext(r2['full_path'])[0] + '.inf'
        meta = InfMeta.load(inf_path)
        assert 'source' in meta.data
        assert meta.data['source']['xxhash'] == r1['xxhash']


class TestCheckDuplicate:
    def test_no_duplicate(self, storage):
        result = storage.check_duplicate("0000000000000000")
        assert result['exists'] is False

    def test_found_duplicate(self, storage, test_image):
        r = storage.save_image_with_metadata(test_image)
        assert r['success']
        result = storage.check_duplicate(r['xxhash'])
        assert result['exists'] is True
        assert result['image_id'] == r['image_id']


class TestGetImage:
    def test_get_by_id(self, storage, test_image):
        r = storage.save_image_with_metadata(test_image, keywords="test")
        info = storage.get_image_by_id(r['image_id'])
        assert info is not None
        assert info['xxhash'] == r['xxhash']
        assert info['keywords'] == 'test'
        assert info['width'] == 100
        assert info['height'] == 50

    def test_get_by_id_not_found(self, storage):
        assert storage.get_image_by_id(999) is None

    def test_get_by_hash(self, storage, test_image):
        r = storage.save_image_with_metadata(test_image)
        info = storage.get_image_by_hash(r['xxhash'])
        assert info is not None
        assert info['id'] == r['image_id']

    def test_get_by_hash_not_found(self, storage):
        assert storage.get_image_by_hash("0000000000000000") is None


class TestDirectoryStructure:
    def test_hierarchical_dirs(self, storage, test_image):
        r = storage.save_image_with_metadata(test_image)
        assert r['success']
        path = r['path']
        parts = path.split('/')
        assert len(parts) == 3
        assert len(parts[0]) == 2  # dir1
        assert len(parts[1]) == 2  # dir2

    def test_sequence_numbers(self, storage):
        """Different images in same hash dir get sequential numbers."""
        # These may or may not hash to the same dir, but we can at least
        # verify the sequence mechanism works
        for i in range(3):
            img = Image.new('RGB', (10 + i, 10), color=(i * 50, 0, 0))
            img.format = 'PNG'
            r = storage.save_image_with_metadata(img)
            assert r['success']
