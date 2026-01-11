# qdimages

Flask image management package with hierarchical storage.

## Overview

`qdimages` provides comprehensive image management for Flask applications:

- Content-addressed storage (xxHash-based, hierarchical)
- 16 API endpoints for image operations
- Web-based image editor (crop, resize, brightness, background removal)
- Image metadata with keywords and EXIF data
- Automatic deduplication
- Thumbnail generation

**Version:** 0.1.0
**PyPI:** [pypi.org/project/qdimages](https://pypi.org/project/qdimages/)
**Source:** [GitHub](https://github.com/almargolis/quickdev/tree/master/qdimages)

## Installation

```bash
pip install qdimages
```

## Quick Start

```python
from flask import Flask
from qdimages import init_image_manager
from qdimages.routes import images_bp

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'

# Initialize image manager
init_image_manager(app, storage_path='./images')

# Register blueprint
app.register_blueprint(images_bp)

if __name__ == '__main__':
    app.run(debug=True)
```

## Features

### Content-Addressed Storage
- xxHash-based file naming
- Hierarchical directory structure (4-level)
- Automatic deduplication
- Efficient storage and retrieval

### Image Editor
- Web-based interface
- Crop, resize, rotate
- Brightness, contrast, saturation
- Background removal (rembg)

### Metadata Management
- Image titles and descriptions
- Keywords/tags
- EXIF data extraction
- Search and filtering

### API Endpoints
16 RESTful endpoints for:
- Upload and download
- Editing and transformation
- Metadata management
- Search and discovery

## Storage Structure

```
images/
├── aa/
│   └── bb/
│       └── cc/
│           └── dd/
│               └── aabbccdd1234567890abcdef12345678.jpg
```

Files are stored in a 4-level hierarchy based on xxHash for efficient filesystem performance.

## Web Interface

Access the image editor at `/images/` (if blueprint registered).

Features:
- Upload images
- Browse gallery
- Edit images
- Manage metadata
- Search by keywords

## API Endpoints

- `POST /images/upload` - Upload image
- `GET /images/<hash>` - Get image
- `POST /images/<hash>/crop` - Crop image
- `POST /images/<hash>/resize` - Resize image
- `POST /images/<hash>/remove-bg` - Remove background
- And 11 more...

## Complete Documentation

See the [qdimages README](https://github.com/almargolis/quickdev/blob/master/qdimages/README.md) for complete documentation including:

- API endpoint reference
- Configuration options
- Storage architecture details
- Editor customization

## Guides

- **[Quick Start](../howto/quickstart.md#flask-integration)** - Get started
- **[Flask Integration](../guides/flask-integration.md)** - Detailed guide

## Next Steps

- **[Quick Start](../howto/quickstart.md#flask-integration)** - Try qdimages
- **[Configuration](../howto/configuration.md)** - Configure image storage
