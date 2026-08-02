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
- `-a /path/to/answers.toml` - Load pre-supplied answers (can be repeated)
- `-r [e::]/path/to/repo` - Add a repository to scan (`e::` prefix = editable install)
- `-c` - Run service configuration checks
- `-c --fix` - Auto-fix configuration issues
- `-c --test` - Validate and run functional tests

### bootstrap.toml workflow

For reproducible installations, create a `bootstrap.toml` that captures all answers:

```toml
[site]
site_dpath = "/var/www/myapp"
qdsite_prefix = "myapp"

[repos]
paths = [
    "e::/path/to/quickdev",
    "e::/path/to/qdflask-repo",
    "e::/path/to/myapp",
]

[answers.qdrestful]
enabled = true
db_type = "sqlite"
sqlite_fpath = "<site_dpath>/conf/db/app_data.db"
url_prefix = "/api"
```

Generate boot files and install:

```bash
python qdbootstrap.py --generate -t /path/to/myapp
sh qdboot.sh plan   # preview
sh qdboot.sh make   # install
```

The `<site_dpath>` placeholder resolves to the actual install directory at install time.

### What qdstart creates
- `conf/` - Configuration directory (site.toml, plugin configs, db/)
- `conf/repos.db` - SQLite database tracking installed packages
- `.venv/` - Site-specific virtual environment
- `qd_create_app.py` - Auto-generated Flask app factory (if Flask packages enabled)
- `wsgi.py` - WSGI deployment file (if Flask packages enabled)

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

# Define a table (is_rowid_table=True adds auto-increment id column)
projects = db_dict.add_table(pdict.DbDictTable("projects"))
projects.add_column(pdict.Text("name", is_create_required=True, max_length=100))
projects.add_column(pdict.Text("description", allow_nulls=True))
projects.add_column(pdict.Number("priority", default_value=0))
projects.add_column(pdict.TimeStamp("created_at",
    default_value=pdict.ColumnName("CURRENT_TIMESTAMP"),
    is_read_only=True))
projects.add_index("idx_name", column_names="name", is_unique=True)
```

**Column types**: `Text` (NOCASE collation), `Number` (INTEGER), `TimeStamp`

**Column options** (constructor kwargs):
- `allow_nulls` — Allow NULL values (default: `False`)
- `is_unique` — Add UNIQUE constraint (default: `False`)
- `default_value` — Default value. Use `pdict.ColumnName("CURRENT_TIMESTAMP")` for SQL expression defaults (rendered unquoted in DDL).
- `is_primary_key` — Mark as primary key (default: `False`; auto-set on the `id` column of rowid tables)
- `is_read_only` — Cannot be set via API (default: `False`)
- `collate` — Collation (default: `"NOCASE"` for Text, `None` for others)

**REST/form metadata** (also constructor kwargs, used by qdrestful and qdforms):
- `is_create_required` — Must be provided on create (default: `False`)
- `is_update_allowed` — Can be modified on update (default: `True`)
- `is_filterable` — Can filter API results by this column (default: `True`)
- `is_sortable` — Can sort API results by this column (default: `True`)
- `rest_label` — Human-readable label for forms and MCP tool descriptions
- `choices` — List of valid values; renders as `<select>` in forms
- `max_length`, `min_length` — Text length constraints
- `max_value`, `min_value` — Numeric range constraints
- `pattern` — Regex validation pattern
- `form_widget` — Override widget: `"text"`, `"textarea"`, `"select"`, `"number"`, `"date"`, `"datetime"`, `"checkbox"`, `"password"`, `"email"`, `"url"`, `"hidden"`
- `placeholder` — HTML placeholder text

**Foreign keys**:
```python
# Column in one table referencing another table's column
tasks.add_column(pdict.Number("project_id",
    foreign_key=pdict.ForeignKey(projects.columns["id"]),
    allow_nulls=True))
```

**Supports**: indexes, foreign keys, deep copy, SQL generation via `db_dict.sql_create_list()`

### qdsqlite - Database Operations

Pythonic SQLite wrapper that auto-generates SQL from Python dicts.

```python
from qdbase import qdsqlite

db = qdsqlite.QdSqlite("myapp.db", db_dict=db_dict)
# foreign_keys=True by default (enforces FK constraints)
# Pass foreign_keys=False for legacy databases or bulk imports

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
- `~/Projects/published/qdflask-repo/` - Flask packages (qdflask, qdflaskauth, qdflaskapi, qdrestful, qdforms, qdimages, qdcomments, qdflaskemail)
- `~/Projects/published/qdextra/` - Archived utility modules
