# qdbase

Foundation utilities with zero external dependencies.

## Overview

`qdbase` provides the minimal utilities needed to bootstrap QuickDev:

- Execution environment detection
- XSynth source file processing
- SQLite database utilities
- Dictionary utilities (including `DbDictDb`)
- Command-line interface helpers

**Version:** 0.2.0
**PyPI:** [pypi.org/project/qdbase](https://pypi.org/project/qdbase/)
**Source:** [GitHub](https://github.com/almargolis/quickdev/tree/master/qdbase)

## Installation

```bash
pip install qdbase
```

## Key Modules

### exenv.py
Execution environment detection and normalization

### xsource.py
XSynth source file processing classes

### qdsqlite.py
SQLite database utilities

### pdict.py
Dictionary utilities including `DbDictDb` for database-backed dictionaries

### cliargs.py, cliinput.py
Command-line interface utilities

### simplelex.py
Simple lexical analysis

## Why Zero Dependencies?

`qdbase` has no external dependencies to ensure it can be used during bootstrapping before the virtual environment is fully configured.

## Complete Documentation

See the [qdbase README](https://github.com/almargolis/quickdev/blob/master/qdbase/README.md) for complete documentation.

## Next Steps

- **[Quick Start](../howto/quickstart.md)** - Get started with QuickDev
- **[Architecture](../overview/architecture.md)** - How qdbase fits in
