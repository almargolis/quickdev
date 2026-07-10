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
table = pdict.DbDictTable("projects", is_rowid_table=True)
table.add_column(pdict.Text("name", nullable=False))
table.add_column(pdict.Number("priority", default_value=0))
table.add_column(pdict.TimeStamp("created_at"))
table.add_index("idx_name", column_names="name", is_unique=True)
db_dict.add_table(table)
```

**Column types**: `Text` (NOCASE collation), `Number` (INTEGER), `TimeStamp`
**Column options**: `nullable`, `unique`, `default_value`, `is_primary_key`, `collate`

## qdsqlite - Database Operations

```python
from qdbase import qdsqlite

db = qdsqlite.QdSqlite("myapp.db", db_dict=db_dict)

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
