# qdimage

Core image processing library for QuickDev. Framework-independent — can be
used from CLI tools, scripts, or web applications.

## Features

- **Image editing** — Crop, resize, brightness/contrast, background removal
- **Content-addressed storage** — xxHash-based deduplication and hierarchical directory layout
- **Metadata sidecars** — `.inf` files (TOML syntax) alongside each image
- **LLM description** — Pass images to Anthropic or OpenAI models for automated description
- **EXIF extraction** — Extract and store camera metadata

## Installation

```bash
pip install qdimage

# With LLM support
pip install qdimage[llm]

# With background removal
pip install qdimage[rembg]
```

## Quick Start

```python
from qdimage.editor import ImageEditor
from qdimage.fileops import ImageFileHandler
from qdimage.storage import ImageStorage

# Load and edit an image
handler = ImageFileHandler()
image = handler.load_image("photo.jpg")
image = ImageEditor.crop_image(image, (100, 100, 800, 600))
image = ImageEditor.adjust_brilliance(image, brightness=1.2)

# Save to content-addressed storage
storage = ImageStorage(base_path="./images", db_path="./images/images.db")
result = storage.save_image_with_metadata(image, keywords="product photo")

# Describe with LLM
from qdimage.llmproviders import get_provider
from qdimage.llmdescribe import describe_image

provider = get_provider("anthropic", api_key="sk-...")
desc = describe_image("./images/ab/cd/1.jpg", provider)
```

## Dependencies

- `qdbase` >= 0.3.0 (zero external deps)
- `Pillow` >= 9.0.0
- `xxhash` >= 3.0.0
- Optional: `anthropic`, `openai` (for LLM description)
- Optional: `rembg` >= 2.0.0 (for background removal)
