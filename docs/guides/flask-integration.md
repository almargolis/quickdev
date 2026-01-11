# Flask Integration

Comprehensive guide to integrating QuickDev packages with Flask applications.

!!! note "Coming Soon"
    Detailed guide covering all Flask integration patterns. For now, see the [Quick Start](../howto/quickstart.md) and individual package documentation.

## Overview

QuickDev provides three Flask packages:

- **qdflask** - Authentication with role-based access control
- **qdimages** - Image management with hierarchical storage
- **qdcomments** - Commenting system with moderation

## Basic Integration

```python
from flask import Flask
from qdflask import init_auth
from qdimages import init_image_manager
from qdcomments import init_comments

app = Flask(__name__)

# Initialize packages
init_auth(app, roles=['admin', 'editor', 'viewer'])
init_image_manager(app, storage_path='./images')
init_comments(app)
```

## Package Documentation

- **[qdflask Package](../packages/qdflask.md)** - Complete qdflask documentation
- **[qdimages Package](../packages/qdimages.md)** - Complete qdimages documentation
- **[qdcomments Package](../packages/qdcomments.md)** - Complete qdcomments documentation

## Quick Start

See [Flask Integration Quick Start](../howto/quickstart.md#flask-integration) for a working example.
