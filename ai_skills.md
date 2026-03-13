# QuickDev Skill Reference

Use this reference when building a new project that uses the QuickDev toolkit.

## Installation: Use qdstart

All new projects should be initialized and configured through the **qdstart** process. Do not manually create configuration files or install packages by hand.

```bash
python qdutils/qdstart.py -s /path/to/new/site
```

qdstart runs a five-phase process:
1. **Scan and Collect** - Discovers packages, reads qd_conf.toml declarations, loads answer files
2. **Configure Site** - Creates `conf/` directory structure and `site.toml`
3. **Process Questions** - Prompts for configuration (or reads from answer files)
4. **Install Packages** - Installs enabled packages via pip (supports editable installs)
5. **Wrap-up** - Persists configuration and database state

### Key options
- `-s /path` - Specify site directory (defaults to cwd)
- `-plan` - Show installation plan without executing
- `-c` - Run service configuration checks
- `-c --fix` - Auto-fix configuration issues
- `-c --test` - Validate and run functional tests
- Answer files (TOML) can pre-supply configuration so qdstart runs non-interactively

### What qdstart creates
- `conf/` - Configuration directory (site.toml, plugin configs, db/)
- `conf/repos.db` - SQLite database tracking installed packages
- `.venv/` - Site-specific virtual environment
- `qd_create_app.py` - Auto-generated Flask app factory (if Flask packages enabled)
- `.wsgi` - Apache deployment file (if Flask packages enabled)

## Creating New Packages: Use qdsetup

All new QuickDev packages **must** be created using `qdcore.qdsetup.create_package()`. Do not manually create package directories, setup.py, or boilerplate files by hand.

```python
from qdcore.qdsetup import create_package

result = create_package(
    dpath,                    # Site root directory
    package_name,             # e.g. "qdanalytics"
    is_flask,                 # True = Flask package, False = library
    description=None,         # One-line description
    author="",
    author_email="",
    version="0.1.0",
    flask_dependencies=None,  # Override default Flask deps list
    install_requires=None,    # Additional pip dependencies
    url_prefix=None,          # Flask URL prefix (default: /<short_name>)
    init_function_name=None,  # Override init function name
    blueprint_name=None,      # Override blueprint variable name
    priority=50,              # Flask init priority in qd_conf.toml
    include_check_module=None,# Default: True for Flask, False for library
    include_cli=None,         # Default: True for Flask, False for library
)
```

### Flask package example

```python
result = create_package('/path/to/site', 'qdanalytics', is_flask=True,
                        description='Analytics dashboard',
                        install_requires=['pandas>=1.0.0'])
assert result.success
# Creates: setup.py, README.md, __init__.py (with blueprint + init function),
#   qd_conf.toml, routes.py, models.py, cli.py, check_analytics.py,
#   conf/qdanalytics.yaml.example, templates/, static/
```

### Naming derivation

The `qd` prefix is stripped to derive a **short_name** used throughout:
- `qdanalytics` -> short_name `analytics`
- init function: `init_analytics`
- blueprint: `analytics_bp`
- URL prefix: `/analytics`
- checker class: `AnalyticsChecker`

## Package Build Configuration

QuickDev packages use `setup.py` (not `pyproject.toml`). Follow the existing pattern when creating packages — `qdsetup.create_package()` generates the correct `setup.py` automatically.

If a third-party repository uses `pyproject.toml`, ensure the build-backend is correct:

```toml
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"
```

**Do not** use `setuptools.backends._legacy:_Backend` as the build-backend. It is a private setuptools API that breaks editable installs and produces confusing `BackendUnavailable` errors during `pip install`.

## Databases: pdict and qdsqlite

Unless the application specifically requires a different database system, use **pdict** for schema definition and **qdsqlite** for database operations.

### pdict - Schema Definition

Define database schemas as Python objects that auto-generate SQLite CREATE statements.

```python
from qdbase import pdict

db_dict = pdict.DbDictDb()

# Define a table (is_rowid_table=True adds auto-increment id)
table = pdict.DbDictTable("projects", is_rowid_table=True)
table.add_column(pdict.Text("name", nullable=False))
table.add_column(pdict.Text("description"))
table.add_column(pdict.Number("priority", default_value=0))
table.add_column(pdict.TimeStamp("created_at"))
table.add_index("idx_name", column_names="name", is_unique=True)

db_dict.add_table(table)
```

**Column types**: `Text` (NOCASE collation), `Number` (INTEGER), `TimeStamp`
**Column options**: `nullable`, `unique`, `default_value`, `is_primary_key`, `collate`
**Supports**: indexes, foreign keys, deep copy

### qdsqlite - Database Operations

Pythonic SQLite wrapper that auto-generates SQL from Python dicts.

```python
from qdbase import qdsqlite

db = qdsqlite.QdSqlite("myapp.db", db_dict=db_dict)

# Insert
db.insert("projects", {"name": "Alpha", "priority": 1})

# Select (returns list of sqlite3.Row)
rows = db.select("projects", where={"priority": (">", 0)})

# Lookup (returns single row or None)
row = db.lookup("projects", where={"name": "Alpha"})

# Require (like lookup but raises KeyError if not found)
row = db.require("projects", where={"name": "Alpha"})

# Update
db.update("projects", {"priority": 2}, where={"name": "Alpha"})

# Upsert
db.update_insert("projects",
    flds={"priority": 3},
    where={"name": "Beta"},
    defaults={"description": "New project"}
)

# Delete
db.delete("projects", where={"name": "Alpha"})
```

Also supports raw `db.execute(sql, values)` and direct cursor/connection access when needed.

## Repository Structure

- `qdbase/src/qdbase/` - Foundation (pdict, qdsqlite, exenv, qdconf, qdcheck, qdos)
- `qdcore/src/qdcore/` - Core (qdrepos, qdsetup, flaskapp, wsgi)
- `qdutils/src/qdutils/` - Entry point (qdstart)

## Related Repositories

- `~/Projects/published/qdbase/` - Standalone qdbase foundation package
- `~/Projects/published/xsource/` - XSynth preprocessor
- `~/Projects/published/qdflask-repo/` - Flask packages (qdflask, qdimages, qdcomments)
- `~/Projects/published/qdextra/` - Archived utility modules
