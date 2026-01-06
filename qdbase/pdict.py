"""
DbDictDb is a simple dictionary for QuickDev.

This is used by XSynth in stand-alone mode, so it can't
use XSynth features.

"""

import numbers


class DbDictDb:
    """
    Database dictionary primarily for use with qdsqlite.
    """

    __slots__ = ("tables",)

    def __init__(self):
        self.tables = {}

    def add_table(self, table_dict):
        """Add a table to the dictionary."""
        if table_dict.name in self.tables:
            raise Exception(f"Duplicate table {table_dict.name}")
        table_dict.db_dict = self
        self.tables[table_dict.name] = table_dict
        return table_dict
    
    def copy(self):
        d = DbDictDb()
        for this_property_name in DbDictDb.__slots__:
            if this_property_name == 'tables':
                for this_table in self.tables.values():
                    d.add_table(this_table.copy(d))
            else:
                setattr(d, this_property_name, getattr(self, this_property_name))
        return d

    def sql_create_list(self):
        """Create a list of sql create statements to create a database."""
        create_list = []
        for this in self.tables.values():
            create_list.append(this.sql())
            for this_index in this.indexes.values():
                create_list.append(this_index.sql())
        return create_list


class DbDictTable:
    """
    DbDictTable is a dictionary primarily intended to define
    sqlite3 tables. The default table design is a
    rowid table with an alias column of id. When needed,
    alternate keys are implemented as indexes.
    """

    __slots__ = ("columns", "db_dict", "indexes", "is_rowid_table", "name")

    def __init__(self, name, db_dict=None, is_rowid_table=True):
        self.columns = {}
        self.db_dict = db_dict # commonly supplied by DbDictDb.add_table()
        self.indexes = {}
        self.name = name
        self.is_rowid_table = is_rowid_table
        if self.is_rowid_table:
            id_col = self.add_column(Number("id"))
            id_col.is_primary_key = True

    def copy(self, db_copy):
        """
        db_dict is set from the start for copy() because it is needed
        to create Column.foreign_key.
        """
        t = DbDictTable(self.name, db_dict=db_copy, is_rowid_table=False)
        for this_property_name in DbDictTable.__slots__:
            if this_property_name == 'name':
                pass
            elif this_property_name == 'columns':
                for this_column in self.columns.values():
                    t.add_column(this_column.copy(t))
            elif this_property_name == 'indexes':
                for this_index in self.indexes.values():
                    t.add_index(this_index.copy(t))
            else:
                setattr(t, this_property_name, getattr(self, this_property_name))
        return t

    def add_column(self, column):
        """Add a column to the table."""
        if column.name in self.columns:
            raise Exception(
                f"Duplicate column name '{column.name}' in table '{self.name}'"
            )
        column.table_dict = self
        self.columns[column.name] = column
        return column

    def add_index(self, name, index=None, column_names=None, is_unique=True):
        """
        Add an index to the table.
        One of the arguments index or column_names is required. This maintains
        compatability with the copy() methods while also providing a convenient
        idion for in-place index creation.
        """
        if name in self.indexes:
            raise Exception(f"Duplicate index name '{name}' in table '{self.name}'")
        if index is None:
            index = Index(name, column_names, self, is_unique=is_unique)
        self.indexes[name] = index
        return index

    def defaults(self, all_columns=False):
        """
        Return a dictionary of a row initialized with default values.
        """
        result_dict = {}
        for this in self.columns.values():
            if all_columns or (this.default_value is not None):
                result_dict[this.name] = this.default_value
        return result_dict

    def sql(self, eol="\n"):
        """Create an sql create table command for this table."""
        table_def = f"CREATE TABLE {self.name} ("
        for ix, this in enumerate(self.columns.values()):
            table_def += f"{',' if ix>0 else ''}{eol}{this.sql()}"
        for this_col in self.columns.values():
            if this_col.foreign_key is None:
                continue
            table_def += f",{eol}{this_col.sql_foreign()}"
        table_def += f"{eol});{eol}"
        return table_def


class ForeignKey:
    """
    ForeignKey is a reference to a column in another table.
    key is a Column object.
    This is a placeholder in case more info about foreign keys bercomes needed.
    """
    __slots__ = ("key",)

    def __init__(self, key):
        self.key = key


class TupleDict(DbDictTable):
    """
    TupleDict is a minor variation of DbDictTable that is used
    to define simple data structure outside the context of an
    RDBMS.
    """

    def __init__(self, name=None):
        super().__init__(name, is_rowid_table=False)


class Index:  # pylint: disable=too-few-public-methods
    """
    Represents an index for a table.
    """

    __slots__ = ("name", "column_names", "is_unique", "table_dict")

    def __init__(self, name, column_names, table_dict, is_unique=True):
        """
        column_names can be either a single column name or a list of
        column names.
        """
        self.name = name
        self.column_names = []
        self.table_dict = table_dict
        if not isinstance(column_names, (list, tuple)):
            column_names = (column_names,)
        for this_column_name in column_names:
            if this_column_name not in table_dict.columns:
                raise Exception(
                    f"Invalid index column '{this_column_name}' for index {table_dict.name}.{self.name}"
                )
            self.column_names.append(this_column_name)
        self.is_unique = is_unique

    def copy(self, table_copy):
        i = Index(self.name, self.column_names, table_copy, is_unique=self.is_unique)
        for this_property_name in Index.__slots__:
            if this_property_name in ['name', 'column_names', 'is_unique', 'table_dict']:
                pass
            else:
                setattr(i, this_property_name, getattr(self, this_property_name))
        return i

    def sql(self, eol="\n"):
        """Create sql CREATE INDEX statement string."""
        index_def = "CREATE"
        if self.is_unique:
            index_def += " UNIQUE"
        index_def += " INDEX " + self.name + eol
        index_def += "ON " + self.table_dict.name + "("
        last_column_ix = len(self.columns) - 1
        for ix, this in enumerate(self.columns):
            index_def += this
            if (last_column_ix > 0) and (ix < last_column_ix):
                index_def += ", "
        index_def += ");" + eol
        return index_def


"""
column_type must be a valid sqlite3 data type affinity
https://sqlite.org/datatype3.html
TEXT, NUMERIC, INTEGER, REAL, BLOB
"""

SQLITE_DATA_TYPES = ["TEXT", "NULL", "INTEGER", "REAL", "BLOB", "TIMESTAMP"]
# Boolean is INTEGER 0=FALSE, 1=TRUE
# Date and Time Datatype

# SQLite does not have a storage class set aside for storing dates and/or times.
# Built-in Date And Time Functions of SQLite are capable of storing
# dates and times as TEXT, REAL, or INTEGER values:

# TEXT as ISO8601 strings ("YYYY-MM-DD HH:MM:SS.SSS").
# REAL as Julian day numbers, the number of days since
#   noon in Greenwich on November 24, 4714 B.C.
#   according to the proleptic Gregorian calendar.
# INTEGER as Unix Time, the number of seconds since 1970-01-01 00:00:00 UTC.
# Applications can choose to store dates and times in any of these formats
# and freely convert between formats using the built-in date and time functions.

SQLITE_COLLATE_TYPES = ["BINARY", "NOCASE", "RTRIM"]


class ColumnName:
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name


class Column:  # pylint: disable=too-few-public-methods
    """Base class for table columns."""

    __slots__ = (
        "allow_nulls",
        "column_type",
        "collate",
        "default_value",
        "foreign_key",
        "is_primary_key",
        "is_read_only",
        "is_unique",
        "name",
        "table_dict",
    )

    def __init__(self, name, **argv):  # pylint: disable=R0913
        self.name = name
        self.column_type = argv.get("column_type", "TEXT")
        if self.column_type not in SQLITE_DATA_TYPES:
            raise ValueError(f"Invalid column_TYPE {self.column_type} for {name}")
        collate = argv.get("colate", None)
        if (self.column_type == "TEXT") and (collate is None):
            collate = "NOCASE"
        self.collate = collate
        self.allow_nulls = argv.get("allow_nulls", False)
        self.default_value = argv.get("default_value", None)
        self.foreign_key = argv.get("foreign_key", None)
        self.is_primary_key = argv.get("is_primary_key", False)
        self.is_read_only = argv.get("is_read_only", False)
        self.is_unique = argv.get("is_unique", False)
        self.table_dict = argv.get("table_dict", None)

    def copy(self, table_copy):
        c = self.__class__(self.name)
        for this_property_name in Column.__slots__:
            if this_property_name == 'name':
                pass
            elif this_property_name == 'foreign_key':
                if self.foreign_key is None:
                    c.foreign_key = None
                else:
                    foreign_table_name = table_copy.db_dict.tables[self.foreign_key.key.table_dict.name]
                    foreign_column_name = table_copy.db_dict.tables[self.foreign_key.key.name]
                    foreign_table_obj = table_copy.db_dict.tables[foreign_table_name]
                    key = foreign_table_obj.columns[foreign_column_name]
                    c.foreign_key = ForeignKey(key)
            elif this_property_name == 'table_dict':
                c.table_dict = table_copy
            else:
                setattr(c, this_property_name, getattr(self, this_property_name))
        return c

    def sql(self):
        """Create sql column definition clause."""
        col_def = self.name + " " + self.column_type
        if self.is_unique:
            col_def += " UNIQUE"
        if not self.allow_nulls:
            col_def += " NOT NULL"
        if self.is_primary_key:
            col_def += " PRIMARY KEY"
        if self.default_value is not None:
            col_def += " DEFAULT "
            if isinstance(self.default_value, numbers.Number):
                col_def += str(self.default_value)
            elif isinstance(self.default_value, ColumnName):
                col_def += self.default_value.name
            else:
                col_def += "'" + self.default_value + "'"
        if self.collate is not None:
            col_def += f" COLLATE {self.collate}"
        return col_def

    def sql_foreign(self):
        if self.foreign_key is None:
            return ""
        else:
            return f"FOREIGN KEY ({self.name}) REFERENCES {self.foreign_key.key.table_dict.name} ({self.foreign_key.key.name})"


class Number(Column):  # pylint: disable=too-few-public-methods
    """Numeric column class."""

    __slots__ = ()

    def __init__(self, name, **argv):
        # sqlite recognize int as an alias for INTEGER but
        # not for the aliasing of rowid.
        argv["column_type"] = "INTEGER"
        super().__init__(name, **argv)


class Text(Column):  # pylint: disable=too-few-public-methods
    """Text column class."""

    __slots__ = ()

    def __init__(self, name, **argv):
        argv["column_type"] = "TEXT"
        super().__init__(
            name,
            **argv,
        )



class TimeStamp(Column):  # pylint: disable=too-few-public-methods
    """
    TimeStamp column class.

    Added because of Flask example.
    Enabled with sqlite3.register_converter() in qdsqlite.
    """

    __slots__ = ()

    def __init__(self, name, **argv):
        argv["column_type"] = "TIMESTAMP"
        super().__init__(
            name,
            **argv,
        )
