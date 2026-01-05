"""
Setup script for qdbase package.

qdbase is the foundation layer of the QuickDev toolkit, providing utilities
for execution environment detection, dictionary operations, SQLite helpers,
CLI utilities, and lexical analysis. It has zero external dependencies
beyond the Python standard library.
"""

from setuptools import setup, find_packages
import os

# Read the README if it exists
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = """
qdbase - Foundation utilities for Python development

A collection of utilities for execution environment management, dictionary
operations, SQLite helpers, CLI tools, and lexical analysis. Part of the
QuickDev metaprogramming toolkit.

Key modules:
- exenv: Execution environment detection and normalization
- pdict: Enhanced dictionary utilities
- qdsqlite: SQLite database helpers
- cliargs, cliinput: Command-line interface utilities
- simplelex: Simple lexical analysis
- xsource: Source file processing

Zero external dependencies - uses only Python standard library.
"""

setup(
    name="qdbase",
    version="0.2.0",
    author="Albert Margolis",
    author_email="albert@quickdev.org",
    description="Foundation utilities for Python development with zero external dependencies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/almargolis/quickdev",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    include_package_data=True,
    install_requires=[
        # Zero external dependencies - stdlib only
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
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
    keywords="utilities development tools dictionary sqlite cli lexer",
)
