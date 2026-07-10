# qdbase

Foundation utilities for Python development with zero external dependencies.

## Overview

`qdbase` is the foundation layer of the QuickDev metaprogramming toolkit, providing a collection of utilities for common development tasks. It has **zero external dependencies** beyond the Python standard library, making it lightweight and easy to integrate into any project.

## Key Modules

### exenv - Execution Environment
Detection and normalization of execution environments:
- Path manipulation with safety checks
- Directory and file utilities
- Environment detection

### pdict - Enhanced Dictionary
Extended dictionary functionality with additional utilities for data manipulation.

### qdsqlite - SQLite Helpers
Simplified SQLite database operations:
- Connection management
- Query helpers
- Schema utilities

### CLI Utilities
- `cliargs` - Command-line argument parsing
- `cliinput` - Interactive command-line input handling

### qdconf - Configuration Management
TOML-based configuration management with cache and validation.

### qdcheck - Check/Validation Framework
Pluggable check runners for validating service configuration and health.

### qdos - OS Operations
Safe filesystem operations with error handling (directory creation, file operations).

## Installation

```bash
pip install qdbase
```

Or install in development mode from a local clone:

```bash
pip install -e /path/to/qdbase
```

## Usage

```python
from qdbase import pdict, qdsqlite, exenv

# Enhanced dictionary operations
data = pdict.PDict()

# SQLite helpers
db = qdsqlite.QdSqlite("mydb.db")

# Environment utilities
safe_path = exenv.safe_join("/base/path", "subdir")
```

## Part of QuickDev

`qdbase` is part of the QuickDev metaprogramming toolkit. Other packages include:
- **xsynth** - Preprocessor for generating Python from high-level declarations
- **qdflask** - Flask authentication with role-based access control
- **qdimages** - Flask image management with hierarchical storage

## License

MIT License - Copyright (C) Albert B. Margolis

## Requirements

- Python >= 3.9
- No external dependencies (stdlib only)
