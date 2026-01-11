# QuickDev Philosophy

## Core Vision

QuickDev emerged from a simple observation: web developers spend too much time writing the same patterns over and over. Authentication systems, image management, CRUD operations, database models - these are solved problems, yet we rebuild them for every project.

QuickDev's philosophy is to **capture common patterns as reusable idioms** - not through runtime abstractions, but through **code generation that produces readable, standard Python**.

## Not a Framework

QuickDev deliberately avoids being a framework. You don't build "a QuickDev app" - you use QuickDev to eliminate boilerplate in Flask apps, Django projects, or standalone Python code.

**What this means:**

- Your app controls the flow, not QuickDev
- Use QuickDev packages selectively - take what you need
- No vendor lock-in - generated code is standard Python
- Works alongside Flask, Django, FastAPI, or any Python framework

This "idiom-based" approach gives you the power of code generation without the constraints of a framework.

## 12-Factor Alignment

QuickDev's design naturally aligns with [12-Factor App](https://12factor.net) principles, particularly around configuration and deployment:

### III. Config - Strict Separation of Secrets and Configuration

QuickDev distinguishes between two types of configuration:

**Secrets** (stored in `.env` files):
```bash
# Sensitive credentials that should never be committed
SECRET_KEY=abc123...
DATABASE_PASSWORD=secret
SENDGRID_API_KEY=SG.xyz...
```

**Configuration** (stored in `site.yaml`):
```yaml
# Application structure and behavior - safe to commit
site_name: myapp
database_name: myapp_prod
features:
  - authentication
  - image_upload
  - comments
```

This separation means:

- **Secrets stay in environment variables** (loaded from `.env` via dotenv)
- **Configuration lives in version control** (YAML, committed safely)
- Same codebase deploys to dev/staging/production with different secrets
- Infrastructure-as-code: site.yaml describes your application structure

### Other 12-Factor Principles

QuickDev also embodies:

- **I. Codebase** - One repo, many deploys (dev/staging/prod use same code)
- **X. Dev/prod parity** - Same packages, same structure across environments
- **XI. Logs** - Treat logs as event streams (QuickDev doesn't capture logs)

## Target Audience: VPS Developers

QuickDev is designed for **developers who manage their own VPS nodes** (Digital Ocean, Linode, AWS EC2, etc.) and want:

- **Control without complexity** - No Docker orchestration, no Ansible learning curve
- **Quick deployment** - `qdstart` creates a working site in seconds
- **Apache integration** - `qdapache` generates configs from site metadata
- **Repeatable patterns** - Same idioms across all your projects

### vs Other Tools

**QuickDev vs Ansible/Chef/Puppet:**

- QuickDev: Application-level patterns (auth, images, site structure)
- Ansible: System-level automation (install packages, configure services)
- **Use together**: Ansible provisions the server, QuickDev manages your app

**QuickDev vs Docker/Kubernetes:**

- QuickDev: Python code generation and site management
- Docker: Process isolation and container orchestration
- **Different needs**: Docker for microservices, QuickDev for monoliths on VPS

**QuickDev vs Django Admin/Flask-Admin:**

- QuickDev: Generate code you can read and modify
- Admin frameworks: Runtime abstractions with less flexibility
- **Philosophy**: QuickDev produces code, not black boxes

## QuickDev Site Structure

A **QuickDev site** is a standardized directory structure for deploying Python web applications:

```
/var/www/mysite/          # Site root
├── conf/                  # Configuration directory
│   ├── .env              # Secrets (never committed)
│   ├── site.yaml         # Site configuration (version controlled)
│   ├── site.conf         # Legacy INI format (being phased out)
│   └── db/               # SQLite databases
├── mysite.venv/          # Python virtual environment
├── static/               # Static assets (symlinked)
├── templates/            # Jinja templates (symlinked)
└── logs/                 # Application logs
```

### Why This Structure?

**Separation of concerns:**

- `/conf/` contains ALL configuration (secrets + config)
- Virtual environment is self-contained
- Application code lives elsewhere (often in source control)
- Logs and data have dedicated locations

**Easy backup/restore:**

- Back up `/conf/` for configuration
- Back up `/conf/db/` for data
- Virtual environment can be recreated
- Static files are often symlinked from source

**Repeatable deployment:**

- `qdstart` creates this structure automatically
- Same layout on dev, staging, and production
- Apache configs generated from `site.yaml` metadata

## Code Generation Philosophy

QuickDev extends DRY (Don't Repeat Yourself) from **runtime code reuse** to **compile-time code generation**.

### XSynth: The Preprocessor

XSynth transforms `.xpy` (XSynth Python) files into standard `.py` files:

```python
# Input: model.xpy
#$ dict User
    username: str
    email: str
    role: str = 'user'

# Generated: model.py
class User:
    def __init__(self, username, email, role='user'):
        self.username = username
        self.email = email
        self.role = role

    def to_dict(self):
        return {
            'username': self.username,
            'email': self.email,
            'role': self.role
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
```

### Why Generate Code?

**Advantages of code generation:**

1. **Readable output** - You can read, debug, and modify generated Python
2. **No runtime overhead** - Generated code runs as fast as hand-written code
3. **Full control** - Edit generated files if needed (though you'll lose changes on regeneration)
4. **Standard Python** - No custom metaclasses, no magic

**When to use XSynth:**

- Data models with repetitive patterns
- CRUD operations
- Form validation
- API endpoint boilerplate

**When NOT to use XSynth:**

- Unique business logic
- Complex algorithms
- One-off code

## Idioms: Reusable Patterns

QuickDev packages like **qdflask**, **qdimages**, and **qdcomments** are **idioms** - complete, production-ready implementations of common patterns.

### What Makes an Idiom?

An idiom is:

- **Complete** - Everything you need for that feature (models, routes, templates, CLI)
- **Integrated** - Works with Flask/Django/etc. via simple init functions
- **Customizable** - Configure via parameters, extend by editing generated code
- **Documented** - README with examples and best practices

### Example: qdflask Authentication

```python
from flask import Flask
from qdflask import init_auth, create_admin_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

# Initialize authentication with custom roles
init_auth(app, roles=['admin', 'editor', 'viewer'])

# Create admin on first run
with app.app_context():
    create_admin_user('admin', os.environ['ADMIN_PASSWORD'])
```

This 10-line snippet gives you:

- User model with password hashing
- Login/logout routes
- Role-based access control
- User management interface
- CLI commands for user creation

No tutorials to follow, no boilerplate to write - just import and initialize.

## Evolution: 1990s to 2026

QuickDev represents **decades of refinement**:

- **1990s**: C library for web applications (pre-dated frameworks)
- **2000s**: Transitioned to Python, developed DRY patterns
- **2010s**: Added XSynth preprocessor, Flask integration
- **2020s**: Open sourced, published to PyPI, modernized documentation

The core insight - **capture patterns as idioms** - has remained constant.

## Guiding Principles

1. **Generate code, don't abstract it** - Code generation > runtime magic
2. **Readable output matters** - Generated Python should be as clear as hand-written
3. **Work with existing tools** - Complement Flask/Django, don't replace them
4. **Separate secrets from config** - .env for credentials, YAML for structure
5. **Convention over configuration** - Standard site structure, predictable layout
6. **Target VPS developers** - Simple deployment without Docker/Kubernetes complexity
7. **Decades of patterns** - Proven idioms refined over 30 years

## Philosophy in Practice

**When QuickDev is a good fit:**

- Building a Flask/Django app and tired of writing auth/images/comments code
- Managing 1-10 VPS nodes and want simpler deployment than Kubernetes
- Using XSynth to generate data models and CRUD operations
- Need Apache configs that stay in sync with application structure

**When QuickDev might not fit:**

- Microservices architecture with container orchestration (use Docker/K8s)
- Large team with dedicated DevOps (Ansible/Terraform may be better)
- Wanting runtime abstractions instead of generated code
- Working in a framework that conflicts with QuickDev's patterns

## Next Steps

- **Understand the architecture:** [Architecture Overview](architecture.md)
- **Compare to frameworks:** [vs Frameworks](vs-frameworks.md)
- **Get started:** [Quick Start Guide](../howto/quickstart.md)
- **Deploy a site:** [Site Setup](../howto/site-setup.md)
