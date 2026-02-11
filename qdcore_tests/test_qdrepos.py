"""
Tests for qdcore.qdrepos - RepoSpec parsing and editable flag round-trip.
"""

import os
import tempfile

from qdcore.qdrepos import RepoSpec, RepoScanner, EDITABLE_PREFIX


class TestRepoSpecParse:
    """Tests for RepoSpec.parse()."""

    def test_repospec_parse_plain(self):
        """No prefix → editable=False."""
        spec = RepoSpec.parse('/tmp/myrepo')
        assert spec.path == '/tmp/myrepo'
        assert spec.editable is False

    def test_repospec_parse_editable(self):
        """e:: prefix → editable=True, prefix stripped from path."""
        spec = RepoSpec.parse('e::/tmp/myrepo')
        assert spec.path == '/tmp/myrepo'
        assert spec.editable is True

    def test_repospec_parse_windows(self):
        """e:: prefix with Windows drive letter path."""
        spec = RepoSpec.parse('e::E:\\my_stuff\\repo')
        assert spec.path == 'E:\\my_stuff\\repo'
        assert spec.editable is True

    def test_repospec_parse_idempotent(self):
        """Passing a RepoSpec returns the same object."""
        original = RepoSpec('/tmp/foo', editable=True)
        result = RepoSpec.parse(original)
        assert result is original

    def test_repospec_repr_plain(self):
        spec = RepoSpec('/tmp/foo', editable=False)
        assert repr(spec) == "RepoSpec('/tmp/foo')"

    def test_repospec_repr_editable(self):
        spec = RepoSpec('/tmp/foo', editable=True)
        assert repr(spec) == "RepoSpec('e::/tmp/foo')"


class TestEditableRoundTrip:
    """Test that editable flag survives scan → DB → retrieve."""

    def test_editable_flag_round_trip(self, tmp_path):
        """Scan with e:: prefix, retrieve, verify editable=1."""
        # Create a minimal installable package using src/ layout:
        #   myrepo/src/mypkg/__init__.py   (package)
        #   myrepo/src/setup.py            (parent of package dir)
        repo_dir = tmp_path / 'myrepo'
        src_dir = repo_dir / 'src'
        pkg_dir = src_dir / 'mypkg'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / '__init__.py').write_text('')
        (src_dir / 'setup.py').write_text(
            'from setuptools import setup\nsetup(name="mypkg")\n'
        )

        # Scan with e:: prefix using in-memory DB
        scanner = RepoScanner(str(tmp_path), in_memory=True)
        counts = scanner.scan_directories([f'{EDITABLE_PREFIX}{repo_dir}'])

        # Verify the package was found
        assert counts['packages'] >= 1

        # Retrieve and check editable flag and setup_path
        packages = scanner.get_installable_packages()
        mypkg = [p for p in packages if p['package'] == 'mypkg']
        assert len(mypkg) == 1
        assert mypkg[0]['editable'] == 1
        assert mypkg[0]['setup_path'] == str(src_dir)

        scanner.close()

    def test_non_editable_flag_round_trip(self, tmp_path):
        """Scan without prefix, verify editable=0."""
        repo_dir = tmp_path / 'myrepo2'
        src_dir = repo_dir / 'src'
        pkg_dir = src_dir / 'mypkg2'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / '__init__.py').write_text('')
        (src_dir / 'setup.py').write_text(
            'from setuptools import setup\nsetup(name="mypkg2")\n'
        )

        scanner = RepoScanner(str(tmp_path), in_memory=True)
        counts = scanner.scan_directories([str(repo_dir)])

        packages = scanner.get_installable_packages()
        mypkg = [p for p in packages if p['package'] == 'mypkg2']
        assert len(mypkg) == 1
        assert mypkg[0]['editable'] == 0

        scanner.close()

    def test_src_layout_setup_detection(self, tmp_path):
        """setup.py in grandparent (repo/setup.py with repo/src/pkg/) is found."""
        repo_dir = tmp_path / 'myrepo3'
        pkg_dir = repo_dir / 'src' / 'mypkg3'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / '__init__.py').write_text('')
        # setup.py is in repo root, two levels above package dir
        (repo_dir / 'setup.py').write_text(
            'from setuptools import setup\nsetup(name="mypkg3")\n'
        )

        scanner = RepoScanner(str(tmp_path), in_memory=True)
        scanner.scan_directories([str(repo_dir)])

        packages = scanner.get_installable_packages()
        mypkg = [p for p in packages if p['package'] == 'mypkg3']
        assert len(mypkg) == 1
        assert mypkg[0]['setup_path'] == str(repo_dir)

        scanner.close()
