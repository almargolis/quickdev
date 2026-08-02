"""
Hierarchical xxHash-based image storage system.

Provides content-addressed image storage with:
- xxHash64-based directory hierarchy (dir1/dir2/sequence.ext)
- Global duplicate detection via hash comparison
- .inf metadata sidecars with source tracking for edited images
- EXIF extraction and storage
- Transaction-safe sequence numbering

Uses QdSqlite (from qdbase) for database operations.

Usage:
    storage = ImageStorage(base_path='/path/to/images', db_path='/path/to/images.db')
    result = storage.save_image_with_metadata(
        image=PIL_image,
        keywords='ebay product electronics',
        source_image_id=123,
        transformations={'crop': {...}, 'brightness': 1.25},
        user_id=1
    )
"""

import io
import json
from pathlib import Path
from PIL import Image
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

from qdbase import pdict
from qdbase.qdsqlite import QdSqlite

from qdimage.hasher import calculate_xxhash
from qdimage.infmeta import InfMeta


def _build_db_dict():
    """Build the pdict schema for image storage."""
    db_dict = pdict.DbDictDb()

    # images table
    images = db_dict.add_table(pdict.DbDictTable("images"))
    images.add_column(pdict.Text("xxhash", is_unique=True))
    images.add_column(pdict.Text("dir1"))
    images.add_column(pdict.Text("dir2"))
    images.add_column(pdict.Number("sequence_num"))
    images.add_column(pdict.Text("filename"))
    images.add_column(pdict.Text("format", allow_nulls=True))
    images.add_column(pdict.Number("width", allow_nulls=True))
    images.add_column(pdict.Number("height", allow_nulls=True))
    images.add_column(pdict.Number("file_size", allow_nulls=True))
    images.add_column(pdict.Text("keywords", allow_nulls=True, default_value=''))
    images.add_column(pdict.Number("has_exif", allow_nulls=True, default_value=0))
    images.add_column(pdict.TimeStamp("created_at",
        default_value=pdict.ColumnName("CURRENT_TIMESTAMP"),
        is_read_only=True))
    images.add_column(pdict.Number("created_by_user_id", allow_nulls=True))
    images.add_index("idx_images_xxhash", column_names="xxhash")

    # directory_sequence table
    dir_seq = db_dict.add_table(pdict.DbDictTable("directory_sequence"))
    dir_seq.add_column(pdict.Text("dir1"))
    dir_seq.add_column(pdict.Text("dir2"))
    dir_seq.add_column(pdict.Number("next_sequence", default_value=1))
    dir_seq.add_index("idx_dir_seq", column_names=["dir1", "dir2"])

    # image_exif table
    exif_table = db_dict.add_table(pdict.DbDictTable("image_exif"))
    exif_table.add_column(pdict.Number("image_id",
        foreign_key=pdict.ForeignKey(images.columns["id"])))
    exif_table.add_column(pdict.Text("tag_name"))
    exif_table.add_column(pdict.Text("tag_value", allow_nulls=True))

    # source_tracking table
    source_table = db_dict.add_table(pdict.DbDictTable("source_tracking"))
    source_table.add_column(pdict.Number("image_id",
        foreign_key=pdict.ForeignKey(images.columns["id"])))
    source_table.add_column(pdict.Number("source_image_id",
        foreign_key=pdict.ForeignKey(images.columns["id"])))
    source_table.add_column(pdict.Text("transformations", allow_nulls=True))

    return db_dict


class ImageStorage:
    """Manages hierarchical xxHash-based image storage with metadata."""

    def __init__(self, base_path: str = None, db_path: str = None):
        """
        Initialize ImageStorage.

        Args:
            base_path: Root directory for image storage
            db_path: Path to SQLite database
        """
        if base_path is None:
            raise ValueError("base_path is required")
        self.base_path = Path(base_path).resolve()

        if db_path is None:
            self.db_path = self.base_path / 'images.db'
        else:
            self.db_path = Path(db_path).resolve()

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Initialize database via QdSqlite
        db_dict = _build_db_dict()
        self.db = QdSqlite(
            str(self.db_path), db_dict=db_dict,
            update_schema=True, foreign_keys=False
        )

    def get_directory_path(self, xxhash_val: str) -> Tuple[str, str, Path]:
        """
        Extract directory structure from xxHash.

        Args:
            xxhash_val: 16-character xxHash64 hex string

        Returns:
            (dir1, dir2, full_path)
        """
        if len(xxhash_val) < 4:
            raise ValueError(f"xxHash too short: {xxhash_val}")

        dir1 = xxhash_val[0:2]
        dir2 = xxhash_val[2:4]
        full_path = self.base_path / dir1 / dir2

        return dir1, dir2, full_path

    def get_next_sequence(self, dir1: str, dir2: str) -> int:
        """
        Get next sequence number for directory.

        Args:
            dir1: First directory level
            dir2: Second directory level

        Returns:
            Next sequence number (1-based)
        """
        row = self.db.lookup("directory_sequence",
                             where={"dir1": dir1, "dir2": dir2})
        if row:
            sequence = row["next_sequence"]
            self.db.update("directory_sequence",
                          {"next_sequence": sequence + 1},
                          where={"dir1": dir1, "dir2": dir2})
        else:
            sequence = 1
            self.db.insert("directory_sequence",
                          {"dir1": dir1, "dir2": dir2, "next_sequence": 2})
        self.db.commit()
        return sequence

    def check_duplicate(self, xxhash_val: str) -> Dict[str, Any]:
        """
        Check if image already exists in database.

        Args:
            xxhash_val: xxHash64 of image

        Returns:
            {'exists': bool, 'image_id': int|None, 'path': str|None}
        """
        row = self.db.lookup("images", where={"xxhash": xxhash_val})
        if row:
            path = f"{row['dir1']}/{row['dir2']}/{row['filename']}"
            return {
                'exists': True,
                'image_id': row['id'],
                'path': path,
            }
        return {'exists': False, 'image_id': None, 'path': None}

    def extract_exif(self, image: Image.Image) -> Optional[Dict[str, str]]:
        """
        Extract EXIF data from PIL Image.

        Args:
            image: PIL Image object

        Returns:
            Dictionary of {tag_name: tag_value} or None if no EXIF
        """
        from PIL.ExifTags import TAGS
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

    def save_image_with_metadata(
        self,
        image: Image.Image,
        keywords: str = '',
        source_image_id: Optional[int] = None,
        transformations: Optional[Dict] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: hash, check duplicate, save image, save .inf, save DB.

        Args:
            image: PIL Image object to save
            keywords: Space-delimited keyword tokens
            source_image_id: If this is an edited image, ID of source
            transformations: Edit operations applied (crop, brightness, etc.)
            user_id: User who created/uploaded the image

        Returns:
            {
                'success': bool,
                'image_id': int,
                'path': str,
                'xxhash': str,
                'error': str
            }
        """
        try:
            # Convert image to bytes for hashing
            img_bytes_io = io.BytesIO()
            image_format = image.format or 'JPEG'
            image.save(img_bytes_io, format=image_format)
            image_data = img_bytes_io.getvalue()

            # Calculate hash
            xxhash_val = calculate_xxhash(image_data)

            # Check for duplicates
            dup_check = self.check_duplicate(xxhash_val)
            if dup_check['exists']:
                return {
                    'success': False,
                    'error': f"Duplicate image found: {dup_check['path']}",
                    'duplicate': True,
                    'existing_image_id': dup_check['image_id'],
                    'existing_path': dup_check['path']
                }

            # Get directory structure
            dir1, dir2, dir_path = self.get_directory_path(xxhash_val)

            # Get next sequence number
            sequence = self.get_next_sequence(dir1, dir2)

            # Determine file extension from format
            format_lower = image_format.lower()
            if format_lower == 'jpeg':
                ext = 'jpg'
            else:
                ext = format_lower

            filename = f"{sequence}.{ext}"

            # Create directory if needed
            dir_path.mkdir(parents=True, exist_ok=True)

            # Save image file
            file_path = dir_path / filename
            image.save(str(file_path), format=image_format)

            # Extract EXIF
            exif_data = self.extract_exif(image)
            has_exif = 1 if exif_data else 0

            # Insert into database
            image_id = self.db.insert("images", {
                "xxhash": xxhash_val,
                "dir1": dir1,
                "dir2": dir2,
                "sequence_num": sequence,
                "filename": filename,
                "format": image_format,
                "width": image.width,
                "height": image.height,
                "file_size": len(image_data),
                "keywords": keywords,
                "has_exif": has_exif,
                "created_by_user_id": user_id,
            })

            # Save EXIF to database if present
            if exif_data:
                for tag_name, tag_value in exif_data.items():
                    self.db.insert("image_exif", {
                        "image_id": image_id,
                        "tag_name": tag_name,
                        "tag_value": tag_value,
                    })

            # Save source tracking if this is an edited image
            if source_image_id and transformations:
                self.db.insert("source_tracking", {
                    "image_id": image_id,
                    "source_image_id": source_image_id,
                    "transformations": json.dumps(transformations),
                })

            self.db.commit()

            # Generate and save .inf metadata
            self._save_inf_metadata(image_id, str(file_path.with_suffix('.inf')))

            return {
                'success': True,
                'image_id': image_id,
                'path': f"{dir1}/{dir2}/{filename}",
                'full_path': str(file_path),
                'xxhash': xxhash_val,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'image_id': None,
                'path': None
            }

    def _build_inf_data(self, image_id: int) -> dict:
        """
        Build .inf data dictionary from database records.

        Args:
            image_id: Database ID of image

        Returns:
            Dictionary for InfMeta
        """
        row = self.db.require("images", where={"id": image_id})

        data = {
            'xxhash': row['xxhash'],
            'file_size': row['file_size'],
            'keywords': row['keywords'] or '',
            'image': {
                'width': row['width'],
                'height': row['height'],
                'format': row['format'],
            },
        }

        # Add EXIF if present
        if row['has_exif']:
            exif_rows = self.db.select("image_exif",
                                        where={"image_id": image_id})
            if exif_rows:
                data['exif'] = {r['tag_name']: r['tag_value'] for r in exif_rows}

        # Add source tracking if this is an edited image
        source_row = self.db.lookup("source_tracking",
                                     where={"image_id": image_id})
        if source_row:
            source_id = source_row['source_image_id']
            transformations = json.loads(source_row['transformations'])

            source_hash_row = self.db.lookup("images", where={"id": source_id})

            source_data = {
                'xxhash': source_hash_row['xxhash'] if source_hash_row else None,
                'file_id': source_hash_row['filename'] if source_hash_row else None,
            }

            # Separate crop and adjustments from transformations
            if 'crop' in transformations:
                source_data['crop'] = transformations.pop('crop')
            remaining = {k: v for k, v in transformations.items()
                        if k != 'file_id'}
            if remaining:
                source_data['adjustments'] = remaining

            data['source'] = source_data

        return data

    def _save_inf_metadata(self, image_id: int, inf_path: str):
        """
        Save .inf metadata file alongside image.

        Args:
            image_id: Database ID of image
            inf_path: Path where .inf file should be saved
        """
        data = self._build_inf_data(image_id)
        meta = InfMeta(inf_path, data)
        meta.save()

    def get_image_by_id(self, image_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve image record from database.

        Args:
            image_id: Database ID of image

        Returns:
            Dictionary with image info or None if not found
        """
        row = self.db.lookup("images", where={"id": image_id})
        if not row:
            return None

        return {
            'id': row['id'],
            'xxhash': row['xxhash'],
            'dir1': row['dir1'],
            'dir2': row['dir2'],
            'sequence_num': row['sequence_num'],
            'filename': row['filename'],
            'format': row['format'],
            'width': row['width'],
            'height': row['height'],
            'file_size': row['file_size'],
            'keywords': row['keywords'],
            'has_exif': row['has_exif'],
            'created_at': row['created_at'],
            'created_by_user_id': row['created_by_user_id'],
            'path': f"{row['dir1']}/{row['dir2']}/{row['filename']}"
        }

    def get_image_by_hash(self, xxhash_val: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve image record by xxHash.

        Args:
            xxhash_val: xxHash64 of image

        Returns:
            Dictionary with image info or None if not found
        """
        row = self.db.lookup("images", where={"xxhash": xxhash_val})
        if not row:
            return None
        return self.get_image_by_id(row['id'])
