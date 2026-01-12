# qdflask

Flask authentication package with role-based access control.

## Overview

`qdflask` provides production-ready user authentication for Flask applications:

- User model with password hashing (Werkzeug)
- Flask-Login integration
- Role-based access control (customizable roles)
- User management interface (admin-only)
- CLI commands for user management
- Email notifications via Flask-Mail

**Version:** 0.1.0
**PyPI:** [pypi.org/project/qdflask](https://pypi.org/project/qdflask/)
**Source:** [GitHub](https://github.com/almargolis/quickdev/tree/master/qdflask)

## Installation

```bash
pip install qdflask
```

## Quick Start

```python
from flask import Flask
from qdflask import init_auth, create_admin_user
from qdflask.auth import auth_bp

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize authentication with custom roles
init_auth(app, roles=['admin', 'editor', 'viewer'])

# Register authentication blueprint
app.register_blueprint(auth_bp)

# Create admin user
with app.app_context():
    create_admin_user('admin', 'secure_password')

@app.route('/')
def index():
    return 'Home page'

if __name__ == '__main__':
    app.run(debug=True)
```

## Features

### Authentication
- Login/logout routes
- Password hashing with Werkzeug
- Flask-Login integration
- Session management

### Authorization
- Role-based access control
- `@require_role()` decorator
- Customizable role hierarchy
- Admin-only routes

### User Management
- Web interface for admins
- CRUD operations for users
- CLI commands
- Email field with verification support

### Email Notifications
- Flask-Mail integration with SMTP
- Configuration via `conf/email.yaml`
- Password via `.env` (SMTP_PW)
- Send to verified admins
- Supports Brevo, SendGrid, Gmail, Mailgun, Amazon SES

## Routes Provided

- `/auth/login` - Login page
- `/auth/logout` - Logout
- `/auth/users` - User management (admin)
- `/auth/users/add` - Add user (admin)
- `/auth/users/edit/<id>` - Edit user (admin)
- `/auth/users/delete/<id>` - Delete user (admin)

## CLI Commands

```bash
# Initialize database and create admin
python -m qdflask.cli init --app myapp:app --admin-username admin --admin-password pass

# Create user
python -m qdflask.cli create-user --app myapp:app --username john --password secret --role editor

# List users
python -m qdflask.cli list-users --app myapp:app
```

## Complete Documentation

See the [qdflask README](https://github.com/almargolis/quickdev/blob/master/qdflask/README.md) for complete documentation including:

- Email configuration (SendGrid, Gmail, etc.)
- Email verification
- Security best practices
- Template customization

## Guides

- **[Quick Start](../howto/quickstart.md#flask-integration)** - Get started
- **[Flask Integration](../guides/flask-integration.md)** - Detailed guide

## Next Steps

- **[Quick Start](../howto/quickstart.md#flask-integration)** - Try qdflask
- **[Secrets Management](../howto/secrets.md)** - Secure your credentials
