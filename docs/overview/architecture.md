# Architecture Overview

QuickDev is organized as a monorepo with multiple packages, each serving a specific purpose.

## Package Structure

```
quickdev/
├── qdbase/          # Foundation utilities (zero dependencies)
├── qdcore/          # Core idioms and utilities
├── qdutils/         # Development tools
├── qdconfig/        # Configuration system
├── qdflask/         # Flask authentication (PyPI package)
├── qdimages/        # Flask image management (PyPI package)
├── qdcomments/      # Flask commenting (PyPI package)
└── xsynth/          # XSynth preprocessor (PyPI package)
```

### qdbase - Foundation Layer

**Purpose:** Minimal utilities with zero external dependencies

**Key modules:**

- `exenv.py` - Execution environment detection and normalization
- `xsource.py` - XSynth source file processing
- `qdsqlite.py` - SQLite database utilities
- `pdict.py` - Dictionary utilities (including `DbDictDb` for database-backed dicts)
- `cliargs.py`, `cliinput.py` - Command-line interface helpers
- `simplelex.py` - Simple lexical analysis

**Why it exists:** During bootstrapping, other QuickDev modules may not be available yet. `qdbase` provides the minimum needed to run `qdstart` and `xsynth`.

**Published:** `pip install qdbase` (v0.2.0+)

### xsynth - XSynth Preprocessor

**Purpose:** Transform `.xpy` files into `.py` files using code generation

**Key features:**

- `#$ dict` declarations for data modeling
- `#$ action` declarations for structured classes
- Template substitution with Python introspection
- SQLite database (`xsynth.db`) to track synthesis state

**How it works:**

1. Parse `.xpy` files for special `#$` directives
2. Use Python dictionaries and introspection to generate code
3. Write standard `.py` files as output
4. Track dependencies in `xsynth.db`

**Published:** `pip install xsynth` (v0.3.0+)

See [XSynth Guide](../guides/xsynth.md) for detailed usage.

### qdcore - Core Idioms

**Purpose:** Fundamental services for building applications

**Key modules:**

- `execontroller.py` - Program execution environment controller
- `qdsite.py` - Site configuration and management
- `qddict.py` - Enhanced dictionary class (generated from `qddict.xpy`)
- `qdhtml.py` - HTML generation utilities
- `httpautomation.py` - HTTP automation and testing
- `datastore.py` - Data storage abstractions
- `rdbms.py` - Relational database utilities

**Note:** Many `.py` files in `qdcore/` are **generated from `.xpy` files**. When modifying these, edit the `.xpy` source and regenerate.

**Status:** Not yet published to PyPI (used primarily in QuickDev development)

### qdutils - Development Tools

**Purpose:** Command-line utilities for QuickDev development

**Key tools:**

- `qdstart.py` - Site initialization and configuration
- `xsynth.py` - XSynth preprocessor entry point
- `hosting.py` - Hosting environment utilities

**Usage:**

```bash
# Create a new QuickDev site
python -m qdutils.qdstart /var/www/mysite --acronym mysite

# Process XSynth files
python qdutils/xsynth.py
```

**Status:** Not yet published to PyPI (used during development)

### qdconfig - Configuration System

**Purpose:** Application configuration management

**Key modules:**

- `configure.py` - Configuration loading and validation

**Status:** Under development

### Flask Integration Packages

#### qdflask - Authentication

**Features:**

- User model with password hashing (Werkzeug)
- Flask-Login integration
- Role-based access control (customizable roles)
- User management interface (admin-only)
- CLI commands for user management
- Email notifications via Flask-Mail

**Installation:** `pip install qdflask`

**Quick start:**

```python
from flask import Flask
from qdflask import init_auth, create_admin_user

app = Flask(__name__)
init_auth(app, roles=['admin', 'editor', 'viewer'])
```

See [qdflask README](https://github.com/almargolis/quickdev/blob/master/qdflask/README.md) for complete documentation.

#### qdimages - Image Management

**Features:**

- Content-addressed storage (xxHash-based, hierarchical)
- 16 API endpoints for image operations
- Web-based image editor (crop, resize, brightness, background removal)
- Image metadata with keywords and EXIF data
- Automatic deduplication

**Installation:** `pip install qdimages`

**Quick start:**

```python
from flask import Flask
from qdimages import init_image_manager

app = Flask(__name__)
init_image_manager(app, storage_path='/var/www/mysite/images')
```

See [qdimages README](https://github.com/almargolis/quickdev/blob/master/qdimages/README.md) for complete documentation.

#### qdcomments - Commenting System

**Features:**

- Comment model with threading support
- Moderation system (approve/reject)
- Content filtering (blocked words)
- Email notifications to admins
- Markdown support

**Installation:** `pip install qdcomments`

**Quick start:**

```python
from flask import Flask
from qdcomments import init_comments

app = Flask(__name__)
init_comments(app)
```

See [qdcomments README](https://github.com/almargolis/quickdev/blob/master/qdcomments/README.md) for complete documentation.

## Bootstrapping Architecture

QuickDev has a carefully designed bootstrapping sequence because **the framework uses its own features**.

### Why Bootstrapping Matters

Problem: `xsynth.py` generates `.py` files from `.xpy` files, but some of those generated files are needed by `xsynth.py` itself.

Solution: Multi-stage bootstrap process.

### Bootstrap Sequence

1. **Stage 0: qdbase only**
   - `qdbase` modules must be importable without XSynth processing
   - No external dependencies
   - Provides minimum utilities for next stages

2. **Stage 1: XSynth stand-alone mode**
   - `xsynth.py` can run before virtual environment is configured
   - Uses defensive imports to handle missing dependencies gracefully
   - Processes `.xpy` files to create `.py` files

3. **Stage 2: Full QuickDev**
   - All generated files now exist
   - Virtual environment configured
   - Full import graph works

### Defensive Import Pattern

Many modules use this pattern to handle bootstrap scenarios:

```python
try:
    from qdcore import qdsite
except ModuleNotFoundError:
    # Bootstrap mode - module not yet available
    qdsite = None

# Later in code:
if qdsite:
    # Use qdsite functionality
else:
    # Fallback or skip feature
```

This allows modules to function during development even when dependencies aren't fully configured.

## Site Configuration

QuickDev sites are configured via files in the `conf/` directory:

### Legacy: site.conf (INI format)

```ini
[site]
qdsite_dpath = /var/www/mysite
acronym = mysite
```

**Status:** Being phased out in favor of `site.yaml`

### Modern: site.yaml (YAML format)

```yaml
site_name: mysite
database_uri: sqlite:///conf/db/mysite.db
features:
  - authentication
  - image_upload
  - comments
roles:
  - admin
  - editor
  - viewer
```

### Secrets: .env (Environment variables)

```bash
SECRET_KEY=your-secret-key-here
DATABASE_PASSWORD=secret
SENDGRID_API_KEY=SG.xyz...
```

**Critical:** `.env` files should **never be committed** to version control. Add to `.gitignore`.

## Database Management

### xsynth.db

SQLite database that tracks XSynth synthesis state:

- Which modules have been processed
- Class dependencies
- Synthesis timestamps

**Location:** Repository root

**Version control:** Tracked in git (represents canonical synthesis state)

### Site Databases

Application-specific SQLite databases:

**Location:** `conf/db/` in each site

**Examples:**

- `conf/db/users.db` - User authentication (qdflask)
- `conf/db/images.db` - Image metadata (qdimages)
- `conf/db/comments.db` - Comments (qdcomments)

**Version control:** **NOT** tracked (contain production data)

## Module Dependencies

```
qdbase (zero dependencies)
  ↓
xsynth → uses qdbase
  ↓
qdcore → uses qdbase, generated by xsynth
  ↓
qdutils → uses qdbase, qdcore
  ↓
Flask packages (qdflask, qdimages, qdcomments)
  → use Flask, Flask-SQLAlchemy
  → independent of qdcore (can be pip installed separately)
```

## Key Architectural Decisions

### Why Monorepo?

**Advantages:**

- Atomic commits across packages
- Easier refactoring across boundaries
- Shared tooling (tests, linting, CI/CD)
- Single source of truth

**Disadvantages:**

- Larger clone size
- More complex CI/CD

**Decision:** Monorepo fits QuickDev's development model. Packages are still published independently to PyPI.

### Why Code Generation?

**Advantages:**

- Readable output (standard Python)
- No runtime overhead
- Full control (can edit generated files)
- No magic (no metaclasses or import hooks)

**Disadvantages:**

- Regeneration required after changes
- Two-file system (`.xpy` + `.py`)

**Decision:** Code generation fits the "idiom" philosophy better than runtime abstractions.

### Why Flask Packages?

**Advantages:**

- Most popular Python web framework
- Minimal, unopinionated
- Easy to extend

**Disadvantages:**

- Not suitable for very large applications (Django might be better)

**Decision:** Flask is the perfect target for QuickDev idioms. Django support may come later.

## Next Steps

- **Understand the philosophy:** [Philosophy](philosophy.md)
- **Compare to other tools:** [vs Frameworks](vs-frameworks.md)
- **Get started:** [Quick Start Guide](../howto/quickstart.md)
- **Learn XSynth:** [XSynth Guide](../guides/xsynth.md)
