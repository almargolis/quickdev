"""
Create a new QuickDev repository with a standard pip-installable structure.

Generates a minimal repository skeleton with:
  - setup.py (src/ layout, pip/PyPI compatible)
  - src/<name>/__init__.py
  - .gitignore (Python/QuickDev standard)
  - pytest.ini (testpaths, optional pythonpath to site venv)
  - <name>_tests/ directory

If --site-path is provided and the site doesn't exist, QdStart is called
to initialize it (creating conf/, venv, etc.).

Usage:
    qd_make_repo --name myapp --site-path /path/to/site
    qd_make_repo -n myapp -s /path/to/site -d /path/to/repo
"""

import keyword
import os
import sys

THIS_MODULE_PATH = os.path.abspath(__file__)
QDUTILS_PKG_PATH = os.path.dirname(THIS_MODULE_PATH)
QDUTILS_SRC_PATH = os.path.dirname(QDUTILS_PKG_PATH)
QDUTILS_PATH = os.path.dirname(QDUTILS_SRC_PATH)
QDDEV_PATH = os.path.dirname(QDUTILS_PATH)
QDBASE_SRC_PATH = os.path.join(QDDEV_PATH, "qdbase", "src")
QDCORE_SRC_PATH = os.path.join(QDDEV_PATH, "qdcore", "src")

try:
    from qdbase import cliargs
except ModuleNotFoundError:
    sys.path.insert(0, QDBASE_SRC_PATH)
    sys.path.insert(0, QDCORE_SRC_PATH)
    from qdbase import cliargs

from qdbase import cliinput
from qdbase import exenv
from qdbase import qdos
from qdbase.qdcheck import CheckResult, CheckStatus


SETUP_PY_TEMPLATE = '''\
from setuptools import setup

setup(
    name="{name}",
    version="0.1.0",
    package_dir={{"": "src"}},
    packages=["{name}"],
    install_requires=["qdbase>=0.3.0"],
    python_requires=">=3.11",
)
'''

INIT_PY_TEMPLATE = '''\
__version__ = '0.1.0'
'''

GITIGNORE_TEMPLATE = '''\
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg-info/
*.egg
build/
dist/
.eggs/

# Virtual Environments
venv/
*.venv/

# Testing
.pytest_cache/
.coverage
htmlcov/

# IDE
.idea/
.vscode/

# OS
.DS_Store

# QuickDev
conf/db/*.db
conf/db/*.sqlite
*.log
*.tmp
'''

PYTEST_INI_TEMPLATE = '''\
[pytest]
testpaths = {test_dir}
'''

PYTEST_INI_WITH_SITE_TEMPLATE = '''\
[pytest]
testpaths = {test_dir}
pythonpath = {site_packages_path}
'''


def _find_site_packages(venv_dpath):
    """
    Find the site-packages directory inside a venv.

    Args:
        venv_dpath: Path to the virtual environment directory

    Returns:
        Absolute path to site-packages, or None if not found
    """
    lib_dpath = os.path.join(venv_dpath, "lib")
    if not os.path.isdir(lib_dpath):
        return None
    for entry in os.listdir(lib_dpath):
        if entry.startswith("python"):
            sp = os.path.join(lib_dpath, entry, "site-packages")
            if os.path.isdir(sp):
                return sp
    return None


def _resolve_site_venv(site_path, quiet=False):
    """
    Resolve the venv site-packages path for a QuickDev site.

    If the site doesn't exist, calls QdStart to initialize it.

    Args:
        site_path: Path to the QuickDev site directory
        quiet: Suppress output

    Returns:
        Absolute path to site-packages, or None on failure
    """
    site_path = os.path.abspath(site_path)

    # Check if site already has a venv
    if os.path.isdir(site_path):
        # Look for an existing *.venv directory
        for entry in os.listdir(site_path):
            candidate = os.path.join(site_path, entry)
            if entry.endswith(".venv") and os.path.isdir(candidate):
                sp = _find_site_packages(candidate)
                if sp:
                    return sp

        # Check conf/site.toml for the prefix
        site_toml = os.path.join(site_path, "conf", "site.toml")
        if os.path.isfile(site_toml):
            import tomllib
            with open(site_toml, "rb") as f:
                data = tomllib.load(f)
            prefix = data.get("qdsite_prefix")
            if prefix:
                venv_dpath = os.path.join(site_path, f"{prefix}.venv")
                sp = _find_site_packages(venv_dpath)
                if sp:
                    return sp

    # Site doesn't exist or has no venv — initialize via QdStart
    if not quiet:
        print(f"Initializing site at {site_path} ...")

    from qdutils.qdstart import QdStart
    site_name = os.path.basename(site_path)
    qs = QdStart(
        qdsite_dpath=site_path,
        qdsite_prefix=site_name,
        quiet=quiet,
    )

    if qs.venv_dpath:
        sp = _find_site_packages(qs.venv_dpath)
        if sp:
            return sp

    return None


class MakeRepo:
    """Create a new QuickDev repository with standard structure."""

    def __init__(self, directory=None, name=None, test_dir=None,
                 site_path=None, quiet=False):
        """
        Initialize MakeRepo.

        Args:
            directory: Repository root directory (default: cwd)
            name: Package name (default: directory basename)
            test_dir: Test directory name (default: <name>_tests)
            site_path: Path to QuickDev site for venv resolution
            quiet: Suppress output
        """
        self.quiet = quiet
        self.errors = []

        # Resolve directory
        if directory is None:
            self.directory = os.getcwd()
        else:
            self.directory = os.path.abspath(directory)

        # Resolve name
        if name is None:
            self.name = os.path.basename(self.directory)
        else:
            self.name = name

        # Validate name
        if not self.name.isidentifier() or keyword.iskeyword(self.name):
            self.errors.append(
                f"'{self.name}' is not a valid Python package name")
            return

        # Resolve test directory
        if test_dir is None:
            self.test_dir = f"{self.name}_tests"
        else:
            self.test_dir = test_dir

        # Resolve site packages path
        self.site_packages_path = None
        if site_path:
            self.site_packages_path = _resolve_site_venv(
                site_path, quiet=quiet)
            if self.site_packages_path is None:
                self.errors.append(
                    f"Could not resolve site-packages for site: {site_path}")

    @property
    def success(self):
        return len(self.errors) == 0

    def create(self):
        """
        Create the repository structure.

        Returns:
            List of created file/directory paths
        """
        if not self.success:
            return []

        created = []

        # Create directories
        src_pkg_dir = os.path.join(self.directory, "src", self.name)
        test_dir_path = os.path.join(self.directory, self.test_dir)

        for d in [self.directory, src_pkg_dir, test_dir_path]:
            os.makedirs(d, exist_ok=True)
            created.append(d)

        # Write setup.py
        setup_path = os.path.join(self.directory, "setup.py")
        if not os.path.exists(setup_path):
            with open(setup_path, "w") as f:
                f.write(SETUP_PY_TEMPLATE.format(name=self.name))
            created.append(setup_path)
            if not self.quiet:
                print(f"  Created {setup_path}")

        # Write __init__.py
        init_path = os.path.join(src_pkg_dir, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write(INIT_PY_TEMPLATE)
            created.append(init_path)
            if not self.quiet:
                print(f"  Created {init_path}")

        # Write .gitignore
        gitignore_path = os.path.join(self.directory, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w") as f:
                f.write(GITIGNORE_TEMPLATE)
            created.append(gitignore_path)
            if not self.quiet:
                print(f"  Created {gitignore_path}")

        # Write pytest.ini
        pytest_ini_path = os.path.join(self.directory, "pytest.ini")
        if not os.path.exists(pytest_ini_path):
            if self.site_packages_path:
                content = PYTEST_INI_WITH_SITE_TEMPLATE.format(
                    test_dir=self.test_dir,
                    site_packages_path=self.site_packages_path)
            else:
                content = PYTEST_INI_TEMPLATE.format(
                    test_dir=self.test_dir)
            with open(pytest_ini_path, "w") as f:
                f.write(content)
            created.append(pytest_ini_path)
            if not self.quiet:
                print(f"  Created {pytest_ini_path}")

        if not self.quiet:
            print(f"\nRepository '{self.name}' created at {self.directory}")

        return created

    def verify(self):
        """
        Verify an existing repository and repair missing/incomplete files.

        Returns:
            List of CheckResult objects
        """
        if not self.success:
            return []

        results = []
        results.append(self._check_setup_py())
        results.append(self._check_src_layout())
        results.append(self._check_init_py())
        results.append(self._check_gitignore())
        results.append(self._check_test_dir())
        results.append(self._check_pytest_ini())
        return results

    def _check_setup_py(self):
        path = os.path.join(self.directory, "setup.py")
        if os.path.isfile(path):
            return CheckResult(
                name="setup.py",
                status=CheckStatus.PASS,
                message="exists",
            )
        return CheckResult(
            name="setup.py",
            status=CheckStatus.FAIL,
            message="missing",
            remediation="Run qd_make_repo on a new directory to generate setup.py",
        )

    def _check_src_layout(self):
        src_pkg_dir = os.path.join(self.directory, "src", self.name)
        if os.path.isdir(src_pkg_dir):
            return CheckResult(
                name=f"src/{self.name}/",
                status=CheckStatus.PASS,
                message="exists",
            )
        # Check for flat layout (package dir at repo root)
        flat_pkg_dir = os.path.join(self.directory, self.name)
        if os.path.isdir(flat_pkg_dir):
            return CheckResult(
                name=f"src/{self.name}/",
                status=CheckStatus.WARNING,
                message=f"flat layout detected ({self.name}/ instead of src/{self.name}/)",
            )
        return CheckResult(
            name=f"src/{self.name}/",
            status=CheckStatus.WARNING,
            message="no package directory found",
        )

    def _check_init_py(self):
        # Check src layout first, then flat layout
        src_init = os.path.join(self.directory, "src", self.name, "__init__.py")
        flat_init = os.path.join(self.directory, self.name, "__init__.py")
        if os.path.isfile(src_init):
            return CheckResult(
                name="__init__.py",
                status=CheckStatus.PASS,
                message=f"exists (src/{self.name}/__init__.py)",
            )
        if os.path.isfile(flat_init):
            return CheckResult(
                name="__init__.py",
                status=CheckStatus.PASS,
                message=f"exists ({self.name}/__init__.py)",
            )
        return CheckResult(
            name="__init__.py",
            status=CheckStatus.WARNING,
            message="not found in package directory",
        )

    def _check_gitignore(self):
        path = os.path.join(self.directory, ".gitignore")
        if os.path.isfile(path):
            return CheckResult(
                name=".gitignore",
                status=CheckStatus.PASS,
                message="exists",
            )
        # Create it
        with open(path, "w") as f:
            f.write(GITIGNORE_TEMPLATE)
        if not self.quiet:
            print(f"  Created {path}")
        return CheckResult(
            name=".gitignore",
            status=CheckStatus.CORRECTED,
            message="created",
        )

    def _check_test_dir(self):
        test_dir_path = os.path.join(self.directory, self.test_dir)
        if os.path.isdir(test_dir_path):
            return CheckResult(
                name=self.test_dir,
                status=CheckStatus.PASS,
                message="exists",
            )
        os.makedirs(test_dir_path, exist_ok=True)
        if not self.quiet:
            print(f"  Created {test_dir_path}")
        return CheckResult(
            name=self.test_dir,
            status=CheckStatus.CORRECTED,
            message="created",
        )

    def _check_pytest_ini(self):
        path = os.path.join(self.directory, "pytest.ini")

        if os.path.isfile(path):
            content = open(path).read()
            has_testpaths = "testpaths" in content
            has_pythonpath = "pythonpath" in content

            if has_pythonpath:
                # Verify the pythonpath directory exists
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("pythonpath"):
                        parts = stripped.split("=", 1)
                        if len(parts) == 2:
                            pp_path = parts[1].strip()
                            if os.path.isdir(pp_path):
                                return CheckResult(
                                    name="pytest.ini",
                                    status=CheckStatus.PASS,
                                    message=f"exists with pythonpath → {pp_path}",
                                )
                            return CheckResult(
                                name="pytest.ini",
                                status=CheckStatus.WARNING,
                                message=f"pythonpath directory does not exist: {pp_path}",
                                remediation="Update pythonpath in pytest.ini or re-run with --site-path",
                            )

            # pytest.ini exists but missing pythonpath — try to add it
            if not has_pythonpath:
                site_packages = self._resolve_pythonpath()
                if site_packages:
                    new_content = self._update_pytest_ini(content, site_packages)
                    with open(path, "w") as f:
                        f.write(new_content)
                    if not self.quiet:
                        print(f"  Updated {path} with pythonpath")
                    return CheckResult(
                        name="pytest.ini",
                        status=CheckStatus.CORRECTED,
                        message=f"added pythonpath → {site_packages}",
                    )
                # No site path available, but pytest.ini exists with testpaths
                if has_testpaths:
                    return CheckResult(
                        name="pytest.ini",
                        status=CheckStatus.WARNING,
                        message="exists but no pythonpath configured",
                        remediation="Re-run with --site-path to add venv resolution",
                    )

            return CheckResult(
                name="pytest.ini",
                status=CheckStatus.PASS,
                message="exists",
            )

        # pytest.ini doesn't exist — create it
        site_packages = self._resolve_pythonpath()
        if site_packages:
            content = PYTEST_INI_WITH_SITE_TEMPLATE.format(
                test_dir=self.test_dir,
                site_packages_path=site_packages)
        else:
            content = PYTEST_INI_TEMPLATE.format(test_dir=self.test_dir)
        with open(path, "w") as f:
            f.write(content)
        if not self.quiet:
            print(f"  Created {path}")
        msg = "created"
        if site_packages:
            msg += f" with pythonpath → {site_packages}"
        return CheckResult(
            name="pytest.ini",
            status=CheckStatus.CORRECTED,
            message=msg,
        )

    def _resolve_pythonpath(self):
        """
        Resolve a site-packages path for pytest.ini pythonpath.

        Uses self.site_packages_path if already resolved (from --site-path),
        otherwise prompts the user.

        Returns:
            Absolute path to site-packages, or None
        """
        if self.site_packages_path:
            return self.site_packages_path

        if self.quiet:
            return None

        site_path = self._prompt_site_path()
        if not site_path:
            return None

        sp = _resolve_site_venv(site_path, quiet=self.quiet)
        if sp:
            self.site_packages_path = sp
        return sp

    def _prompt_site_path(self):
        """
        Prompt the user for a site path.

        Returns:
            Site path string, or None if skipped
        """
        resp = cliinput.cli_input(
            "Site path for venv resolution (or Enter to skip): ")
        if resp.strip():
            return resp.strip()
        return None

    def _update_pytest_ini(self, content, site_packages_path):
        """
        Update existing pytest.ini content to add or replace pythonpath.

        Preserves all other content. If pythonpath exists, replaces it.
        If missing, inserts after testpaths line.

        Args:
            content: Existing pytest.ini content
            site_packages_path: Path to add as pythonpath value

        Returns:
            Updated content string
        """
        lines = content.splitlines(keepends=True)
        new_lines = []
        replaced = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("pythonpath"):
                new_lines.append(f"pythonpath = {site_packages_path}\n")
                replaced = True
            else:
                new_lines.append(line)
                if not replaced and stripped.startswith("testpaths"):
                    new_lines.append(f"pythonpath = {site_packages_path}\n")
                    replaced = True

        if not replaced:
            # No testpaths line found either, append to end
            result = "".join(new_lines)
            if not result.endswith("\n"):
                result += "\n"
            result += f"pythonpath = {site_packages_path}\n"
            return result

        return "".join(new_lines)


def main():
    """Main entry point for qd_make_repo CLI."""
    menu = cliargs.CliCommandLine()

    # Register parameters on the menu first (cliargs requires this)
    menu.add_item(cliargs.CliCommandLineParameterItem(
        "d",
        help_description="Repository root directory (default: cwd).",
        default_none=True,
        value_type=cliargs.PARAMETER_STRING,
    ))
    menu.add_item(cliargs.CliCommandLineParameterItem(
        "n",
        help_description="Package name (default: directory name).",
        default_none=True,
        value_type=cliargs.PARAMETER_STRING,
    ))
    menu.add_item(cliargs.CliCommandLineParameterItem(
        "t",
        help_description="Test directory name (default: <name>_tests).",
        default_none=True,
        value_type=cliargs.PARAMETER_STRING,
    ))
    exenv.command_line_site(menu)     # -s for site path
    exenv.command_line_quiet(menu)    # -q for quiet

    # Register the default action and bind parameters to it
    m = menu.add_item(
        cliargs.CliCommandLineActionItem(
            cliargs.DEFAULT_ACTION_CODE,
            _run_make_repo,
            help_description="Create a new QuickDev repository.",
        )
    )
    m.add_parameter(cliargs.CliCommandLineParameterItem(
        "d", parameter_name="directory", is_positional=False,
    ))
    m.add_parameter(cliargs.CliCommandLineParameterItem(
        "n", parameter_name="name", is_positional=False,
    ))
    m.add_parameter(cliargs.CliCommandLineParameterItem(
        "t", parameter_name="test_dir", is_positional=False,
    ))
    m.add_parameter(cliargs.CliCommandLineParameterItem(
        exenv.ARG_S_SITE_DPATH, parameter_name="site_path",
        is_positional=False,
    ))
    m.add_parameter(cliargs.CliCommandLineParameterItem(
        exenv.ARG_Q_QUIET, parameter_name="quiet", is_positional=False,
    ))

    menu.cli_run()


def _run_make_repo(directory=None, name=None, test_dir=None,
                   site_path=None, quiet=False, **kwargs):
    """Action handler for the CLI."""
    # Determine actual directory to check for existing repo
    if directory is None:
        check_dir = os.getcwd()
    else:
        check_dir = os.path.abspath(directory)

    setup_py = os.path.join(check_dir, "setup.py")
    is_existing_repo = os.path.isfile(setup_py)

    maker = MakeRepo(
        directory=directory,
        name=name,
        test_dir=test_dir,
        site_path=site_path,
        quiet=quiet,
    )
    if not maker.success:
        for err in maker.errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    if is_existing_repo:
        if not quiet:
            print(f"Verifying existing repository '{maker.name}' "
                  f"at {maker.directory} ...")
        results = maker.verify()
        if not quiet:
            print()
            for r in results:
                print(f"  {r.symbol} {r.name}: {r.message}")
                if r.remediation and r.status == CheckStatus.FAIL:
                    print(f"    \u2192 {r.remediation}")
            passed = sum(1 for r in results if r.is_success)
            total = len(results)
            print(f"\n  {passed}/{total} checks passed")
    else:
        maker.create()
