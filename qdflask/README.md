# qdflask - QuickDev Flask Authentication

A reusable Flask authentication package that provides user login, role-based access control, and user management. Designed to be easily integrated into any Flask application.

## Features

- User authentication with Flask-Login
- Role-based access control with customizable roles
- Password hashing with Werkzeug
- User management interface (admin only)
- CLI commands for user management
- Easy integration into existing Flask apps

## Installation

The package is part of the QuickDev framework. To use it in your Flask application:

```python
import sys
sys.path.append('/path/to/QuickDev')
```

## Quick Start

### 1. Basic Setup

```python
from flask import Flask
from qdflask import init_auth, create_admin_user
from qdflask.auth import auth_bp

app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize authentication with custom roles
init_auth(app, roles=['admin', 'manager', 'staff', 'customer'])

# Register authentication blueprint
app.register_blueprint(auth_bp)

# Create admin user on first run
with app.app_context():
    create_admin_user('admin', 'secure_password')

@app.route('/')
def index():
    return "Home page"

if __name__ == '__main__':
    app.run(debug=True)
```

### 2. Protecting Routes

```python
from flask_login import login_required, current_user
from qdflask import require_role

@app.route('/dashboard')
@login_required
def dashboard():
    return f"Welcome {current_user.username}!"

@app.route('/admin')
@login_required
@require_role('admin')
def admin_panel():
    return "Admin panel"

@app.route('/edit')
@login_required
@require_role('admin', 'manager')
def edit_content():
    return "Edit content (admin or manager)"
```

### 3. Using the User Model

```python
from qdflask.models import User, db

# Get user by username
user = User.get_by_username('john')

# Check password
if user and user.check_password('password123'):
    print("Valid credentials")

# Check role
if user.is_admin():
    print("User is admin")

if user.has_role('admin', 'manager'):
    print("User can manage content")

# Create new user
new_user = User(username='jane', role='editor')
new_user.set_password('secret123')
db.session.add(new_user)
db.session.commit()
```

## CLI Commands

### Initialize Database and Create Admin User

```bash
python -m qdflask.cli init --app myapp:app --admin-username admin --admin-password secure_pass
```

### Create Additional Users

```bash
python -m qdflask.cli create-user --app myapp:app --username john --password secret --role editor
```

### List All Users

```bash
python -m qdflask.cli list-users --app myapp:app
```

## Routes Provided

The `auth_bp` blueprint provides the following routes:

- `/auth/login` - Login page (GET) and login processing (POST)
- `/auth/logout` - Logout (requires login)
- `/auth/users` - User management page (admin only)
- `/auth/users/add` - Add new user (admin only)
- `/auth/users/edit/<id>` - Edit user (admin only)
- `/auth/users/delete/<id>` - Delete user (admin only)

## Configuration

### Required Configuration

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Required for sessions
```

### Optional Configuration

```python
# Custom roles (must include 'admin')
init_auth(app, roles=['admin', 'editor', 'viewer'])

# Custom login view
init_auth(app, login_view='custom_auth.login')
```

## Role Management

Every application must have an 'admin' role. Additional roles can be specified when initializing:

```python
# E-commerce roles
init_auth(app, roles=['admin', 'manager', 'staff', 'customer'])

# CMS roles
init_auth(app, roles=['admin', 'editor', 'author', 'viewer'])

# Simple roles
init_auth(app, roles=['admin', 'user'])
```

## Email Notifications

qdflask includes email notification support via Flask-Mail, allowing you to send transactional emails to users or admins.

### SMTP Configuration

Configure email in your `.env` file or application config:

#### SendGrid (Recommended)
```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

**SendGrid Setup:**
1. Sign up at https://sendgrid.com (free tier: 100 emails/day)
2. Go to Settings → API Keys → Create API Key
3. Select "Full Access" and create
4. Copy the API key and use it as `MAIL_PASSWORD`

#### Gmail
```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

**Gmail Setup:**
1. Enable 2-factor authentication on your Google account
2. Go to Google Account → Security → App Passwords
3. Generate an app password for "Mail"
4. Use that app password (not your regular password)

**Note:** Gmail has a daily limit of ~500 emails and may not be suitable for production.

#### Mailgun
```bash
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=postmaster@your-domain.mailgun.org
MAIL_PASSWORD=your-mailgun-password
```

#### Amazon SES
```bash
MAIL_SERVER=email-smtp.us-east-1.amazonaws.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-ses-username
MAIL_PASSWORD=your-ses-password
```

### Using Email in Your Application

```python
from flask import Flask
from qdflask import init_auth
from qdflask.email import init_mail, send_to_admins, send_email

app = Flask(__name__)

# Configure email
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = os.environ.get('SENDGRID_API_KEY')
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@example.com'

# Initialize auth and email
init_auth(app)
init_mail(app)

# Send email to verified admins
send_to_admins(
    subject="Important Alert",
    body="Something happened that requires your attention."
)

# Send email to specific recipients
send_email(
    subject="Welcome",
    recipients=["user@example.com"],
    body="Welcome to our application!"
)
```

### Email Verification

Users have an `email_verified` field ('Y' or 'N') that controls whether they receive routine notifications:

- Only users with `email_verified='Y'` receive routine emails
- Admins can set this field when editing users
- Users can have a blank `email_address` to prevent all emails
- Use `User.get_verified_admins()` to get admins who should receive notifications

### Best Practices

1. **Use environment variables** for sensitive credentials (API keys, passwords)
2. **Start with SendGrid** for its free tier and reliability
3. **Only send to verified emails** for routine notifications
4. **Add unsubscribe links** for user-facing emails (account confirmations, password resets)
5. **Rate limit registration emails** to prevent spam
6. **Test email configuration** before deploying to production
7. **Monitor your email quota** to avoid hitting provider limits

## Security Notes

- Passwords are hashed using Werkzeug's `generate_password_hash()`
- Never store plain text passwords
- Change default admin password immediately after first login
- Use a strong `SECRET_KEY` in production
- Consider using environment variables for sensitive configuration

## Templates

The package includes styled templates for:
- Login page
- User management page
- Add user page
- Edit user page

Templates are located in `qdflask/templates/qdflask/` and can be customized by copying them to your application's template directory.

## Example: Complete Application

See `../commercenode/cnflask/app.py` for a complete example of integrating qdflask into a Flask application.
