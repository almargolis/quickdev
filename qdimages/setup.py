"""
Setup script for qdimages package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="qdimages",
    version="0.1.0",
    author="QuickDev",
    description="Reusable Flask image management package with hierarchical storage and web-based editor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'qdimages': [
            'templates/*.html',
            'static/*',
        ],
    },
    install_requires=[
        "Flask>=2.0.0",
        "Flask-SQLAlchemy>=2.5.0",
        "Flask-Login>=0.5.0",
        "Pillow>=9.0.0",
        "xxhash>=3.0.0",
        "PyYAML>=6.0",
        "rembg>=2.0.0",  # For background removal
        "Werkzeug>=2.0.0",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Framework :: Flask",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
