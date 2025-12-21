# Flask Integration Example

This example demonstrates how QuickDev idioms integrate with Flask to eliminate boilerplate code.

## The Power of Idioms

Traditional Flask app with auth + image management: **~500+ lines of code**
- User model, forms, routes, password hashing, sessions
- Image model, upload handling, storage, editing, metadata
- Database migrations, CLI commands, error handling

**With QuickDev idioms: 2 lines of code**

```python
from qdflask import init_auth
init_auth(app, db)

from qdimages import init_image_manager
init_image_manager(app, db, storage_path='./image_storage')
```

## What You Get

### qdflask Authentication Idiom

✓ User model with email, password_hash, roles
✓ Login/logout routes and templates
✓ Role-based access control decorators
✓ Password hashing (Werkzeug)
✓ Session management (Flask-Login)
✓ CLI commands: `flask user create`, `flask user add-role`

### qdimages Image Management Idiom

✓ 16 RESTful API endpoints
✓ Content-addressed storage (xxHash-based)
✓ Automatic deduplication
✓ Web-based image editor interface
✓ Image operations: crop, resize, brightness, background removal
✓ Metadata and keyword tracking
✓ EXIF data extraction

## Running the Example

```bash
# Install dependencies (when packages are ready)
pip install -e ../../qdflask
pip install -e ../../qdimages

# Uncomment the init_auth and init_image_manager lines in app.py

# Run the app
python app.py

# Try the CLI
flask user create admin@example.com --password admin123
flask user add-role admin@example.com admin
```

## The Point

QuickDev doesn't replace Flask - it enhances it. You still write Flask routes, templates, and application logic. QuickDev just generates the boring, repetitive parts you'd otherwise copy-paste from project to project.

## Philosophy

Each QuickDev idiom encapsulates:
- A common pattern (auth, image management, etc.)
- Decades of refinement
- Best practices baked in
- Readable, standard Python output

Use the idioms you need, skip the ones you don't. It's code generation, not magic.
