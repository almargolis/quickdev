"""
File I/O operations for images.
Separates file handling from image processing for modularity.
"""

from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image
import os
from datetime import datetime


class ImageFileHandler:
    """Manages image file operations"""

    def __init__(self, default_directory: str = None):
        """
        Initialize ImageFileHandler

        Args:
            default_directory: Default path for file browser
        """
        self.default_directory = default_directory or "/commercenode/test_images"

    @staticmethod
    def load_image(filepath: str) -> Image.Image:
        """
        Load image from disk

        Args:
            filepath: Path to image file

        Returns:
            PIL Image object

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file can't be opened as image
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Image file not found: {filepath}")

        try:
            image = Image.open(filepath)
            # Load the image data
            image.load()
            return image
        except Exception as e:
            raise IOError(f"Failed to load image {filepath}: {str(e)}")

    @staticmethod
    def save_image(image: Image.Image, original_path: str,
                   suffix: str = "_new") -> str:
        """
        Save image with modified filename

        Args:
            image: PIL Image to save
            original_path: Original file path
            suffix: String to append before extension (default: "_new")

        Returns:
            Path to saved file

        Example:
            "/path/image.jpg" -> "/path/image_new.jpg"
        """
        output_path = ImageFileHandler.generate_output_filename(original_path, suffix)

        # If image has transparency (RGBA), save as PNG regardless of original format
        if image.mode in ('RGBA', 'LA', 'PA'):
            # Change extension to .png
            output_path = str(Path(output_path).with_suffix('.png'))
            image.save(output_path, 'PNG')
        else:
            # Determine format from extension
            ext = Path(output_path).suffix.lower()
            if ext == '.jpg' or ext == '.jpeg':
                # Convert to RGB if needed (removes any alpha channel)
                if image.mode in ('RGBA', 'LA', 'PA'):
                    # Create white background
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = rgb_image
                image.save(output_path, 'JPEG', quality=95)
            elif ext == '.png':
                image.save(output_path, 'PNG')
            elif ext == '.gif':
                image.save(output_path, 'GIF')
            else:
                # Default to PNG for unknown extensions
                image.save(output_path, 'PNG')

        return output_path

    def list_images(self, directory: str = None) -> List[Dict[str, str]]:
        """
        List images in directory

        Args:
            directory: Directory to list (uses default if None)

        Returns:
            List of dicts with {name, path, size, modified}
        """
        if directory is None:
            directory = self.default_directory

        if not os.path.exists(directory):
            return []

        images = []
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif'}

        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)

                # Skip directories
                if os.path.isdir(filepath):
                    continue

                # Check extension
                ext = Path(filename).suffix.lower()
                if ext not in valid_extensions:
                    continue

                # Get file stats
                stat = os.stat(filepath)
                size_kb = stat.st_size / 1024
                if size_kb < 1024:
                    size_str = f"{size_kb:.1f} KB"
                else:
                    size_str = f"{size_kb/1024:.1f} MB"

                modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')

                images.append({
                    'name': filename,
                    'path': filepath,
                    'size': size_str,
                    'modified': modified
                })

            # Sort by modification time (newest first)
            images.sort(key=lambda x: x['modified'], reverse=True)

        except Exception as e:
            print(f"Error listing images in {directory}: {str(e)}")
            return []

        return images

    @staticmethod
    def validate_path(filepath: str, allowed_base: str) -> bool:
        """
        Security: Ensure path is within allowed directory
        Prevents path traversal attacks

        Args:
            filepath: Path to validate
            allowed_base: Base directory that path must be within

        Returns:
            True if path is valid and within allowed_base
        """
        try:
            # Resolve to absolute paths
            real_path = os.path.realpath(filepath)
            real_base = os.path.realpath(allowed_base)

            # Check if path starts with base directory
            return real_path.startswith(real_base)
        except Exception:
            return False

    @staticmethod
    def generate_output_filename(original_path: str, suffix: str = "_new") -> str:
        """
        Generate output filename with suffix before extension

        Args:
            original_path: Original file path
            suffix: Suffix to add before extension

        Returns:
            New filepath with suffix

        Example:
            "/path/image.jpg", "_new" -> "/path/image_new.jpg"
            "/path/photo.jpeg", "_edited" -> "/path/photo_edited.jpeg"
        """
        path = Path(original_path)
        stem = path.stem  # filename without extension
        ext = path.suffix  # extension including dot
        parent = path.parent

        new_filename = f"{stem}{suffix}{ext}"
        return str(parent / new_filename)
