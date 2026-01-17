"""
XSynth - A preprocessor for Python that adds data modeling and structured programming.

XSynth transforms .xpy (XSynth Python) files into standard .py files, providing:
- Data modeling with #$ dict declarations
- Structured action/class generation with #$ action declarations
- Template substitution for generating repetitive code patterns
- SQLite database tracking of modules, classes, and dependencies

XSynth has two modes:
1. Stand-alone mode: Processes files with minimal QuickDev dependencies
2. QuickDev mode: Full integration with the QuickDev framework
"""

__version__ = "0.3.0"

# The main XSynth class is in qdutils/xsynth.py for backwards compatibility
# Import it here for package-level access
try:
    import sys
    import os
    # Add parent directory to path to find qdutils
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from qdutils.xsynth import XSynth
    __all__ = ['XSynth']
except ImportError:
    # In development/installation, this might not be available yet
    __all__ = []
