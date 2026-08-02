"""
xxHash calculation for content-addressed image storage.
"""

import xxhash


def calculate_xxhash(image_data: bytes) -> str:
    """
    Calculate xxHash64 for image data.

    Args:
        image_data: Raw image bytes

    Returns:
        16-character hex string
    """
    return xxhash.xxh64(image_data).hexdigest()
