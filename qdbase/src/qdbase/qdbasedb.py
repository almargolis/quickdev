"""
QdBaseDb is a base class for pythonic database wrappers.

It captures the shared SQL generation logic and CRUD methods
that are portable across database engines using '?' placeholders
(sqlite3, mariadb).

Subclasses must implement:
- load_schema()
- db_update_tables()

And set self.db_module to the database driver module (e.g., sqlite3
or mariadb) so that exception handling works correctly.
"""


class AttributeName:  # pylint: disable=too-few-public-methods
    """
    Container for attribute names.
    """

    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name


def _dict_sql_clauses(source_dict, separator):
    """
    Convert a dictionary to separator-joined SQL clauses
    plus a list of substitution values.

    Each dictionary key is a field / attribute name. If the
    value is a tuple, the first element is the comparison
    operator and the second is the operand. If the value is
    not a tuple, equality (=) is assumed. If the operand is
    an instance of AttributeName, it is treated as a field
    name; otherwise it is treated as a literal value.
    """
    sql_parts = []
    values = []
    for key, value in source_dict.items():
        if isinstance(value, tuple):
            sql_operator = value[0]
            sql_operand = value[1]
        else:
            sql_operator = "="
            sql_operand = value
        if isinstance(sql_operand, AttributeName):
            sql_parts.append(key + sql_operator + sql_operand.name)
        else:
            sql_parts.append(key + sql_operator + "?")
            values.append(sql_operand)
    return separator.join(sql_parts), values


def _sql_expr_recursive(source):
    """
    Recursively convert dicts and lists to SQL expressions.

    A dict produces AND-joined clauses wrapped in parentheses.
    A list produces OR-joined elements wrapped in parentheses.
    """
    if isinstance(source, dict):
        inner_sql, values = _dict_sql_clauses(source, " AND ")
        return "(" + inner_sql + ")", values
    if isinstance(source, list):
        sql_parts = []
        values = []
        for element in source:
            el_sql, el_values = _sql_expr_recursive(element)
            sql_parts.append(el_sql)
            values.extend(el_values)
        return "(" + " OR ".join(sql_parts) + ")", values
    raise TypeError(
        f"Expected dict or list, got {type(source).__name__}"
    )


def dict_to_sql_expression(source, seperator):
    """
    Convert a dict or list to a SQL expression string plus
    a list of substitution values.

    A dict ANDs its elements using the provided separator.
    A list ORs its elements. Dicts and lists can be nested
    recursively to build complex expressions. Each nested
    dict or list is enclosed in parentheses.

    The most common case is a list of dicts, which produces
    an OR of AND groups.

    This can be used both for update assignments and
    where clause comparisons.
    """
    if source is None:
        return "", []
    if isinstance(source, dict):
        return _dict_sql_clauses(source, seperator)
    if isinstance(source, list):
        return _sql_expr_recursive(source)
    raise TypeError(
        f"Expected dict or list, got {type(source).__name__}"
    )


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


class QdBaseDb:
    """
    Base class for database wrappers with dictionary support
    and Python methods that create all SQL.

    Subclasses must:
    1. Set self.db_module to the database driver module
    2. Set self.db_conn and self.db_cursor
    3. Implement load_schema() and db_update_tables()
    """

    __slots__ = (
        "db_conn",
        "db_cursor",
        "db_dict",
        "db_module",
        "db_schema",
        "debug",
        "detailed_exceptions",
        "sql_create",
    )

    @property
    def IntegrityError(self):
        return self.db_module.IntegrityError

    def close(self):
        if self.db_conn is not None:
            self.db_conn.close()
            self.db_conn = None

    def commit(self):
        """
        Execute the SQL statement. Compatible with basic sqlite3 db.
        """
        self.db_conn.commit()

    def load_schema(self):
        """
        Load the database schema into self.db_schema.

        Subclasses must implement this. The result should be a dict
        mapping table names to their CREATE TABLE SQL.
        """
        raise NotImplementedError("Subclasses must implement load_schema()")

    def db_update_tables(self):
        """
        Create/update tables to match self.db_dict.

        Subclasses must implement this with engine-specific DDL.
        """
        raise NotImplementedError(
            "Subclasses must implement db_update_tables()"
        )

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
        Execute the SQL statement. Compatible with basic sqlite3 db.
        """
        try:
            r = self.db_cursor.execute(
                sql, () if flds_values is None else tuple(flds_values)
            )
        except self.db_module.Error:
            if self.detailed_exceptions:
                print(f"QdBaseDb exception for {sql}")
                if flds_values is not None:
                    print(f"QdBaseDb values: {flds_values}")
            raise
        return r

    def insert(self, table, flds):
        """Perform SQL insert command."""
        flds_sql_list, flds_value_str, flds_values = dict_to_sql_flds(flds)
        sql = f"INSERT INTO {table} ({flds_sql_list}) VALUES ({flds_value_str});"
        if self.debug > 0:
            print(f"SQL {sql} {flds_values}")
        self.execute(sql, tuple(flds_values))
        self.db_conn.commit()
        return self.db_cursor.lastrowid

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
