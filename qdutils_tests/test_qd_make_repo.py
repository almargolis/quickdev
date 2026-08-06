"""Tests for qdutils.qd_make_repo"""

import os
import tempfile

import pytest

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
