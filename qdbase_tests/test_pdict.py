from qdbase import pdict


def compare_pdict_table_columns(t1, t2):
    assert len(t1.columns) == len(t2.columns)
    for this_column_name in t1.columns.keys():
        assert this_column_name in t2.columns
