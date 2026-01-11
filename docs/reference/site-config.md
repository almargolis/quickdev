# Site Configuration Reference

Complete reference for `site.yaml` configuration files.

!!! note "Coming Soon"
    Complete site.yaml schema documentation.

## Overview

`site.yaml` defines your QuickDev site structure and behavior.

## Basic Example

```yaml
site_name: mysite
acronym: mysite
description: My QuickDev application

features:
  - authentication
  - image_upload
  - comments

auth:
  roles:
    - admin
    - editor
    - viewer

apache:
  server_name: mysite.example.com
  ssl_enabled: true
```

## Configuration Sections

### Site Metadata

- `site_name` - Full site name
- `acronym` - Short identifier
- `description` - Brief description
- `version` - Application version

### Features

List of enabled features:

- `authentication` - Enable qdflask
- `image_upload` - Enable qdimages
- `comments` - Enable qdcomments

### Authentication (qdflask)

- `roles` - List of user roles
- `allow_registration` - Enable self-registration
- `require_email_verification` - Email verification required

### Images (qdimages)

- `storage_path` - Image storage directory
- `max_file_size` - Maximum upload size (bytes)
- `allowed_extensions` - Allowed file types

### Comments (qdcomments)

- `require_login` - Login required to comment
- `moderation_enabled` - Comment moderation
- `max_length` - Maximum comment length

### Apache

- `server_name` - Primary domain
- `server_alias` - Additional domains
- `ssl_enabled` - Enable SSL/HTTPS
- `ssl_certificate` - SSL certificate path
- `ssl_certificate_key` - SSL key path

## See Also

- **[Configuration Guide](../howto/configuration.md)** - Using site.yaml
- **[Secrets Management](../howto/secrets.md)** - Using .env for secrets
