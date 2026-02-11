# qdstart Reference

Site initialization and configuration utility.

!!! note "Coming Soon"
    Complete qdstart documentation. Migrating content from `sphinx/docs/ezstart.rst`.

## Overview

`qdstart` creates, repairs, and configures QuickDev sites.

## Basic Usage

```bash
# Create site in specified directory
python -m qdutils.qdstart /var/www/mysite --acronym mysite

# Create site in current directory
python -m qdutils.qdstart --acronym mysite

# Repair existing site
cd /var/www/mysite
python -m qdutils.qdstart --acronym mysite
```

## Command-Line Options

```
usage: qdstart.py [-s SITE_DIR] [-a ANSWER_FILE ...] [-r REPO_DIR ...] [-q]

options:
  -s SITE_DIR         Site directory (default: current directory)
  -q                  Quiet mode (suppress informational output)
  -a ANSWER_FILE      YAML file with pre-supplied answers (repeatable)
  -r REPO_DIR         Repository directory to scan (repeatable)
```

### The `-r` flag and `e::` prefix

The `-r` flag specifies directories containing installable packages.
Each directory is scanned for Python packages (directories with
`__init__.py` and a `setup.py`).

By default, packages are installed in normal (non-editable) mode.
Prefix the path with `e::` to install in editable mode (`pip install -e`):

```bash
-r /path/to/repo              # normal install
-r e::/path/to/repo           # editable install
```

The double-colon avoids ambiguity with Windows drive letters
(e.g., `e::E:\repos\myapp`).

Packages discovered under the site's `repos/` directory are always
non-editable.

### The `-a` flag

The `-a` flag specifies YAML files containing pre-supplied answers to
configuration questions. Answers are loaded before scanning, and the
first answer for a given key wins. This allows fully non-interactive
site creation.

## What qdstart Does

1. Loads answer files (`-a`)
2. Scans repo directories (`-r`) and `repos/` for packages
3. Creates directory structure (`conf/`, etc.)
4. Uses the active virtual environment, or creates one
5. Processes configuration questions (enabled flags first)
6. Installs enabled packages (editable or normal per `e::` flag)
7. Persists `repos.db` and site configuration

## Virtual Environment

QuickDev sites require a virtual environment. When qdstart runs:

- If a venv is **already active**, it is used as-is
- If the expected venv (`<prefix>.venv`) **exists**, it is used
- Otherwise, the expected venv is **created automatically**

No interactive prompt is needed.

## Idempotent Operation

`qdstart` is safe to run multiple times - it will:

- Skip existing directories
- Repair missing components
- Update outdated configurations

## See Also

- **[Site Setup Guide](../howto/site-setup.md)** - Using qdstart
- **[Site Structure](../guides/site-structure.md)** - What qdstart creates
