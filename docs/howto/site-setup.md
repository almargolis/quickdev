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
|   |__ email.yaml        # email configuration, except PW
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

**Answers to have ready:**

1. Acronym: a two or three letter acronym that will be used in various places to help distinguish between similar looking sites and applications.

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
SMTP_PW=SG.xyz...
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

Each site has its own virtual environment. You can create and manage it separately 
but qdstart and other quickdev components will handle it for you. When you need
to activate the venv,

```bash
# Activate virtual environment
cd /<site directory> # usually like /var/www/<site>/
source venv

# Note that the environment reference in the CLI prompt includes the site
# acronym to help you keep track of which site you have enabled.
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

## Scripted Site Creation

For repeatable site creation, write a shell script that calls `qdstart`
with `-r` (repository directories) and `-a` (answer files). This
eliminates interactive prompts and documents exactly how the site is
built.

### Repo directories (`-r`)

The `-r` flag tells qdstart where to find installable packages. Each
`-r` path is scanned for Python packages (directories containing
`__init__.py` with a `setup.py`).

Use the `e::` prefix for editable installs (`pip install -e`), which is
typical for development. Without the prefix, packages are installed
normally, which is typical for production.

```bash
-r e::/path/to/quickdev       # editable (development)
-r /path/to/quickdev           # normal (production)
```

### Answer files (`-a`)

QuickDev packages can declare configuration questions in `qd_conf.yaml`
files. For example, qdflask, qdimages, and qdcomments each declare an
`enabled` question. Packages whose enabled answer is `false` are not
installed.

An answer file is a YAML file that supplies answers to these questions
so qdstart can run non-interactively:

```yaml
# mk_mysite.yaml - answers for non-interactive setup
qdimages:
  enabled: false
```

Application repos can also supply answers. For example, an application
that requires qdflask can include a `qd_conf.yaml` in its package
directory:

```yaml
# myapp/qd_conf.yaml
answers:
  qdflask:
    enabled: true
```

This ensures qdflask is installed whenever the application repo is
scanned, without requiring a separate answer file.

### Example: development site script

This script creates a site from scratch, using quickdev and an
application repo (trellis shown as an example):

```bash
#!/bin/bash
# mk_mysite.sh - create a development site
rm -fr /path/to/sites/mysite
source /path/to/quickdev/qd.venv/bin/activate
python3 /path/to/quickdev/qdutils/src/qdutils/qdstart.py \
    -s /path/to/sites/mysite \
    -a /path/to/mk_mysite.yaml \
    -r e::/path/to/quickdev \
    -r e::/path/to/myapp
```

With a companion answer file:

```yaml
# mk_mysite.yaml
qdimages:
  enabled: false
```

**What happens when this runs:**

1. Answer file loaded — `qdimages.enabled` set to `false`
2. Repos scanned — quickdev and myapp packages discovered; any
   `qd_conf.yaml` answers (e.g., `qdflask.enabled: true`) collected
3. `conf/` directory created
4. Active venv detected and used (no prompt)
5. Enabled questions processed — qdflask and qdcomments enabled (from
   myapp's answers), qdimages disabled (from the answer file)
6. Enabled packages installed in editable mode (due to `e::` prefix)
7. `repos.db` and site config saved

### Example: production site

For production, omit the `e::` prefix so packages install normally,
and activate (or let qdstart create) the site's own venv:

```bash
#!/bin/bash
python3 /path/to/quickdev/qdutils/src/qdutils/qdstart.py \
    -s /var/www/mysite \
    -a /path/to/answers.yaml \
    -r /path/to/quickdev \
    -r /path/to/myapp
```

### How `qd_conf.yaml` files work

Packages declare questions and/or answers in a `qd_conf.yaml` file
placed in their package directory (next to `__init__.py`). The file
has two optional top-level sections:

```yaml
# questions section — prompts the installer
questions:
  mypackage:
    enabled:
      help: "Enable mypackage?"
      type: boolean

# answers section — supplies answers automatically
answers:
  some_dependency:
    enabled: true
```

Questions ending in `.enabled` are processed first. If answered `false`,
the package is skipped and all its other questions are suppressed.

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
