# Quickstart Revision Plan 1

## Original Prompt

The quickstart.md is supposed to be a guide to teach about using QuickDev via example. I find it a bit confusing. It will probably take a few iterations to refine it to meet my goals. I want to start with the following changes. Some of the confusion stems from messy implementation code, so this plan includes QuickDev code changes to make the documentation and code execution as consistent and logical as possible.

- **Overview**: QuickDev is a lightweight application framework that implements application infrastructure with minimal code and maximum flexibility. By using QuickDev, the developer can focus on application code instead of basic mechanics needed for all applications, such as installation, configuration, API, MCP, and tools for managing application secrets and databases. Virtually none of these are requirements. The developer can use QuickDev features or any other implementation method.

- A QuickDev developer must be aware of two types of directory trees: repositories and sites.
    - QuickDev includes utilities to assist in creating and managing both types of directory trees.
    - All code must reside in standard pip-installable repositories.
    - It is an expectation but not a requirement that source code is managed using git.
    - It is an expectation but not a requirement that code is executed within a Python venv.
    - Applications should be thought of as compositions of QuickDev repositories, application-specific repositories, and any other repositories the developer chooses.
    - A site is a directory tree where applications execute. This can be a limited test directory, a full test application directory used by the developer, or a production directory such as `/var/www/app` for a production Apache website.

- Create new utility `qd_make_repo.py`
    - Make use of this utility near the top of quickstart.md.
    - The current quickstart has repository restructuring in Step 6, line 665. This structure should be implemented from the start.
    - In working on QuickDev projects, repository structure has often been a pain point requiring multiple revisions to correct. It should be compatible with pip and pypi.org from the start.
    - In working on QuickDev projects, a common point of confusion when running pytest has been errors caused by use of the wrong venv, or not using a venv when that is the location of a required package. This is resolved here by explicitly identifying the path to a site to be used for the test environment.
        - This could be a unique test site for this repository, a common test site for a group of repositories, or a complete application site.
    - Create starting `.gitignore` and `pytest.ini`.
    - `qd_make_repo.py` parameters:
        - directory path (default: cwd)
        - repository name (default: repository directory name)
        - test directory path (default: `<directory_path>_tests`)
    - Update `ai_skills.md`, `CLAUDE.md`, etc. to reflect this as the normal start of development.

- The discussions of qdboot and qdstart need clarification that they are used to create and manage site directory trees.

---

## Implementation Plan

### Clarifications from discussion

- **Location**: `qd_make_repo.py` lives in `qdutils/src/qdutils/` alongside `qdstart.py`, with a `console_scripts` entry point.
- **Scope**: Creates a minimal repository skeleton (setup.py, `src/` layout, `__init__.py`, `.gitignore`, `pytest.ini`, tests directory). The existing `qdsetup.create_package()` remains available for adding Flask-specific scaffolding on top.
- **Test suffix**: `_tests` (matching existing convention: `qdbase_tests/`, `qdimage_tests/`).
- **Site initialization**: `qd_make_repo` writes `pytest.ini` with the site's venv in `pythonpath`. If the specified site path doesn't exist, `qd_make_repo` calls `qdstart` to initialize it (creating `conf/`, venv, etc.).

### What `qd_make_repo` generates

Given: `qd_make_repo --name todo --site-path /path/to/site`

```
todo/                              # repository root (--directory, default: cwd)
├── setup.py                       # pip-installable, src/ layout
├── src/
│   └── todo/
│       └── __init__.py            # __version__ = '0.1.0'
├── .gitignore                     # Python/QuickDev standard
├── pytest.ini                     # testpaths + pythonpath to site venv
└── todo_tests/                    # test directory (--test-dir, default: <name>_tests)
    └── (empty, ready for tests)
```

### Generated file contents

**setup.py**:
```python
from setuptools import setup
setup(
    name="todo",
    version="0.1.0",
    package_dir={'': 'src'},
    packages=['todo'],
    install_requires=["qdbase>=0.3.0"],
    python_requires=">=3.11",
)
```

**src/todo/__init__.py**:
```python
__version__ = '0.1.0'
```

**pytest.ini**:
```ini
[pytest]
testpaths = todo_tests
pythonpath = /path/to/site/site.venv/lib/python3.11/site-packages
```

The `pythonpath` value is resolved at generation time by locating the site's venv and its Python version. This ensures `pytest` finds packages installed in the site's venv without requiring the developer to activate it first.

**.gitignore**: Standard Python/QuickDev gitignore (matching `qdbase/.gitignore` pattern).

### CLI parameters

| Parameter | Short | Default | Description |
|-----------|-------|---------|-------------|
| `--directory` | `-d` | cwd | Repository root directory (created if needed) |
| `--name` | `-n` | directory name | Package name (must be valid Python identifier) |
| `--test-dir` | `-t` | `<name>_tests` | Test directory path |
| `--site-path` | `-s` | None | Path to QuickDev site (for venv resolution) |
| `--quiet` | `-q` | False | Suppress output |

If `--site-path` is provided and the directory doesn't exist, `qd_make_repo` calls `QdStart` to initialize a minimal site (creates `conf/`, venv). If `--site-path` is omitted, `pytest.ini` is generated without a `pythonpath` entry.

### Phases

#### Phase 1: Create `qd_make_repo.py`

- Add `qdutils/src/qdutils/qd_make_repo.py` with:
  - `MakeRepo` class: validates name, creates directory tree, writes files
  - `main()` function: CLI argument parsing via `cliargs`
  - Site resolution: if `--site-path` given, resolve venv `site-packages` path; if site doesn't exist, call `QdStart` to create it
- Add `qd_make_repo=qdutils.qd_make_repo:main` to `qdutils/setup.py` `console_scripts`
- Reinstall qdutils

#### Phase 2: Create tests

- Add `qdutils_tests/test_qd_make_repo.py`:
  - Test: creates correct directory structure
  - Test: generates valid setup.py, __init__.py, .gitignore, pytest.ini
  - Test: default name from directory name
  - Test: test dir defaults to `<name>_tests`
  - Test: pytest.ini includes pythonpath when site-path given
  - Test: validates package name as Python identifier

#### Phase 3: Update documentation

- Update `quickdev/CLAUDE.md`: add `qd_make_repo` to qdutils module listing
- Update `quickdev/ai_skills.md`: document `qd_make_repo` as the standard way to start a new repository
- Update `quickstart.md`: restructure to use `qd_make_repo` early (new Step 1), move data spec to Step 2, clarify repositories vs. sites and qdboot/qdstart as site management tools
