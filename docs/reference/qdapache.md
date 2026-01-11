# qdapache Reference

Apache configuration generator for QuickDev sites.

!!! note "Coming Soon"
    Complete qdapache documentation.

## Overview

`qdapache` reads your QuickDev site configuration and generates Apache virtual host configs.

## Basic Usage

```bash
# Generate Apache config
python -m qdutils.qdapache /var/www/mysite

# Outputs:
# - /etc/apache2/sites-available/mysite.conf
# - /var/www/mysite/app.wsgi
```

## Configuration

Define Apache settings in `conf/site.yaml`:

```yaml
apache:
  server_name: mysite.example.com
  server_alias: www.mysite.example.com
  document_root: /var/www/mysite
  wsgi_script: app.wsgi
  python_home: mysite.venv
  ssl_enabled: true
```

## See Also

- **[Apache Configuration Guide](../howto/apache-config.md)** - Complete guide
- **[Deployment Guide](../howto/deployment.md)** - Deploying with Apache
