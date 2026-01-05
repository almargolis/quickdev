"""
Setup script for xsynth package.

XSynth is a preprocessor that transforms .xpy files into Python .py files,
adding data modeling and structured programming features.
"""

from setuptools import setup
import os
import sys

# Add parent directory to path to find qdutils
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Read the README if it exists
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = """
XSynth - A preprocessor for Python

XSynth transforms .xpy (XSynth Python) files into standard .py files, providing
data modeling and structured programming features without interfering with
Python fundamentals.

Features:
- Data modeling with #$ dict declarations
- Structured action/class generation with #$ action declarations
- Template substitution for repetitive code patterns
- SQLite database for tracking synthesis state

XSynth can run in stand-alone mode with minimal dependencies or integrate
fully with the QuickDev framework.
"""

setup(
    name="xsynth",
    version="0.3.0",
    author="Albert Margolis",
    author_email="almargolis@gmail.com",
    description="A preprocessor for Python adding data modeling and structured programming",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/almargolis/quickdev",
    project_urls={
        "Bug Tracker": "https://github.com/almargolis/quickdev/issues",
        "Documentation": "https://github.com/almargolis/quickdev/blob/master/xsynth/README.md",
        "Source Code": "https://github.com/almargolis/quickdev/tree/master/xsynth",
    },
    py_modules=["xsynth"],
    install_requires=[
        "qdbase>=0.2.0",  # Requires qdbase foundation
    ],
    extras_require={
        "quickdev": [
            "qdcore",  # Full QuickDev integration
        ],
    },
    entry_points={
        "console_scripts": [
            "xsynth=qdutils.xsynth:main",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Pre-processors",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="preprocessor metaprogramming code-generation data-modeling",
)
