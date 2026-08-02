# Image Cleanup Plan — Extract qdimage core library from qdimages

## Original Prompt

> create new plan /quickdev/image_cleanup_plan.md. /qdflask-repo/qdimages/ contains an installable image editing service for a quickdev flask app. I want to strip out the file handling and image manipulation code and move that to /quickdev/. When complete, it should be possible to develop a cli app that works with the flask web app. Potentially /qdimages/ would not directly import PIL or any other image processing library. No backward compatability or data conversion needs to be provided. Create /quickdev/image_processing.md as developer docuementation for theses features. It should document the .inf file that accompanies each image. Add the capabiity to have multiple description sections to the inf file. Add a function to pass the image to an object identificatgion llm and add the results to the .inf description. The .inf should include the processing date and model accessed. The function should process one image at a time. A working system may utilize multiple llm with different api keys. Include this prompt in image_cleanup_plan.md for reference.

## Context

qdimages (in qdflask-repo) is a Flask extension that bundles image processing, content-addressed storage, and web UI together. This makes it impossible to use the image processing and storage capabilities from a CLI tool. The goal is to extract the framework-independent code into a new `qdimage` package in quickdev, leaving qdimages as a thin Flask wrapper that imports from `qdimage`.

The metadata format changes from YAML sidecar files (.yaml) to TOML-syntax sidecar files (.inf), with support for multiple description sections and LLM-based image identification.

## Architecture After Restructuring

```
quickdev/qdimage/src/qdimage/        NEW — core library (no Flask)
├── __init__.py                      Package init
├── editor.py                        Image editing (from qdimages/editor.py)
├── fileops.py                       File I/O (from qdimages/file_handler.py)
├── hasher.py                        xxHash calculation (from storage.py)
├── infmeta.py                       .inf metadata read/write (NEW, replaces YAML)
├── storage.py                       Content-addressed storage (refactored to use QdSqlite)
├── llmproviders.py                  LLM provider base class + Anthropic/OpenAI (NEW)
└── llmdescribe.py                   Single-image LLM description function (NEW)

quickdev/qdimage_tests/              NEW — tests
qdflask-repo/qdimages/src/qdimages/  MODIFIED — Flask wrapper only
├── __init__.py                      init_image_manager(), blueprint (kept)
├── routes.py                        Flask routes (imports changed to qdimage)
├── models.py                        SQLAlchemy models (kept, Flask-specific)
├── templates/image_editor.html      Web UI (kept)
└── qd_conf.toml                     qdstart config (kept)
```

Deleted from qdflask-repo: `editor.py`, `file_handler.py`, `storage.py`

### Dependencies

```
qdbase (zero external deps)
  ↓
qdimage (qdbase, Pillow, xxhash; optional: anthropic, openai, rembg)
  ↓
qdimages (qdimage, Flask, Flask-SQLAlchemy, Flask-Login)
```

## Phases

### Phase 1: Create qdimage package skeleton + write plan/docs
- Create `quickdev/qdimage/setup.py`, `src/qdimage/__init__.py`, `README.md`
- Write `quickdev/image_cleanup_plan.md` (this plan with original prompt)
- Write `quickdev/image_processing.md` (developer docs with .inf spec)

### Phase 2: Migrate pure modules (no behavior change)
- `qdimage/editor.py` — Copy verbatim from `qdimages/editor.py` (206 lines, pure PIL)
- `qdimage/fileops.py` — Copy from `qdimages/file_handler.py` (200 lines, pure PIL). Change default_directory from `/commercenode/test_images` to `None`
- `qdimage/hasher.py` — Extract `calculate_xxhash()` from `storage.py`. Drop SHA1
- Create `qdimage_tests/test_editor.py`, `test_fileops.py`, `test_hasher.py`

### Phase 3: Build .inf metadata system (new)
- `qdimage/infmeta.py` — `InfMeta` class: `from_image_path()`, `create_new()`, `load()`, `save()`, `add_description()`, `get_descriptions()`
- Uses `tomllib` for reading, `qdos.write_toml()` for writing
- Create `qdimage_tests/test_infmeta.py` — round-trip, multiple descriptions, key generation

### Phase 4: Migrate storage module
- `qdimage/storage.py` — Refactor from direct sqlite3 to QdSqlite (from qdbase). Define schema with pdict. Replace YAML output with InfMeta. Drop SHA1
- Same public API: `ImageStorage(base_path, db_path)`, `save_image_with_metadata()`, `check_duplicate()`, `get_image_by_id()`, `get_image_by_hash()`
- Create `qdimage_tests/test_storage.py`

### Phase 5: Build LLM integration (new)
- `qdimage/llmproviders.py` — Provider base class, Anthropic/OpenAI implementations, registry
- `qdimage/llmdescribe.py` — `describe_image()` single-image function
- Create `qdimage_tests/test_llmproviders.py`, `test_llmdescribe.py` (mock-based)

### Phase 6: Update qdimages Flask wrapper
- Delete `qdimages/editor.py`, `file_handler.py`, `storage.py`
- Update `qdimages/routes.py` imports: `from qdimage.editor import ImageEditor`, `from qdimage.fileops import ImageFileHandler`, `from qdimage.storage import ImageStorage`
- Update `qdimages/setup.py`: add `qdimage>=0.1.0`, remove `Pillow`, `xxhash`, `PyYAML`
- Update `qdimages/check_images.py` to delegate to qdimage

### Phase 7: Update documentation
- Update quickdev `CLAUDE.md` and `ai_skills.md` with qdimage package
- Update qdflask-repo `CLAUDE.md` and `ai_skills.md` to reflect qdimages is now a thin wrapper

## Verification

After each phase, run tests:
```bash
pytest qdimage_tests/                    # qdimage tests (phases 2-5)
pytest qdimages_tests/                   # qdimages tests (phase 6)
pip install -e ./qdimage && pip install -e ../qdflask-repo/qdimages  # integration
```
