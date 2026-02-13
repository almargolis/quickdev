"""
Tests for qdcore.flaskapp - FlaskAppGenerator.

Tests the generation of qd_create_app.py and .wsgi files from
repos.db flask_init metadata.
"""

import ast
import json
import os

from qdcore.qdrepos import RepoScanner
from qdcore.flaskapp import FlaskAppGenerator


def _make_pkg_with_flask_conf(tmp_path, pkg_name, flask_section,
                              questions=None, answers=None):
    """
    Create a minimal package with a qd_conf.toml containing a flask: section.

    Args:
        tmp_path: pytest tmp_path
        pkg_name: package directory name
        flask_section: dict for the flask: section
        questions: optional dict for the questions: section
        answers: optional dict for the answers: section

    Returns:
        Path to the repo directory
    """
    from qdbase import qdos

    repo_dir = tmp_path / 'repo'
    pkg_dir = repo_dir / 'src' / pkg_name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / '__init__.py').write_text('')

    conf = {}
    if questions:
        conf['questions'] = questions
    if answers:
        conf['answers'] = answers
    conf['flask'] = flask_section

    qdos.write_toml(str(pkg_dir / 'qd_conf.toml'), conf)
    return repo_dir


def _scan_and_generate(tmp_path, repo_dirs, venv_dpath=None,
                       answer_files=None):
    """
    Scan repos and create a FlaskAppGenerator.

    Returns:
        (generator, scanner) tuple
    """
    scanner = RepoScanner(str(tmp_path), in_memory=True)
    if answer_files:
        scanner.load_answer_files(answer_files)
    scanner.scan_directories([str(d) for d in repo_dirs])

    generator = FlaskAppGenerator(
        repo_scanner=scanner,
        qdsite_dpath=str(tmp_path),
        venv_dpath=venv_dpath,
        qdsite_prefix='test',
    )
    return generator, scanner


class TestFlaskSectionParsing:
    """Tests for RepoScanner parsing of flask: sections in qd_conf.toml."""

    def test_scan_flask_section(self, tmp_path):
        """Flask init_function is stored in flask_init table."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'mypkg', {
            'init_function': {
                'module': 'mypkg',
                'function': 'init_thing',
                'priority': 30,
            }
        })

        scanner = RepoScanner(str(tmp_path), in_memory=True)
        scanner.scan_directories([str(repo_dir)])

        seq = scanner.get_flask_init_sequence()
        assert len(seq) == 1
        assert seq[0]['module'] == 'mypkg'
        assert seq[0]['function'] == 'init_thing'
        assert seq[0]['priority'] == 30
        assert seq[0]['params'] is None
        scanner.close()

    def test_scan_flask_with_params(self, tmp_path):
        """Params are stored as JSON and retrieved as dicts."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'authpkg', {
            'init_function': {
                'module': 'authpkg',
                'function': 'init_auth',
                'priority': 10,
                'params': {
                    'roles': {
                        'source': 'answer',
                        'key': 'authpkg.roles',
                        'type': 'list',
                        'default': "['admin']",
                    }
                }
            }
        })

        scanner = RepoScanner(str(tmp_path), in_memory=True)
        scanner.scan_directories([str(repo_dir)])

        seq = scanner.get_flask_init_sequence()
        assert len(seq) == 1
        assert seq[0]['params'] is not None
        assert 'roles' in seq[0]['params']
        assert seq[0]['params']['roles']['source'] == 'answer'
        scanner.close()

    def test_scan_post_init(self, tmp_path):
        """post_init entries are stored as separate flask_init rows."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'flaskpkg', {
            'init_function': {
                'module': 'flaskpkg',
                'function': 'init_main',
                'priority': 10,
            },
            'post_init': [
                {
                    'module': 'flaskpkg.extras',
                    'function': 'init_extras',
                    'priority': 80,
                }
            ]
        })

        scanner = RepoScanner(str(tmp_path), in_memory=True)
        scanner.scan_directories([str(repo_dir)])

        seq = scanner.get_flask_init_sequence()
        assert len(seq) == 2
        assert seq[0]['function'] == 'init_main'
        assert seq[0]['priority'] == 10
        assert seq[1]['function'] == 'init_extras'
        assert seq[1]['priority'] == 80
        scanner.close()

    def test_flask_init_disabled_package(self, tmp_path):
        """Disabled packages are excluded from get_flask_init_sequence."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'disabled', {
            'init_function': {
                'module': 'disabled',
                'function': 'init_disabled',
                'priority': 50,
            }
        })

        scanner = RepoScanner(str(tmp_path), in_memory=True)
        scanner.scan_directories([str(repo_dir)])
        scanner.set_package_enabled('disabled', False)

        seq = scanner.get_flask_init_sequence()
        assert len(seq) == 0
        scanner.close()

    def test_flask_priority_ordering(self, tmp_path):
        """Multiple packages are returned in priority order."""
        from qdbase import qdos

        repo_dir = tmp_path / 'repo'

        # Package A: priority 50
        pkg_a = repo_dir / 'src' / 'pkga'
        pkg_a.mkdir(parents=True)
        (pkg_a / '__init__.py').write_text('')
        qdos.write_toml(str(pkg_a / 'qd_conf.toml'), {
            'flask': {
                'init_function': {
                    'module': 'pkga', 'function': 'init_a', 'priority': 50
                }
            }
        })

        # Package B: priority 10
        pkg_b = repo_dir / 'src' / 'pkgb'
        pkg_b.mkdir(parents=True)
        (pkg_b / '__init__.py').write_text('')
        qdos.write_toml(str(pkg_b / 'qd_conf.toml'), {
            'flask': {
                'init_function': {
                    'module': 'pkgb', 'function': 'init_b', 'priority': 10
                }
            }
        })

        scanner = RepoScanner(str(tmp_path), in_memory=True)
        scanner.scan_directories([str(repo_dir)])

        seq = scanner.get_flask_init_sequence()
        assert len(seq) == 2
        assert seq[0]['function'] == 'init_b'  # priority 10
        assert seq[1]['function'] == 'init_a'  # priority 50
        scanner.close()

    def test_config_module_stored_as_answer(self, tmp_path):
        """flask.config_module is stored in conf_answers."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'sitepkg', {
            'config_module': 'myapp.config.MyConfig',
        })

        scanner = RepoScanner(str(tmp_path), in_memory=True)
        scanner.scan_directories([str(repo_dir)])

        answers = scanner.get_answers()
        assert answers.get('flask.config_module') == \
            'myapp.config.MyConfig'
        scanner.close()

    def test_site_blueprints_stored_as_json_answer(self, tmp_path):
        """flask.site_blueprints is stored as JSON in conf_answers."""
        bps = [
            {'module': 'myapp.routes', 'name': 'main_bp'},
            {'module': 'myapp.routes', 'name': 'admin_bp'},
        ]
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'sitepkg', {
            'site_blueprints': bps,
        })

        scanner = RepoScanner(str(tmp_path), in_memory=True)
        scanner.scan_directories([str(repo_dir)])

        answers = scanner.get_answers()
        raw = answers.get('flask.site_blueprints')
        assert raw is not None
        parsed = json.loads(raw)
        assert len(parsed) == 2
        assert parsed[0]['name'] == 'main_bp'
        scanner.close()


class TestFlaskAppGeneration:
    """Tests for FlaskAppGenerator.generate_create_app()."""

    def test_generate_empty(self, tmp_path):
        """No flask_init rows → no file generated."""
        scanner = RepoScanner(str(tmp_path), in_memory=True)
        generator = FlaskAppGenerator(
            repo_scanner=scanner,
            qdsite_dpath=str(tmp_path),
        )
        result = generator.generate_create_app()
        assert result is None
        scanner.close()

    def test_generate_single_init(self, tmp_path):
        """Single init function generates valid Python with correct call."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'mypkg', {
            'init_function': {
                'module': 'mypkg',
                'function': 'init_thing',
                'priority': 50,
            }
        })

        generator, scanner = _scan_and_generate(tmp_path, [repo_dir])
        path = generator.generate_create_app()

        assert path is not None
        assert os.path.isfile(path)

        content = open(path).read()
        # Verify valid Python
        ast.parse(content)
        # Verify expected content
        assert 'from mypkg import init_thing' in content
        assert 'init_thing(app)' in content
        assert 'def qd_init_app(app):' in content
        assert 'def create_app(' in content
        scanner.close()

    def test_generate_ordering(self, tmp_path):
        """Init calls appear in priority order in generated code."""
        from qdbase import qdos

        repo_dir = tmp_path / 'repo'
        for name, priority in [('pkga', 50), ('pkgb', 10), ('pkgc', 90)]:
            pkg = repo_dir / 'src' / name
            pkg.mkdir(parents=True, exist_ok=True)
            (pkg / '__init__.py').write_text('')
            qdos.write_toml(str(pkg / 'qd_conf.toml'), {
                'flask': {
                    'init_function': {
                        'module': name,
                        'function': f'init_{name}',
                        'priority': priority,
                    }
                }
            })

        generator, scanner = _scan_and_generate(tmp_path, [repo_dir])
        path = generator.generate_create_app()
        content = open(path).read()

        # Verify order in the file
        pos_b = content.index('init_pkgb')
        pos_a = content.index('init_pkga')
        pos_c = content.index('init_pkgc')
        assert pos_b < pos_a < pos_c
        scanner.close()

    def test_generate_with_site_blueprints(self, tmp_path):
        """Site blueprints produce register_blueprint calls."""
        bps = [
            {'module': 'myapp.routes', 'name': 'main_bp'},
            {'module': 'myapp.routes', 'name': 'api_bp'},
        ]
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'mypkg', {
            'init_function': {
                'module': 'mypkg',
                'function': 'init_thing',
                'priority': 50,
            },
            'site_blueprints': bps,
        })

        generator, scanner = _scan_and_generate(tmp_path, [repo_dir])
        path = generator.generate_create_app()
        content = open(path).read()

        ast.parse(content)
        assert 'from myapp.routes import main_bp, api_bp' in content
        assert 'app.register_blueprint(main_bp)' in content
        assert 'app.register_blueprint(api_bp)' in content
        scanner.close()

    def test_generate_with_config_module(self, tmp_path):
        """config_module produces import in create_app()."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'mypkg', {
            'init_function': {
                'module': 'mypkg',
                'function': 'init_thing',
                'priority': 50,
            },
            'config_module': 'myapp.config.MyConfig',
        })

        generator, scanner = _scan_and_generate(tmp_path, [repo_dir])
        path = generator.generate_create_app()
        content = open(path).read()

        ast.parse(content)
        assert 'from myapp.config import MyConfig' in content
        assert 'config_class = MyConfig' in content
        scanner.close()

    def test_param_resolution_from_answer(self, tmp_path):
        """conf_answer source resolves to Python literal."""
        from qdbase import qdos

        repo_dir = tmp_path / 'repo'
        pkg = repo_dir / 'src' / 'authpkg'
        pkg.mkdir(parents=True)
        (pkg / '__init__.py').write_text('')
        qdos.write_toml(str(pkg / 'qd_conf.toml'), {
            'answers': {
                'authpkg': {
                    'roles': 'admin, editor, reader',
                    'login_view': 'auth.login',
                }
            },
            'flask': {
                'init_function': {
                    'module': 'authpkg',
                    'function': 'init_auth',
                    'priority': 10,
                    'params': {
                        'roles': {
                            'source': 'answer',
                            'key': 'authpkg.roles',
                            'type': 'list',
                            'default': "['admin']",
                        },
                        'login_view': {
                            'source': 'answer',
                            'key': 'authpkg.login_view',
                            'type': 'string',
                            'default': "'auth.login'",
                        }
                    }
                }
            }
        })

        generator, scanner = _scan_and_generate(tmp_path, [repo_dir])
        path = generator.generate_create_app()
        content = open(path).read()

        ast.parse(content)
        assert "['admin', 'editor', 'reader']" in content
        assert "'auth.login'" in content
        scanner.close()

    def test_param_resolution_default(self, tmp_path):
        """Missing answer falls back to default value."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'authpkg', {
            'init_function': {
                'module': 'authpkg',
                'function': 'init_auth',
                'priority': 10,
                'params': {
                    'roles': {
                        'source': 'answer',
                        'key': 'authpkg.roles',
                        'type': 'list',
                        'default': "['admin', 'editor']",
                    }
                }
            }
        })

        generator, scanner = _scan_and_generate(tmp_path, [repo_dir])
        path = generator.generate_create_app()
        content = open(path).read()

        ast.parse(content)
        # Default should appear since no answer was provided
        assert "['admin', 'editor']" in content
        scanner.close()

    def test_generate_idempotent(self, tmp_path):
        """Two consecutive generates produce identical output."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'mypkg', {
            'init_function': {
                'module': 'mypkg',
                'function': 'init_thing',
                'priority': 50,
            }
        })

        generator, scanner = _scan_and_generate(tmp_path, [repo_dir])
        path1 = generator.generate_create_app()
        content1 = open(path1).read()

        path2 = generator.generate_create_app()
        content2 = open(path2).read()

        assert content1 == content2
        scanner.close()

    def test_hooks_section_present(self, tmp_path):
        """Generated code contains hook loading and calling."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'mypkg', {
            'init_function': {
                'module': 'mypkg',
                'function': 'init_thing',
                'priority': 50,
            }
        })

        generator, scanner = _scan_and_generate(tmp_path, [repo_dir])
        path = generator.generate_create_app()
        content = open(path).read()

        assert '_load_hooks' in content
        assert 'register_error_handlers' in content
        assert 'register_context_processors' in content
        assert 'register_cli_commands' in content
        assert 'configure_app' in content
        assert 'site_hooks.py' in content
        scanner.close()


class TestWsgiGeneration:
    """Tests for FlaskAppGenerator.generate_wsgi()."""

    def test_generate_wsgi_no_venv(self, tmp_path):
        """No venv → no wsgi file generated."""
        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'mypkg', {
            'init_function': {
                'module': 'mypkg',
                'function': 'init_thing',
                'priority': 50,
            }
        })

        generator, scanner = _scan_and_generate(tmp_path, [repo_dir])
        result = generator.generate_wsgi()
        assert result is None
        scanner.close()

    def test_generate_wsgi_with_venv(self, tmp_path):
        """WSGI file contains correct paths and import."""
        # Create a fake venv with site-packages
        venv_dir = tmp_path / 'venv'
        sp_dir = venv_dir / 'lib' / 'python3.11' / 'site-packages'
        sp_dir.mkdir(parents=True)

        repo_dir = _make_pkg_with_flask_conf(tmp_path, 'mypkg', {
            'init_function': {
                'module': 'mypkg',
                'function': 'init_thing',
                'priority': 50,
            }
        })

        generator, scanner = _scan_and_generate(
            tmp_path, [repo_dir], venv_dpath=str(venv_dir))
        path = generator.generate_wsgi()

        assert path is not None
        assert path.endswith('wsgi.py')
        assert os.path.isfile(path)

        content = open(path).read()
        assert str(tmp_path) in content
        assert str(sp_dir) in content
        assert 'from qd_create_app import create_app' in content
        assert 'application = create_app()' in content
        scanner.close()


class TestFormatValue:
    """Tests for FlaskAppGenerator._format_value()."""

    def setup_method(self):
        self.gen = FlaskAppGenerator.__new__(FlaskAppGenerator)

    def test_list_from_comma_string(self):
        result = self.gen._format_value('admin, editor, reader', 'list')
        assert result == "['admin', 'editor', 'reader']"

    def test_list_from_list(self):
        result = self.gen._format_value(['a', 'b'], 'list')
        assert result == "['a', 'b']"

    def test_string(self):
        result = self.gen._format_value('hello', 'string')
        assert result == "'hello'"

    def test_boolean_true(self):
        result = self.gen._format_value('true', 'boolean')
        assert result == 'True'

    def test_boolean_yes(self):
        result = self.gen._format_value('yes', 'boolean')
        assert result == 'True'

    def test_boolean_false(self):
        result = self.gen._format_value('false', 'boolean')
        assert result == 'False'

    def test_int(self):
        result = self.gen._format_value('42', 'int')
        assert result == '42'

    def test_dict(self):
        result = self.gen._format_value({'key': 'val'}, 'dict')
        assert result == "{'key': 'val'}"
