"""
QdMariaDB is a pythonic wrapper around the mariadb connector
that inherits from QdBaseDb for shared SQL generation and CRUD methods.

MariaDB's Python connector uses '?' placeholders (same as sqlite3),
so all SQL generation code in QdBaseDb is fully portable.

The mariadb package is an optional dependency — it is imported
inside __init__ so the module can be imported without mariadb
installed (for introspection, help, etc.).
"""

from qdbase import pdict
from qdbase.qdbasedb import QdBaseDb


def mariadb_to_pdict_table(sql, db_pdict=None, debug=False):
    """
    Parse MariaDB's SHOW CREATE TABLE output into a pdict table.

    MariaDB's CREATE TABLE output uses backtick-quoted identifiers
    and includes engine/charset clauses that SQLite does not.
    """
    if db_pdict is None:
        db_pdict = pdict.DbDictDb()
    lines = sql.split("\n")
    # First line: CREATE TABLE `table_name` (
    create_parts = lines[0].split()
    table_name = create_parts[2].strip('`')
    t = pdict.DbDictTable(table_name, is_rowid_table=False)
    if debug:
        print(f"***** Create pdict table from MariaDB schema for '{table_name}'")
    for column_line in lines[1:]:
        if debug:
            print("COL SQL:", column_line)
        column_line = column_line.strip()
        if column_line.startswith(")"):
            break
        # Skip constraint lines
        if column_line.startswith("PRIMARY KEY"):
            continue
        if column_line.startswith("KEY ") or column_line.startswith("UNIQUE KEY"):
            continue
        if column_line.startswith("CONSTRAINT"):
            continue
        if column_line.startswith("FOREIGN KEY"):
            # FOREIGN KEY (`col`) REFERENCES `table` (`id`)
            parts = column_line.split()
            this_field_name = parts[2].strip('`()')
            this_field_obj = t.columns[this_field_name]
            foreign_table_name = parts[4].strip('`')
            foreign_table_obj = db_pdict.tables[foreign_table_name]
            foreign_field_name = parts[5].strip('`()')
            foreign_field_obj = foreign_table_obj.columns[foreign_field_name]
            this_field_obj.foreign_key = pdict.ForeignKey(foreign_field_obj)
            continue
        # Column definition: `col_name` type ...
        column_parts = column_line.rstrip(',').split()
        column_name = column_parts[0].strip('`')
        field_type_raw = column_parts[1].upper()
        if "NOT NULL" in column_line.upper():
            allow_nulls = False
        else:
            allow_nulls = True
        if "PRIMARY KEY" in column_line.upper() or "AUTO_INCREMENT" in column_line.upper():
            is_primary_key = True
        else:
            is_primary_key = False
        collate = None
        # Map MariaDB types to pdict types
        if field_type_raw.startswith("INT") or field_type_raw.startswith("BIGINT"):
            c = pdict.Number(
                column_name,
                allow_nulls=allow_nulls,
                collate=collate,
                default_value=None,
                is_primary_key=is_primary_key,
                is_read_only=False,
            )
        elif (
            field_type_raw.startswith("VARCHAR")
            or field_type_raw.startswith("TEXT")
            or field_type_raw.startswith("CHAR")
            or field_type_raw.startswith("LONGTEXT")
            or field_type_raw.startswith("MEDIUMTEXT")
        ):
            c = pdict.Text(
                column_name,
                allow_nulls=allow_nulls,
                collate=collate,
                default_value=None,
                is_primary_key=is_primary_key,
                is_read_only=False,
            )
        else:
            raise ValueError(
                f"Unknown MariaDB field type '{field_type_raw}' in: {column_line}"
            )
        t.add_column(c)
    db_pdict.add_table(t)
    if debug:
        print(f"***** End pdict table with {len(t.columns)} columns")
    return t


class QdMariaDB(QdBaseDb):
    """
    MariaDB api with dictionary support and python methods
    that create all sql.
    """

    __slots__ = ()

    def __init__(
        self,
        user,
        password,
        host="localhost",
        port=3306,
        database=None,
        db_dict=None,
        sql_create=None,
        detailed_exceptions=True,
        update_schema=False,
        debug=0,
    ):  # pylint: disable=too-many-arguments
        """
        Initialize MariaDB access.

        The mariadb package is imported here so it remains an
        optional dependency.
        """
        import mariadb
        self.db_dict = db_dict
        self.sql_create = sql_create
        self.detailed_exceptions = detailed_exceptions
        self.debug = debug
        self.db_module = mariadb
        self.db_conn = mariadb.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
        )
        self.db_cursor = self.db_conn.cursor(dictionary=True)
        self.load_schema()
        if (len(self.db_schema) == 0) or update_schema:
            self.db_update_tables()

    def load_schema(self):
        """
        Load the database schema using MariaDB's SHOW commands.

        Populates self.db_schema as {table_name: create_sql}.
        """
        self.db_schema = {}
        self.db_cursor.execute("SHOW TABLES;")
        tables = self.db_cursor.fetchall()
        for row in tables:
            # dictionary cursor returns {column_name: value}
            # SHOW TABLES returns a single column whose name
            # varies (e.g., Tables_in_<database>)
            table_name = list(row.values())[0]
            self.db_cursor.execute(f"SHOW CREATE TABLE `{table_name}`;")
            create_row = self.db_cursor.fetchall()[0]
            # Result has two columns: Table, Create Table
            create_sql = list(create_row.values())[1]
            self.db_schema[table_name] = create_sql

    def db_update_columns(self, table_name):
        """
        Update columns for an existing table to match db_dict.

        MariaDB supports DROP COLUMN natively (no table rebuild needed).
        """
        schema_sql = self.db_schema[table_name]
        schema_t = mariadb_to_pdict_table(schema_sql)
        dict_t = self.db_dict.tables[table_name]
        for this_schema_column_name in list(schema_t.columns.keys()):
            if this_schema_column_name not in dict_t.columns:
                sql = (
                    f"ALTER TABLE `{table_name}` "
                    f"DROP COLUMN `{this_schema_column_name}`;"
                )
                self.db_cursor.execute(sql)
                self.db_conn.commit()
                del schema_t.columns[this_schema_column_name]
        for this_dict_field_name in dict_t.columns.keys():
            if this_dict_field_name not in schema_t.columns:
                column_sql = dict_t.columns[this_dict_field_name].sql()
                sql = (
                    f"ALTER TABLE `{table_name}` "
                    f"ADD COLUMN {column_sql};"
                )
                self.db_cursor.execute(sql)
                self.db_conn.commit()

    def db_update_tables(self):
        """
        Create/update tables to match self.db_dict.

        Drops tables not in dict, creates missing tables, and
        updates columns on existing tables.
        """
        if self.db_dict is None:
            return
        for this_schema_table_name in list(self.db_schema.keys()):
            if this_schema_table_name not in self.db_dict.tables:
                sql = f"DROP TABLE `{this_schema_table_name}`;"
                self.db_cursor.execute(sql)
                self.db_conn.commit()
                del self.db_schema[this_schema_table_name]
        for this_dict_table_name in self.db_dict.tables.keys():
            if this_dict_table_name in self.db_schema:
                self.db_update_columns(this_dict_table_name)
            else:
                sql = self.db_dict.tables[this_dict_table_name].sql()
                self.db_cursor.execute(sql)
                self.db_conn.commit()
                self.db_schema[this_dict_table_name] = sql
