# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuickDev is a metaprogramming toolkit and collection of DRY idioms for Python development. It is **not a framework** - it works alongside Flask, Django, and other tools to eliminate boilerplate through preprocessor-based code generation.

The core value proposition is reducing repetitive code by:
- Using the XSynth preprocessor to generate Python from high-level declarations
- Providing reusable idioms (like qdflask for auth, qdimages for image management)
- Employing dictionaries and introspection to auto-generate common patterns

QuickDev complements existing frameworks rather than replacing them.

## Key Architectural Concepts

### XSynth Preprocessor System

XSynth is a preprocessor that transforms `.xpy` (XSynth Python) files into standard `.py` files. It provides:
- Data modeling with `#$ dict` declarations
- Structured action/class generation with `#$ action` declarations
- Template substitution for generating repetitive code patterns
- A SQLite database (`xsynth.db`) to track modules, classes, and dependencies during synthesis

XSynth has two modes:
1. **Stand-alone mode**: Processes files with minimal QuickDev dependencies (used during bootstrapping)
2. **QuickDev mode**: Full integration with the QuickDev framework

**Important**: Many `.py` files in `qdcore/` are generated from `.xpy` files. When modifying functionality that has a corresponding `.xpy` file, edit the `.xpy` source file, not the generated `.py` file.

### Module Structure

The codebase is organized into several package directories:

- **qdbase/**: Foundation layer with minimal dependencies
  - `exenv.py`: Execution environment detection and normalization
  - `xsource.py`: XSynth source file processing classes
  - `qdsqlite.py`: SQLite database utilities
  - `cliargs.py`, `cliinput.py`: Command-line interface utilities
  - `pdict.py`: Dictionary utilities
  - `simplelex.py`: Simple lexical analysis

- **qdcore/**: Core idioms and utilities
  - `execontroller.py`: Program execution environment controller
  - `qdsite.py`: Site configuration and management
  - `qddict.py`: Enhanced dictionary class (generated from `qddict.xpy`)
  - `qdhtml.py`: HTML generation utilities
  - `httpautomation.py`: HTTP automation and testing
  - `datastore.py`: Data storage abstractions
  - `rdbms.py`: Relational database utilities

- **qdutils/**: Development utilities
  - `qdstart.py`: Site initialization and configuration tool
  - `xsynth.py`: XSynth preprocessor main entry point
  - `hosting.py`: Hosting environment utilities

- **qdconfig/**: Configuration and setup utilities
  - `configure.py`: Application configuration system

- **qdflask/**: Flask authentication package (reusable)
  - `auth.py`: Login, logout, and authentication routes
  - `models.py`: User model with role-based access control
  - `cli.py`: Command-line tools for user management
  - `templates/qdflask/`: Login and user management UI templates

- **qdimages/**: Flask image management package (reusable)
  - `routes.py`: 16 API endpoints for image operations
  - `storage.py`: Hierarchical xxHash-based content storage
  - `editor.py`: Image processing (crop, resize, brightness, background removal)
  - `models.py`: Image metadata database model
  - `file_handler.py`: File I/O operations
  - `templates/`: Web-based image editor interface

### Flask Integration Packages

QuickDev includes reusable Flask packages for common web application features:

**qdflask** - User authentication with Flask-Login integration
- Initialize: `from qdflask import init_auth`
- Role-based access control with customizable roles
- User management interface and CLI commands
- See `qdflask/README.md` for full documentation
- Installable: `pip install -e ./qdflask` (recommended)
- Dependencies: Flask, Flask-SQLAlchemy, Flask-Login, Werkzeug

**qdimages** - Image management with hierarchical storage
- Initialize: `from qdimages import init_image_manager`
- xxHash-based content-addressed storage with automatic deduplication
- Web-based image editor (crop, resize, brightness, background removal)
- Metadata tracking with keywords and EXIF data
- See `qdimages/README.md` for full documentation
- Installable: `pip install -e ./qdimages`
- Dependencies: Flask, Pillow, xxhash, PyYAML, rembg

Both packages follow the QuickDev pattern of simple integration via init functions and work seamlessly together.

### Bootstrapping Architecture

QuickDev has a carefully designed bootstrapping sequence because the framework uses its own features:

1. `qdbase` modules must be importable without XSynth processing
2. `xsynth.py` can run before the virtual environment is fully configured
3. `qdstart.py` handles site initialization and may run with incomplete Python paths
4. Import exception handling allows graceful degradation during bootstrap

Key files involved in bootstrapping:
- `qdutils/qdstart.py`: Creates/repairs QuickDev sites
- `qdutils/xsynth.py`: Preprocesses `.xpy` files to `.py` files
- `qdbase/exenv.py`: Provides execution environment utilities used during bootstrap

### Site Configuration

QuickDev sites are configured via `conf/site.conf`:
- `qdsite_dpath`: Path to the QuickDev site directory
- `acronym`: Short name for the site

The `xsynth.db` SQLite database tracks synthesis state for all modules.

## Development Commands

### Virtual Environment

Activate the virtual environment:
```bash
source ezdev.venv/bin/activate
# or use the symlink
source venv
```

### Running Tests

Run all tests:
```bash
pytest
```

Run tests for a specific module:
```bash
pytest qdbase_tests/test_exenv.py
pytest qdcore_tests/test_qdhtml.py
```

Run a specific test function:
```bash
pytest qdbase_tests/test_exenv.py::test_safe_join
```

Test directories follow the pattern `{package}_tests/` (e.g., `qdbase_tests/`, `qdcore_tests/`).

### XSynth Processing

Process XSynth files (`.xpy` to `.py`):
```bash
python qdutils/xsynth.py
```

The `bin/makepy` script runs XSynth preprocessing on specified directories.

### Code Quality

Linting configuration:
- **flake8**: Configured in `.flake8` (ignores E127, E128; max line length 89)
- **pylint**: Configured in `pylintrc` (disables bad-continuation warnings)

Run linters:
```bash
flake8 qdbase/
pylint qdcore/
```

## Important Implementation Notes

### Working with .xpy Files

Before editing Python files in `qdcore/`, check if a corresponding `.xpy` file exists:
```bash
ls qdcore/*.xpy
```

If a `.xpy` file exists (e.g., `qddict.xpy`), edit the `.xpy` file and regenerate the `.py` file using XSynth, not the generated `.py` file directly.

### Import Patterns

Many modules have defensive imports to handle bootstrap scenarios:
```python
try:
    from qdcore import qdsite
except ModuleNotFoundError:
    # Bootstrap mode - module not yet available
    qdsite = None
```

This pattern allows modules to function during development even when dependencies aren't fully configured.

### Database Usage

The framework uses SQLite for various purposes:
- `xsynth.db`: XSynth synthesis database (tracked in git)
- Site-specific databases in `conf/db/`

Use `qdbase.qdsqlite` module for SQLite operations within the framework.

## Site Configuration Management and Testing

QuickDev includes support for site-specific configuration management and testing through a standardized check/validation framework.

### Configuration Files

Each service package has a configuration file in `conf/<service>.yaml`:

- `conf/qdflask.yaml` - Flask authentication settings
- `conf/qdimages.yaml` - Image management settings
- `conf/qdcomments.yaml` - Comments system settings

Each configuration file includes a `service_enabled` flag that controls whether checks run for that service:

```yaml
# conf/qdflask.yaml
service_enabled: true

users:
  default_role: reader
  valid_roles: [admin, editor, reader]
```

Example templates are provided in each package's `conf/` directory (e.g., `qdflask/qdflask/conf/qdflask.yaml.example`).

### Check/Validation Framework

The check framework (`qdbase/qdcheck.py`) provides three operation modes:

1. **VALIDATE** - Check configuration and report issues (default)
2. **TEST** - Validate + run functional tests
3. **CORRECT** - Validate + auto-fix issues where possible

### Running Checks

**Check all services:**
```bash
python qdutils/qdstart.py -c           # Validate all
python qdutils/qdstart.py -c --fix     # Validate + auto-fix
python qdutils/qdstart.py -c --test    # Validate + test
```

**Check specific service:**
```bash
python -m qdflask.check_users          # Validate qdflask
python -m qdflask.check_users --fix    # Validate + fix
python -m qdflask.check_users --test   # Validate + test
python -m qdflask.check_users --conf /path/to/conf  # Specify conf directory
```

### Check Output

Checks produce visual output with status indicators:

```
============================================================
Flask Authentication Configuration Check
============================================================
✓ SECRET_KEY: Configured (64 chars)
✓ Database Access: Connected
✗ User Schema: Missing columns: ['email_verified']
  → Run database migrations or use --fix
⚠ Admin User: No admin user exists
  → Run: python -m qdflask.cli init-db

Results: 2/4 checks passed
```

### Creating Custom Check Modules

To create a check module for a new service:

1. Create a checker class extending `CheckRunner`:

```python
from qdbase.qdcheck import CheckRunner, CheckResult, CheckStatus, CheckMode

class MyServiceChecker(CheckRunner):
    service_name = "myservice"
    service_display_name = "My Service"
    config_filename = "myservice.yaml"

    def _run_checks(self):
        self._check_config()
        self._check_database()

    def _check_config(self):
        # Perform check and add result
        self.add_result(CheckResult(
            name="Config File",
            status=CheckStatus.PASS,
            message="Configuration loaded"
        ))
```

2. Register the checker in `qdbase/qdcheck.py`:

```python
register_checker('myservice', 'mypackage.check_myservice.MyServiceChecker')
```

3. Create a configuration template `mypackage/conf/myservice.yaml.example`

### Service Discovery

Services are discovered automatically when:
- They are registered in `CHECK_REGISTRY` in `qdbase/qdcheck.py`
- Their check module is importable
- `service_enabled` is not explicitly set to `false` in the config

Disabled services are skipped during check-all operations.
