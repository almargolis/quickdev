"""Tests for qdutils.qd_make_repo"""

import os
import tempfile

import pytest

from qdbase.qdcheck import CheckStatus
from qdutils.qd_make_repo import MakeRepo


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestMakeRepoValidation:
    def test_valid_name(self, tmp_dir):
        maker = MakeRepo(directory=tmp_dir, name="myapp")
        assert maker.success

    def test_invalid_name_keyword(self, tmp_dir):
        maker = MakeRepo(directory=tmp_dir, name="class")
        assert not maker.success
        assert "not a valid Python package name" in maker.errors[0]

    def test_invalid_name_starts_with_number(self, tmp_dir):
        maker = MakeRepo(directory=tmp_dir, name="123abc")
        assert not maker.success

    def test_invalid_name_has_hyphen(self, tmp_dir):
        maker = MakeRepo(directory=tmp_dir, name="my-app")
        assert not maker.success

    def test_default_name_from_directory(self, tmp_dir):
        subdir = os.path.join(tmp_dir, "myproject")
        os.makedirs(subdir)
        maker = MakeRepo(directory=subdir)
        assert maker.name == "myproject"
        assert maker.success


class TestMakeRepoCreate:
    def test_creates_directory_structure(self, tmp_dir):
        repo_dir = os.path.join(tmp_dir, "myapp")
        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        created = maker.create()

        assert os.path.isdir(repo_dir)
        assert os.path.isdir(os.path.join(repo_dir, "src", "myapp"))
        assert os.path.isdir(os.path.join(repo_dir, "myapp_tests"))

    def test_creates_setup_py(self, tmp_dir):
        repo_dir = os.path.join(tmp_dir, "myapp")
        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        maker.create()

        setup_path = os.path.join(repo_dir, "setup.py")
        assert os.path.isfile(setup_path)
        content = open(setup_path).read()
        assert 'name="myapp"' in content
        assert "package_dir" in content
        assert '"src"' in content

    def test_creates_init_py(self, tmp_dir):
        repo_dir = os.path.join(tmp_dir, "myapp")
        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        maker.create()

        init_path = os.path.join(repo_dir, "src", "myapp", "__init__.py")
        assert os.path.isfile(init_path)
        content = open(init_path).read()
        assert "__version__" in content

    def test_creates_gitignore(self, tmp_dir):
        repo_dir = os.path.join(tmp_dir, "myapp")
        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        maker.create()

        gitignore_path = os.path.join(repo_dir, ".gitignore")
        assert os.path.isfile(gitignore_path)
        content = open(gitignore_path).read()
        assert "__pycache__" in content
        assert ".pytest_cache" in content

    def test_creates_pytest_ini(self, tmp_dir):
        repo_dir = os.path.join(tmp_dir, "myapp")
        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        maker.create()

        ini_path = os.path.join(repo_dir, "pytest.ini")
        assert os.path.isfile(ini_path)
        content = open(ini_path).read()
        assert "testpaths = myapp_tests" in content

    def test_does_not_overwrite_existing_files(self, tmp_dir):
        repo_dir = os.path.join(tmp_dir, "myapp")
        os.makedirs(repo_dir)

        # Pre-create setup.py with custom content
        setup_path = os.path.join(repo_dir, "setup.py")
        with open(setup_path, "w") as f:
            f.write("# custom setup\n")

        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        maker.create()

        content = open(setup_path).read()
        assert content == "# custom setup\n"


class TestMakeRepoDefaults:
    def test_default_directory_is_cwd(self):
        maker = MakeRepo(name="test_pkg", quiet=True)
        assert maker.directory == os.getcwd()

    def test_default_test_dir(self, tmp_dir):
        maker = MakeRepo(directory=tmp_dir, name="myapp", quiet=True)
        assert maker.test_dir == "myapp_tests"

    def test_custom_test_dir(self, tmp_dir):
        maker = MakeRepo(directory=tmp_dir, name="myapp",
                         test_dir="tests", quiet=True)
        assert maker.test_dir == "tests"
        maker.create()
        assert os.path.isdir(os.path.join(tmp_dir, "tests"))


class TestMakeRepoWithSite:
    def test_pytest_ini_without_site(self, tmp_dir):
        repo_dir = os.path.join(tmp_dir, "myapp")
        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        maker.create()

        content = open(os.path.join(repo_dir, "pytest.ini")).read()
        assert "pythonpath" not in content

    def test_pytest_ini_with_site(self, tmp_dir):
        # Create a fake site with a venv structure
        site_dir = os.path.join(tmp_dir, "site")
        venv_dir = os.path.join(site_dir, "site.venv")
        sp_dir = os.path.join(venv_dir, "lib", "python3.11", "site-packages")
        os.makedirs(sp_dir)
        # Create pyvenv.cfg so it looks like a real venv
        with open(os.path.join(venv_dir, "pyvenv.cfg"), "w") as f:
            f.write("home = /usr/bin\n")

        repo_dir = os.path.join(tmp_dir, "myapp")
        maker = MakeRepo(directory=repo_dir, name="myapp",
                         site_path=site_dir, quiet=True)
        assert maker.site_packages_path == sp_dir
        maker.create()

        content = open(os.path.join(repo_dir, "pytest.ini")).read()
        assert f"pythonpath = {sp_dir}" in content


def _make_complete_repo(repo_dir, name="myapp"):
    """Helper: create a fully-formed repo skeleton for verify tests."""
    src_pkg = os.path.join(repo_dir, "src", name)
    test_dir = os.path.join(repo_dir, f"{name}_tests")
    os.makedirs(src_pkg, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)

    with open(os.path.join(repo_dir, "setup.py"), "w") as f:
        f.write(f'from setuptools import setup\nsetup(name="{name}")\n')

    with open(os.path.join(src_pkg, "__init__.py"), "w") as f:
        f.write("__version__ = '0.1.0'\n")

    with open(os.path.join(repo_dir, ".gitignore"), "w") as f:
        f.write("__pycache__/\n")

    with open(os.path.join(repo_dir, "pytest.ini"), "w") as f:
        f.write(f"[pytest]\ntestpaths = {name}_tests\n")


def _make_site_with_venv(base_dir, site_name="mysite"):
    """Helper: create a fake site with a venv containing site-packages."""
    site_dir = os.path.join(base_dir, site_name)
    venv_dir = os.path.join(site_dir, f"{site_name}.venv")
    sp_dir = os.path.join(venv_dir, "lib", "python3.11", "site-packages")
    os.makedirs(sp_dir)
    with open(os.path.join(venv_dir, "pyvenv.cfg"), "w") as f:
        f.write("home = /usr/bin\n")
    return site_dir, sp_dir


class TestMakeRepoVerify:
    def test_verify_complete_repo(self, tmp_dir):
        """All checks pass on a fully-formed repo."""
        repo_dir = os.path.join(tmp_dir, "myapp")
        os.makedirs(repo_dir)
        _make_complete_repo(repo_dir)

        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        results = maker.verify()

        assert len(results) == 6
        # setup.py, src/myapp/, __init__.py, .gitignore, test dir all pass
        for r in results[:5]:
            assert r.status in (CheckStatus.PASS, CheckStatus.WARNING), \
                f"{r.name}: {r.status} - {r.message}"
        # pytest.ini exists but has no pythonpath — WARNING in quiet mode
        # (no prompt happens because quiet=True)
        assert results[5].name == "pytest.ini"

    def test_verify_missing_pytest_ini(self, tmp_dir):
        """Creates pytest.ini when missing."""
        repo_dir = os.path.join(tmp_dir, "myapp")
        os.makedirs(repo_dir)
        _make_complete_repo(repo_dir)
        os.remove(os.path.join(repo_dir, "pytest.ini"))

        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        results = maker.verify()

        pytest_result = [r for r in results if r.name == "pytest.ini"][0]
        assert pytest_result.status == CheckStatus.CORRECTED
        assert "created" in pytest_result.message

        # Verify file was actually created
        ini_path = os.path.join(repo_dir, "pytest.ini")
        assert os.path.isfile(ini_path)
        content = open(ini_path).read()
        assert "testpaths = myapp_tests" in content

    def test_verify_missing_pytest_ini_with_site(self, tmp_dir):
        """Creates pytest.ini with pythonpath when site-path is given."""
        repo_dir = os.path.join(tmp_dir, "myapp")
        os.makedirs(repo_dir)
        _make_complete_repo(repo_dir)
        os.remove(os.path.join(repo_dir, "pytest.ini"))

        site_dir, sp_dir = _make_site_with_venv(tmp_dir)

        maker = MakeRepo(directory=repo_dir, name="myapp",
                         site_path=site_dir, quiet=True)
        results = maker.verify()

        pytest_result = [r for r in results if r.name == "pytest.ini"][0]
        assert pytest_result.status == CheckStatus.CORRECTED
        assert sp_dir in pytest_result.message

        content = open(os.path.join(repo_dir, "pytest.ini")).read()
        assert f"pythonpath = {sp_dir}" in content

    def test_verify_pytest_ini_missing_pythonpath(self, tmp_dir):
        """Adds pythonpath to existing pytest.ini when site-path given."""
        repo_dir = os.path.join(tmp_dir, "myapp")
        os.makedirs(repo_dir)
        _make_complete_repo(repo_dir)

        site_dir, sp_dir = _make_site_with_venv(tmp_dir)

        maker = MakeRepo(directory=repo_dir, name="myapp",
                         site_path=site_dir, quiet=True)
        results = maker.verify()

        pytest_result = [r for r in results if r.name == "pytest.ini"][0]
        assert pytest_result.status == CheckStatus.CORRECTED
        assert "added pythonpath" in pytest_result.message

        content = open(os.path.join(repo_dir, "pytest.ini")).read()
        assert "testpaths = myapp_tests" in content
        assert f"pythonpath = {sp_dir}" in content

    def test_verify_pytest_ini_stale_pythonpath(self, tmp_dir):
        """Warns when pythonpath directory does not exist."""
        repo_dir = os.path.join(tmp_dir, "myapp")
        os.makedirs(repo_dir)
        _make_complete_repo(repo_dir)

        # Write pytest.ini with a nonexistent pythonpath
        fake_path = os.path.join(tmp_dir, "nonexistent", "site-packages")
        with open(os.path.join(repo_dir, "pytest.ini"), "w") as f:
            f.write(f"[pytest]\ntestpaths = myapp_tests\npythonpath = {fake_path}\n")

        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        results = maker.verify()

        pytest_result = [r for r in results if r.name == "pytest.ini"][0]
        assert pytest_result.status == CheckStatus.WARNING
        assert "does not exist" in pytest_result.message

    def test_verify_missing_gitignore(self, tmp_dir):
        """Creates .gitignore when missing."""
        repo_dir = os.path.join(tmp_dir, "myapp")
        os.makedirs(repo_dir)
        _make_complete_repo(repo_dir)
        os.remove(os.path.join(repo_dir, ".gitignore"))

        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        results = maker.verify()

        gi_result = [r for r in results if r.name == ".gitignore"][0]
        assert gi_result.status == CheckStatus.CORRECTED
        assert os.path.isfile(os.path.join(repo_dir, ".gitignore"))

    def test_verify_missing_test_dir(self, tmp_dir):
        """Creates test directory when missing."""
        repo_dir = os.path.join(tmp_dir, "myapp")
        os.makedirs(repo_dir)
        _make_complete_repo(repo_dir)
        os.rmdir(os.path.join(repo_dir, "myapp_tests"))

        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        results = maker.verify()

        test_result = [r for r in results if r.name == "myapp_tests"][0]
        assert test_result.status == CheckStatus.CORRECTED
        assert os.path.isdir(os.path.join(repo_dir, "myapp_tests"))

    def test_verify_updates_pytest_ini_preserving_content(self, tmp_dir):
        """Adding pythonpath preserves existing pytest.ini settings."""
        repo_dir = os.path.join(tmp_dir, "myapp")
        os.makedirs(repo_dir)
        _make_complete_repo(repo_dir)

        # Write pytest.ini with extra settings
        with open(os.path.join(repo_dir, "pytest.ini"), "w") as f:
            f.write("[pytest]\ntestpaths = myapp_tests\n"
                    "addopts = -v --tb=short\n")

        site_dir, sp_dir = _make_site_with_venv(tmp_dir)

        maker = MakeRepo(directory=repo_dir, name="myapp",
                         site_path=site_dir, quiet=True)
        results = maker.verify()

        content = open(os.path.join(repo_dir, "pytest.ini")).read()
        assert "testpaths = myapp_tests" in content
        assert f"pythonpath = {sp_dir}" in content
        assert "addopts = -v --tb=short" in content

    def test_verify_flat_layout_warning(self, tmp_dir):
        """Reports warning for flat layout (no src/)."""
        repo_dir = os.path.join(tmp_dir, "myapp")
        flat_pkg = os.path.join(repo_dir, "myapp")
        os.makedirs(flat_pkg)
        _make_complete_repo(repo_dir)
        # Remove the src/ layout that _make_complete_repo created
        import shutil
        shutil.rmtree(os.path.join(repo_dir, "src"))

        # Create __init__.py in flat layout
        with open(os.path.join(flat_pkg, "__init__.py"), "w") as f:
            f.write("__version__ = '0.1.0'\n")

        maker = MakeRepo(directory=repo_dir, name="myapp", quiet=True)
        results = maker.verify()

        src_result = [r for r in results if "src/" in r.name][0]
        assert src_result.status == CheckStatus.WARNING
        assert "flat layout" in src_result.message

    def test_create_runs_on_new_dir(self, tmp_dir):
        """create() still works normally for new directories."""
        repo_dir = os.path.join(tmp_dir, "newapp")
        maker = MakeRepo(directory=repo_dir, name="newapp", quiet=True)
        created = maker.create()

        assert os.path.isfile(os.path.join(repo_dir, "setup.py"))
        assert os.path.isfile(os.path.join(repo_dir, "pytest.ini"))
        assert os.path.isdir(os.path.join(repo_dir, "src", "newapp"))
