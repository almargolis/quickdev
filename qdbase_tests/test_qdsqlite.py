import pytest

from qdbase import pdict
from qdbase import qdsqlite
from qdbase.qdsqlite import dict_to_sql_expression, AttributeName

from . import test_pdict


def make_pdict():
    """ Make a pdict with two tables. """
    test_dict = pdict.DbDictDb()
    table_1 = test_dict.add_table(pdict.DbDictTable("table_1"))
    table_1.add_column(pdict.Text("col_1a"))
    table_1.add_column(pdict.Number("col_1b"))
    table_1.add_column(pdict.Text("col_1c"))

    table_2 = test_dict.add_table(pdict.DbDictTable("table_2"))
    table_2.add_column(pdict.Text("col_2a"))
    table_2.add_column(
        pdict.Number("col_2b", foreign_key=pdict.ForeignKey(table_1.columns["id"]))
    )
    return test_dict


def test_create_db():
    """ Create a database and make sure that it is consisten with the specification pdict. """
    specification_pdict = make_pdict()
    db = qdsqlite.QdSqlite(
        qdsqlite.SQLITE_IN_MEMORY_FN, db_dict=specification_pdict, update_schema=True
    )
    db_pdict = pdict.DbDictDb()
    for ix, (this_table_name, this_table_sql) in enumerate(db.db_schema.items()):
        print(f"***** Schema Table {ix}: '{this_table_name}'")
        print(this_table_sql)
        print("***** End Schema")
        this_table_dict = qdsqlite.sql_to_pdict_table(this_table_sql, db_pdict, debug=True)
        test_pdict.compare_pdict_tables(
            this_table_dict, specification_pdict.tables[this_table_name]
        )


def test_drop_column():
    # column count is one higher than obvious due to column 'id'
    db = qdsqlite.QdSqlite(
        qdsqlite.SQLITE_IN_MEMORY_FN, db_dict=make_pdict(), update_schema=True
    )
    print(db.db_dict.tables["table_1"].columns.keys())
    assert len(db.db_dict.tables["table_1"].columns) == 4
    schema_table_sql = db.db_schema["table_1"]
    db_pdict = pdict.DbDictDb()
    schema_table_pdict = qdsqlite.sql_to_pdict_table(schema_table_sql, db_pdict, debug=True)
    assert len(schema_table_pdict.columns) == 4
    #
    # drop sqlite3 column and get new schema pdict
    #
    db.drop_column("table_1", "col_1b")
    db.load_schema()
    schema_table_sql = db.db_schema["table_1"]
    db_pdict = pdict.DbDictDb()
    schema_table_pdict = qdsqlite.sql_to_pdict_table(schema_table_sql, db_pdict, debug=True)
    assert len(schema_table_pdict.columns) == 3
    #
    # create modified specification reflecting dropped column
    #
    deleted_spec_table = db.db_dict.tables["table_1"].copy(None)
    del deleted_spec_table.columns["col_1b"]
    assert len(deleted_spec_table.columns) == 3
    #
    test_pdict.compare_pdict_tables(schema_table_pdict, deleted_spec_table)


# ---- dict_to_sql_expression tests ----


def test_expr_dict_and():
    """Dict with AND separator produces same result as before."""
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


def test_expr_list_with_select():
    """List-based WHERE works end-to-end through QdSqlite.select()."""
    spec = pdict.DbDictDb()
    table = spec.add_table(pdict.DbDictTable("items"))
    table.add_column(pdict.Text("name"))
    table.add_column(pdict.Text("color"))

    db = qdsqlite.QdSqlite(
        qdsqlite.SQLITE_IN_MEMORY_FN, db_dict=spec, update_schema=True
    )
    db.insert("items", {"name": "apple", "color": "red"})
    db.insert("items", {"name": "banana", "color": "yellow"})
    db.insert("items", {"name": "cherry", "color": "red"})
    db.insert("items", {"name": "daisy", "color": "white"})

    # OR query: name='banana' OR color='red'
    rows = db.select("items", "*", where=[
        {'name': 'banana'},
        {'color': 'red'},
    ])
    names = sorted(row['name'] for row in rows)
    assert names == ['apple', 'banana', 'cherry']
