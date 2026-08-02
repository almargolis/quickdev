"""
qdimage - Core image processing library for QuickDev

Framework-independent image editing, content-addressed storage with xxHash,
.inf metadata sidecars, and LLM-based image description.

Modules:
    editor      - Image editing (crop, resize, brightness, background removal)
    fileops     - File I/O operations for images
    hasher      - xxHash calculation for content addressing
    infmeta     - .inf metadata sidecar read/write
    storage     - Content-addressed image storage with QdSqlite
    llmproviders - LLM provider base class and implementations
    llmdescribe  - Single-image LLM description function
"""

__version__ = '0.1.0'
