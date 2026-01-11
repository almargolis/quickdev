# XSynth Preprocessor

Advanced code generation with XSynth.

!!! note "Coming Soon"
    Comprehensive XSynth guide. Migrating content from `sphinx/docs/xsynth.rst`.

## Overview

XSynth transforms `.xpy` files into standard `.py` files using code generation.

## Basic Usage

```bash
# Process XSynth files
python -m xsynth model.xpy
```

## Quick Example

```python
# model.xpy
#$ dict User
    username: str
    email: str
    role: str = 'user'
```

Generates:

```python
# model.py
class User:
    def __init__(self, username, email, role='user'):
        self.username = username
        self.email = email
        self.role = role

    def to_dict(self):
        return {...}

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
```

## Documentation

- **[XSynth Package](../packages/xsynth.md)** - Package documentation
- **[Quick Start - XSynth Usage](../howto/quickstart.md#xsynth-usage)** - Getting started
