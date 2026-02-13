"""
pytest for qdstart.py.

This includes several classes and functions, including MakeQdChroot(),
that build an environment for testing that avoids writing to actual
system configuration files.
"""

import os
import re

from qdbase import cliinput
from qdbase import exenv
from qdbase import qdconf
from qdbase import qdos
from qdcore import qdrepos

from qdutils import hosting
from qdutils import qdstart

SITE_PREFIX = "test"


class MakeQdChroot:
    """
    This makes a safe test environment for QuickDev utility
    testing so they don't write to the actual system
    directories.

    exenv.ExenvGlobals is designed for this, so most things
    don't have to be particularly test-aware in order to
    run in this artificial environment.
    """

    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        root_dpath = os.path.join(tmpdir, "root")
        self.make_os_directories(root_dpath)
        private_dpath = os.path.join(root_dpath, "private")
        self.make_os_directories(private_dpath)
        var_dpath = os.path.join(root_dpath, "var")
        www_dpath = os.path.join(var_dpath, "www")
        os.mkdir(var_dpath)
        os.mkdir(www_dpath)
        exenv.g.init(root_dpath)
        try:
            hosting.init_hosting(force=True)
        except SystemExit as error_info:
            # SystemExit is a pytest exception
            if error_info.code != 0:
                raise

    def make_os_directories(self, root_dpath):  # pylint: disable=no-self-use
        """
        Make needed directories that live in /etc.
        This get called twice, first to create the directories
        under /etc and then under /private/etc.
        On MacOS the actual directories are under /private/etc
        and /etc is a symlink to that. I am making them
        separately so I can check where the actual writes get
        aimed. I'm not sure how that will work out in the long run.
        """
        etc_dpath = os.path.join(root_dpath, "etc")
        apache_dpath = os.path.join(etc_dpath, "apache2")
        sites_available_dpath = os.path.join(apache_dpath, "sites-available")
        os.mkdir(root_dpath)
        os.mkdir(etc_dpath)
        os.mkdir(apache_dpath)
        os.mkdir(sites_available_dpath)

    def make_qdsite_dpath(self, acronym):  # pylint: disable=no-self-use
        """Make a dpath to a qdsite."""
        return os.path.join(exenv.g.qdsites_dpath, acronym)


def make_qdsite(tmpdir):
    """Make a test qdsite within a chroot environment."""
    qd_chroot = MakeQdChroot(tmpdir)
    qdsite_dpath = qd_chroot.make_qdsite_dpath(SITE_PREFIX)
    # Provide answers for interactive prompts
    cliinput.debug_input_answers["Do you want to use this VENV for this project?"] = "y"
    cliinput.debug_input_answers["Create VENV"] = "y"
    return qdstart.QdStart(qdsite_dpath=qdsite_dpath, debug=1)


def test_basic(tmpdir):
    """A simple test to make sure the basics are working."""
    qdsite_start = make_qdsite(tmpdir)
    # Create a new site object to verify that all persistent data
    # collected by QdStart() was actually saved.
    qdsite_info = exenv.QdSite(qdsite_dpath=qdsite_start.qdsite_info.qdsite_dpath)
    # site_prefix defaults to site_dname if not set
    assert qdsite_info.qdsite_prefix == SITE_PREFIX


# --- Tests for expand_answer_refs, resolve_question, and plan_site ---

class TestExpandAnswerRefs:
    """Tests for the expand_answer_refs() function."""

    def test_no_refs(self):
        """Plain string is returned unchanged."""
        assert qdstart.expand_answer_refs("hello", {}) == "hello"

    def test_non_string(self):
        """Non-string values are returned unchanged."""
        assert qdstart.expand_answer_refs(42, {}) == 42
        assert qdstart.expand_answer_refs(True, {}) is True

    def test_expand_from_cache(self):
        """Reference is expanded from answer_cache."""
        cache = {'trellis.content_dpath': '/var/www/content'}
        result = qdstart.expand_answer_refs(
            '<trellis.content_dpath>/users.db', cache
        )
        assert result == '/var/www/content/users.db'

    def test_expand_from_conf(self, tmp_path):
        """Reference is expanded from QdConf."""
        conf_dir = tmp_path / 'conf'
        conf_dir.mkdir()
        qdos.write_toml(str(conf_dir / 'trellis.toml'),
                        {'content_dpath': '/srv/content'})
        conf = qdconf.QdConf(str(conf_dir))

        result = qdstart.expand_answer_refs(
            '<trellis.content_dpath>/data.db', {}, conf
        )
        assert result == '/srv/content/data.db'

    def test_cache_priority_over_conf(self, tmp_path):
        """answer_cache takes priority over conf for refs."""
        conf_dir = tmp_path / 'conf'
        conf_dir.mkdir()
        qdos.write_toml(str(conf_dir / 'trellis.toml'),
                        {'content_dpath': '/old'})
        conf = qdconf.QdConf(str(conf_dir))

        cache = {'trellis.content_dpath': '/new'}
        result = qdstart.expand_answer_refs(
            '<trellis.content_dpath>/db', cache, conf
        )
        assert result == '/new/db'

    def test_unresolvable_left_as_is(self):
        """Unresolvable references are left in the string."""
        result = qdstart.expand_answer_refs(
            '<unknown.key>/file.db', {}
        )
        assert result == '<unknown.key>/file.db'

    def test_multiple_refs(self):
        """Multiple references in one string are all expanded."""
        cache = {'a.x': 'hello', 'b.y': 'world'}
        result = qdstart.expand_answer_refs('<a.x> <b.y>', cache)
        assert result == 'hello world'

    def test_partial_expansion(self):
        """Resolvable refs are expanded, unresolvable left."""
        cache = {'a.x': 'hello'}
        result = qdstart.expand_answer_refs(
            '<a.x>/<b.y>', cache
        )
        assert result == 'hello/<b.y>'

    def test_has_unresolved_refs(self):
        """has_unresolved_refs detects remaining references."""
        assert qdstart.has_unresolved_refs('<a.b>/foo') is True
        assert qdstart.has_unresolved_refs('/plain/path') is False
        assert qdstart.has_unresolved_refs(42) is False


class TestResolveQuestion:
    """Tests for ConfAnswer.resolve() classmethod."""

    def test_constant_from_answer_cache(self):
        """Answer in answer_cache returns SOURCE_CONSTANT."""
        question = qdrepos.ConfQuestion('boolean', 'qdflask.enabled', '')
        cache = {'qdflask.enabled': True}
        answer = qdrepos.ConfAnswer.resolve(question, cache)
        assert answer.conf_value is True
        assert answer.source == qdstart.SOURCE_CONSTANT

    def test_configured_from_conf(self, tmp_path):
        """Answer in conf returns SOURCE_CONFIGURED."""
        # Create a conf dir with a toml file
        conf_dir = tmp_path / 'conf'
        conf_dir.mkdir()
        qdos.write_toml(str(conf_dir / 'qdflask.toml'),
                        {'enabled': True, 'roles': 'admin, editor'})

        conf = qdconf.QdConf(str(conf_dir))
        question = qdrepos.ConfQuestion('string', 'qdflask.roles', '')
        cache = {}
        answer = qdrepos.ConfAnswer.resolve(question, cache, conf)
        assert answer.conf_value == 'admin, editor'
        assert answer.source == qdstart.SOURCE_CONFIGURED

    def test_prompt_when_no_answer(self):
        """No answer anywhere returns SOURCE_PROMPT."""
        question = qdrepos.ConfQuestion('string', 'qdflask.roles', '')
        cache = {}
        answer = qdrepos.ConfAnswer.resolve(question, cache)
        assert answer.conf_value is None
        assert answer.source == qdstart.SOURCE_PROMPT

    def test_cache_takes_priority_over_conf(self, tmp_path):
        """answer_cache (constant) wins over conf (configured)."""
        conf_dir = tmp_path / 'conf'
        conf_dir.mkdir()
        qdos.write_toml(str(conf_dir / 'qdflask.toml'),
                        {'roles': 'old_value'})

        conf = qdconf.QdConf(str(conf_dir))
        question = qdrepos.ConfQuestion('string', 'qdflask.roles', '')
        cache = {'qdflask.roles': 'new_value'}
        answer = qdrepos.ConfAnswer.resolve(question, cache, conf)
        assert answer.conf_value == 'new_value'
        assert answer.source == qdstart.SOURCE_CONSTANT

    def test_prompt_when_conf_key_missing(self, tmp_path):
        """Key not in conf and not in cache returns SOURCE_PROMPT."""
        conf_dir = tmp_path / 'conf'
        conf_dir.mkdir()
        qdos.write_toml(str(conf_dir / 'qdflask.toml'),
                        {'enabled': True})

        conf = qdconf.QdConf(str(conf_dir))
        question = qdrepos.ConfQuestion('string', 'qdflask.login_view', '')
        cache = {}
        answer = qdrepos.ConfAnswer.resolve(question, cache, conf)
        assert answer.conf_value is None
        assert answer.source == qdstart.SOURCE_PROMPT


class TestPlanSite:
    """Tests for plan_site() reporting function."""

    def _make_repo_with_qd_conf(self, repo_dir, qd_conf_data):
        """Helper to create a repo directory with a qd_conf.toml."""
        pkg_dir = repo_dir / 'mypkg'
        pkg_dir.mkdir(parents=True)
        qdos.write_toml(str(pkg_dir / 'qd_conf.toml'), qd_conf_data)

    def test_plan_no_repo_questions(self, tmp_path, capsys):
        """Report with no repos still shows built-in questions."""
        site_dir = tmp_path / 'site'
        site_dir.mkdir()
        qdstart.plan_site(str(site_dir), quiet=False)
        captured = capsys.readouterr()
        # Built-in questions (site.qdsite_dpath, site.qdsite_prefix)
        # are always present from the scanner
        assert "QdStart Planning Report" in captured.out
        assert "Will Be Prompted" in captured.out

    def test_plan_shows_constants(self, tmp_path, capsys):
        """Questions with answers in answer_cache show as constants."""
        site_dir = tmp_path / 'site'
        site_dir.mkdir()
        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()

        qd_conf = {
            'questions': {
                'mypkg': {
                    'enabled': {
                        'help': 'Enable mypkg?',
                        'conf_type': 'boolean'
                    }
                }
            },
            'answers': {
                'mypkg': {
                    'enabled': True
                }
            }
        }
        self._make_repo_with_qd_conf(repo_dir, qd_conf)
        qdstart.plan_site(str(site_dir), quiet=False,
                          repo_list=[str(repo_dir)])
        captured = capsys.readouterr()
        assert "Application Constants" in captured.out
        assert "mypkg.enabled" in captured.out

    def test_plan_shows_configured(self, tmp_path, capsys):
        """Questions with answers in conf show as previously answered."""
        site_dir = tmp_path / 'site'
        site_dir.mkdir()
        conf_dir = site_dir / 'conf'
        conf_dir.mkdir()

        # Write existing conf value
        qdos.write_toml(str(conf_dir / 'mypkg.toml'), {'color': 'blue'})

        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()
        qd_conf = {
            'questions': {
                'mypkg': {
                    'color': {
                        'help': 'Pick a color',
                        'conf_type': 'string'
                    }
                }
            }
        }
        self._make_repo_with_qd_conf(repo_dir, qd_conf)
        qdstart.plan_site(str(site_dir), quiet=False,
                          repo_list=[str(repo_dir)])
        captured = capsys.readouterr()
        assert "Previously Answered" in captured.out
        assert "mypkg.color" in captured.out
        assert "blue" in captured.out

    def test_plan_shows_prompts(self, tmp_path, capsys):
        """Questions with no answer show as will be prompted."""
        site_dir = tmp_path / 'site'
        site_dir.mkdir()
        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()

        qd_conf = {
            'questions': {
                'mypkg': {
                    'secret': {
                        'help': 'Enter secret key',
                        'conf_type': 'string'
                    }
                }
            }
        }
        self._make_repo_with_qd_conf(repo_dir, qd_conf)
        qdstart.plan_site(str(site_dir), quiet=False,
                          repo_list=[str(repo_dir)])
        captured = capsys.readouterr()
        assert "Will Be Prompted" in captured.out
        assert "mypkg.secret" in captured.out

    def test_plan_skips_disabled_questions(self, tmp_path, capsys):
        """Questions for disabled plugins are not shown."""
        site_dir = tmp_path / 'site'
        site_dir.mkdir()
        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()

        qd_conf = {
            'questions': {
                'mypkg': {
                    'enabled': {
                        'help': 'Enable mypkg?',
                        'conf_type': 'boolean'
                    },
                    'color': {
                        'help': 'Pick a color',
                        'conf_type': 'string'
                    }
                }
            },
            'answers': {
                'mypkg': {
                    'enabled': False
                }
            }
        }
        self._make_repo_with_qd_conf(repo_dir, qd_conf)
        qdstart.plan_site(str(site_dir), quiet=False,
                          repo_list=[str(repo_dir)])
        captured = capsys.readouterr()
        # enabled question itself is shown (as constant)
        assert "mypkg.enabled" in captured.out
        # but color question for disabled plugin is skipped
        assert "mypkg.color" not in captured.out

    def test_plan_all_three_categories(self, tmp_path, capsys):
        """Report shows all three categories when all are present."""
        site_dir = tmp_path / 'site'
        site_dir.mkdir()
        conf_dir = site_dir / 'conf'
        conf_dir.mkdir()

        # Existing conf value
        qdos.write_toml(str(conf_dir / 'mypkg.toml'), {'color': 'red'})

        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()
        qd_conf = {
            'questions': {
                'mypkg': {
                    'enabled': {
                        'help': 'Enable mypkg?',
                        'conf_type': 'boolean'
                    },
                    'color': {
                        'help': 'Pick a color',
                        'conf_type': 'string'
                    },
                    'size': {
                        'help': 'Pick a size',
                        'conf_type': 'string'
                    }
                }
            },
            'answers': {
                'mypkg': {
                    'enabled': True
                }
            }
        }
        self._make_repo_with_qd_conf(repo_dir, qd_conf)
        qdstart.plan_site(str(site_dir), quiet=False,
                          repo_list=[str(repo_dir)])
        captured = capsys.readouterr()
        assert "Application Constants (1)" in captured.out
        assert "Previously Answered (1)" in captured.out
        # Will Be Prompted includes mypkg.size plus built-in questions
        assert "Will Be Prompted" in captured.out
        assert "mypkg.size" in captured.out

    def test_plan_shows_symbolic_ref(self, tmp_path, capsys):
        """Symbolic <conf_key> references are shown with expansion."""
        site_dir = tmp_path / 'site'
        site_dir.mkdir()

        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()
        qd_conf = {
            'questions': {
                'trellis': {
                    'content_dpath': {
                        'help': 'Path to site content',
                        'conf_type': 'string'
                    }
                },
                'qdflask': {
                    'user_db_path': {
                        'help': 'Path to user database',
                        'conf_type': 'string'
                    }
                }
            },
            'answers': {
                'trellis': {
                    'content_dpath': '/var/www/content'
                },
                'qdflask': {
                    'user_db_path': '<trellis.content_dpath>/users.db'
                }
            }
        }
        self._make_repo_with_qd_conf(repo_dir, qd_conf)
        qdstart.plan_site(str(site_dir), quiet=False,
                          repo_list=[str(repo_dir)])
        captured = capsys.readouterr()
        assert "qdflask.user_db_path" in captured.out
        assert "<trellis.content_dpath>/users.db" in captured.out
        # Expanded value shown
        assert "/var/www/content/users.db" in captured.out


class TestRandomFill:
    """Tests for CONF_TYPE_RANDOM_FILL auto-generation."""

    _HEX64_RE = re.compile(r'^[0-9a-f]{64}$')

    def _make_qdstart_stub(self, tmp_path, answer_cache=None, conf=None):
        """Build a minimal QdStart-like object for handle_question()."""
        stub = object.__new__(qdstart.QdStart)
        stub.quiet = False
        stub.conf = conf
        stub.repo_scanner = qdrepos.RepoScanner(
            str(tmp_path), in_memory=True
        )
        if answer_cache:
            stub.repo_scanner.answer_cache.update(answer_cache)
        return stub

    def test_random_fill_generates_when_no_answer(self, tmp_path):
        """random_fill question with no pre-existing answer auto-generates."""
        stub = self._make_qdstart_stub(tmp_path)
        question = qdrepos.ConfQuestion(
            qdrepos.CONF_TYPE_RANDOM_FILL,
            'denv.FLASK_SECRET_KEY',
            'Secret key for Flask session signing'
        )
        answer = stub.handle_question(question)
        assert answer.conf_value is not None
        assert self._HEX64_RE.match(answer.conf_value)

    def test_random_fill_uses_existing_conf(self, tmp_path):
        """random_fill uses SOURCE_CONFIGURED when key exists in conf."""
        conf_dir = tmp_path / 'conf'
        conf_dir.mkdir()
        env_file = conf_dir / '.env'
        env_file.write_text('FLASK_SECRET_KEY=existing_secret\n')
        conf = qdconf.QdConf(str(conf_dir))

        stub = self._make_qdstart_stub(tmp_path, conf=conf)
        question = qdrepos.ConfQuestion(
            qdrepos.CONF_TYPE_RANDOM_FILL,
            'denv.FLASK_SECRET_KEY',
            'Secret key for Flask session signing'
        )
        answer = stub.handle_question(question)
        assert answer.conf_value == 'existing_secret'
        assert answer.source == qdstart.SOURCE_CONFIGURED

    def test_random_fill_uses_answer_cache(self, tmp_path):
        """random_fill uses SOURCE_CONSTANT when key is in answer_cache."""
        stub = self._make_qdstart_stub(
            tmp_path,
            answer_cache={'denv.FLASK_SECRET_KEY': 'cached_secret'}
        )
        question = qdrepos.ConfQuestion(
            qdrepos.CONF_TYPE_RANDOM_FILL,
            'denv.FLASK_SECRET_KEY',
            'Secret key for Flask session signing'
        )
        answer = stub.handle_question(question)
        assert answer.conf_value == 'cached_secret'
        assert answer.source == qdstart.SOURCE_CONSTANT

    def test_plan_site_labels_random_fill(self, tmp_path, capsys):
        """plan_site() shows '(auto-generated)' for random_fill questions."""
        site_dir = tmp_path / 'site'
        site_dir.mkdir()
        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()

        pkg_dir = repo_dir / 'mypkg'
        pkg_dir.mkdir(parents=True)
        qd_conf = {
            'questions': {
                'denv': {
                    'MY_SECRET': {
                        'help': 'A secret value',
                        'conf_type': 'random_fill'
                    }
                }
            }
        }
        qdos.write_toml(str(pkg_dir / 'qd_conf.toml'), qd_conf)
        qdstart.plan_site(str(site_dir), quiet=False,
                          repo_list=[str(repo_dir)])
        captured = capsys.readouterr()
        assert "denv.MY_SECRET (auto-generated)" in captured.out
