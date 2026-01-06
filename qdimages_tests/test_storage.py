"""
Tests for qdimages storage module.
"""

import pytest
import os
import tempfile
from PIL import Image
from flask import Flask
from qdimages import init_image_manager
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
def app(temp_storage_dir):
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    db_path = os.path.join(temp_storage_dir, 'test_images.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize qdimages with test configuration
    init_image_manager(app, {
        'IMAGES_BASE_PATH': temp_storage_dir,
        'TEMP_IMAGES_PATH': os.path.join(temp_storage_dir, 'temp'),
        'TEMP_DIRECTORY': os.path.join(temp_storage_dir, 'tmp'),
        'UPLOAD_FOLDER': os.path.join(temp_storage_dir, 'uploads'),
    })

    yield app


@pytest.fixture
def storage(app, temp_storage_dir):
    """Create an ImageStorage instance with initialized database."""
    db_path = os.path.join(temp_storage_dir, 'test_images.db')
    with app.app_context():
        storage = ImageStorage(
            base_path=temp_storage_dir,
            db_path=db_path
        )
        yield storage



def test_storage_initialization(storage, temp_storage_dir):
    """Test that ImageStorage initializes correctly."""
    # Compare resolved paths (handles /var vs /private/var on macOS)
    from pathlib import Path
    assert Path(storage.base_path).resolve() == Path(temp_storage_dir).resolve()
    assert os.path.exists(storage.base_path)


def test_compute_hash(storage, sample_image):
    """Test hash computation for images."""
    # Read image data
    with open(sample_image, 'rb') as f:
        image_data = f.read()

    hashes = storage.calculate_hashes(image_data)
    assert hashes is not None
    assert isinstance(hashes, dict)
    assert 'xxhash' in hashes
    assert 'sha1' in hashes
    assert len(hashes['xxhash']) > 0

    # Same file should produce same hash
    hashes2 = storage.calculate_hashes(image_data)
    assert hashes['xxhash'] == hashes2['xxhash']


def test_hierarchical_path_generation(storage):
    """Test that hierarchical paths are generated correctly."""
    hash_value = "a1b2c3d4e5f6"
    dir1, dir2, full_path = storage.get_directory_path(hash_value)

    # Path should contain hash prefix directories
    assert dir1 == 'a1'
    assert dir2 == 'b2'
    assert 'a1' in str(full_path)
    assert 'b2' in str(full_path)


def test_save_image(storage, sample_image):
    """Test saving an image to hierarchical storage."""
    # Load the sample image
    from PIL import Image
    img = Image.open(sample_image)

    # Save the image with metadata
    result = storage.save_image_with_metadata(
        image=img,
        keywords='test sample red',
        user_id=1
    )

    assert result['success'] is True
    assert result['image_id'] is not None
    assert result['path'] is not None
    assert result['xxhash'] is not None
    assert 'error' not in result or result['error'] is None

    # Verify the image file was created
    import os
    full_path = result['full_path']
    assert os.path.exists(full_path)

    # Verify YAML metadata was created
    yaml_path = full_path.replace('.png', '.yaml')
    assert os.path.exists(yaml_path)


def test_get_image_by_hash(storage, sample_image):
    """Test retrieving image by hash."""
    # First save an image
    from PIL import Image
    img = Image.open(sample_image)

    save_result = storage.save_image_with_metadata(
        image=img,
        keywords='test lookup',
        user_id=1
    )

    assert save_result['success'] is True
    xxhash = save_result['xxhash']

    # Now retrieve it by hash
    retrieved = storage.get_image_by_hash(xxhash)

    assert retrieved is not None
    assert retrieved['xxhash'] == xxhash
    assert retrieved['keywords'] == 'test lookup'
    assert retrieved['width'] == 100
    assert retrieved['height'] == 100

    # Verify duplicate detection works
    dup_result = storage.save_image_with_metadata(
        image=img,
        keywords='duplicate test',
        user_id=1
    )

    assert dup_result['success'] is False
    assert dup_result.get('duplicate') is True
    assert dup_result['existing_image_id'] == save_result['image_id']
