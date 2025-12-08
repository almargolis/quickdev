from qdbase import pdict
from qdbase import qdsqlite

from . import test_pdict


def make_dict():
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
    db = qdsqlite.QdSqlite(
        qdsqlite.SQLITE_IN_MEMORY_FN, db_dict=make_dict(), update_schema=True
    )
    for this_table_name, this_table_sql in db.db_schema.items():
        print(this_table_sql)
        this_table_dict = qdsqlite.sql_to_pdict_table(this_table_sql, debug=True)
        test_pdict.compare_pdict_table_columns(
            this_table_dict, db.db_dict.tables[this_table_name]
        )


def test_drop_column():
    # column count is one higher than obvious due to column 'id'
    db = qdsqlite.QdSqlite(
        qdsqlite.SQLITE_IN_MEMORY_FN, db_dict=make_dict(), update_schema=True
    )
    print(db.db_dict.tables["table_1"].columns.keys())
    assert len(db.db_dict.tables["table_1"].columns) == 4
    schema_table_sql = db.db_schema["table_1"]
    schema_table_pdict = qdsqlite.sql_to_pdict_table(schema_table_sql, debug=True)
    assert len(schema_table_pdict.columns) == 4
    #
    db.drop_column("table_1", "col_1b")
    db.load_schema()
    gen_pdict_table = db.db_dict.tables["table_1"].copy()
    del gen_pdict_table.columns["col_1b"]
    assert len(gen_pdict_table.columns) == 3
    schema_table_sql = db.db_schema["table_1"]
    schema_table_pdict = qdsqlite.sql_to_pdict_table(schema_table_sql, debug=True)
    assert len(schema_table_pdict.columns) == 3
    test_pdict.compare_pdict_table_columns(gen_pdict_table, schema_table_pdict)
