"""
Database methods for XPython project database.
"""

import sqlite3

def dict_to_sql_equal(source_dict, seperator):
    """
    Convert a dictionary to a string of comma separated
    sql "fld = ?" statements plus a list of substituion
    values.

    This can be used both for update asignments and
    where clause comparisions.
    """
    sql = ''
    values = []
    if source_dict is not None:
        ix = -1
        for this in source_dict.items():
            ix += 1
            if ix > 0:
                sql += seperator
            sql += this[0] + '=?'
            values.append(this[1])
    return sql, values

def dict_to_sql_flds(source_dict):
    """
    Create a list of comma separated field names
    from a dictionary.
    """
    flds = ''
    value_str = ''
    value_data = []
    for ix, this in enumerate(source_dict.items()):
        if ix > 0:
            flds += ', '
            value_str += ', '
        flds += this[0]
        value_str += '?'
        value_data.append(this[1])
    return flds, value_str, value_data



class SqliteEz:
    """
    Sqlite3 api with dictionary support and python methods
    that create all sql.
    """
    __slots__ = ('db_conn', 'db_cursor', 'db_dict', 'debug', 'sql_create')

    def __init__(self, path, db_dict=None, sql_create=None, debug=0):
        self.db_dict = db_dict
        self.sql_create = sql_create
        self.debug = debug
        self.db_conn = sqlite3.connect(path)
        self.db_conn.row_factory = sqlite3.Row
        self.db_cursor = self.db_conn.cursor()
        self.db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [v[0] for v in self.db_cursor.fetchall() if v[0] != "sqlite_sequence"]
        if len(tables) == 0:
            self.db_init()

    def db_init(self):
        """
        Create tables and indexes for a database.

        The create statements can either be supplied as a list
        of sql statements or a pdict dictionary.
        """
        if self.db_dict is not None:
            self.sql_create = self.db_dict.sql_list()
            print(self.sql_create)
        if self.sql_create is not None:
            for this in self.sql_create:
                self.db_cursor.execute(this)

        self.db_conn.commit()

    def delete(self, table, where=None):
        """Perform SQL delete command."""
        sql = 'DELETE FROM {}'.format(table)
        if where is not None:
            where_sql, where_values = dict_to_sql_equal(where, ' AND ')
            sql += ' WHERE ' + where_sql
        else:
            where_values = []
        sql += ';'
        if self.debug > 0:
            print("SQL {} {}".format(sql, where_values))
        self.db_cursor.execute(sql, tuple(where_values))

    def insert(self, table, flds):
        """Perform SQL insert command."""
        flds_sql_list, flds_value_str, flds_values = dict_to_sql_flds(flds)
        sql = 'INSERT INTO {} ({}) VALUES ({});'.format(table, flds_sql_list, flds_value_str)
        if self.debug > 0:
            print("SQL {} {}".format(sql, flds_values))
        self.db_cursor.execute(sql, tuple(flds_values))
        self.db_conn.commit()

    def select(self, table, flds='*', where=None):
        """Perform SQL select command."""
        sql = 'SELECT '
        if isinstance(flds, str):
            sql += flds
        else:
            sql += ' '.join(flds)
        sql += ' FROM ' + table
        if where is None:
            where_values = []
        else:
            where_sql, where_values = dict_to_sql_equal(where, ' AND ')
            sql += ' WHERE ' + where_sql
        sql += ';'
        if self.debug > 0:
            print("SQL {} {}".format(sql, where_values))
        self.db_cursor.execute(sql, tuple(where_values))
        return self.db_cursor.fetchall()

    def update_insert(self, table, flds, where):
        """
        Perform SQL insert or update command depending
        on whether or not a match is found for where clause.
        """
        sql_data = self.select(table, '*', where=where)
        if len(sql_data) == 0:
            self.insert(table, flds)
        else:
            self.update(table, flds, where=where)

    def update(self, table, flds, where=None):
        """Perform SQL update command."""
        flds_sql, flds_values = dict_to_sql_equal(flds, ', ')
        sql = 'UPDATE {} SET {}'.format(table, flds_sql)
        if where is not None:
            where_sql, where_values = dict_to_sql_equal(where, ' AND ')
            sql += ' WHERE ' + where_sql
            flds_values += where_values
        sql += ';'
        if self.debug > 0:
            print("SQL {} {}".format(sql, flds_values))
        self.db_cursor.execute(sql, tuple(flds_values))
