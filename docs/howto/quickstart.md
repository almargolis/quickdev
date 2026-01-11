# Quick Start

Get QuickDev running in 5 minutes.

## Choose Your Path

=== "Flask Integration (Recommended)"

    Install and use QuickDev's Flask packages - perfect for adding auth, images, and comments to your Flask app.

    ```bash
    # Install Flask packages from PyPI
    pip install qdflask qdimages qdcomments
    ```

    See [Flask Integration](#flask-integration) below.

=== "Code Generation (XSynth)"

    Use the XSynth preprocessor to generate Python from high-level declarations.

    ```bash
    # Install XSynth
    pip install xsynth
    ```

    See [XSynth Usage](#xsynth-usage) below.

=== "Full Development Setup"

    Clone the repository for QuickDev development or to use unreleased features.

    ```bash
    # Clone and install in development mode
    git clone https://github.com/almargolis/quickdev.git
    cd quickdev
    pip install -e ./qdbase -e ./xsynth
    pip install -e ./qdflask -e ./qdimages -e ./qdcomments
    ```

    See [Development Setup](#development-setup) below.

## Flask Integration

Add authentication, image management, and comments to your Flask app in minutes.

### 1. Install Packages

```bash
pip install qdflask qdimages qdcomments
```

### 2. Create Flask App

```python
# app.py
import os
from flask import Flask
from qdflask import init_auth, create_admin_user
from qdflask.auth import auth_bp
from qdimages import init_image_manager
from qdimages.routes import images_bp
from qdcomments import init_comments
from qdcomments.routes import comments_bp

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Initialize QuickDev packages
init_auth(app, roles=['admin', 'editor', 'viewer'])
init_image_manager(app, storage_path='./images')
init_comments(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(images_bp)
app.register_blueprint(comments_bp)

# Create admin user on first run
with app.app_context():
    from qdflask.models import db
    db.create_all()
    create_admin_user('admin', os.environ.get('ADMIN_PASSWORD', 'admin'))

@app.route('/')
def index():
    return 'QuickDev Flask App'

if __name__ == '__main__':
    app.run(debug=True)
```

### 3. Run the App

```bash
# Set environment variables
export SECRET_KEY="your-secret-key-here"
export ADMIN_PASSWORD="secure-password"

# Run the app
python app.py
```

### 4. Test It Out

- Visit `http://localhost:5000/`
- Login at `http://localhost:5000/auth/login` (username: `admin`, password: what you set)
- Manage users at `http://localhost:5000/auth/users`

**That's it!** You now have:

- ✅ User authentication with login/logout
- ✅ Role-based access control
- ✅ User management interface
- ✅ Image upload and management
- ✅ Commenting system

## XSynth Usage

Use XSynth to generate Python code from high-level declarations.

### 1. Install XSynth

```bash
pip install xsynth
```

### 2. Create an XSynth File

```python
# model.xpy
#$ dict User
    username: str
    email: str
    role: str = 'user'
    active: bool = True

#$ dict Product
    name: str
    price: float
    description: str = ''
    in_stock: bool = True
```

### 3. Process with XSynth

```bash
# Process .xpy files to generate .py files
python -m xsynth model.xpy
```

### 4. Generated Output

```python
# model.py (generated)
class User:
    def __init__(self, username, email, role='user', active=True):
        self.username = username
        self.email = email
        self.role = role
        self.active = active

    def to_dict(self):
        return {
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'active': self.active
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class Product:
    def __init__(self, name, price, description='', in_stock=True):
        self.name = name
        self.price = price
        self.description = description
        self.in_stock = in_stock

    def to_dict(self):
        return {
            'name': self.name,
            'price': self.price,
            'description': self.description,
            'in_stock': self.in_stock
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
```

### 5. Use Generated Code

```python
# Use the generated classes
from model import User, Product

user = User('john', 'john@example.com', role='admin')
print(user.to_dict())

product = Product('Widget', 19.99, description='A useful widget')
print(product.to_dict())
```

See the [XSynth Guide](../guides/xsynth.md) for more advanced features.

## Development Setup

Set up QuickDev for development or to use unreleased features.

### 1. Clone Repository

```bash
git clone https://github.com/almargolis/quickdev.git
cd quickdev
```

### 2. Create Virtual Environment

```bash
python3 -m venv ezdev.venv
source ezdev.venv/bin/activate
```

### 3. Install in Development Mode

```bash
# Core packages
pip install -e ./qdbase
pip install -e ./xsynth

# Flask packages
pip install -e ./qdflask
pip install -e ./qdimages
pip install -e ./qdcomments

# Development dependencies
pip install pytest pytest-cov
```

### 4. Run Tests

```bash
pytest
```

### 5. Process XSynth Files

```bash
# Generate .py files from .xpy files
python qdutils/xsynth.py
```

## Next Steps

### Learn More

- **[Site Setup](site-setup.md)** - Create a full QuickDev site with `qdstart`
- **[Flask Integration Guide](../guides/flask-integration.md)** - Detailed Flask integration
- **[XSynth Guide](../guides/xsynth.md)** - Advanced XSynth features
- **[Site Structure](../guides/site-structure.md)** - Understanding QuickDev sites

### Explore Packages

- **[qdflask](../packages/qdflask.md)** - Authentication and user management
- **[qdimages](../packages/qdimages.md)** - Image management and editor
- **[qdcomments](../packages/qdcomments.md)** - Commenting system

### Configure Your Environment

- **[Secrets Management](secrets.md)** - Using `.env` files for credentials
- **[Configuration](configuration.md)** - Using `site.yaml` for app structure
- **[Apache Setup](apache-config.md)** - Deploying with Apache

## Common Issues

### Import Errors

If you see `ModuleNotFoundError`, ensure packages are installed:

```bash
pip install qdflask qdimages qdcomments
```

For development mode:

```bash
pip install -e ./qdflask -e ./qdimages -e ./qdcomments
```

### Database Errors

If you see database errors, ensure tables are created:

```python
with app.app_context():
    from qdflask.models import db
    db.create_all()
```

### SECRET_KEY Errors

Flask requires a `SECRET_KEY` for sessions. Set it in your environment:

```bash
export SECRET_KEY="your-secret-key-here"
```

Or in your `.env` file:

```bash
SECRET_KEY=your-secret-key-here
```

See [Secrets Management](secrets.md) for best practices.

## Getting Help

- **Documentation:** [quickdev.readthedocs.io](https://quickdev.readthedocs.io) (coming soon)
- **Issues:** [GitHub Issues](https://github.com/almargolis/quickdev/issues)
- **Examples:** Check the `examples/` directory in the repository

## What You've Learned

✅ How to install QuickDev packages from PyPI
✅ How to add authentication to Flask apps with qdflask
✅ How to use XSynth for code generation
✅ How to set up a development environment
✅ Where to find more documentation

Ready to dive deeper? Check out the [Site Setup guide](site-setup.md) or explore the [Flask Integration guide](../guides/flask-integration.md).
