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
usage: qdstart [directory] [options]

positional arguments:
  directory           Site directory (default: current directory)

options:
  --acronym ACRONYM   Site acronym (required)
  --python PYTHON     Python interpreter path
  --help              Show this help message
```

## What qdstart Does

1. Creates directory structure (conf/, logs/, etc.)
2. Initializes Python virtual environment
3. Creates configuration templates (site.yaml, site.conf)
4. Sets up convenience symlinks

## Idempotent Operation

`qdstart` is safe to run multiple times - it will:

- Skip existing directories
- Repair missing components
- Update outdated configurations

## See Also

- **[Site Setup Guide](../howto/site-setup.md)** - Using qdstart
- **[Site Structure](../guides/site-structure.md)** - What qdstart creates
