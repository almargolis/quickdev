from qdbase import pdict
from qdbase import qdsqlite

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
