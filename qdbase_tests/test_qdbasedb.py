"""
Tests for qdbase.qdbasedb module-level SQL generation helpers.

These test the shared helpers that are now in qdbasedb and
re-exported by qdsqlite for backward compatibility.
"""

import pytest

from qdbase import pdict
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


# ---- select order_by and count tests (via QdSqlite) ----


def _make_items_db():
    """Helper: create an in-memory db with a simple items table."""
    from qdbase import qdsqlite, pdict
    spec = pdict.DbDictDb()
    table = spec.add_table(pdict.DbDictTable("items"))
    table.add_column(pdict.Text("name"))
    table.add_column(pdict.Number("quantity"))

    db = qdsqlite.QdSqlite(
        qdsqlite.SQLITE_IN_MEMORY_FN, db_dict=spec, update_schema=True
    )
    db.insert("items", {"name": "cherry", "quantity": 5})
    db.insert("items", {"name": "apple", "quantity": 10})
    db.insert("items", {"name": "banana", "quantity": 3})
    return db


def test_select_order_by_single():
    """order_by with a single column string."""
    db = _make_items_db()
    rows = db.select("items", "*", order_by="name")
    names = [row["name"] for row in rows]
    assert names == ["apple", "banana", "cherry"]


def test_select_order_by_desc():
    """order_by with DESC suffix."""
    db = _make_items_db()
    rows = db.select("items", "*", order_by="quantity DESC")
    quantities = [row["quantity"] for row in rows]
    assert quantities == [10, 5, 3]


def test_select_order_by_list():
    """order_by with a list of columns."""
    db = _make_items_db()
    rows = db.select("items", "*", order_by=["quantity ASC", "name"])
    names = [row["name"] for row in rows]
    assert names == ["banana", "cherry", "apple"]


def test_select_order_by_with_limit():
    """order_by combined with limit."""
    db = _make_items_db()
    rows = db.select("items", "*", order_by="name", limit=2)
    names = [row["name"] for row in rows]
    assert names == ["apple", "banana"]


def test_select_order_by_with_limit_offset():
    """order_by combined with limit and offset."""
    db = _make_items_db()
    rows = db.select("items", "*", order_by="name", limit=1, offset=1)
    names = [row["name"] for row in rows]
    assert names == ["banana"]


def test_count_all():
    """count() without where returns total rows."""
    db = _make_items_db()
    assert db.count("items") == 3


def test_count_with_where():
    """count() with where clause filters rows."""
    db = _make_items_db()
    assert db.count("items", where={"name": "apple"}) == 1


def test_count_no_matches():
    """count() returns 0 when no rows match."""
    db = _make_items_db()
    assert db.count("items", where={"name": "grape"}) == 0


def test_count_with_comparison():
    """count() with tuple-based comparison operator."""
    db = _make_items_db()
    assert db.count("items", where={"quantity": (">", 4)}) == 2


# ---- pdict REST metadata tests ----


def test_column_rest_metadata_defaults():
    """New REST metadata slots have correct defaults."""
    col = pdict.Text("test_col")
    assert col.is_filterable is True
    assert col.is_sortable is True
    assert col.is_create_required is False
    assert col.is_update_allowed is True
    assert col.rest_label is None


def test_column_rest_metadata_custom():
    """REST metadata can be set via constructor."""
    col = pdict.Text(
        "test_col",
        is_filterable=False,
        is_sortable=False,
        is_create_required=True,
        is_update_allowed=False,
        rest_label="Test Column",
    )
    assert col.is_filterable is False
    assert col.is_sortable is False
    assert col.is_create_required is True
    assert col.is_update_allowed is False
    assert col.rest_label == "Test Column"


def test_column_rest_metadata_ignored_by_sql():
    """REST metadata does not affect SQL generation."""
    col_plain = pdict.Text("col_a")
    col_rest = pdict.Text(
        "col_a",
        is_filterable=False,
        is_create_required=True,
        rest_label="Label",
    )
    assert col_plain.sql() == col_rest.sql()
