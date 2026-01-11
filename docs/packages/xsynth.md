# xsynth

XSynth preprocessor for code generation.

## Overview

XSynth transforms `.xpy` (XSynth Python) files into standard `.py` files using code generation.

**Features:**

- `#$ dict` declarations for data modeling
- `#$ action` declarations for structured classes
- Template substitution for repetitive patterns
- SQLite database (`xsynth.db`) to track synthesis state

**Version:** 0.3.0
**PyPI:** [pypi.org/project/xsynth](https://pypi.org/project/xsynth/)
**Source:** [GitHub](https://github.com/almargolis/quickdev/tree/master/xsynth)

## Installation

```bash
pip install xsynth
```

## Quick Example

```python
# model.xpy
#$ dict User
    username: str
    email: str
    role: str = 'user'
```

Process with XSynth:

```bash
python -m xsynth model.xpy
```

Generated output:

```python
# model.py (generated)
class User:
    def __init__(self, username, email, role='user'):
        self.username = username
        self.email = email
        self.role = role

    def to_dict(self):
        return {
            'username': self.username,
            'email': self.email,
            'role': self.role
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
```

## Complete Documentation

See the [xsynth README](https://github.com/almargolis/quickdev/blob/master/xsynth/README.md) for complete documentation.

## Guides

- **[XSynth Guide](../guides/xsynth.md)** - Advanced usage
- **[Quick Start](../howto/quickstart.md#xsynth-usage)** - Getting started
- **[Philosophy](../overview/philosophy.md#code-generation-philosophy)** - Why code generation?

## Next Steps

- **[Quick Start - XSynth](../howto/quickstart.md#xsynth-usage)** - Try XSynth
- **[XSynth Guide](../guides/xsynth.md)** - Advanced features
