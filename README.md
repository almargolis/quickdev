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

**qdcomments** - Commenting system idiom
```python
from qdcomments import init_comments
# Generates: Comment model, moderation system, content filtering, email notifications
```

All Flask packages are published on PyPI and work with any Flask application:
```bash
pip install qdflask qdimages qdcomments
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
- **qdcomments/** - Flask commenting system package
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
# Foundation utilities (v0.2.0)
pip install qdbase

# XSynth preprocessor (v0.3.0)
pip install xsynth

# Flask packages (v0.1.0)
pip install qdflask      # User authentication
pip install qdimages     # Image management
pip install qdcomments   # Commenting system
```

Or install all Flask packages at once:

```bash
pip install qdflask qdimages qdcomments
```

Or for development:

```bash
git clone https://github.com/almargolis/quickdev.git
cd quickdev
pip install -e ./qdbase
pip install -e ./xsynth
pip install -e ./qdflask
pip install -e ./qdimages
pip install -e ./qdcomments
```

## Published Packages

| Package | Version | PyPI | Description |
|---------|---------|------|-------------|
| **qdbase** | 0.2.0 | [pypi.org/project/qdbase](https://pypi.org/project/qdbase/) | Foundation utilities with zero dependencies |
| **xsynth** | 0.3.0 | [pypi.org/project/xsynth](https://pypi.org/project/xsynth/) | XSynth preprocessor for code generation |
| **qdflask** | 0.1.0 | [pypi.org/project/qdflask](https://pypi.org/project/qdflask/) | Flask authentication with role-based access |
| **qdimages** | 0.1.0 | [pypi.org/project/qdimages](https://pypi.org/project/qdimages/) | Flask image management with hierarchical storage |
| **qdcomments** | 0.1.0 | [pypi.org/project/qdcomments](https://pypi.org/project/qdcomments/) | Flask commenting system with moderation |

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
