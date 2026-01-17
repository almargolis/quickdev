"""
Setup script for qdcore package.

qdcore provides core idioms and utilities for QuickDev applications,
including site configuration, execution control, data serialization,
HTML generation, and file handling utilities.
"""

from setuptools import setup

setup(
    name="qdcore",
    version="0.1.0",
    author="Albert Margolis",
    author_email="almargolis@gmail.com",
    description="Core idioms and utilities for QuickDev applications",
    url="https://github.com/almargolis/quickdev",
    project_urls={
        "Bug Tracker": "https://github.com/almargolis/quickdev/issues",
        "Source Code": "https://github.com/almargolis/quickdev/tree/master/qdcore",
    },
    package_dir={'': 'src'},
    packages=['qdcore'],
    install_requires=[
        "qdbase>=0.2.0",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
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
    keywords="utilities development quickdev framework",
)
