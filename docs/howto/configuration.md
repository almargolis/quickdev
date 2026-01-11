# Configuration Files

Structure your QuickDev application with `site.yaml` configuration.

## Overview

QuickDev separates **secrets** from **configuration**:

- **Secrets** (`.env`) - Sensitive credentials, never committed
- **Configuration** (`site.yaml`) - Application structure, safe to commit

This guide covers `site.yaml` - the declarative configuration for your site.

## Basic site.yaml

```yaml
# conf/site.yaml
site_name: mysite
acronym: mysite
description: My QuickDev application

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
```

## Full Example

```yaml
# conf/site.yaml
site_name: mysite
acronym: mysite
description: A QuickDev-powered content management system
version: 1.0.0

# Database configuration (non-sensitive)
database:
  name: mysite_db
  type: postgresql
  # Password comes from .env: DATABASE_PASSWORD

# Features
features:
  - authentication
  - image_upload
  - comments
  - email_notifications

# Authentication configuration
auth:
  roles:
    - admin
    - editor
    - author
    - viewer
  allow_registration: false
  require_email_verification: true

# Image management
images:
  storage_path: /var/www/mysite/images
  max_file_size: 10485760  # 10MB
  allowed_extensions:
    - jpg
    - jpeg
    - png
    - gif
    - webp
  generate_thumbnails: true
  thumbnail_sizes:
    - [150, 150]
    - [300, 300]
    - [800, 600]

# Comments
comments:
  require_login: true
  moderation_enabled: true
  max_length: 5000

# Apache/deployment
apache:
  server_name: mysite.example.com
  server_alias: www.mysite.example.com
  document_root: /var/www/mysite
  wsgi_script: /var/www/mysite/app.wsgi
  ssl_enabled: true
  require_https: true

# Logging
logging:
  level: INFO
  file: logs/mysite.log
```

## Configuration Sections

### Site Metadata

```yaml
site_name: mysite
acronym: mysite  # Short identifier
description: Brief description of your site
version: 1.0.0
```

### Features

Enable/disable major features:

```yaml
features:
  - authentication  # qdflask
  - image_upload    # qdimages
  - comments        # qdcomments
  - email_notifications
  - api_access
```

### Authentication (qdflask)

```yaml
auth:
  roles:
    - admin
    - manager
    - staff
  allow_registration: false
  require_email_verification: true
  password_reset_enabled: true
  session_timeout_minutes: 30
```

### Images (qdimages)

```yaml
images:
  storage_path: /var/www/mysite/images
  max_file_size: 10485760  # bytes
  allowed_extensions: [jpg, png, gif]
  generate_thumbnails: true
  thumbnail_sizes:
    - [150, 150]
    - [300, 300]
```

### Comments (qdcomments)

```yaml
comments:
  require_login: true
  moderation_enabled: true
  max_length: 5000
  allow_markdown: true
  email_notifications: true
```

### Database

```yaml
database:
  name: mysite_db
  type: postgresql  # or sqlite, mysql
  host: localhost
  port: 5432
  # Credentials come from .env:
  # DATABASE_USER, DATABASE_PASSWORD
```

### Apache

```yaml
apache:
  server_name: mysite.example.com
  server_alias: www.mysite.example.com
  document_root: /var/www/mysite
  wsgi_script: app.wsgi
  python_home: mysite.venv
  ssl_enabled: true
  ssl_certificate: /etc/letsencrypt/live/mysite.example.com/fullchain.pem
  ssl_certificate_key: /etc/letsencrypt/live/mysite.example.com/privkey.pem
```

## Loading Configuration

### In Your Application

```python
# app.py
import yaml
from pathlib import Path

# Load site configuration
config_path = Path(__file__).parent / 'conf' / 'site.yaml'
with open(config_path) as f:
    site_config = yaml.safe_load(f)

# Use configuration
app.config['SITE_NAME'] = site_config['site_name']
roles = site_config['auth']['roles']
max_upload_size = site_config['images']['max_file_size']
```

### With QuickDev Utilities

```python
from qdcore import qdsite

# QuickDev's built-in site config loader
site = qdsite.load_site('/var/www/mysite')
print(site.config['site_name'])
print(site.config['features'])
```

## Best Practices

### 1. Version Control

✅ **Commit site.yaml** - It's safe and documents your configuration

```bash
git add conf/site.yaml
git commit -m "Update site configuration"
```

### 2. Environment-Specific Values

Use environment variables for values that change:

```yaml
# site.yaml
database:
  host: localhost  # Development
  # Production will override with env var

# .env (production)
DATABASE_HOST=prod-db.example.com
```

### 3. Documentation

Add comments explaining complex configuration:

```yaml
# site.yaml
images:
  # Maximum upload size in bytes (10MB)
  # Increase if users need larger images
  max_file_size: 10485760

  # Thumbnail sizes for responsive images
  # Format: [width, height] in pixels
  thumbnail_sizes:
    - [150, 150]  # Small thumbnails
    - [800, 600]  # Medium previews
```

### 4. Validation

Validate configuration on startup:

```python
# app.py
def validate_config(config):
    required_keys = ['site_name', 'features', 'roles']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config: {key}")

validate_config(site_config)
```

## Migration from site.conf

### Old Format (site.conf - INI)

```ini
# conf/site.conf
[site]
qdsite_dpath = /var/www/mysite
acronym = mysite

[database]
name = mysite_db
```

### New Format (site.yaml)

```yaml
# conf/site.yaml
site_name: mysite
acronym: mysite

database:
  name: mysite_db
```

### Migration Script

```python
import configparser
import yaml

# Read old INI format
config = configparser.ConfigParser()
config.read('conf/site.conf')

# Convert to YAML
site_yaml = {
    'site_name': config.get('site', 'acronym'),
    'acronym': config.get('site', 'acronym'),
    'qdsite_dpath': config.get('site', 'qdsite_dpath'),
}

if 'database' in config:
    site_yaml['database'] = {
        'name': config.get('database', 'name'),
    }

# Write YAML
with open('conf/site.yaml', 'w') as f:
    yaml.dump(site_yaml, f, default_flow_style=False)
```

## Troubleshooting

### "FileNotFoundError: site.yaml"

Ensure file exists:

```bash
ls -la conf/site.yaml
```

Create if missing:

```bash
cat > conf/site.yaml << EOF
site_name: mysite
acronym: mysite
EOF
```

### "YAML Parse Error"

Validate YAML syntax:

```bash
python -c "import yaml; yaml.safe_load(open('conf/site.yaml'))"
```

Or use online validator: [yamllint.com](http://www.yamllint.com/)

### "KeyError" When Loading

Add error handling:

```python
config = yaml.safe_load(open('conf/site.yaml'))
site_name = config.get('site_name', 'default')
features = config.get('features', [])
```

## Next Steps

- **[Secrets Management](secrets.md)** - Managing credentials with .env
- **[Apache Configuration](apache-config.md)** - Using site.yaml for Apache
- **[Deployment](deployment.md)** - Deploying with configuration

## Reference

- **[Site Configuration Reference](../reference/site-config.md)** - Complete configuration options
- **[YAML Specification](https://yaml.org/spec/1.2/spec.html)** - YAML syntax reference
