# Secrets Management

Manage sensitive credentials securely with `.env` files and environment variables.

## The Problem

Your application needs sensitive data:

- Database passwords
- API keys (SendGrid, AWS, Stripe)
- Secret keys for sessions/JWT
- OAuth client secrets

**But these must NEVER be committed to version control.**

## QuickDev's Solution

QuickDev uses the **12-Factor App** approach: **secrets in environment variables, config in code**.

### Separation Strategy

| Type | Storage | Version Control | Example |
|------|---------|-----------------|---------|
| **Secrets** | `.env` file | ❌ Never | `SECRET_KEY=abc123...` |
| **Configuration** | `site.yaml` | ✅ Yes | `site_name: myapp` |
| **Code** | Python files | ✅ Yes | `app.py`, `models.py` |

## Using .env Files

### 1. Create conf/.env

```bash
# conf/.env
SECRET_KEY=your-long-random-secret-key-here
DATABASE_PASSWORD=secure-database-password
SMTP_PW=your-smtp-password-here
ADMIN_PASSWORD=initial-admin-password

# Optional: Development vs Production
FLASK_ENV=development
DEBUG=True
```

### 2. Add to .gitignore

**Critical:** Ensure `.env` is never committed:

```gitignore
# .gitignore
conf/.env
*.env
.env

# Also ignore SQLite databases with real data
*.db
conf/db/*.db
```

### 3. Load in Your Application

#### Using python-dotenv

```bash
pip install python-dotenv
```

```python
# app.py
import os
from dotenv import load_dotenv
from flask import Flask

# Load environment variables from conf/.env
load_dotenv('conf/.env')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://user:{os.environ['DATABASE_PASSWORD']}@localhost/mydb"
```

#### Flask Automatic Loading

Flask 2.0+ automatically loads `.env` files:

```python
# .flaskenv (development config)
FLASK_APP=app.py
FLASK_ENV=development

# conf/.env (secrets)
SECRET_KEY=your-secret-key
```

Run with:

```bash
flask run
```

## Best Practices

### 1. Never Commit Secrets

❌ **Bad:**

```python
# app.py
app.config['SECRET_KEY'] = 'abc123'  # Hard-coded!
```

✅ **Good:**

```python
# app.py
import os
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
```

### 2. Provide Defaults for Development

```python
# Development-friendly with fallback
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-unsafe-for-production')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
```

But **require secrets in production**:

```python
# Fail fast if missing in production
if not os.environ.get('SECRET_KEY'):
    raise RuntimeError("SECRET_KEY environment variable is required")
```

### 3. Use Different Secrets for Each Environment

```bash
# Development (conf/.env)
SECRET_KEY=dev-key-12345
DATABASE_URL=sqlite:///dev.db

# Production (conf/.env on server)
SECRET_KEY=prod-key-very-long-random-string-here
DATABASE_URL=postgresql://user:pass@db.example.com/prod
```

### 4. Generate Strong Secrets

```bash
# Generate a random secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Or using OpenSSL
openssl rand -hex 32
```

### 5. Document Required Variables

Create a `.env.example` file (safe to commit):

```bash
# .env.example - Template for required environment variables
SECRET_KEY=your-secret-key-here
DATABASE_PASSWORD=your-db-password-here
SMTP_PW=your-smtp-password-or-api-key

# Optional variables
DEBUG=False
LOG_LEVEL=INFO
```

Users copy and fill in:

```bash
cp .env.example conf/.env
# Edit conf/.env with real values
```

## Common Secrets

### Flask SECRET_KEY

Used for sessions, cookies, CSRF tokens:

```bash
# Generate
python -c "import secrets; print(secrets.token_hex(32))"

# conf/.env
SECRET_KEY=a1b2c3d4e5f6...
```

```python
# app.py
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
```

### Database Credentials

```bash
# conf/.env
DATABASE_URL=postgresql://username:password@localhost:5432/mydb
# Or
DATABASE_USER=myuser
DATABASE_PASSWORD=secure-password
DATABASE_HOST=localhost
DATABASE_NAME=mydb
```

```python
# app.py
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    user = os.environ['DATABASE_USER']
    password = os.environ['DATABASE_PASSWORD']
    host = os.environ['DATABASE_HOST']
    db = os.environ['DATABASE_NAME']
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{user}:{password}@{host}/{db}"
```

### Email (SMTP)

qdflask uses a two-file approach for email configuration:

**SMTP settings** (conf/email.yaml - safe to commit):
```yaml
# conf/email.yaml
server: smtp-relay.brevo.com
port: 587
use_tls: true
username: your-email@example.com
default_sender: noreply@yourdomain.com
```

**SMTP password** (.env - NEVER commit):
```bash
# conf/.env
SMTP_PW=your-smtp-password-or-api-key
```

**Application code:**
```python
# app.py
from qdflask.mail_utils import init_mail

init_mail(app)  # Automatically loads conf/email.yaml + SMTP_PW
```

**Providers:**
- **Brevo** (recommended): 300 emails/day free forever
- **SendGrid**: 100 emails/day free
- **Gmail**: Development only (not production)

### AWS Credentials

```bash
# conf/.env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

```python
# app.py
import boto3

s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name=os.environ['AWS_REGION']
)
```

### OAuth Secrets

```bash
# conf/.env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

## Deployment Workflows

### Development

```bash
# Developer's local machine
cd /path/to/project
cp .env.example conf/.env
# Edit conf/.env with dev secrets
source venv/bin/activate
python app.py
```

### Staging

```bash
# Staging server
cd /var/www/myapp-staging
# Create conf/.env with staging secrets
SECRET_KEY=staging-key...
DATABASE_URL=postgresql://...staging-db
DEBUG=True
```

### Production

```bash
# Production server
cd /var/www/myapp
# Create conf/.env with production secrets
SECRET_KEY=prod-key-very-long-random...
DATABASE_URL=postgresql://...prod-db
DEBUG=False
SMTP_PW=SG.real-production-key
```

## Security Checklist

✅ **Do:**

- Store secrets in `.env` files
- Add `.env` to `.gitignore`
- Use different secrets for dev/staging/prod
- Generate strong random secrets
- Restrict file permissions: `chmod 600 conf/.env`
- Rotate secrets periodically
- Use key management services (AWS Secrets Manager, HashiCorp Vault) for large deployments

❌ **Don't:**

- Commit secrets to git (even in private repos)
- Share secrets via email/Slack
- Hard-code secrets in Python files
- Use the same secrets across environments
- Store secrets in logs
- Print secrets in debug output

## Troubleshooting

### "KeyError: 'SECRET_KEY'"

Environment variable not loaded:

```python
# Add debug output
import os
print("SECRET_KEY exists:", 'SECRET_KEY' in os.environ)
print("Loaded .env from:", os.path.abspath('conf/.env'))

# Ensure dotenv is loading
from dotenv import load_dotenv
load_dotenv('conf/.env', verbose=True)
```

### "File Not Found: conf/.env"

Path issue - ensure correct relative path:

```python
import os
from pathlib import Path

# Get absolute path to conf/.env
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / 'conf' / '.env'

load_dotenv(ENV_PATH)
```

### Secrets Accidentally Committed

**If you commit secrets to git:**

1. **Rotate them immediately** (change passwords, regenerate keys)
2. Remove from git history: `git filter-branch` or `BFG Repo-Cleaner`
3. Force push: `git push --force` (if safe to do so)

**Prevention:**

```bash
# Pre-commit hook to prevent .env commits
echo "*.env" >> .gitignore
git add .gitignore
git commit -m "Ensure .env files never committed"
```

## Advanced: Secret Management Services

For large deployments, consider:

### AWS Secrets Manager

```python
import boto3
import json

client = boto3.client('secretsmanager', region_name='us-east-1')
response = client.get_secret_value(SecretId='prod/myapp/secrets')
secrets = json.loads(response['SecretString'])

app.config['SECRET_KEY'] = secrets['SECRET_KEY']
```

### HashiCorp Vault

```python
import hvac

client = hvac.Client(url='https://vault.example.com')
client.auth.approle.login(role_id='...', secret_id='...')

secret = client.secrets.kv.v2.read_secret_version(path='myapp/config')
app.config['SECRET_KEY'] = secret['data']['data']['SECRET_KEY']
```

### Environment Variables (Cloud Platforms)

Many platforms provide secret management:

- **Heroku:** Config Vars
- **AWS Elastic Beanstalk:** Environment Properties
- **Google Cloud Run:** Secret Manager
- **Azure App Service:** Application Settings

## Next Steps

- **[Configuration Files](configuration.md)** - Manage non-secret config with site.yaml
- **[Deployment Guide](deployment.md)** - Deploy with secrets
- **[Apache Configuration](apache-config.md)** - Pass secrets to Apache/WSGI

## Reference

- [12-Factor App: Config](https://12factor.net/config)
- [python-dotenv Documentation](https://pypi.org/project/python-dotenv/)
- [Flask Configuration Handling](https://flask.palletsprojects.com/en/latest/config/)
