# qdimage — Developer Documentation

## Overview

qdimage is the core image processing library for QuickDev. It provides framework-independent image editing, content-addressed storage, metadata management, and LLM-based image description. It can be used from CLI tools, scripts, or web applications (qdimages provides the Flask wrapper).

## Modules

### editor.py — Image Editing

Stateless image editing operations using PIL. All methods are `@staticmethod` on the `ImageEditor` class.

```python
from qdimage.editor import ImageEditor

ImageEditor.crop_image(image, (left, top, right, bottom))
ImageEditor.adjust_brilliance(image, brightness=1.2, contrast=1.1)
ImageEditor.remove_background(image)      # requires rembg
ImageEditor.resize_for_preview(image, max_dimension=1200)
ImageEditor.resize(image, width=800)       # height calculated proportionally
ImageEditor.auto_orient(image)             # fix EXIF rotation
```

### fileops.py — File I/O

Image file operations: load, save, list, validate paths.

```python
from qdimage.fileops import ImageFileHandler

handler = ImageFileHandler(default_directory="/path/to/images")
image = handler.load_image("/path/to/photo.jpg")
output = handler.save_image(image, "/path/to/photo.jpg", suffix="_edited")
files = handler.list_images("/path/to/images")
```

### hasher.py — xxHash Calculation

Content hashing for deduplication.

```python
from qdimage.hasher import calculate_xxhash

hash_value = calculate_xxhash(image_bytes)  # returns 16-char hex string
```

### infmeta.py — .inf Metadata

Read and write `.inf` sidecar files. See `.inf File Format` section below.

```python
from qdimage.infmeta import InfMeta

# Create from an image file (reads image dimensions, calculates hash)
meta = InfMeta.from_image_path("/path/to/3.jpg")

# Load existing .inf file
meta = InfMeta.load("/path/to/3.inf")

# Add a description
meta.add_description(
    text="Blue widget on white background",
    source="manual"
)

# Add LLM description
meta.add_description(
    text="A blue plastic widget with rounded edges...",
    source="llm",
    model="claude-sonnet-4-20250514"
)

# Save
meta.save()

# Access data
descriptions = meta.get_descriptions()
print(meta.data['xxhash'])
print(meta.data['image']['width'])
```

### storage.py — Content-Addressed Storage

Hierarchical storage with xxHash-based directory layout and SQLite tracking.

```python
from qdimage.storage import ImageStorage

storage = ImageStorage(base_path="/path/to/images", db_path="/path/to/images.db")

result = storage.save_image_with_metadata(
    image=pil_image,
    keywords="ebay product electronics",
    source_image_id=123,
    transformations={'crop': {'upper_left_x': 100, ...}, 'brightness': 1.25}
)
# result: {'success': True, 'image_id': 42, 'path': 'ab/cd/1.jpg', ...}

dup = storage.check_duplicate("a1b2c3d4e5f67890")
info = storage.get_image_by_id(42)
info = storage.get_image_by_hash("a1b2c3d4e5f67890")
```

Directory layout: `base_path/XX/YY/N.ext` where XX = first 2 hex chars of xxhash, YY = next 2, N = sequence number.

### llmproviders.py — LLM Providers

Provider-based system for image description via LLMs.

```python
from qdimage.llmproviders import get_provider, register_provider

# Get a built-in provider
provider = get_provider("anthropic", api_key="sk-ant-...", model="claude-sonnet-4-20250514")
provider = get_provider("openai", api_key="sk-...", model="gpt-4o")

# Each call creates an independent instance (different API keys supported)
claude = get_provider("anthropic", api_key="key1")
gpt = get_provider("openai", api_key="key2")

# Register a custom provider
from qdimage.llmproviders import LLMProvider

class MyProvider(LLMProvider):
    def describe_image(self, image_data, media_type, prompt=None):
        ...
        return "description text"

register_provider("my_llm", MyProvider)
```

### llmdescribe.py — Image Description

High-level function that reads an image file, sends it to an LLM, and stores the result in the .inf sidecar.

```python
from qdimage.llmproviders import get_provider
from qdimage.llmdescribe import describe_image

provider = get_provider("anthropic", api_key="sk-ant-...")
result = describe_image(
    image_path="/path/to/3.jpg",
    provider=provider,
    prompt="Describe this product image for an e-commerce listing.",
    save_to_inf=True    # writes description to 3.inf
)
# result: {'text': '...', 'model': 'claude-sonnet-4-20250514', 'date': '...', 'source': 'llm'}
```

## .inf File Format

TOML syntax with `.inf` extension. Sidecar file alongside each image (e.g., `3.jpg` has `3.inf`).

Read with `tomllib` (Python 3.11+ stdlib). Written with `qdos.write_toml()`.

### Example

```toml
xxhash = "a1b2c3d4e5f67890"
file_size = 245760
keywords = "ebay product electronics blue widget"

[image]
width = 1920
height = 1080
format = "JPEG"

[exif]
Make = "Canon"
Model = "EOS R5"
DateTime = "2024:01:15 14:30:00"

[source]
xxhash = "9876543210fedcba"
file_id = "3.jpg"

[source.crop]
upper_left_x = 100
upper_left_y = 200
lower_right_x = 800
lower_right_y = 600

[source.adjustments]
brightness = 1.25
background_removed = true

[description.manual_20240115]
source = "manual"
date = "2024-01-15T14:30:00"
text = "Product photo of blue widget on white background"

[description.claude_20240115_150000]
source = "llm"
model = "claude-sonnet-4-20250514"
date = "2024-01-15T15:00:00"
text = "A blue plastic widget with rounded edges sitting on a white surface."

[description.gpt4o_20240116_090000]
source = "llm"
model = "gpt-4o-2024-05-13"
date = "2024-01-16T09:00:00"
text = "This image shows a blue consumer electronics widget..."
```

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `xxhash` | string | xxHash64 hex digest (16 chars) |
| `file_size` | integer | File size in bytes |
| `keywords` | string | Space-delimited keyword tokens |

### [image] Section

| Field | Type | Description |
|-------|------|-------------|
| `width` | integer | Image width in pixels |
| `height` | integer | Image height in pixels |
| `format` | string | Image format (JPEG, PNG, etc.) |

### [exif] Section

Optional. Contains EXIF tag names as keys with string values. Only present if the image has EXIF data.

### [source] Section

Optional. Present when this image was derived from another image (crop, edit, etc.).

| Field | Type | Description |
|-------|------|-------------|
| `xxhash` | string | xxHash of the source image |
| `file_id` | string | Filename of the source image |

Sub-tables `[source.crop]` and `[source.adjustments]` record the transformations applied.

### [description.*] Sections

Multiple description sections are supported. Each key encodes `<source>_<YYYYMMDD>` or `<source>_<YYYYMMDD_HHMMSS>` for uniqueness and chronological ordering.

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | `"manual"` or `"llm"` |
| `date` | string | ISO 8601 datetime |
| `model` | string | LLM model identifier (only for `source="llm"`) |
| `text` | string | The description text |

### Key Generation for Descriptions

Description keys are generated automatically:
- Manual: `manual_YYYYMMDD` (e.g., `manual_20240115`)
- LLM: `<model_short>_YYYYMMDD_HHMMSS` (e.g., `claude_20240115_150000`)

The model short name is derived from the model identifier:
- `claude-sonnet-4-20250514` → `claude`
- `gpt-4o-2024-05-13` → `gpt4o`
- Other models use the first word before any hyphen or period
