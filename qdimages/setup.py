"""
Setup script for qdimages package.
"""

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="qdimages",
    version="0.1.0",
    author="Albert Margolis",
    author_email="almargolis@gmail.com",
    description="Reusable Flask image management package with hierarchical storage and web-based editor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/almargolis/quickdev",
    project_urls={
        "Bug Tracker": "https://github.com/almargolis/quickdev/issues",
        "Documentation": "https://github.com/almargolis/quickdev/blob/master/qdimages/README.md",
        "Source Code": "https://github.com/almargolis/quickdev/tree/master/qdimages",
    },
    license="MIT",
    package_dir={'': 'src'},
    packages=['qdimages'],
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
