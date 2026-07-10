"""
Tests for qdbase.qdbasedb module-level SQL generation helpers.

These test the shared helpers that are now in qdbasedb and
re-exported by qdsqlite for backward compatibility.
"""

import pytest

from qdbase.qdbasedb import (
    AttributeName,
    dict_to_sql_expression,
    dict_to_sql_flds,
    row_repr,
)


# ---- dict_to_sql_expression tests ----


def test_expr_dict_and():
    """Dict with AND separator produces AND-joined clauses."""
    sql, vals = dict_to_sql_expression(
        {'status': 'active', 'role': 'admin'}, ' AND '
    )
    assert sql == 'status=? AND role=?'
    assert vals == ['active', 'admin']


def test_expr_dict_comma():
    """Dict with comma separator (UPDATE SET) still works."""
    sql, vals = dict_to_sql_expression({'name': 'Alice', 'age': 30}, ', ')
    assert sql == 'name=?, age=?'
    assert vals == ['Alice', 30]


def test_expr_none():
    sql, vals = dict_to_sql_expression(None, ' AND ')
    assert sql == ''
    assert vals == []


def test_expr_tuple_operator():
    """Tuple values provide a custom operator."""
    sql, vals = dict_to_sql_expression({'age': ('>', 18)}, ' AND ')
    assert sql == 'age>?'
    assert vals == [18]


def test_expr_attribute_name():
    """AttributeName operand emits a field name, not a placeholder."""
    sql, vals = dict_to_sql_expression(
        {'a': AttributeName('b')}, ' AND '
    )
    assert sql == 'a=b'
    assert vals == []


def test_expr_list_of_dicts():
    """A list of dicts produces OR of AND groups."""
    sql, vals = dict_to_sql_expression([
        {'status': 'active', 'role': 'admin'},
        {'status': 'active', 'role': 'editor'},
    ], ' AND ')
    assert sql == '((status=? AND role=?) OR (status=? AND role=?))'
    assert vals == ['active', 'admin', 'active', 'editor']


def test_expr_list_single_dict():
    """A single-element list still wraps in parens."""
    sql, vals = dict_to_sql_expression([{'x': 42}], ' AND ')
    assert sql == '((x=?))'
    assert vals == [42]


def test_expr_nested_list():
    """A list nested inside a list produces nested OR groups."""
    sql, vals = dict_to_sql_expression([
        {'a': 1},
        [{'b': 2}, {'c': 3}],
    ], ' AND ')
    assert sql == '((a=?) OR ((b=?) OR (c=?)))'
    assert vals == [1, 2, 3]


def test_expr_deep_recursion():
    """Three levels deep: list > list > list."""
    sql, vals = dict_to_sql_expression([
        {'a': 1},
        [{'b': 2}, [{'c': 3}, {'d': 4}]],
    ], ' AND ')
    assert sql == '((a=?) OR ((b=?) OR ((c=?) OR (d=?))))'
    assert vals == [1, 2, 3, 4]


def test_expr_tuple_operator_in_list():
    """Tuple operators work inside nested dicts."""
    sql, vals = dict_to_sql_expression([
        {'age': ('>', 18), 'status': 'active'},
        {'role': 'admin'},
    ], ' AND ')
    assert sql == '((age>? AND status=?) OR (role=?))'
    assert vals == [18, 'active', 'admin']


def test_expr_attribute_name_in_list():
    """AttributeName operands work inside nested dicts."""
    sql, vals = dict_to_sql_expression([
        {'a': AttributeName('b')},
        {'c': 1},
    ], ' AND ')
    assert sql == '((a=b) OR (c=?))'
    assert vals == [1]


def test_expr_type_error():
    """Passing an unsupported type raises TypeError."""
    with pytest.raises(TypeError):
        dict_to_sql_expression("bad", ' AND ')


# ---- dict_to_sql_flds tests ----


def test_dict_to_sql_flds():
    """dict_to_sql_flds produces field list, placeholder list, and values."""
    flds, value_str, values = dict_to_sql_flds(
        {'name': 'Alice', 'age': 30}
    )
    assert flds == 'name, age'
    assert value_str == '?, ?'
    assert values == ['Alice', 30]


def test_dict_to_sql_flds_single():
    """Single-field dict produces no commas."""
    flds, value_str, values = dict_to_sql_flds({'id': 1})
    assert flds == 'id'
    assert value_str == '?'
    assert values == [1]


# ---- row_repr tests ----


def test_row_repr():
    """row_repr formats a row-like object as a dict string."""

    class FakeRow:
        def __init__(self, data):
            self._data = data

        def keys(self):
            return self._data.keys()

        def __getitem__(self, key):
            return self._data[key]

    row = FakeRow({'name': 'Alice', 'age': 30})
    result = row_repr(row)
    assert result == '{name: Alice, age: 30}'
