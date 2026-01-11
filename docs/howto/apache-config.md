# Apache Configuration

Generate Apache configurations with `qdapache` for deploying QuickDev applications.

!!! note "Work in Progress"
    This guide covers the vision for `qdapache` - automated Apache configuration generation from QuickDev site metadata. Implementation details are being refined.

## Overview

`qdapache` automates Apache configuration by reading your QuickDev site structure and generating appropriate virtual host configs.

**Philosophy:** Your `site.yaml` describes your application. `qdapache` translates that into Apache configuration.

## The Vision

### Without qdapache (Manual Configuration)

```apache
# /etc/apache2/sites-available/mysite.conf
<VirtualHost *:80>
    ServerName mysite.example.com
    DocumentRoot /var/www/mysite

    WSGIDaemonProcess mysite python-home=/var/www/mysite/mysite.venv
    WSGIProcessGroup mysite
    WSGIScriptAlias / /var/www/mysite/app.wsgi

    <Directory /var/www/mysite>
        Require all granted
    </Directory>

    Alias /static /var/www/mysite/static
    <Directory /var/www/mysite/static>
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/mysite-error.log
    CustomLog ${APACHE_LOG_DIR}/mysite-access.log combined
</VirtualHost>
```

**Problems:**

- Manual configuration prone to errors
- Easy to forget security settings
- Inconsistent across sites
- Must manually update when site changes

### With qdapache (Automated)

```bash
# Generate Apache config from site.yaml
python -m qdutils.qdapache /var/www/mysite

# Outputs:
# - /etc/apache2/sites-available/mysite.conf
# - /var/www/mysite/app.wsgi
```

**Advantages:**

- Consistent configuration
- Security best practices built-in
- Single source of truth (site.yaml)
- Easy updates when site structure changes

## Site Configuration

Define your site in `conf/site.yaml`:

```yaml
# conf/site.yaml
site_name: mysite
acronym: mysite

apache:
  server_name: mysite.example.com
  server_alias: www.mysite.example.com
  document_root: /var/www/mysite
  wsgi_script: /var/www/mysite/app.wsgi
  python_home: /var/www/mysite/mysite.venv

  # Static files
  static_url: /static
  static_path: /var/www/mysite/static

  # SSL configuration
  ssl_enabled: true
  ssl_certificate: /etc/letsencrypt/live/mysite.example.com/fullchain.pem
  ssl_certificate_key: /etc/letsencrypt/live/mysite.example.com/privkey.pem

  # Logging
  error_log: ${APACHE_LOG_DIR}/mysite-error.log
  access_log: ${APACHE_LOG_DIR}/mysite-access.log

  # Security
  require_https: true
  allow_from: all
```

## Generating Configuration

```bash
# Generate Apache config
python -m qdutils.qdapache /var/www/mysite

# Review generated config
cat /etc/apache2/sites-available/mysite.conf

# Enable site
sudo a2ensite mysite
sudo systemctl reload apache2
```

## WSGI Script

`qdapache` also generates the WSGI script:

```python
# /var/www/mysite/app.wsgi (generated)
import sys
import os

# Add site directory to Python path
sys.path.insert(0, '/var/www/mysite')

# Load environment variables from conf/.env
from dotenv import load_dotenv
load_dotenv('/var/www/mysite/conf/.env')

# Import Flask application
from app import app as application
```

## SSL/HTTPS Configuration

### Let's Encrypt Integration

```yaml
# conf/site.yaml
apache:
  ssl_enabled: true
  ssl_certificate: /etc/letsencrypt/live/mysite.example.com/fullchain.pem
  ssl_certificate_key: /etc/letsencrypt/live/mysite.example.com/privkey.pem
  require_https: true
```

### Obtaining Certificates

```bash
# Install Certbot
sudo apt install certbot python3-certbot-apache

# Get certificate
sudo certbot --apache -d mysite.example.com -d www.mysite.example.com

# Regenerate Apache config
python -m qdutils.qdapache /var/www/mysite
```

## Multi-Site Configuration

Manage multiple sites on one server:

```bash
# Site 1
python -m qdutils.qdapache /var/www/site1
sudo a2ensite site1

# Site 2
python -m qdutils.qdapache /var/www/site2
sudo a2ensite site2

# Reload Apache
sudo systemctl reload apache2
```

## Advanced Configuration

### Custom Apache Directives

```yaml
# conf/site.yaml
apache:
  custom_directives:
    - "Header set X-Content-Type-Options nosniff"
    - "Header set X-Frame-Options DENY"
    - "Header set X-XSS-Protection '1; mode=block'"
```

### Virtual Environment

```yaml
apache:
  python_home: /var/www/mysite/mysite.venv
  python_path: /var/www/mysite:/var/www/mysite/lib
```

### Environment Variables

Pass secrets to WSGI application:

```yaml
apache:
  env_file: /var/www/mysite/conf/.env
```

## Troubleshooting

### "Internal Server Error"

Check Apache error log:

```bash
sudo tail -f /var/log/apache2/mysite-error.log
```

Common issues:

- Python virtual environment not found
- Import errors (missing dependencies)
- Permission issues

### "Permission Denied"

Fix ownership:

```bash
sudo chown -R www-data:www-data /var/www/mysite
sudo chmod -R 755 /var/www/mysite
```

### "Module Not Found"

Ensure virtual environment is activated in WSGI:

```python
# app.wsgi
activate_this = '/var/www/mysite/mysite.venv/bin/activate_this.py'
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})
```

## Complete Example

### 1. Create Site

```bash
python -m qdutils.qdstart /var/www/mysite --acronym mysite
cd /var/www/mysite
```

### 2. Configure site.yaml

```yaml
# conf/site.yaml
site_name: mysite
apache:
  server_name: mysite.example.com
  ssl_enabled: true
```

### 3. Install Dependencies

```bash
source venv/bin/activate
pip install qdflask qdimages
```

### 4. Create Application

```python
# app.py
import os
from flask import Flask
from qdflask import init_auth

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
init_auth(app)

@app.route('/')
def index():
    return 'Hello from MyApp'
```

### 5. Generate Apache Config

```bash
python -m qdutils.qdapache /var/www/mysite
```

### 6. Enable and Test

```bash
sudo a2ensite mysite
sudo systemctl reload apache2
curl https://mysite.example.com/
```

## Next Steps

- **[Deployment Guide](deployment.md)** - Complete deployment checklist
- **[Site Setup](site-setup.md)** - Understanding QuickDev sites
- **[Secrets Management](secrets.md)** - Secure configuration

## Reference

- **[qdapache Reference](../reference/qdapache.md)** - Complete qdapache documentation
- **[Site Configuration](../reference/site-config.md)** - site.yaml reference
