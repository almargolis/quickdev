# qdbase Skill Reference

Foundation utilities for Python development with zero external dependencies.

## Modules

| Module | Description |
|--------|-------------|
| `exenv` | Execution environment detection and normalization |
| `pdict` | Database schema definition (generates SQLite CREATE statements) |
| `qdsqlite` | Pythonic SQLite wrapper with auto-generated SQL |
| `cliargs` | Command-line argument parsing |
| `cliinput` | Interactive command-line input handling |
| `qdconf` | TOML-based configuration management with cache |
| `qdcheck` | Pluggable check/validation framework |
| `qdos` | Safe filesystem operations with error handling |
| `initializer` | Property initialization helper |

## pdict - Schema Definition

```python
from qdbase import pdict

db_dict = pdict.DbDictDb()

# DbDictTable with is_rowid_table=True (default) adds auto-increment id column
projects = db_dict.add_table(pdict.DbDictTable("projects"))
projects.add_column(pdict.Text("name", is_create_required=True, max_length=100))
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
- `default_value` — Default value. Use `pdict.ColumnName("EXPR")` for SQL expression defaults (e.g., `CURRENT_TIMESTAMP`).
- `is_primary_key`, `is_read_only`, `collate`

**REST/form metadata** (used by qdrestful and qdforms, ignored by sql()):
- `is_create_required`, `is_update_allowed`, `is_filterable`, `is_sortable`
- `rest_label`, `choices`, `max_length`, `min_length`, `max_value`, `min_value`
- `pattern`, `form_widget`, `placeholder`

**Foreign keys**: `pdict.Number("fk_col", foreign_key=pdict.ForeignKey(other_table.columns["id"]))`

## qdsqlite - Database Operations

```python
from qdbase import qdsqlite

db = qdsqlite.QdSqlite("myapp.db", db_dict=db_dict)
# foreign_keys=True by default (PRAGMA foreign_keys=ON)

db.insert("projects", {"name": "Alpha", "priority": 1})
rows = db.select("projects", where={"priority": (">", 0)})
row = db.lookup("projects", where={"name": "Alpha"})
row = db.require("projects", where={"name": "Alpha"})
db.update("projects", {"priority": 2}, where={"name": "Alpha"})
db.update_insert("projects", flds={"priority": 3}, where={"name": "Beta"},
                 defaults={"description": "New project"})
db.delete("projects", where={"name": "Alpha"})
```

## qdcheck - Validation Framework

Three operation modes:
1. **VALIDATE** - Check configuration and report issues (default)
2. **TEST** - Validate + run functional tests
3. **CORRECT** - Validate + auto-fix issues where possible

## Installation

```bash
pip install qdbase
# or
pip install -e /path/to/qdbase
```

## Repository Structure

```
qdbase/
├── src/qdbase/      # All modules
├── qdbase_tests/    # Tests
├── setup.py
└── README.md
```
