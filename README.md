# QuickDev

**Code generation and DRY idioms for Python web applications**

QuickDev is a metaprogramming toolkit that eliminates boilerplate through preprocessor-based code generation. Rather than competing with frameworks like Flask or Django, QuickDev works alongside them - generating the repetitive code you'd otherwise write by hand.

## What Makes QuickDev Different

**Not a framework** - QuickDev is a collection of idioms and utilities that complement your existing tools.

**XSynth Preprocessor** - Transforms `.xpy` files into standard Python, using:
- Data modeling with `#$ dict` declarations
- Structured class generation with `#$ action` declarations
- Template substitution for repetitive code patterns
- Dictionary-based introspection to auto-generate boilerplate

**DRY Taken Further** - Uses Python dictionaries and introspection to capture patterns once and generate code, not just reuse it.

## Concrete Examples

### Flask Integration Packages

**qdflask** - User authentication idiom
```python
from qdflask import init_auth
# Generates: User model, login/logout routes, role-based access control, CLI tools
```

**qdimages** - Image management idiom
```python
from qdimages import init_image_manager
# Generates: 16 API endpoints, content-addressed storage, web-based editor, metadata tracking
```

Both packages are installable and work with any Flask application:
```bash
pip install -e ./qdflask
pip install -e ./qdimages
```

## Why Use QuickDev?

- **Reduce boilerplate** - Data models, CRUD operations, web forms - let XSynth generate them
- **Decades of patterns** - Captures idioms refined since the 1990s
- **Works with existing code** - Use as much or as little as you need
- **Python throughout** - Generated code is readable, standard Python

## Key Components

- **qdbase/** - Foundation utilities (minimal dependencies)
- **qdcore/** - Core idioms (databases, HTML generation, HTTP automation)
- **qdflask/** - Flask authentication package
- **qdimages/** - Flask image management package
- **qdutils/** - Development tools (XSynth preprocessor, site initialization)

## Getting Started

```bash
# Activate virtual environment
source ezdev.venv/bin/activate

# Process XSynth files (.xpy → .py)
python qdutils/xsynth.py

# Run tests
pytest
```

## Development Philosophy

QuickDev encapsulates common patterns as idioms - reusable code that eliminates repetition. The XSynth preprocessor uses dictionaries and introspection to generate Python code from high-level declarations, extending DRY principles beyond runtime code reuse into compile-time code generation.

Perfect for developers who:
- Are tired of writing the same CRUD code
- Want to capture their own patterns as reusable idioms
- Appreciate metaprogramming without magic

## Installation

QuickDev packages can be installed individually from PyPI:

```bash
# Foundation utilities
pip install qdbase

# XSynth preprocessor
pip install xsynth

# Flask authentication
pip install qdflask

# Flask image management
pip install qdimages
```

Or for development:

```bash
git clone https://github.com/almargolis/quickdev.git
cd quickdev
pip install -e ./qdbase
pip install -e ./xsynth
pip install -e ./qdflask
pip install -e ./qdimages
```

## Documentation

- [Package Architecture](PACKAGING.md) - Multi-package structure and publishing
- [Claude Code Guide](CLAUDE.md) - Project instructions for AI assistants
- Individual package READMEs in each subdirectory

## License

MIT License - See [LICENSE](LICENSE) file for details.

Copyright (c) 2001-2026 Albert B. Margolis

## Contributing

QuickDev is now open source! Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## History

QuickDev has been in development since the 1990s, evolving from a C library to the current Python toolkit. Recently moved to open source to share patterns refined over three decades of development.
