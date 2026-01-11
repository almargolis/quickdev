# QuickDev Documentation

**Code generation and DRY idioms for Python web applications**

QuickDev is a metaprogramming toolkit that eliminates boilerplate through preprocessor-based code generation. Rather than competing with frameworks like Flask or Django, QuickDev works alongside them - generating the repetitive code you'd otherwise write by hand.

## Quick Links

### :zap: Quick Start
Get started with QuickDev in minutes
→ [Quick Start Guide](howto/quickstart.md)

### :package: Flask Integration
Add auth, images, and comments to Flask apps
→ [Flask Packages](guides/flask-integration.md)

### :wrench: Site Management
Deploy and manage QuickDev sites
→ [Site Setup](howto/site-setup.md)

### :computer: XSynth Preprocessor
Generate Python from high-level declarations
→ [XSynth Guide](guides/xsynth.md)

## What Makes QuickDev Different

**Not a framework** - QuickDev is a collection of idioms and utilities that complement your existing tools.

**XSynth Preprocessor** - Transforms `.xpy` files into standard Python, using:

- Data modeling with `#$ dict` declarations
- Structured class generation with `#$ action` declarations
- Template substitution for repetitive code patterns
- Dictionary-based introspection to auto-generate boilerplate

**DRY Taken Further** - Uses Python dictionaries and introspection to capture patterns once and generate code, not just reuse it.

## Published Packages

QuickDev packages are published on PyPI and can be installed individually:

| Package | Version | Description |
|---------|---------|-------------|
| **[qdbase](packages/qdbase.md)** | 0.2.0 | Foundation utilities with zero dependencies |
| **[xsynth](packages/xsynth.md)** | 0.3.0 | XSynth preprocessor for code generation |
| **[qdflask](packages/qdflask.md)** | 0.1.0 | Flask authentication with role-based access |
| **[qdimages](packages/qdimages.md)** | 0.1.0 | Flask image management with hierarchical storage |
| **[qdcomments](packages/qdcomments.md)** | 0.1.0 | Flask commenting system with moderation |

Install packages individually:

```bash
pip install qdbase xsynth
pip install qdflask qdimages qdcomments
```

## Installation

For package usage, install from PyPI:

```bash
# Foundation and preprocessor
pip install qdbase xsynth

# Flask integration packages
pip install qdflask qdimages qdcomments
```

For development:

```bash
git clone https://github.com/almargolis/quickdev.git
cd quickdev
pip install -e ./qdbase -e ./xsynth
pip install -e ./qdflask -e ./qdimages -e ./qdcomments
```

## Why Use QuickDev?

- **Reduce boilerplate** - Data models, CRUD operations, web forms - let XSynth generate them
- **Decades of patterns** - Captures idioms refined since the 1990s
- **Works with existing code** - Use as much or as little as you need
- **Python throughout** - Generated code is readable, standard Python

## Next Steps

- **New to QuickDev?** Start with the [Quick Start Guide](howto/quickstart.md)
- **Using Flask?** Check out the [Flask Integration Guide](guides/flask-integration.md)
- **Managing servers?** Read about [Site Structure](guides/site-structure.md) and [Apache Configuration](howto/apache-config.md)
- **Want the philosophy?** See [Overview](overview/philosophy.md)

## Contributing

QuickDev is open source! Contributions are welcome.

1. Fork the [repository](https://github.com/almargolis/quickdev)
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - See [LICENSE](https://github.com/almargolis/quickdev/blob/master/LICENSE) file for details.
