# Site Setup

Create and configure a QuickDev site with `qdstart`.

## What is a QuickDev Site?

A **QuickDev site** is a standardized directory structure for deploying Python web applications. It separates:

- **Configuration** (`conf/`) - Settings and secrets
- **Code** (symlinked or deployed separately)
- **Data** (`conf/db/`) - SQLite databases
- **Logs** (`logs/`) - Application logs
- **Virtual environment** (`{acronym}.venv/`) - Python dependencies

This structure makes deployment repeatable, backup simple, and configuration explicit.

## Quick Start

```bash
# Create a new site
python -m qdutils.qdstart /var/www/mysite --acronym mysite

# Or from within the directory
cd /var/www/mysite
python -m qdutils.qdstart --acronym mysite
```

## Site Directory Structure

After running `qdstart`, you'll have:

```
/var/www/mysite/          # Site root
├── conf/                  # Configuration directory
│   ├── .env              # Secrets (never commit!)
│   ├── site.yaml         # Site configuration
│   ├── site.conf         # Legacy INI format
│   └── db/               # SQLite databases
├── mysite.venv/          # Python virtual environment
├── static/               # Static assets (symlinked)
├── templates/            # Jinja templates (symlinked)
├── logs/                 # Application logs
└── venv                  # Symlink to mysite.venv
|__ repos                 # root of any needed 'git clone'
```

## Creating a Site

### Basic Site Creation

```bash
# Create site in /var/www/mysite
python -m qdutils.qdstart /var/www/mysite --acronym mysite
```

**What happens:**

1. Creates directory structure
2. Initializes virtual environment (`mysite.venv/`)
3. Creates configuration files in `conf/`
4. Sets up symlinks for convenience

### Site in Current Directory

```bash
# Create site in current directory
mkdir mysite && cd mysite
python -m qdutils.qdstart --acronym mysite
```

### Repair Existing Site

If your site is partially configured or broken, `qdstart` can repair it:

```bash
cd /var/www/mysite
python -m qdutils.qdstart --acronym mysite
```

**qdstart is idempotent** - safe to run multiple times.

## Configuration Files

### conf/site.yaml (Recommended)

Modern YAML-based configuration:

```yaml
# conf/site.yaml
site_name: mysite
acronym: mysite

# Database configuration
database_uri: sqlite:///conf/db/mysite.db

# Features to enable
features:
  - authentication
  - image_upload
  - comments

# User roles
roles:
  - admin
  - editor
  - viewer

# Apache configuration
apache:
  server_name: mysite.example.com
  document_root: /var/www/mysite
  wsgi_script: /var/www/mysite/app.wsgi
```

**Advantages:**

- Structured, type-safe
- Easy to parse programmatically
- Natural for nested configuration
- Safe to commit to version control

### conf/.env (Secrets)

Environment variables for sensitive data:

```bash
# conf/.env
SECRET_KEY=your-secret-key-here
DATABASE_PASSWORD=secure-password
SENDGRID_API_KEY=SG.xyz...
ADMIN_PASSWORD=admin-password

# NEVER commit this file to version control!
```

**Critical:** Add `.env` to `.gitignore`:

```gitignore
# .gitignore
conf/.env
*.db
```

See [Secrets Management](secrets.md) for details.

### conf/site.conf (Legacy)

Older INI-based format (being phased out):

```ini
# conf/site.conf
[site]
qdsite_dpath = /var/www/mysite
acronym = mysite
```

**Status:** Still supported, but migrate to `site.yaml` for new sites.

## Virtual Environment

Each site has its own virtual environment:

```bash
# Activate virtual environment
source /var/www/mysite/mysite.venv/bin/activate

# Or use the symlink
source /var/www/mysite/venv/bin/activate
```

### Installing Dependencies

```bash
source venv/bin/activate

# Install QuickDev packages
pip install qdflask qdimages qdcomments

# Install your application dependencies
pip install -r requirements.txt
```

## Site Types

QuickDev supports different site types:

### Development Site

**Purpose:** Local development and testing

**Location:** Usually `~/projects/mysite/` or similar

**Features:**

- Full development tools (pytest, flake8, etc.)
- Test/sample data
- Debug mode enabled
- May include Sphinx/MkDocs documentation

**Creation:**

```bash
cd ~/projects
python -m qdutils.qdstart mysite --acronym mysite
```

### Production Site

**Purpose:** Live application serving real users

**Location:** Usually `/var/www/mysite/`

**Features:**

- Minimal dependencies (no dev tools)
- Production data
- Debug mode disabled
- Optimized settings

**Creation:**

```bash
sudo python -m qdutils.qdstart /var/www/mysite --acronym mysite
```

### PIP Site

**Purpose:** Development site for creating PyPI packages

**Features:**

- Package structure (`setup.py`, `pyproject.toml`)
- Build tools
- PyPI upload utilities

**Status:** Specialized site type for package authors

## Workflow Example

Here's a complete workflow from site creation to deployment:

### 1. Create Development Site

```bash
cd ~/projects
python -m qdutils.qdstart mysite --acronym mysite
cd mysite
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install qdflask qdimages qdcomments
pip install flask python-dotenv
```

### 3. Configure Site

Edit `conf/site.yaml`:

```yaml
site_name: mysite
features:
  - authentication
  - image_upload
roles:
  - admin
  - editor
```

Edit `conf/.env`:

```bash
SECRET_KEY=dev-key-not-for-production
ADMIN_PASSWORD=admin
```

### 4. Create Application

```python
# app.py
import os
from flask import Flask
from qdflask import init_auth, create_admin_user
from qdflask.auth import auth_bp

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///conf/db/mysite.db'
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

init_auth(app, roles=['admin', 'editor'])
app.register_blueprint(auth_bp)

with app.app_context():
    from qdflask.models import db
    db.create_all()
    create_admin_user('admin', os.environ['ADMIN_PASSWORD'])

@app.route('/')
def index():
    return 'MyApp Home'

if __name__ == '__main__':
    app.run(debug=True)
```

### 5. Run Development Server

```bash
python app.py
```

Visit `http://localhost:5000/`

### 6. Deploy to Production

```bash
# On production server
sudo python -m qdutils.qdstart /var/www/mysite --acronym mysite
cd /var/www/mysite
source venv/bin/activate
pip install qdflask qdimages qdcomments

# Copy application code
# Configure production .env
# Generate Apache config (see Apache Configuration guide)
```

## Common Tasks

### Add a Database

SQLite databases go in `conf/db/`:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///conf/db/myapp.db'
```

### Add Static Files

Symlink or copy to `static/`:

```bash
ln -s /path/to/source/static /var/www/mysite/static
```

### Add Templates

Symlink or copy to `templates/`:

```bash
ln -s /path/to/source/templates /var/www/mysite/templates
```

### Backup Site

```bash
# Backup configuration and databases
tar czf mysite-backup.tar.gz conf/

# Restore
cd /var/www/mysite
tar xzf mysite-backup.tar.gz
```

## Troubleshooting

### "ModuleNotFoundError"

Virtual environment not activated:

```bash
source venv/bin/activate
pip install qdflask
```

### "Permission Denied"

Production sites in `/var/www/` may require sudo:

```bash
sudo python -m qdutils.qdstart /var/www/mysite --acronym mysite
sudo chown -R www-data:www-data /var/www/mysite
```

### "Database Locked"

SQLite database locked (multiple processes):

```bash
# Check for running processes
ps aux | grep python

# Consider PostgreSQL for production
```

## Next Steps

- **[Apache Configuration](apache-config.md)** - Deploy with Apache and mod_wsgi
- **[Secrets Management](secrets.md)** - Secure your credentials
- **[Configuration Files](configuration.md)** - Deep dive into site.yaml
- **[Deployment](deployment.md)** - Production deployment checklist
- **[Site Structure Guide](../guides/site-structure.md)** - Detailed site anatomy

## Reference

- **[qdstart Reference](../reference/qdstart.md)** - Complete qdstart documentation
- **[Site Configuration](../reference/site-config.md)** - Configuration file reference
