# QuickDev

**DRY idioms and code generation for Python web applications**

QuickDev is a metaprogramming toolkit that eliminates boilerplate. Rather than competing with frameworks like Flask or Django, QuickDev works alongside them - generating the repetitive code you'd otherwise write by hand, and providing a plug-in architecture that lets packages configure themselves.

## The Plug-in System

QuickDev's most distinctive feature is its **self-declaring plug-in architecture**. Every QuickDev package ships a `qd_conf.toml` file that declares:

- **What questions to ask** during site setup (with types: boolean, path, string, auto-generated secrets)
- **What answers to pre-supply** (sensible defaults the user never needs to think about)
- **How to wire into Flask** (init functions, parameter bindings, execution priority)

When you run `qdstart`, it scans all installed packages, discovers their `qd_conf.toml` files, and walks you through configuration - asking only the questions that matter, skipping packages you disable, and auto-generating values like secret keys.

### How It Works

1. **Discovery** - `qdstart` scans installed packages and repositories for `qd_conf.toml` files
2. **Questions** - Each package declares its own configuration questions (the package author knows what to ask, not the framework)
3. **Smart prompting** - Boolean "enabled" questions gate everything below them. Say "no" to `qdflask.enabled` and its other questions are skipped entirely
4. **Auto-generation** - Secret keys, tokens, and other `random_fill` values are generated automatically
5. **Partitioned output** - Answers are auto-partitioned by dot-notation into separate config files: `qdflask.roles` goes to `conf/qdflask.toml`, `denv.SMTP_PW` goes to `conf/.env`

### Real Example: qdflask's `qd_conf.toml`

This is the actual file shipped inside the qdflask package:

```toml
[questions.qdflask.enabled]
help = "Enable Flask authentication? (qdflask)"
conf_type = "boolean"

[questions.qdflask.roles]
help = "Comma-separated user roles (must include admin)"

[questions.qdflask.login_view]
help = "Flask endpoint name for login redirect"

[questions.qdflask.passwordsdb_fpath]
help = "Path to the passwords database file"
conf_type = "fpath"

[questions.denv.FLASK_SECRET_KEY]
help = "Secret key for Flask session signing"
conf_type = "random_fill"

[flask.init_function]
module = "qdflask"
function = "init_auth"
priority = 10

[flask.init_function.params.roles]
source = "answer"
key = "qdflask.roles"
type = "list"
default = "['admin', 'editor']"
```

The package author writes this once. The framework handles discovery, prompting, config file generation, and Flask wiring - all automatically.

## Answer Files: Reproducible Installs

The `-a` flag lets you replay a configuration non-interactively:

```bash
# First machine: answer questions interactively, save the results
# (answers are written to conf/*.toml files)

# Second machine: replay those same answers
python qdutils/qdstart.py -a answers.toml
```

An answer file is plain TOML with the same dot-notation:

```toml
[qdflask]
enabled = true
roles = "admin, editor, reader"
login_view = "auth.login"

[qdimages]
enabled = true
storage_path = "/var/data/images"
```

This makes site setup **fully reproducible** - deploy to staging, production, or a teammate's machine with one command and zero interactive prompts. First answer wins, so you can layer multiple answer files for environment-specific overrides:

```bash
python qdutils/qdstart.py -a base.toml -a production.toml
```

## Flask Integration Packages

QuickDev includes reusable Flask packages that demonstrate the plug-in architecture:

**qdflask** - User authentication idiom
```python
from qdflask import init_auth
# Provides: User model, login/logout routes, role-based access control, CLI tools
```

**qdimages** - Image management idiom
```python
from qdimages import init_image_manager
# Provides: 16 API endpoints, content-addressed storage, web-based editor, metadata tracking
```

**qdcomments** - Commenting system idiom
```python
from qdcomments import init_comments
# Provides: Comment model, moderation system, content filtering, email notifications
```

Each package ships its own `qd_conf.toml`, so installing a new package automatically extends `qdstart` with that package's configuration questions - no registration step required.

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

## XSynth Preprocessor

QuickDev also includes XSynth, a preprocessor that transforms `.xpy` files into standard Python:

- Data modeling with `#$ dict` declarations
- Structured class generation with `#$ action` declarations
- Template substitution for repetitive code patterns
- Dictionary-based introspection to auto-generate boilerplate

XSynth extends DRY beyond runtime code reuse into compile-time code generation - capturing patterns as declarations that produce readable, standard Python.

```bash
# Process XSynth files (.xpy -> .py)
python qdutils/xsynth.py
```

## Key Components

- **qdbase/** - Foundation utilities (minimal dependencies)
- **qdcore/** - Core idioms (databases, HTML generation, HTTP automation)
- **qdflask/** - Flask authentication package
- **qdimages/** - Flask image management package
- **qdcomments/** - Flask commenting system package
- **qdutils/** - Development tools (XSynth preprocessor, site initialization)

## Getting Started

```bash
# Install packages
pip install qdbase qdflask qdimages qdcomments

# Initialize a site (interactive)
python qdutils/qdstart.py

# Or initialize from an answer file (non-interactive)
python qdutils/qdstart.py -a answers.toml

# Run tests
pytest
```

## History

QuickDev has been in development since the 1990s, evolving from a C library to the current Python toolkit. Recently moved to open source to share patterns refined over three decades of development.

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

## Documentation

- [Package Architecture](PACKAGING.md) - Multi-package structure and publishing
- [Claude Code Guide](CLAUDE.md) - Project instructions for AI assistants
- Individual package READMEs in each subdirectory
