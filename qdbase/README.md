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

### simplelex - Lexical Analysis
Simple lexical analysis utilities for parsing text and code.

### xsource - Source Processing
Source file processing classes used by the XSynth preprocessor.

## Installation

```bash
pip install qdbase
```

Or install in development mode:

```bash
pip install -e ./qdbase
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

- Python >= 3.7
- No external dependencies (stdlib only)
