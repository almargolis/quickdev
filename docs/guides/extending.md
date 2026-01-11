# Extending QuickDev

Build your own idioms and contribute to QuickDev.

!!! note "Coming Soon"
    Guide for creating custom QuickDev packages and contributing.

## Overview

QuickDev is extensible - you can create your own idioms following the same patterns as qdflask, qdimages, and qdcomments.

## Package Structure

```
my_package/
├── __init__.py          # Exports init_my_feature()
├── models.py            # SQLAlchemy models
├── routes.py            # Flask blueprint
├── templates/           # Jinja templates
├── static/              # CSS, JS
├── setup.py             # PyPI package metadata
└── README.md            # Documentation
```

## Contributing

QuickDev is open source! Contributions welcome:

1. Fork [the repository](https://github.com/almargolis/quickdev)
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

See [GitHub repository](https://github.com/almargolis/quickdev) for details.
