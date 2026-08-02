"""
.inf metadata sidecar files for images.

TOML syntax with .inf extension. Sidecar file alongside each image
(e.g., 3.jpg has 3.inf).

Read with tomllib (Python 3.11+ stdlib).
Written with qdos.write_toml().
"""

import io
import os
import re
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ExifTags import TAGS

from qdbase import qdos
from qdimage.hasher import calculate_xxhash


def _model_short_name(model: str) -> str:
    """
    Derive a short name from an LLM model identifier.

    claude-sonnet-4-20250514 -> claude
    gpt-4o-2024-05-13 -> gpt4o
    """
    if not model:
        return "llm"
    lower = model.lower()
    if lower.startswith("claude"):
        return "claude"
    if lower.startswith("gpt-4o"):
        return "gpt4o"
    if lower.startswith("gpt-4"):
        return "gpt4"
    if lower.startswith("gpt-"):
        return "gpt"
    # Use first word before any hyphen or period
    match = re.match(r'([a-z0-9]+)', lower)
    return match.group(1) if match else "llm"


def _description_key(source: str, model: str = None, dt: datetime = None) -> str:
    """
    Generate a unique description key.

    Manual: manual_YYYYMMDD
    LLM: <model_short>_YYYYMMDD_HHMMSS
    """
    if dt is None:
        dt = datetime.now()
    if source == "manual":
        return f"manual_{dt.strftime('%Y%m%d')}"
    short = _model_short_name(model or "")
    return f"{short}_{dt.strftime('%Y%m%d_%H%M%S')}"


def _extract_exif(image: Image.Image) -> Optional[dict]:
    """Extract EXIF data from PIL Image as a dict of string values."""
    try:
        exif_data = image.getexif()
        if not exif_data:
            return None

        exif_dict = {}
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, f"Unknown_{tag_id}")

            if isinstance(value, bytes):
                try:
                    value = value.decode('utf-8', errors='ignore')
                except Exception:
                    value = str(value)

            if not isinstance(value, (str, int, float)):
                value = str(value)

            exif_dict[tag_name] = str(value)

        return exif_dict if exif_dict else None
    except Exception:
        return None


class InfMeta:
    """
    Read/write .inf metadata sidecar files.

    The .inf file uses TOML syntax and lives alongside each image file.
    """

    def __init__(self, inf_path: str, data: dict = None):
        """
        Initialize InfMeta.

        Args:
            inf_path: Path to the .inf file
            data: Pre-loaded data dict (if None, starts empty)
        """
        self.inf_path = inf_path
        self.data = data or {}

    @classmethod
    def from_image_path(cls, image_path: str) -> 'InfMeta':
        """
        Create InfMeta from an image file.

        Reads the image to extract dimensions, format, EXIF, and calculates
        the xxhash. If a .inf file already exists, loads it and merges.

        Args:
            image_path: Path to the image file

        Returns:
            InfMeta instance with image metadata populated
        """
        image_path = str(image_path)
        inf_path = str(Path(image_path).with_suffix('.inf'))

        # Calculate hash from raw file bytes
        with open(image_path, 'rb') as f:
            raw_bytes = f.read()
        xxhash_val = calculate_xxhash(raw_bytes)

        # Open image for metadata
        image = Image.open(image_path)
        image.load()

        data = {}

        # Load existing .inf if present
        if os.path.exists(inf_path):
            with open(inf_path, 'rb') as f:
                data = tomllib.load(f)

        # Set/update core fields
        data['xxhash'] = xxhash_val
        data['file_size'] = len(raw_bytes)

        # Image section
        img_format = image.format or Path(image_path).suffix.lstrip('.').upper()
        if img_format == 'JPG':
            img_format = 'JPEG'
        data['image'] = {
            'width': image.width,
            'height': image.height,
            'format': img_format,
        }

        # EXIF section
        exif = _extract_exif(image)
        if exif:
            data['exif'] = exif

        # Preserve existing keywords and descriptions
        if 'keywords' not in data:
            data['keywords'] = ''

        return cls(inf_path, data)

    @classmethod
    def create_new(cls, inf_path: str, xxhash: str, file_size: int,
                   width: int, height: int, image_format: str,
                   keywords: str = '', exif: dict = None) -> 'InfMeta':
        """
        Create a new InfMeta with explicit values (no image file needed).

        Args:
            inf_path: Path where .inf file will be saved
            xxhash: xxHash64 hex string
            file_size: File size in bytes
            width: Image width in pixels
            height: Image height in pixels
            image_format: Image format string (JPEG, PNG, etc.)
            keywords: Space-delimited keywords
            exif: Optional EXIF dict

        Returns:
            InfMeta instance
        """
        data = {
            'xxhash': xxhash,
            'file_size': file_size,
            'keywords': keywords,
            'image': {
                'width': width,
                'height': height,
                'format': image_format,
            },
        }
        if exif:
            data['exif'] = exif
        return cls(inf_path, data)

    @classmethod
    def load(cls, inf_path: str) -> 'InfMeta':
        """
        Load an existing .inf file.

        Args:
            inf_path: Path to the .inf file

        Returns:
            InfMeta instance

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        with open(inf_path, 'rb') as f:
            data = tomllib.load(f)
        return cls(inf_path, data)

    def save(self):
        """Write the .inf file to disk."""
        qdos.write_toml(self.inf_path, self.data)

    def add_description(self, text: str, source: str = "manual",
                        model: str = None, date: datetime = None,
                        key: str = None):
        """
        Add a description section.

        Args:
            text: Description text
            source: "manual" or "llm"
            model: LLM model identifier (required if source="llm")
            date: Datetime of description (default: now)
            key: Override the auto-generated key
        """
        if date is None:
            date = datetime.now()
        if key is None:
            key = _description_key(source, model, date)

        if 'description' not in self.data:
            self.data['description'] = {}

        desc = {
            'source': source,
            'date': date.strftime('%Y-%m-%dT%H:%M:%S'),
            'text': text,
        }
        if source == 'llm' and model:
            desc['model'] = model

        self.data['description'][key] = desc

    def get_descriptions(self) -> dict:
        """
        Get all description sections.

        Returns:
            Dict of {key: {source, date, text, model?}}
        """
        return self.data.get('description', {})

    def set_source(self, xxhash: str, file_id: str,
                   crop: dict = None, adjustments: dict = None):
        """
        Set source tracking for a derived image.

        Args:
            xxhash: xxHash of the source image
            file_id: Filename of the source image
            crop: Crop coordinates dict
            adjustments: Adjustments dict (brightness, background_removed, etc.)
        """
        source = {
            'xxhash': xxhash,
            'file_id': file_id,
        }
        if crop:
            source['crop'] = crop
        if adjustments:
            source['adjustments'] = adjustments
        self.data['source'] = source
