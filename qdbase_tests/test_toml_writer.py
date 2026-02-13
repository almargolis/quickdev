"""
Tests for qdos.write_toml() TOML writer.
"""

import os
import tomllib

from qdbase import qdos


def _roundtrip(tmp_path, data):
    """Write data to TOML and read it back."""
    fpath = os.path.join(str(tmp_path), 'test.toml')
    qdos.write_toml(fpath, data)
    with open(fpath, 'rb') as f:
        return tomllib.load(f)


class TestTomlWriterScalars:
    """Test scalar value types."""

    def test_string(self, tmp_path):
        result = _roundtrip(tmp_path, {'name': 'hello'})
        assert result['name'] == 'hello'

    def test_string_with_quotes(self, tmp_path):
        result = _roundtrip(tmp_path, {'msg': 'say "hi"'})
        assert result['msg'] == 'say "hi"'

    def test_string_with_backslash(self, tmp_path):
        result = _roundtrip(tmp_path, {'path': 'C:\\Users\\test'})
        assert result['path'] == 'C:\\Users\\test'

    def test_string_with_newline(self, tmp_path):
        result = _roundtrip(tmp_path, {'text': 'line1\nline2'})
        assert result['text'] == 'line1\nline2'

    def test_boolean_true(self, tmp_path):
        result = _roundtrip(tmp_path, {'flag': True})
        assert result['flag'] is True

    def test_boolean_false(self, tmp_path):
        result = _roundtrip(tmp_path, {'flag': False})
        assert result['flag'] is False

    def test_integer(self, tmp_path):
        result = _roundtrip(tmp_path, {'count': 42})
        assert result['count'] == 42

    def test_negative_integer(self, tmp_path):
        result = _roundtrip(tmp_path, {'offset': -5})
        assert result['offset'] == -5

    def test_float(self, tmp_path):
        result = _roundtrip(tmp_path, {'ratio': 3.14})
        assert abs(result['ratio'] - 3.14) < 0.001

    def test_none_skipped(self, tmp_path):
        result = _roundtrip(tmp_path, {'a': 1, 'b': None, 'c': 3})
        assert 'a' in result
        assert 'b' not in result
        assert 'c' in result


class TestTomlWriterLists:
    """Test list/array types."""

    def test_list_of_strings(self, tmp_path):
        result = _roundtrip(tmp_path, {'tags': ['a', 'b', 'c']})
        assert result['tags'] == ['a', 'b', 'c']

    def test_list_of_ints(self, tmp_path):
        result = _roundtrip(tmp_path, {'nums': [1, 2, 3]})
        assert result['nums'] == [1, 2, 3]

    def test_empty_list(self, tmp_path):
        result = _roundtrip(tmp_path, {'items': []})
        assert result['items'] == []

    def test_list_of_booleans(self, tmp_path):
        result = _roundtrip(tmp_path, {'flags': [True, False, True]})
        assert result['flags'] == [True, False, True]


class TestTomlWriterTables:
    """Test nested dict / table types."""

    def test_nested_dict(self, tmp_path):
        data = {'server': {'host': 'localhost', 'port': 8080}}
        result = _roundtrip(tmp_path, data)
        assert result['server']['host'] == 'localhost'
        assert result['server']['port'] == 8080

    def test_deeply_nested(self, tmp_path):
        data = {'a': {'b': {'c': {'d': 'deep'}}}}
        result = _roundtrip(tmp_path, data)
        assert result['a']['b']['c']['d'] == 'deep'

    def test_mixed_scalars_and_tables(self, tmp_path):
        data = {
            'title': 'My App',
            'database': {'host': 'db.local', 'port': 5432},
            'version': 1,
        }
        result = _roundtrip(tmp_path, data)
        assert result['title'] == 'My App'
        assert result['database']['host'] == 'db.local'
        assert result['version'] == 1


class TestTomlWriterArraysOfTables:
    """Test lists of dicts (TOML arrays of tables)."""

    def test_array_of_tables(self, tmp_path):
        data = {
            'servers': [
                {'name': 'alpha', 'port': 8001},
                {'name': 'beta', 'port': 8002},
            ]
        }
        result = _roundtrip(tmp_path, data)
        assert len(result['servers']) == 2
        assert result['servers'][0]['name'] == 'alpha'
        assert result['servers'][1]['port'] == 8002

    def test_nested_array_of_tables(self, tmp_path):
        data = {
            'flask': {
                'post_init': [
                    {'module': 'mod_a', 'function': 'init_a', 'priority': 10},
                    {'module': 'mod_b', 'function': 'init_b', 'priority': 90},
                ]
            }
        }
        result = _roundtrip(tmp_path, data)
        assert len(result['flask']['post_init']) == 2
        assert result['flask']['post_init'][0]['module'] == 'mod_a'
        assert result['flask']['post_init'][1]['priority'] == 90


class TestTomlWriterKeyQuoting:
    """Test keys that need quoting."""

    def test_key_with_dot(self, tmp_path):
        fpath = os.path.join(str(tmp_path), 'test.toml')
        data = {'server.name': 'test'}
        qdos.write_toml(fpath, data)
        with open(fpath, 'rb') as f:
            result = tomllib.load(f)
        assert result['server.name'] == 'test'

    def test_key_with_space(self, tmp_path):
        fpath = os.path.join(str(tmp_path), 'test.toml')
        data = {'my key': 'value'}
        qdos.write_toml(fpath, data)
        with open(fpath, 'rb') as f:
            result = tomllib.load(f)
        assert result['my key'] == 'value'


class TestTomlWriterComplex:
    """Test complex/realistic data structures."""

    def test_qd_conf_structure(self, tmp_path):
        """Simulate a qd_conf.toml structure."""
        data = {
            'questions': {
                'qdflask': {
                    'enabled': {
                        'help': 'Enable Flask authentication?',
                        'type': 'boolean',
                    },
                    'roles': {
                        'help': 'Comma-separated user roles',
                        'type': 'string',
                    },
                }
            },
            'flask': {
                'init_function': {
                    'module': 'qdflask',
                    'function': 'init_auth',
                    'priority': 10,
                },
                'post_init': [
                    {
                        'module': 'qdflask.mail_utils',
                        'function': 'init_mail',
                        'priority': 90,
                    }
                ],
            },
        }
        result = _roundtrip(tmp_path, data)
        assert result['questions']['qdflask']['enabled']['help'] == \
            'Enable Flask authentication?'
        assert result['flask']['init_function']['priority'] == 10
        assert len(result['flask']['post_init']) == 1
        assert result['flask']['post_init'][0]['module'] == \
            'qdflask.mail_utils'

    def test_empty_dict(self, tmp_path):
        result = _roundtrip(tmp_path, {})
        assert result == {}
