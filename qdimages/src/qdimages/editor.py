"""
Core image editing operations
Pure functions that work with PIL Image objects
"""

from PIL import Image, ImageEnhance, ImageOps
from typing import Tuple, Optional
import io


class ImageEditor:
    """Stateless image editing operations"""

    @staticmethod
    def crop_image(image: Image.Image, coords: Tuple[int, int, int, int]) -> Image.Image:
        """
        Crop image to specified rectangle

        Args:
            image: PIL Image object
            coords: (left, top, right, bottom) in pixels

        Returns:
            Cropped PIL Image

        Example:
            crop_image(img, (100, 100, 500, 500))
        """
        # Ensure coordinates are integers
        left, top, right, bottom = [int(c) for c in coords]

        # Validate coordinates are within image bounds
        width, height = image.size
        left = max(0, min(left, width))
        top = max(0, min(top, height))
        right = max(0, min(right, width))
        bottom = max(0, min(bottom, height))

        # Ensure right > left and bottom > top
        if right <= left or bottom <= top:
            raise ValueError("Invalid crop coordinates: right must be > left and bottom must be > top")

        return image.crop((left, top, right, bottom))

    @staticmethod
    def adjust_brilliance(image: Image.Image, brightness: float = 1.0,
                         contrast: float = 1.0) -> Image.Image:
        """
        Adjust brightness and contrast

        Args:
            image: PIL Image object
            brightness: 0.5 (darker) to 2.0 (brighter), 1.0 = no change
            contrast: 0.5 (less) to 2.0 (more), 1.0 = no change

        Returns:
            Adjusted PIL Image

        Example:
            adjust_brilliance(img, brightness=1.2, contrast=1.1)
        """
        # Apply brightness adjustment
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(brightness)

        # Apply contrast adjustment
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(contrast)

        return image

    @staticmethod
    def remove_background(image: Image.Image) -> Image.Image:
        """
        Remove background using rembg (AI-based)

        Args:
            image: PIL Image object

        Returns:
            PNG Image with transparent background

        Note:
            First run will download ~176MB AI model to ~/.u2net
            Processing takes 10-30 seconds depending on image size
        """
        try:
            from rembg import remove
        except ImportError:
            raise ImportError(
                "rembg is not installed. Install with: pip install rembg"
            )

        # rembg.remove() can work with PIL Image objects directly
        try:
            # Convert image to RGB if needed (rembg handles RGB best)
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGB')

            # Remove background
            output = remove(image)

            # Ensure output is RGBA for transparency
            if output.mode != 'RGBA':
                output = output.convert('RGBA')

            return output

        except Exception as e:
            raise RuntimeError(f"Background removal failed: {str(e)}")

    @staticmethod
    def resize_for_preview(image: Image.Image, max_dimension: int = 1200) -> Image.Image:
        """
        Resize large images for web display while maintaining aspect ratio

        Args:
            image: PIL Image object
            max_dimension: Maximum width or height

        Returns:
            Resized PIL Image (or original if already small enough)

        Example:
            resize_for_preview(img, max_dimension=1200)
        """
        width, height = image.size

        # If image is already small enough, return as-is
        if max(width, height) <= max_dimension:
            return image

        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))

        # Use high-quality LANCZOS resampling
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    @staticmethod
    def resize(image: Image.Image, width: Optional[int] = None,
               height: Optional[int] = None, maintain_aspect: bool = True) -> Image.Image:
        """
        Resize image to specified dimensions

        Args:
            image: PIL Image object
            width: Target width in pixels (None to calculate from height)
            height: Target height in pixels (None to calculate from width)
            maintain_aspect: If True and only one dimension specified, calculate the other proportionally

        Returns:
            Resized PIL Image

        Raises:
            ValueError: If neither width nor height is specified

        Examples:
            resize(img, width=800, height=600)  # Resize to exact dimensions
            resize(img, width=800)              # Resize width, calculate height proportionally
            resize(img, height=600)             # Resize height, calculate width proportionally
        """
        if width is None and height is None:
            raise ValueError("At least one of width or height must be specified")

        original_width, original_height = image.size
        aspect_ratio = original_width / original_height

        # Calculate missing dimension if only one is provided
        if width is None:
            # Calculate width from height
            width = int(height * aspect_ratio)
        elif height is None:
            # Calculate height from width
            height = int(width / aspect_ratio)

        # Resize using high-quality LANCZOS resampling
        return image.resize((width, height), Image.Resampling.LANCZOS)

    @staticmethod
    def auto_orient(image: Image.Image) -> Image.Image:
        """
        Auto-rotate image based on EXIF orientation data

        Args:
            image: PIL Image object

        Returns:
            Correctly oriented PIL Image

        Note:
            Useful for images from phones/cameras that may have EXIF orientation tags
        """
        try:
            # ImageOps.exif_transpose handles EXIF orientation
            return ImageOps.exif_transpose(image)
        except Exception:
            # If EXIF processing fails, return original
            return image
