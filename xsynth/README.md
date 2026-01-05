# XSynth

A preprocessor for Python that adds data modeling and structured programming features.

## Overview

XSynth transforms `.xpy` (XSynth Python) files into standard `.py` files, providing declarative data modeling and code generation capabilities without interfering with Python fundamentals.

## Features

- **Data Modeling**: Define data structures with `#$ dict` declarations
- **Structured Actions**: Generate classes and methods with `#$ action` declarations
- **Template Substitution**: Generate repetitive code patterns automatically
- **Synthesis Tracking**: SQLite database tracks modules, classes, and dependencies
- **Two Modes**: Stand-alone (minimal deps) or QuickDev integration (full features)

## Installation

```bash
pip install xsynth
```

Or install in development mode:

```bash
pip install -e ./xsynth
```

XSynth requires `qdbase` which will be installed automatically.

## Usage

### Command Line

Process all `.xpy` files in a directory:

```bash
xsynth
```

Process specific files:

```bash
xsynth file1.xpy file2.xpy
```

### Python API

```python
from qdutils.xsynth import XSynth

# Create XSynth instance
synth = XSynth(
    sources=['my_module.xpy'],
    verbose=True
)

# Process files
synth.run()
```

## XSynth File Format

XSynth files use the `.xpy` extension and contain special directives:

```python
#$ dict UserData
#$   name: str
#$   email: str
#$   created: datetime

#$ action CreateUser
#$   params: UserData
#$   returns: User
```

These directives are processed by XSynth to generate Python code with proper class definitions, type hints, and boilerplate.

## Modes

### Stand-alone Mode
- Minimal dependencies (only `qdbase`)
- Processes `.xpy` files in specified directories
- Suitable for any Python project

### QuickDev Mode
- Full integration with QuickDev framework
- Access to site configuration
- Enhanced code generation features

## Part of QuickDev

XSynth is part of the QuickDev metaprogramming toolkit. Other packages include:
- **qdbase** - Foundation utilities (required dependency)
- **qdflask** - Flask authentication with role-based access control
- **qdimages** - Flask image management with hierarchical storage

## License

MIT License - Copyright (C) Albert B. Margolis

## Requirements

- Python >= 3.7
- qdbase >= 0.2.0
