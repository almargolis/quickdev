# Migration Guide: Using qdimages in CommerceNode

## Package Structure Created

```
QuickDev/qdimages/
├── __init__.py              # Package initialization, init_image_manager()
├── models.py                # Database models (Image model)
├── routes.py                # All image routes (29KB, 600+ lines)
├── storage.py               # ImageStorage class (hierarchical storage)
├── editor.py                # ImageEditor class (crop, resize, etc.)
├── file_handler.py          # ImageFileHandler class (legacy support)
├── setup.py                 # Package installation
├── README.md                # Documentation
├── templates/
│   └── image_editor.html    # Web editor interface (1452 lines)
└── static/                  # (empty, for future use)
```

## Installation

From the QuickDev directory:

```bash
cd /Users/almargolis/Projects/QuickDev
pip install -e ./qdimages
```

## Updating app.py

### Step 1: Remove old imports

**REMOVE these lines from app.py:**
```python
from image_editor import ImageEditor
from image_file_handler import ImageFileHandler
from image_storage import ImageStorage
```

### Step 2: Add qdimages import

**ADD this import:**
```python
from qdimages import init_image_manager
```

### Step 3: Remove configuration

**REMOVE these configuration lines** (they're now handled by qdimages):
```python
# Image editor configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
TEMP_DIRECTORY = os.getenv('TEMP_DIRECTORY', '/tmp/commercenode_temp')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMP_DIRECTORY'] = TEMP_DIRECTORY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create temp directory
os.makedirs(TEMP_DIRECTORY, exist_ok=True)

# Hierarchical image storage configuration
IMAGES_BASE_PATH = os.getenv('IMAGES_BASE_PATH', ...)
TEMP_IMAGES_PATH = os.getenv('TEMP_IMAGES_PATH', ...)
app.config['IMAGES_BASE_PATH'] = IMAGES_BASE_PATH
app.config['TEMP_IMAGES_PATH'] = TEMP_IMAGES_PATH
os.makedirs(IMAGES_BASE_PATH, exist_ok=True)
os.makedirs(TEMP_IMAGES_PATH, exist_ok=True)

# Image handler instance
image_handler = ImageFileHandler(...)
image_storage = ImageStorage(...)
```

### Step 4: Remove all image routes

**DELETE these entire route functions** (lines ~306-1018):
- `@app.route("/api/images/list")`
- `@app.route("/api/images/metadata")`
- `@app.route("/images/<path:filename>")`
- `@app.route("/api/images/process")`
- `@app.route("/api/images/upload")`
- `@app.route("/api/images/save")`
- `@app.route("/api/images/temp-staging/list")`
- `@app.route("/api/images/temp-staging/import")`
- `@app.route("/api/images/browse")`
- `@app.route("/api/images/search")`
- `@app.route("/api/images/metadata/update")`
- `@app.route("/image-editor")` ← The massive one!

### Step 5: Initialize qdimages

**ADD this after auth initialization:**

```python
# Initialize authentication
init_auth(app, roles=['admin', 'manager', 'staff'])
app.register_blueprint(auth_bp)

# Initialize image manager
init_image_manager(app, {
    'IMAGES_BASE_PATH': os.path.join(os.path.dirname(__file__), '../images'),
    'TEMP_IMAGES_PATH': os.path.join(os.path.dirname(__file__), '../temp_images'),
    'TEMP_DIRECTORY': '/tmp/commercenode_temp',
    'UPLOAD_FOLDER': os.path.join(os.path.dirname(__file__), 'uploads'),
    'MAX_CONTENT_LENGTH': 10 * 1024 * 1024  # 10MB
})

# Create admin user (existing code)
with app.app_context():
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
    create_admin_user('admin', admin_password)
```

## Minimal app.py Example

After migration, your app.py should look like:

```python
from flask import Flask, request, jsonify, render_template_string, session
from flask_login import login_required, current_user
import logging
import os
import sys

# Add QuickDev to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../QuickDev'))

from qdflask import init_auth, create_admin_user
from qdflask.auth import auth_bp
from qdflask.models import db
from qdimages import init_image_manager

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(os.path.dirname(__file__), 'commercenode.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize authentication
init_auth(app, roles=['admin', 'manager', 'staff'])
app.register_blueprint(auth_bp)

# Initialize image manager
init_image_manager(app, {
    'IMAGES_BASE_PATH': os.path.join(os.path.dirname(__file__), '../images'),
    'TEMP_IMAGES_PATH': os.path.join(os.path.dirname(__file__), '../temp_images')
})

# Create admin user
with app.app_context():
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
    create_admin_user('admin', admin_password)

# Your existing CommerceNode routes
@app.route("/")
def index():
    # ... existing code ...

@app.route("/ebay/marketplace-account-deletion", methods=["GET", "POST"])
def ebay_marketplace_account_deletion():
    # ... existing code ...

# etc.

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
```

## Benefits

✅ **app.py reduced** from ~2479 lines to ~300 lines
✅ **Reusable** in other Flask applications
✅ **Maintainable** - image features in separate package
✅ **Testable** - can test qdimages independently
✅ **Professional** - follows QuickDev architecture pattern

## Testing

After migration:

1. Install the package: `cd QuickDev && pip install -e ./qdimages`
2. Update app.py as described above
3. Run the app: `./run_flask.sh`
4. Visit `/image-editor` to test functionality
5. All existing features should work identically

## Troubleshooting

**Import errors:**
- Make sure QuickDev is in your Python path
- Check that qdimages is installed: `pip list | grep qdimages`

**Database errors:**
- The Image model is now in `qdimages.models.Image`
- Database migrations should work automatically

**Route conflicts:**
- Ensure all old image routes are removed from app.py
- qdimages registers its own blueprint with all routes

## Next Steps

Once working in CommerceNode, you can use qdimages in other projects:

```python
from flask import Flask
from qdimages import init_image_manager

app = Flask(__name__)
init_image_manager(app)
# Instant image management!
```
