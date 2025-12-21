#!/usr/bin/env python3
"""
Hierarchical xxHash-based image storage system.

This module provides content-addressed image storage with:
- xxHash64-based directory hierarchy (dir1/dir2/sequence.ext)
- Global duplicate detection via hash comparison
- YAML metadata with source tracking for edited images
- EXIF extraction and storage
- Transaction-safe sequence numbering

Usage:
    storage = ImageStorage(base_path='/path/to/images')
    result = storage.save_image_with_metadata(
        image=PIL_image,
        keywords='ebay product electronics',
        source_image_id=123,  # If this is an edited image
        transformations={'crop': {...}, 'brightness': 1.25},
        user_id=1
    )
"""

import os
import sqlite3
import hashlib
import xxhash
import yaml
import json
import io
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
from typing import Optional, Tuple, Dict, Any


class ImageStorage:
    """Manages hierarchical xxHash-based image storage with metadata."""

    def __init__(self, base_path: str = None, db_path: str = None):
        """
        Initialize ImageStorage.

        Args:
            base_path: Root directory for image storage (default: ../images)
            db_path: Path to SQLite database (default: ../cnflask/commercenode.db)
        """
        if base_path is None:
            script_dir = Path(__file__).parent
            self.base_path = (script_dir.parent / 'images').resolve()
        else:
            self.base_path = Path(base_path).resolve()

        if db_path is None:
            script_dir = Path(__file__).parent
            self.db_path = (script_dir.parent / 'cnflask' / 'commercenode.db').resolve()
        else:
            self.db_path = Path(db_path).resolve()

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def calculate_hashes(self, image_data: bytes) -> Dict[str, str]:
        """
        Calculate xxHash64 and SHA1 for image data.

        Args:
            image_data: Raw image bytes

        Returns:
            {'xxhash': '...', 'sha1': '...'}
        """
        # xxHash64 (fast, good collision resistance)
        xx_hash = xxhash.xxh64(image_data).hexdigest()

        # SHA1 (legacy compatibility - deprecated)
        sha1_hash = hashlib.sha1(image_data).hexdigest()

        return {
            'xxhash': xx_hash,
            'sha1': sha1_hash
        }

    def get_directory_path(self, xxhash: str) -> Tuple[str, str, Path]:
        """
        Extract directory structure from xxHash.

        Args:
            xxhash: 16-character xxHash64 hex string

        Returns:
            (dir1, dir2, full_path) where:
            - dir1: First 2 chars of hash
            - dir2: Next 2 chars of hash
            - full_path: Complete directory path
        """
        if len(xxhash) < 4:
            raise ValueError(f"xxHash too short: {xxhash}")

        dir1 = xxhash[0:2]
        dir2 = xxhash[2:4]
        full_path = self.base_path / dir1 / dir2

        return dir1, dir2, full_path

    def get_next_sequence(self, dir1: str, dir2: str, conn: sqlite3.Connection = None) -> int:
        """
        Get next sequence number for directory (thread-safe).

        Args:
            dir1: First directory level
            dir2: Second directory level
            conn: Optional database connection (for transaction safety)

        Returns:
            Next sequence number (1-based)
        """
        own_conn = conn is None
        if own_conn:
            conn = sqlite3.connect(str(self.db_path))

        try:
            cursor = conn.cursor()

            # Lock the row for update (SQLite uses automatic locking)
            cursor.execute('''
                SELECT next_sequence FROM directory_sequence
                WHERE dir1 = ? AND dir2 = ?
            ''', (dir1, dir2))

            row = cursor.fetchone()

            if row:
                # Directory exists, increment sequence
                sequence = row[0]
                cursor.execute('''
                    UPDATE directory_sequence
                    SET next_sequence = next_sequence + 1
                    WHERE dir1 = ? AND dir2 = ?
                ''', (dir1, dir2))
            else:
                # New directory, start at 1
                sequence = 1
                cursor.execute('''
                    INSERT INTO directory_sequence (dir1, dir2, next_sequence)
                    VALUES (?, ?, 2)
                ''', (dir1, dir2))

            if own_conn:
                conn.commit()

            return sequence

        finally:
            if own_conn:
                conn.close()

    def check_duplicate(self, xxhash: str, sha1: str) -> Dict[str, Any]:
        """
        Check if image already exists in database.

        Args:
            xxhash: xxHash64 of image
            sha1: SHA1 of image

        Returns:
            {'exists': bool, 'image_id': int|None, 'path': str|None, 'match_type': str|None}
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Check xxHash first (primary content addressing)
            cursor.execute('''
                SELECT id, dir1, dir2, filename FROM images WHERE xxhash = ?
            ''', (xxhash,))
            row = cursor.fetchone()

            if row:
                image_id, dir1, dir2, filename = row
                path = f"{dir1}/{dir2}/{filename}"
                return {
                    'exists': True,
                    'image_id': image_id,
                    'path': path,
                    'match_type': 'xxhash'
                }

            # Check SHA1 (should match if xxHash matched, but check anyway)
            cursor.execute('''
                SELECT id, dir1, dir2, filename FROM images WHERE sha1 = ?
            ''', (sha1,))
            row = cursor.fetchone()

            if row:
                image_id, dir1, dir2, filename = row
                path = f"{dir1}/{dir2}/{filename}"
                return {
                    'exists': True,
                    'image_id': image_id,
                    'path': path,
                    'match_type': 'sha1'
                }

            return {'exists': False, 'image_id': None, 'path': None, 'match_type': None}

        finally:
            conn.close()

    def extract_exif(self, image: Image.Image) -> Optional[Dict[str, str]]:
        """
        Extract EXIF data from PIL Image.

        Args:
            image: PIL Image object

        Returns:
            Dictionary of {tag_name: tag_value} or None if no EXIF
        """
        try:
            exif_data = image.getexif()
            if not exif_data:
                return None

            exif_dict = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, f"Unknown_{tag_id}")

                # Convert bytes to string
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8', errors='ignore')
                    except:
                        value = str(value)

                # Convert other complex types to string
                if not isinstance(value, (str, int, float)):
                    value = str(value)

                exif_dict[tag_name] = str(value)

            return exif_dict if exif_dict else None

        except Exception as e:
            print(f"Warning: Failed to extract EXIF: {e}")
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
        Complete workflow: hash, check duplicate, save image, save YAML, save DB.

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
                'sha1': str,
                'error': str
            }
        """
        try:
            # Convert image to bytes for hashing
            img_bytes_io = io.BytesIO()
            image_format = image.format or 'JPEG'
            image.save(img_bytes_io, format=image_format)
            image_data = img_bytes_io.getvalue()

            # Calculate hashes
            hashes = self.calculate_hashes(image_data)
            xxhash_val = hashes['xxhash']
            sha1_val = hashes['sha1']

            # Check for duplicates
            dup_check = self.check_duplicate(xxhash_val, sha1_val)
            if dup_check['exists']:
                return {
                    'success': False,
                    'error': f"Duplicate image found (matched by {dup_check['match_type']}): {dup_check['path']}",
                    'duplicate': True,
                    'existing_image_id': dup_check['image_id'],
                    'existing_path': dup_check['path']
                }

            # Get directory structure
            dir1, dir2, dir_path = self.get_directory_path(xxhash_val)

            # Database transaction for sequence + insert
            conn = sqlite3.connect(str(self.db_path))
            try:
                # Get next sequence number
                sequence = self.get_next_sequence(dir1, dir2, conn)

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
                has_exif = exif_data is not None

                # Insert into database
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO images (
                        xxhash, sha1, dir1, dir2, sequence_num, filename,
                        format, width, height, file_size, keywords, has_exif,
                        created_by_user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    xxhash_val, sha1_val, dir1, dir2, sequence,
                    filename, image_format, image.width, image.height,
                    len(image_data), keywords, has_exif, user_id
                ))

                image_id = cursor.lastrowid

                # Save EXIF to database if present
                if exif_data:
                    for tag_name, tag_value in exif_data.items():
                        cursor.execute('''
                            INSERT INTO image_exif (image_id, tag_name, tag_value)
                            VALUES (?, ?, ?)
                        ''', (image_id, tag_name, tag_value))

                # Save source tracking if this is an edited image
                if source_image_id and transformations:
                    cursor.execute('''
                        INSERT INTO source_tracking (image_id, source_image_id, transformations)
                        VALUES (?, ?, ?)
                    ''', (image_id, source_image_id, json.dumps(transformations)))

                conn.commit()

                # Generate and save YAML metadata
                self.save_yaml_metadata(image_id, str(file_path.with_suffix('.yaml')))

                return {
                    'success': True,
                    'image_id': image_id,
                    'path': f"{dir1}/{dir2}/{filename}",
                    'full_path': str(file_path),
                    'xxhash': xxhash_val,
                    'sha1': sha1_val,
                    'error': None
                }

            except Exception as e:
                conn.rollback()
                raise

            finally:
                conn.close()

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'image_id': None,
                'path': None
            }

    def build_yaml_metadata(self, image_id: int) -> Dict[str, Any]:
        """
        Build complete YAML structure from database records.

        Args:
            image_id: Database ID of image

        Returns:
            Dictionary representing YAML structure
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Get main image record
            cursor.execute('''
                SELECT xxhash, sha1, format, width, height, keywords, has_exif
                FROM images WHERE id = ?
            ''', (image_id,))

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Image ID {image_id} not found")

            xxhash, sha1, img_format, width, height, keywords, has_exif = row

            yaml_data = {
                'xxhash': xxhash,
                'sha1': sha1,  # Deprecated but included for compatibility
                'keywords': keywords or '',
                'image': {
                    'width': width,
                    'height': height,
                    'format': img_format
                }
            }

            # Add EXIF if present
            if has_exif:
                cursor.execute('''
                    SELECT tag_name, tag_value FROM image_exif
                    WHERE image_id = ?
                ''', (image_id,))

                exif_rows = cursor.fetchall()
                if exif_rows:
                    yaml_data['exif'] = {tag_name: tag_value for tag_name, tag_value in exif_rows}

            # Add source tracking if this is an edited image
            cursor.execute('''
                SELECT source_image_id, transformations FROM source_tracking
                WHERE image_id = ?
            ''', (image_id,))

            source_row = cursor.fetchone()
            if source_row:
                source_id, transformations_json = source_row

                # Get source image hash
                cursor.execute('SELECT xxhash, filename FROM images WHERE id = ?', (source_id,))
                source_hash_row = cursor.fetchone()

                transformations = json.loads(transformations_json)

                yaml_data['source'] = {
                    'xxhash': source_hash_row[0] if source_hash_row else None,
                    'file_id': source_hash_row[1] if source_hash_row else None,
                    **transformations
                }

            return yaml_data

        finally:
            conn.close()

    def save_yaml_metadata(self, image_id: int, yaml_path: str):
        """
        Save YAML metadata file alongside image.

        Args:
            image_id: Database ID of image
            yaml_path: Path where YAML file should be saved
        """
        yaml_data = self.build_yaml_metadata(image_id)

        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def get_image_by_id(self, image_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve image record from database.

        Args:
            image_id: Database ID of image

        Returns:
            Dictionary with image info or None if not found
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT id, xxhash, sha1, dir1, dir2, sequence_num, filename,
                       format, width, height, file_size, keywords, has_exif,
                       created_at, created_by_user_id
                FROM images WHERE id = ?
            ''', (image_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'id': row[0],
                'xxhash': row[1],
                'sha1': row[2],
                'dir1': row[3],
                'dir2': row[4],
                'sequence_num': row[5],
                'filename': row[6],
                'format': row[7],
                'width': row[8],
                'height': row[9],
                'file_size': row[10],
                'keywords': row[11],
                'has_exif': row[12],
                'created_at': row[13],
                'created_by_user_id': row[14],
                'path': f"{row[3]}/{row[4]}/{row[6]}"
            }

        finally:
            conn.close()

    def get_image_by_hash(self, xxhash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve image record by xxHash.

        Args:
            xxhash: xxHash64 of image

        Returns:
            Dictionary with image info or None if not found
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT id FROM images WHERE xxhash = ?', (xxhash,))
            row = cursor.fetchone()

            if not row:
                return None

            return self.get_image_by_id(row[0])

        finally:
            conn.close()
