"""
QdSqlite is a pythonic wrapper around SqLite3 that inherits
from QdBaseDb for shared SQL generation and CRUD methods.

This is used by XSynth in stand-alone mode, so it can't
use XSynth features.

A pdict.DbDictDb object provides the canonical schema for the database.
Methods are provided to create a new datadabase and to update an
existing database to match the dictionary.

Specific methods are for most SQl statements to generate the statements,
generally using convenient Python dict objects to spedify what is
needed.

The object also exposes sqlite3.execute(), sqlite.commit() and other
methods so it can often also be used as an ordinary sqlite database
object. This allows many examples of standard code to work as-is.
This was used effectively with the blog example code in the Flask
tutorial.
"""

import datetime
import sqlite3
from qdbase import pdict
from qdbase.qdbasedb import (
    QdBaseDb,
    AttributeName,
    dict_to_sql_expression,
    dict_to_sql_flds,
    row_repr,
)

# Re-export helpers for backward compatibility
__all__ = [
    "QdSqlite",
    "AttributeName",
    "dict_to_sql_expression",
    "dict_to_sql_flds",
    "row_repr",
    "sql_to_pdict_table",
    "SQLITE_IN_MEMORY_FN",
    "SQLITE_TEMP_FN",
]

# 1   configure a better timestamp format.
# borrowed from flask tutorial db.py.
# works with connect(detect_types=sqlite3.PARSE_DECLTYPES)
sqlite3.register_converter(
    "TIMESTAMP", lambda v: datetime.datetime.fromisoformat(v.decode())
)


SQLITE_IN_MEMORY_FN = ":memory:"
SQLITE_TEMP_FN = ""


def sql_to_pdict_table(sql, db_pdict=None, debug=False):
    if db_pdict is None:
        db_pdict = pdict.DbDictDb()
    lines = sql.split("\n")
    create_parts = lines[0].split()
    table_name = create_parts[2]
    t = pdict.DbDictTable(table_name, is_rowid_table=False)
    if debug:
        print(f"***** Create pdict table from schema for '{table_name}'")
    for column_line in lines[1:]:
        if debug:
            print("COL SQL:", column_line)
        column_line = column_line.strip()
        if column_line in [")", ");"]:
            break
        column_parts = column_line.split()
        if column_parts[0] == 'FOREIGN':
            # FOREIGN KEY (col_2b) REFERENCES table_1 (id)
            this_field_name = column_parts[2]
            this_field_name = this_field_name[1:-1]
            this_field_obj = t.columns[this_field_name]
            foreign_table_name = column_parts[4]
            foreign_table_obj = db_pdict.tables[foreign_table_name]
            foreign_field_name = column_parts[5]
            foreign_field_name = foreign_field_name[1:-1]
            foreign_field_obj = foreign_table_obj.columns[foreign_field_name]
            this_field_obj.foreign_key = pdict.ForeignKey(foreign_field_obj)
            continue
        column_name = column_parts[0]
        field_type = column_parts[1]
        if "NOT NULL" in column_line:
            allow_nulls = False
        else:
            allow_nulls = True
        if "PRIMARY KEY" in column_line:
            is_primary_key = True
        else:
            is_primary_key = False
        if "COLLATE NOCASE" in column_line:
            collate = "NOCASE"
        else:
            collate = None
        # default_value=None, is_read_only=False)
        if field_type == "INTEGER":
            c = pdict.Number(
                column_name,
                allow_nulls=allow_nulls,
                collate=collate,
                default_value=None,
                is_primary_key=is_primary_key,
                is_read_only=False,
            )
        elif field_type == "TEXT":
            c = pdict.Text(
                column_name,
                allow_nulls=allow_nulls,
                collate=collate,
                default_value=None,
                is_primary_key=is_primary_key,
                is_read_only=False,
            )
        else:
            raise ValueError(f"Unknown field type {column_parts}")
        t.add_column(c)
    db_pdict.add_table(t)
    if debug:
        print(f"***** End pdict table with {len(t.columns)} columns")
    return t


class QdSqlite(QdBaseDb):
    """
    Sqlite3 api with dictionary support and python methods
    that create all sql.
    """

    __slots__ = ()

    def __init__(
        self,
        fpath,
        db_dict=None,
        sql_create=None,
        detailed_exceptions=True,
        update_schema=False,
        debug=0,
    ):  # pylint: disable=too-many-arguments
        """
        Initialize Sqlite3 access

        If this is a new database, either db_dict or sql_create can be provided
        to define database structure.
        """
        self.db_dict = db_dict
        self.sql_create = sql_create
        self.detailed_exceptions = detailed_exceptions
        self.debug = debug
        self.db_module = sqlite3
        self.db_conn = sqlite3.connect(fpath, detect_types=sqlite3.PARSE_DECLTYPES)
        if self.debug > 0:
            self.db_conn.set_trace_callback(print)
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()
        self.load_schema()
        if (len(self.db_schema) == 0) or update_schema:
            self.db_update_tables()

    def load_schema(self):
        self.db_schema = {}
        self.db_cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table';"
        )
        for t in self.db_cursor.fetchall():
            self.db_schema[t[0]] = t[1]

    def drop_column(self, table_name, column_name):
        sql = f"ALTER TABLE {table_name} DROP COLUMN {column_name};"
        self.db_cursor.execute(sql)
        self.db_conn.commit()

    def db_update_columns(self, table_name):
        schema_sql = self.db_schema[table_name]
        schema_t = sql_to_pdict_table(schema_sql)
        dict_t = self.db_dict.tables[table_name]
        for this_schema_column_name in schema_t.columns.keys():
            if this_schema_column_name not in dict_t.columns:
                self.drop_column(table_name, this_schema_column_name)
                del schema_t.columns[this_schema_column_name]
        for this_dict_field_name in dict_t.columns.keys():
            if this_dict_field_name not in schema_t.columns:
                column_sql = dict_t.columns[this_dict_field_name].sql()
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_sql};"
                self.db_cursor.execute(sql)
                self.db_conn.commit()

    def db_update_tables(self):
        """
        Create tables and indexes for a database.

        The create statements can either be supplied as a list
        of sql statements (self.sql_create)
        or a pdict dictionary (self.db_dict).
        """
        if self.db_dict is None:
            return
        for this_schema_table_name in list(self.db_schema.keys()):
            # drop tables that are not in dict
            if this_schema_table_name not in self.db_dict.tables:
                sql = f"DROP TABLE {this_schema_table_name};"
                self.db_cursor.execute(sql)
                self.db_conn.commit()
                del self.db_schema[this_schema_table_name]
        for this_dict_table_name in self.db_dict.tables.keys():
            if this_dict_table_name in self.db_schema:
                # check fields if existing table
                self.db_update_columns(this_dict_table_name)
            else:
                # create table that has been added to dictionary
                sql = self.db_dict.tables[this_dict_table_name].sql()
                self.db_cursor.execute(sql)
                self.db_conn.commit()
                self.db_schema[this_dict_table_name] = sql

    def executescript(self, sql_script):
        self.db_conn.executescript(sql_script)
