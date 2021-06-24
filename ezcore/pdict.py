"""
DbTableDict is a low level dictionary for raw python
components of EzDev.

This is used by XPython in stand-alone mode, so it can't
use XPython features.

"""

class DbDict:
    """
    Database dictionary primarily for use with sqlite_ez.
    """
    __slots__ = ('tables',)

    def __init__(self):
        self.tables = {}

    def add_table(self, table_dict):
        """Add a table to the dictionary."""
        if table_dict.name in self.tables:
            raise Exception("Duplicate table {}".format(table_dict.name))
        self.tables[table_dict.name] = table_dict
        return table_dict

    def sql_list(self):
        """Create a list of sql create statements to create database."""
        create_list = []
        for this in self.tables.values():
            create_list.append(this.sql())
            for this_index in this.indexes.values():
                create_list.append(this_index.sql())
        return create_list

class DbTableDict:
    """
    DbTableDict is a dictionary primarily intended to define
    sqlite3 databases. The default table design is a
    rowid table with an alias column of id. When needed,
    alternate keys are implemented as indexes.
    """
    __slots__ = ('columns', 'indexes', 'is_rowid_table', 'name')

    def __init__(self, name, is_rowid_table=True):
        self.columns = {}
        self.indexes = {}
        self.name = name
        self.is_rowid_table = is_rowid_table
        if self.is_rowid_table:
            id_col = self.add_column(Number('id'))
            id_col.is_primary_key = True

    def add_column(self, column):
        """Add a column to the table."""
        if column.name in self.columns:
            raise Exception("Duplicate column name '{}' in table '{}'".format(
                                column.name, self.name))
        self.columns[column.name] = column
        return column

    def add_index(self, name, columns, is_unique=True):
        """
            Add an index to the table.

            columns can be either a single column name or a list of
            column names.
        """
        if name in self.indexes:
            raise Exception("Duplicate index name '{}' in table '{}'".format(
                                name, self.name))
        if not isinstance(columns, list):
            columns = [columns]
        index = Index(name, columns, self, is_unique=is_unique)
        self.indexes[name] = index
        return index

    def sql(self, eol='\n'):
        """Create an sql create table command for this table."""
        table_def = "CREATE TABLE {} ({}".format(self.name, eol)
        last_column_ix = len(self.columns) - 1
        for ix, this in enumerate(self.columns.values()):
            table_def += this.sql()
            if (last_column_ix > 0) and (ix < last_column_ix):
                table_def += ','
            table_def += eol
        table_def += ");" + eol
        return table_def

class Index: # pylint: disable=too-few-public-methods
    """Represents an index for a table."""
    __slots__ = ('name', 'columns', 'is_unique', 'table_dict')

    def __init__(self, name, columns, table_dict, is_unique=True):
        self.name = name
        self.columns = []
        self.table_dict = table_dict
        for this in columns:
            if this not in table_dict.columns:
                raise Exception("Invalid index column '{}' for index {}.{}".format(
                                    this, table_dict.name, self.name
                ))
            self.columns.append(this)
        self.is_unique = is_unique

    def sql(self, eol='\n'):
        """Create sql CREATE INDEX statement string."""
        index_def = 'CREATE'
        if self.is_unique:
            index_def += ' UNIQUE'
        index_def += ' INDEX ' + self.name + eol
        index_def += 'ON ' + self.table_dict.name + '('
        last_column_ix = len(self.columns) - 1
        for ix, this in enumerate(self.columns):
            index_def += this
            if (last_column_ix > 0) and (ix < last_column_ix):
                index_def += ', '
        index_def += ');' + eol
        return index_def

class Column: # pylint: disable=too-few-public-methods
    """Base class for table columns."""
    __slots__ = ('allow_nulls', 'column_type', 'is_primary_key', 'name')

    def __init__(self, name, column_type, allow_nulls=False):
        self.name = name
        self.column_type = column_type
        self.allow_nulls = allow_nulls
        self.is_primary_key = False

    def sql(self):
        """Create sql column definition clause."""
        col_def = self.name + ' ' + self.column_type
        if not self.allow_nulls:
            col_def += ' NOT NULL'
        if self.is_primary_key:
            col_def += ' PRIMARY KEY'
        return col_def

class Number(Column): # pylint: disable=too-few-public-methods
    """Numeric column class."""
    __slots__ = ()

    def __init__(self, name, allow_nulls=False):
        # sqlite recognize int as an alias for INTEGER but
        # not for the aliasing of rowid.
        super().__init__(name, 'INTEGER', allow_nulls=allow_nulls)

class Text(Column): # pylint: disable=too-few-public-methods
    """Text column class."""
    __slots__ = ('allow_nulls',)

    def __init__(self, name, allow_nulls=False):
        super().__init__(name, 'TEXT', allow_nulls=allow_nulls)
