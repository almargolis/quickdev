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
        

