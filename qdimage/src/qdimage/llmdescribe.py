"""
Single-image LLM description function.

Reads an image file, sends it to an LLM provider, and optionally stores
the result in the .inf sidecar file.

Usage:
    from qdimage.llmproviders import get_provider
    from qdimage.llmdescribe import describe_image

    provider = get_provider("anthropic", api_key="sk-ant-...")
    result = describe_image("/path/to/image.jpg", provider)
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from qdimage.infmeta import InfMeta
from qdimage.llmproviders import LLMProvider


# MIME type mapping
_MEDIA_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
}


def describe_image(image_path: str, provider: LLMProvider,
                   prompt: Optional[str] = None,
                   save_to_inf: bool = True) -> dict:
    """
    Describe a single image using an LLM provider.

    Reads the image file, sends it to the LLM, and optionally stores
    the result in the .inf sidecar file.

    Args:
        image_path: Path to the image file
        provider: LLM provider instance (from get_provider)
        prompt: Custom prompt for the LLM (None for default)
        save_to_inf: If True, write description to .inf sidecar

    Returns:
        {
            'text': str,       # Description text
            'model': str,      # Model identifier
            'date': str,       # ISO datetime string
            'source': 'llm',
        }

    Raises:
        FileNotFoundError: If image file doesn't exist
    """
    image_path = str(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Determine media type
    ext = Path(image_path).suffix.lower()
    media_type = _MEDIA_TYPES.get(ext)
    if media_type is None:
        raise ValueError(f"Unsupported image format: {ext}")

    # Read image bytes
    with open(image_path, 'rb') as f:
        image_data = f.read()

    # Call LLM
    now = datetime.now()
    text = provider.describe_image(image_data, media_type, prompt)
    model = provider.model_name

    result = {
        'text': text,
        'model': model,
        'date': now.strftime('%Y-%m-%dT%H:%M:%S'),
        'source': 'llm',
    }

    # Save to .inf
    if save_to_inf:
        inf_path = str(Path(image_path).with_suffix('.inf'))
        if os.path.exists(inf_path):
            meta = InfMeta.load(inf_path)
        else:
            meta = InfMeta.from_image_path(image_path)

        meta.add_description(
            text=text,
            source='llm',
            model=model,
            date=now,
        )
        meta.save()

    return result
