# qdcomments

Flask commenting system with moderation and content filtering.

## Overview

`qdcomments` provides a full-featured commenting system for Flask applications:

- Comment model with threading support
- Moderation system (approve/reject)
- Content filtering (blocked words from YAML)
- Email notifications to admins
- Markdown support
- CLI commands for moderation

**Version:** 0.1.0
**PyPI:** [pypi.org/project/qdcomments](https://pypi.org/project/qdcomments/)
**Source:** [GitHub](https://github.com/almargolis/quickdev/tree/master/qdcomments)

## Installation

```bash
pip install qdcomments
```

## Quick Start

```python
from flask import Flask
from qdcomments import init_comments
from qdcomments.routes import comments_bp

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'

# Initialize comments
init_comments(app)

# Register blueprint
app.register_blueprint(comments_bp)

if __name__ == '__main__':
    app.run(debug=True)
```

## Features

### Comment Management
- Create, read, update, delete comments
- Threading/replies support
- Markdown formatting
- Character limits

### Moderation
- Approve/reject comments
- Admin interface
- Email notifications
- CLI commands

### Content Filtering
- Blocked words from YAML file
- Automatic flagging
- Moderation queue

### Email Integration
- Notify admins of new comments
- Flask-Mail integration
- Configurable recipients

## Routes Provided

- `POST /comments/submit` - Submit comment
- `GET /comments/<id>` - Get comment
- `GET /comments/pending` - View pending (admin)
- `POST /comments/<id>/approve` - Approve (admin)
- `POST /comments/<id>/reject` - Reject (admin)

## CLI Commands

```bash
# List pending comments
qdcomments-pending --app myapp:app

# Approve comment
qdcomments-approve --app myapp:app --id 123

# Reject comment
qdcomments-reject --app myapp:app --id 456

# Initialize blocked words file
qdcomments-init-blocked-words
```

## Configuration

### Blocked Words

Create `data/blocked_words.yaml`:

```yaml
blocked_words:
  - spam
  - offensive_word
  - another_bad_word
```

### Email Notifications

Configure in your app:

```python
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = os.environ['SMTP_PW']
```

## Comment Model

```python
class Comment:
    id: int
    content: str
    author_id: int
    parent_id: int (optional, for threading)
    status: str ('pending', 'approved', 'rejected')
    created_at: datetime
    updated_at: datetime
```

## Complete Documentation

See the [qdcomments README](https://github.com/almargolis/quickdev/blob/master/qdcomments/README.md) for complete documentation including:

- API endpoint details
- Moderation workflows
- Email configuration
- Template customization

## Guides

- **[Quick Start](../howto/quickstart.md#flask-integration)** - Get started
- **[Flask Integration](../guides/flask-integration.md)** - Detailed guide

## Next Steps

- **[Quick Start](../howto/quickstart.md#flask-integration)** - Try qdcomments
- **[Secrets Management](../howto/secrets.md)** - Configure email
