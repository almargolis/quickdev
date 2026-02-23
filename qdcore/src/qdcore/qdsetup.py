"""
qdcore.qdsetup - Package scaffolding for QuickDev

Generates the boilerplate directory structure, setup.py, __init__.py,
qd_conf.toml, and other standard files for new QuickDev packages.

Supports two modes:
- Flask packages: Full web package with blueprint, routes, models, templates
- Library packages: Minimal package with just __init__.py and qd_conf.toml

Usage:
    from qdcore.qdsetup import create_package

    # Flask package
    result = create_package('/path/to/site', 'qdanalytics', is_flask=True,
                            description='Analytics dashboard for QuickDev')

    # Library package
    result = create_package('/path/to/site', 'qdutils', is_flask=False)
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from qdbase import qdos


@dataclass
class PackageResult:
    """Result of a create_package() operation."""
    success: bool = False
    package_path: str = ""
    files_created: List[str] = field(default_factory=list)
    dirs_created: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# --- Naming helpers ---

def _derive_short_name(package_name):
    """Strip 'qd' prefix if present: qdanalytics -> analytics."""
    if package_name.startswith("qd") and len(package_name) > 2:
        return package_name[2:]
    return package_name


def _derive_display_name(short_name):
    """Title-case the short_name: analytics -> Analytics."""
    return short_name.title()


def _derive_checker_class_name(short_name):
    """PascalCase + Checker: analytics -> AnalyticsChecker."""
    return short_name.title() + "Checker"


# --- Internal helpers ---

def _write_file(filepath, content, result):
    """Write text to a file and track it in result."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        result.files_created.append(filepath)
    except OSError as e:
        result.errors.append(f"Failed to write {filepath}: {e}")


def _make_dirs(dir_list, result):
    """Create directories and track them in result."""
    for name, path in dir_list:
        try:
            os.makedirs(path, exist_ok=True)
            result.dirs_created.append(path)
        except OSError as e:
            result.errors.append(f"Failed to create directory {path}: {e}")


# --- Content generators ---

def _gen_setup_py(package_name, version, description, author,
                  author_email, is_flask, flask_dependencies,
                  install_requires):
    """Generate setup.py content matching qdflask/qdimages pattern."""
    desc = description or f"QuickDev {package_name} package"

    deps = []
    if is_flask:
        if flask_dependencies is not None:
            deps.extend(flask_dependencies)
        else:
            deps.extend([
                "Flask>=2.0.0",
                "Flask-SQLAlchemy>=2.5.0",
                "Werkzeug>=2.0.0",
            ])
    if install_requires:
        deps.extend(install_requires)

    deps_str = ""
    if deps:
        items = ",\n        ".join(f'"{d}"' for d in deps)
        deps_str = f"""
    install_requires=[
        {items},
    ],"""

    pkg_data = ""
    if is_flask:
        pkg_data = f"""
    package_data={{
        '{package_name}': [
            'templates/{package_name}/*.html',
            'static/*',
            'conf/*.example',
        ],
    }},"""

    return f'''"""
Setup script for {package_name} package.
"""

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="{package_name}",
    version="{version}",
    author="{author}",
    author_email="{author_email}",
    description="{desc}",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    package_dir={{'': 'src'}},
    packages=['{package_name}'],
    include_package_data=True,{pkg_data}{deps_str}
    python_requires=">=3.7",
)
'''


def _gen_init_py_flask(package_name, short_name, display_name, version,
                       init_function_name, blueprint_name, url_prefix):
    """Generate Flask-mode __init__.py matching qdimages pattern."""
    return f'''"""
{package_name} - QuickDev {display_name} Package

Usage:
    from flask import Flask
    from {package_name} import {init_function_name}

    app = Flask(__name__)
    {init_function_name}(app)
"""

from flask import Blueprint

__version__ = '{version}'
__all__ = ['{init_function_name}', '{blueprint_name}']

{blueprint_name} = Blueprint(
    '{short_name}',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='{url_prefix}'
)


def {init_function_name}(app, db_instance=None):
    """
    Initialize {short_name} for a Flask application.

    Args:
        app: Flask application instance
        db_instance: Optional SQLAlchemy db instance to reuse
    """
    from {package_name}.models import db

    if db_instance:
        pass  # Use the shared db instance
    else:
        db.init_app(app)

    with app.app_context():
        db.create_all()

    from {package_name} import routes  # noqa: F401
    app.register_blueprint({blueprint_name})

    app.logger.info(f"{package_name} initialized (v{{__version__}})")
'''


def _gen_init_py_library(package_name, version, description):
    """Generate library-mode __init__.py."""
    desc = description or f"QuickDev {package_name} package"
    return f'''"""
{package_name} - {desc}
"""

__version__ = '{version}'
'''


def _gen_qd_conf_data(package_name, short_name, is_flask,
                      init_function_name, priority):
    """Generate qd_conf.toml data dict for qdos.write_toml()."""
    data = {
        "questions": {
            package_name: {
                "enabled": {
                    "help": f"Enable {short_name}? ({package_name})",
                    "conf_type": "boolean",
                }
            }
        }
    }
    if is_flask:
        data["flask"] = {
            "init_function": {
                "module": package_name,
                "function": init_function_name,
                "priority": priority,
            }
        }
    return data


def _gen_routes_py(package_name, short_name, blueprint_name):
    """Generate routes.py with a single index route."""
    return f'''"""
{package_name}.routes - URL routes for {short_name}
"""

from flask import render_template
from {package_name} import {blueprint_name}


@{blueprint_name}.route('/')
def index():
    """Index page for {short_name}."""
    return render_template('{package_name}/index.html')
'''


def _gen_models_py(package_name, short_name):
    """Generate models.py with SQLAlchemy db instance."""
    return f'''"""
{package_name}.models - Database models for {short_name}
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
'''


def _gen_cli_py(package_name, short_name):
    """Generate cli.py with argparse skeleton."""
    return f'''#!/usr/bin/env python3
"""
{package_name}.cli - Command-line utilities for {short_name}
"""

import argparse
import sys


def main():
    """CLI entry point for {package_name}."""
    parser = argparse.ArgumentParser(
        description='{package_name} command-line utilities'
    )
    parser.add_argument('--conf', metavar='DIR',
                        help='Path to conf directory')
    args = parser.parse_args()

    print(f"{package_name} CLI (conf={{args.conf}})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
'''


def _gen_check_module(package_name, short_name, display_name,
                      checker_class_name):
    """Generate check module subclassing CheckRunner."""
    return f'''#!/usr/bin/env python3
"""
Check {package_name} configuration.

Usage:
    python -m {package_name}.check_{short_name}           # Validate only
    python -m {package_name}.check_{short_name} --test    # Validate and test
    python -m {package_name}.check_{short_name} --fix     # Validate and fix issues
    python -m {package_name}.check_{short_name} --conf /path/to/conf
"""

import sys
import os

try:
    from qdbase.qdcheck import CheckRunner, CheckResult, CheckStatus, CheckMode
except ModuleNotFoundError:
    quickdev_path = os.path.join(os.path.dirname(__file__), '../../..')
    sys.path.insert(0, os.path.join(quickdev_path, 'qdbase'))
    from qdbase.qdcheck import CheckRunner, CheckResult, CheckStatus, CheckMode


class {checker_class_name}(CheckRunner):
    """{display_name} configuration checker."""

    service_name = "{package_name}"
    service_display_name = "{display_name}"
    config_filename = "{package_name}.toml"

    def _run_checks(self):
        """Run all {short_name} checks."""
        self._check_config()

    def _check_config(self):
        """Check that configuration is present."""
        self.add_result(CheckResult(
            name="Configuration",
            status=CheckStatus.PASS,
            message="Basic configuration present"
        ))


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Check {package_name} configuration'
    )
    parser.add_argument('--test', action='store_true',
                        help='Run functional tests')
    parser.add_argument('--fix', action='store_true',
                        help='Fix issues if possible')
    parser.add_argument('--conf', metavar='DIR',
                        help='Path to conf directory')
    args = parser.parse_args()

    if args.fix:
        mode = CheckMode.CORRECT
    elif args.test:
        mode = CheckMode.TEST
    else:
        mode = CheckMode.VALIDATE

    checker = {checker_class_name}(conf_dir=args.conf, mode=mode)
    checker.run_all()
    checker.print_results()

    sys.exit(0 if checker.success else 1)


if __name__ == '__main__':
    main()
'''


def _gen_yaml_example(package_name, short_name, display_name):
    """Generate conf/<name>.yaml.example."""
    return f"""# {display_name} Configuration
# Copy this file to your site's conf/{package_name}.yaml

# Service enabled flag - set to false to skip {package_name} checks
service_enabled: true
"""


def _gen_readme(package_name, short_name, display_name, description,
                is_flask, init_function_name):
    """Generate README.md."""
    desc = description or f"QuickDev {display_name} package"

    if is_flask:
        return f"""# {package_name} - QuickDev {display_name}

{desc}

## Installation

```bash
pip install -e ./{package_name}
```

## Quick Start

```python
from flask import Flask
from {package_name} import {init_function_name}

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'your-secret-key'

{init_function_name}(app)

if __name__ == '__main__':
    app.run(debug=True)
```
"""
    else:
        return f"""# {package_name} - QuickDev {display_name}

{desc}

## Installation

```bash
pip install -e ./{package_name}
```

## Usage

```python
import {package_name}
```
"""


# --- Main public function ---

def create_package(
    dpath,
    package_name,
    is_flask,
    description=None,
    author="",
    author_email="",
    version="0.1.0",
    flask_dependencies=None,
    install_requires=None,
    url_prefix=None,
    init_function_name=None,
    blueprint_name=None,
    priority=50,
    include_check_module=None,
    include_cli=None,
):
    """
    Create a new QuickDev package with standard scaffolding.

    Args:
        dpath: Site root directory (must exist)
        package_name: Package name (e.g. "qdanalytics")
        is_flask: True for Flask package, False for library
        description: One-line description
        author: Author name
        author_email: Author email
        version: Package version string
        flask_dependencies: Override default Flask deps list
        install_requires: Additional pip dependencies
        url_prefix: Flask URL prefix (default: /<short_name>)
        init_function_name: Override init function name
        blueprint_name: Override blueprint variable name
        priority: Flask init priority in qd_conf.toml
        include_check_module: Generate check module (default: True for Flask)
        include_cli: Generate cli.py (default: True for Flask)

    Returns:
        PackageResult with success, paths, and errors
    """
    result = PackageResult()

    # --- Input validation ---
    if not package_name.isidentifier():
        result.errors.append(
            f"'{package_name}' is not a valid Python identifier")
        return result

    if not os.path.isdir(dpath):
        result.errors.append(f"'{dpath}' is not an existing directory")
        return result

    pkg_root = os.path.join(dpath, package_name)
    if os.path.exists(pkg_root):
        result.errors.append(
            f"'{pkg_root}' already exists; will not overwrite")
        return result

    result.package_path = pkg_root

    # --- Derive names ---
    short_name = _derive_short_name(package_name)
    display_name = _derive_display_name(short_name)
    checker_class_name = _derive_checker_class_name(short_name)

    if init_function_name is None:
        init_function_name = f"init_{short_name}"
    if blueprint_name is None:
        blueprint_name = f"{short_name}_bp"
    if url_prefix is None:
        url_prefix = f"/{short_name}"
    if include_check_module is None:
        include_check_module = is_flask
    if include_cli is None:
        include_cli = is_flask

    # --- Create directories ---
    src_pkg = os.path.join(pkg_root, "src", package_name)

    dirs = [
        ("package root", pkg_root),
        ("src", os.path.join(pkg_root, "src")),
        ("src package", src_pkg),
    ]

    if is_flask:
        dirs.extend([
            ("conf", os.path.join(src_pkg, "conf")),
            ("templates", os.path.join(src_pkg, "templates")),
            ("templates pkg", os.path.join(src_pkg, "templates", package_name)),
            ("static", os.path.join(src_pkg, "static")),
        ])

    _make_dirs(dirs, result)

    # Bail early if directory creation had errors
    if result.errors:
        result.success = False
        return result

    # --- Generate files ---

    # setup.py
    _write_file(
        os.path.join(pkg_root, "setup.py"),
        _gen_setup_py(package_name, version, description, author,
                      author_email, is_flask, flask_dependencies,
                      install_requires),
        result,
    )

    # README.md
    _write_file(
        os.path.join(pkg_root, "README.md"),
        _gen_readme(package_name, short_name, display_name, description,
                    is_flask, init_function_name),
        result,
    )

    # __init__.py
    if is_flask:
        init_content = _gen_init_py_flask(
            package_name, short_name, display_name, version,
            init_function_name, blueprint_name, url_prefix)
    else:
        init_content = _gen_init_py_library(package_name, version,
                                            description)
    _write_file(os.path.join(src_pkg, "__init__.py"), init_content, result)

    # qd_conf.toml (via qdos.write_toml)
    qd_conf_path = os.path.join(src_pkg, "qd_conf.toml")
    try:
        conf_data = _gen_qd_conf_data(
            package_name, short_name, is_flask,
            init_function_name, priority)
        qdos.write_toml(qd_conf_path, conf_data)
        result.files_created.append(qd_conf_path)
    except OSError as e:
        result.errors.append(f"Failed to write {qd_conf_path}: {e}")

    # Flask-specific files
    if is_flask:
        _write_file(
            os.path.join(src_pkg, "routes.py"),
            _gen_routes_py(package_name, short_name, blueprint_name),
            result,
        )
        _write_file(
            os.path.join(src_pkg, "models.py"),
            _gen_models_py(package_name, short_name),
            result,
        )

        # .gitkeep files
        _write_file(
            os.path.join(src_pkg, "templates", package_name, ".gitkeep"),
            "", result)
        _write_file(
            os.path.join(src_pkg, "static", ".gitkeep"),
            "", result)

        # conf/<name>.yaml.example
        _write_file(
            os.path.join(src_pkg, "conf", f"{package_name}.yaml.example"),
            _gen_yaml_example(package_name, short_name, display_name),
            result,
        )

    if include_cli:
        _write_file(
            os.path.join(src_pkg, "cli.py"),
            _gen_cli_py(package_name, short_name),
            result,
        )

    if include_check_module:
        _write_file(
            os.path.join(src_pkg, f"check_{short_name}.py"),
            _gen_check_module(package_name, short_name, display_name,
                              checker_class_name),
            result,
        )

    # --- Final status ---
    result.success = len(result.errors) == 0
    return result
