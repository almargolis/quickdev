from qdbase import pdict


def compare_pdict_tables(schema_pdict, spec_pdict):
    """
    compare_pdict_tables()
    """
    assert len(schema_pdict.columns) == len(spec_pdict.columns)
    for this_column_name in schema_pdict.columns.keys():
        assert this_column_name in spec_pdict.columns
        schema_column = schema_pdict.columns[this_column_name]
        spec_column = spec_pdict.columns[this_column_name]
        assert isinstance(schema_column, spec_column.__class__)
        for this_attr_name in pdict.Column.__slots__:
            if this_attr_name == 'table_dict':
                assert schema_column.table_dict.name == spec_column.table_dict.name
                continue
            if this_attr_name == 'foreign_key':
                if schema_column.foreign_key is None:
                    assert spec_column.foreign_key is None
                else:
                    assert schema_column.foreign_key.key.table_dict.name == spec_column.foreign_key.key.table_dict.name
                    assert schema_column.foreign_key.key.name == spec_column.foreign_key.key.name
                continue
            if getattr(schema_column, this_attr_name) != getattr(spec_column, this_attr_name):
                print(f">>> COLUMN ATTR {this_attr_name} -- schema, spec")
                print(f"{schema_column.table_dict.name} {spec_column.table_dict.name}")
                print(schema_pdict.columns.keys())
                print(spec_pdict.columns.keys())
                print(f"{getattr(schema_column, this_attr_name)} {getattr(spec_column, this_attr_name)}")
            assert getattr(schema_column, this_attr_name) == getattr(spec_column, this_attr_name)


# --- Tests for form/validation metadata on Column ---

def test_column_form_metadata_defaults():
    """New form/validation slots should have sensible defaults."""
    col = pdict.Text("test_col")
    assert col.max_length is None
    assert col.min_length is None
    assert col.max_value is None
    assert col.min_value is None
    assert col.choices is None
    assert col.pattern is None
    assert col.form_widget is None
    assert col.placeholder is None


def test_column_form_metadata_set():
    """Form/validation metadata can be set via kwargs."""
    col = pdict.Text("name",
                     max_length=200,
                     min_length=1,
                     choices=['a', 'b', 'c'],
                     pattern=r'^[a-z]+$',
                     form_widget='select',
                     placeholder='Enter name')
    assert col.max_length == 200
    assert col.min_length == 1
    assert col.choices == ['a', 'b', 'c']
    assert col.pattern == r'^[a-z]+$'
    assert col.form_widget == 'select'
    assert col.placeholder == 'Enter name'


def test_number_column_value_metadata():
    """Number columns can use min_value and max_value."""
    col = pdict.Number("price", min_value=0, max_value=99999)
    assert col.min_value == 0
    assert col.max_value == 99999
    assert col.column_type == "INTEGER"


def test_form_metadata_does_not_affect_sql():
    """Form/validation metadata should not appear in SQL output."""
    col = pdict.Text("name",
                     max_length=200,
                     min_length=1,
                     choices=['a', 'b'],
                     pattern=r'^[a-z]+$',
                     form_widget='select',
                     placeholder='Enter name')
    sql = col.sql()
    assert "max_length" not in sql
    assert "min_length" not in sql
    assert "choices" not in sql
    assert "pattern" not in sql
    assert "form_widget" not in sql
    assert "placeholder" not in sql
    assert "name TEXT" in sql


def test_form_metadata_preserved_in_copy():
    """Form/validation metadata should survive copy()."""
    db = pdict.DbDictDb()
    t = db.add_table(pdict.DbDictTable("test"))
    col = t.add_column(pdict.Text("status",
                                  choices=['active', 'inactive'],
                                  max_length=20,
                                  form_widget='select'))
    db_copy = db.copy()
    col_copy = db_copy.tables["test"].columns["status"]
    assert col_copy.choices == ['active', 'inactive']
    assert col_copy.max_length == 20
    assert col_copy.form_widget == 'select'

