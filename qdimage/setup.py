"""
Setup script for qdimage package.

qdimage provides core image processing, content-addressed storage, and
LLM-based image description capabilities. It is framework-independent
and can be used from CLI tools or web applications.
"""

from setuptools import setup
import os

readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = """
qdimage - Core image processing library for QuickDev

Framework-independent image editing, content-addressed storage, and
LLM-based image description. Extracted from qdimages to enable CLI usage.
"""

setup(
    name="qdimage",
    version="0.1.0",
    author="Albert Margolis",
    author_email="almargolis@gmail.com",
    description="Core image processing, storage, and LLM description for QuickDev",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/almargolis/quickdev",
    project_urls={
        "Bug Tracker": "https://github.com/almargolis/quickdev/issues",
        "Documentation": "https://github.com/almargolis/quickdev/blob/master/qdimage/README.md",
        "Source Code": "https://github.com/almargolis/quickdev/tree/master/qdimage",
    },
    license="MIT",
    package_dir={'': 'src'},
    packages=['qdimage'],
    install_requires=[
        "qdbase>=0.3.0",
        "Pillow>=9.0.0",
        "xxhash>=3.0.0",
    ],
    extras_require={
        "llm": ["anthropic", "openai"],
        "rembg": ["rembg>=2.0.0"],
    },
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="image processing storage hash llm description",
)
