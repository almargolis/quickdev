"""
Setup script for qdflask package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="qdflask",
    version="0.1.0",
    author="Albert Margolis",
    author_email="almargolis@gmail.com",
    description="Reusable Flask authentication package with role-based access control",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/almargolis/quickdev",
    project_urls={
        "Bug Tracker": "https://github.com/almargolis/quickdev/issues",
        "Documentation": "https://github.com/almargolis/quickdev/blob/master/qdflask/README.md",
        "Source Code": "https://github.com/almargolis/quickdev/tree/master/qdflask",
    },
    license="MIT",
    package_dir={'': 'src'},
    packages=['qdflask'],
    include_package_data=True,
    package_data={
        'qdflask': [
            'templates/qdflask/*.html',
            'static/*',
            'conf/email.toml.example',
        ],
    },
    install_requires=[
        "Flask>=2.0.0",
        "Flask-SQLAlchemy>=2.5.0",
        "Flask-Login>=0.5.0",
        "Flask-Mail>=0.9.1",
        "Werkzeug>=2.0.0",
        "PyYAML>=5.0",  # Used by qdyaml for data files
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
