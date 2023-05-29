"""
SqliteEz is a stand-alone pythonic wrapper around SqLite3.

This is used by XSynth in stand-alone mode, so it can't
use XSynth features.
"""

import sqlite3

SQLITE_IN_MEMORY_FN = ":memory:"
SQLITE_TEMP_FN = ""


class AttributeName:  # pylint: disable=too-few-public-methods
    """
    Container for attribute names.
    """

    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name


def dict_to_sql_expression(source_dict, seperator):
    """
    Convert a dictionary to a string of comma separated
    sql "fld = ?" statements plus a list of substituion
    values.

    The dictionary key is the first element of a
    comparison clause and is always assumed to be a
    field / attribute name. If the dictionay element
    value is a tuple,
    the first element is the comparison sql_operatorerator and
    the second element is the second element of the
    comparison. If the second element is an instance
    of AttributeName, it is treated as a
    field / attribute name. Otherwise it is treated
    as a literal value.

    This can be used both for update asignments and
    where clause comparisions.
    """
    sql = ""
    values = []
    if source_dict is not None:
        for ix, (key, value) in enumerate(source_dict.items()):
            if ix > 0:
                sql += seperator
            if isinstance(value, tuple):
                sql_operator = value[0]
                sql_operand = value[1]
            else:
                sql_operator = "="
                sql_operand = value
            if isinstance(sql_operand, AttributeName):
                sql += key + sql_operator + sql_operand.name
            else:
                sql += key + sql_operator + "?"
                values.append(sql_operand)
    return sql, values


def dict_to_sql_flds(source_dict):
    """
    Create a list of comma separated field names
    from a dictionary.
    """
    flds = ""
    value_str = ""
    value_data = []
    for ix, this in enumerate(source_dict.items()):
        if ix > 0:
            flds += ", "
            value_str += ", "
        flds += this[0]
        value_str += "?"
        value_data.append(this[1])
    return flds, value_str, value_data


def row_repr(row):
    """
    The Sqlite Row object behaves more or less like a named tuple,
    but it doesn't have an __repr__ method. This method provides a
    dict-like __repr__ capability.
    """
    result = ""
    for key in row.keys():
        value = row[key]
        if result == "":
            sep = ""
        else:
            sep = ", "
        result += f"{sep}{key}: {value}"
    return "{" + result + "}"


class QdSqlite:
    """
    Sqlite3 api with dictionary support and python methods
    that create all sql.
    """

    __slots__ = (
        "db_conn",
        "db_cursor",
        "db_dict",
        "debug",
        "detailed_exceptions",
        "sql_create",
    )

    def __init__(
        self, fpath, db_dict=None, sql_create=None, detailed_exceptions=True, debug=0
    ):  # pylint: disable=too-many-arguments
        self.db_dict = db_dict
        self.sql_create = sql_create
        self.detailed_exceptions = detailed_exceptions
        self.debug = debug
        self.db_conn = sqlite3.connect(fpath)
        if self.debug > 0:
            self.db_conn.set_trace_callback(print)
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()
        self.db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [v[0] for v in self.db_cursor.fetchall() if v[0] != "sqlite_sequence"]
        if len(tables) == 0:
            self.db_create()

    def db_create(self):
        """
        Create tables and indexes for a database.

        The create statements can either be supplied as a list
        of sql statements or a pdict dictionary.
        """
        if self.db_dict is not None:
            self.sql_create = self.db_dict.sql_create_list()
            if self.debug > 0:
                print(self.sql_create)
        if self.sql_create is not None:
            for this in self.sql_create:
                self.db_cursor.execute(this)

        self.db_conn.commit()

    def delete(self, table, where=None):
        """Perform SQL delete command."""
        sql = f"DELETE FROM {table}"
        if where is not None:
            where_sql, where_values = dict_to_sql_expression(where, " AND ")
            sql += " WHERE " + where_sql
        else:
            where_values = []
        sql += ";"
        if self.debug > 0:
            print(f"SQL {sql} {where_values}")
        self.db_cursor.execute(sql, tuple(where_values))

    def execute(self, sql, flds_values=None):
        """
        Execute the SQL statement.
        """
        try:
            self.db_cursor.execute(sql, tuple(flds_values))
        except:
            if self.detailed_exceptions:
                # sqlite3 exceptions like sqlite3.IntegrityError
                # don't print enough information to identify error.
                # This just prints some context before letting the
                # exception process continue normally.
                print(f"EzSqlite exception for {sql}")
                if flds_values is not None:
                    print(f"EzSqlite values: {flds_values}")
            raise

    def insert(self, table, flds):
        """Perform SQL insert command."""
        flds_sql_list, flds_value_str, flds_values = dict_to_sql_flds(flds)
        sql = f"INSERT INTO {table} ({flds_sql_list}) VALUES ({flds_value_str});"
        if self.debug > 0:
            print(f"SQL {sql} {flds_values}")
        self.execute(sql, tuple(flds_values))
        self.db_conn.commit()

    def insert_unique(self, table, flds, where):
        """Perform SQL insert command if no existing records satisfy where."""
        select = self.select(table, "*", where=where)
        if len(select) > 0:
            raise KeyError(f'duplicate "{where}" found in table {table}')
        self.insert(table, flds)

    def lookup(self, table, flds="*", where=None):
        """
        Access a unique row. Often used for code lookups.

        Returns either the row or None.
        Raises KeyError if the selection isn't unique.
        """
        select = self.select(table, flds=flds, where=where)
        if len(select) > 1:
            raise KeyError(f'duplicate "{where}" found in table {table}')
        if len(select) == 1:
            return select[0]
        return None

    def require(self, table, flds="*", where=None):
        """
        Access a unique row. Often used for code lookups.

        Similar to lookup() but raises KeyError if the selection
        isn't unique or no matches found.
        """
        select = self.select(table, flds=flds, where=where)
        if len(select) != 1:
            raise KeyError(f'"{where}" not found in table {table}')
        return select[0]

    def select(
        self, table, flds="*", where=None, limit=0, offset=0
    ):  # pylint: disable=too-many-arguments
        """Perform SQL select command."""
        sql = "SELECT "
        if isinstance(flds, str):
            sql += flds
        else:
            sql += " ".join(flds)
        sql += " FROM " + table
        if where is None:
            where_values = []
        else:
            where_sql, where_values = dict_to_sql_expression(where, " AND ")
            sql += " WHERE " + where_sql
        if limit > 0:
            sql += f" LIMIT {limit}"
        if offset > 0:
            sql += f" OFFSET {offset}"
        sql += ";"
        if self.debug > 0:
            print(f"SQL {sql} {where_values}")
        self.db_cursor.execute(sql, tuple(where_values))
        return self.db_cursor.fetchall()

    def update_insert(self, table, flds, where, defaults=None):
        """
        Perform SQL insert or update command depending
        on whether or not a match is found for where clause.
        This methon only supports cases where the where
        clause identifies a single row / record.

        flds are the fields that we want to update for an existing
        row / record.

        where is assumed to be a simple dictionary and its values
        are inserted into the new row / record if no match is found.
        That assures that there is a match the next time that where
        clause is used. Despite that, this method can be used to
        change the columns / fields mentioned in the where clause by
        having the new values in the flds dictionary.

        defaults is a dictionary of column / field names and values that are
        inserted when a new row / record is inserted and are not specified
        by flds and where. These are only
        needed where they differ from column defaults specified when the
        sqlite3 table was created.
        """
        sql_data = self.select(table, "*", where=where)
        if len(sql_data) > 1:
            raise KeyError(f"Duplicate matches for {where} in table {table}")
        if len(sql_data) == 1:
            self.update(table, flds, where=where)
            return
        uflds = {}
        if defaults is not None:
            uflds.update(defaults)
        uflds.update(where)
        uflds.update(flds)
        self.insert(table, uflds)

    def update(self, table, flds, where=None):
        """Perform SQL update command."""
        flds_sql, flds_values = dict_to_sql_expression(flds, ", ")
        sql = f"UPDATE {table} SET {flds_sql}"
        if where is not None:
            where_sql, where_values = dict_to_sql_expression(where, " AND ")
            sql += " WHERE " + where_sql
            flds_values += where_values
        sql += ";"
        if self.debug > 0:
            print(f"SQL {sql} {flds_values}")
        self.db_cursor.execute(sql, tuple(flds_values))
        self.db_conn.commit()
