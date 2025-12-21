# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuickDev (also referred to as EzDev) is an application development and hosting framework for Python. It includes a preprocessor called XSynth that adds data modeling and structured programming features to Python source files.

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

- **qdcore/**: Core application framework features
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
