"""
Tests for qdbase.qdmariadb using a mocked mariadb module.

No MariaDB server or mariadb package is required.
"""

import sys
import types
from unittest import mock

import pytest

from qdbase import pdict


# ---- Create a mock mariadb module before importing qdmariadb ----


def _make_mock_mariadb():
    """Build a mock mariadb module with Error and IntegrityError."""
    mod = types.ModuleType("mariadb")
    mod.Error = type("Error", (Exception,), {})
    mod.IntegrityError = type(
        "IntegrityError", (mod.Error,), {}
    )
    mod.connect = mock.MagicMock()
    return mod


MOCK_MARIADB = _make_mock_mariadb()


@pytest.fixture(autouse=True)
def _patch_mariadb():
    """Inject mock mariadb into sys.modules for every test."""
    with mock.patch.dict(sys.modules, {"mariadb": MOCK_MARIADB}):
        # Reset the mock connect for each test
        MOCK_MARIADB.connect.reset_mock()
        yield


def _make_cursor():
    """Create a mock cursor with standard attributes."""
    cursor = mock.MagicMock()
    cursor.fetchall.return_value = []
    cursor.lastrowid = 0
    return cursor


def _make_conn(cursor):
    """Create a mock connection returning the given cursor."""
    conn = mock.MagicMock()
    conn.cursor.return_value = cursor
    MOCK_MARIADB.connect.return_value = conn
    return conn


def _make_db(cursor=None, db_dict=None, update_schema=False):
    """Create a QdMariaDB with mocked connection."""
    if cursor is None:
        cursor = _make_cursor()
    _make_conn(cursor)
    from qdbase.qdmariadb import QdMariaDB
    db = QdMariaDB(
        user="testuser",
        password="testpass",
        host="localhost",
        port=3306,
        database="testdb",
        db_dict=db_dict,
        update_schema=update_schema,
    )
    return db, cursor


# ---- Connection tests ----


def test_connect_params():
    """Verify mariadb.connect is called with correct params."""
    _db, _cursor = _make_db()
    MOCK_MARIADB.connect.assert_called_once_with(
        user="testuser",
        password="testpass",
        host="localhost",
        port=3306,
        database="testdb",
    )


def test_cursor_dictionary_mode():
    """Verify cursor is created with dictionary=True."""
    db, _cursor = _make_db()
    db.db_conn.cursor.assert_called_with(dictionary=True)


def test_db_module_is_mariadb():
    """db_module should be the mariadb module."""
    db, _cursor = _make_db()
    assert db.db_module is MOCK_MARIADB


def test_integrity_error_property():
    """IntegrityError property returns mariadb.IntegrityError."""
    db, _cursor = _make_db()
    assert db.IntegrityError is MOCK_MARIADB.IntegrityError


# ---- load_schema tests ----


def test_load_schema_empty():
    """Empty database produces empty schema."""
    db, _cursor = _make_db()
    assert db.db_schema == {}


def test_load_schema_with_tables():
    """load_schema populates db_schema from SHOW TABLES + SHOW CREATE TABLE."""
    cursor = _make_cursor()
    # First call: SHOW TABLES during __init__.load_schema
    # returns empty so __init__ finishes
    cursor.fetchall.return_value = []
    conn = _make_conn(cursor)

    from qdbase.qdmariadb import QdMariaDB
    db = QdMariaDB(
        user="u", password="p", database="testdb"
    )

    # Now set up cursor for a real load_schema call
    show_tables_result = [
        {"Tables_in_testdb": "users"},
        {"Tables_in_testdb": "posts"},
    ]
    create_users = (
        "CREATE TABLE `users` (\n"
        "  `id` int(11) NOT NULL AUTO_INCREMENT,\n"
        "  `name` varchar(255) DEFAULT NULL,\n"
        "  PRIMARY KEY (`id`)\n"
        ") ENGINE=InnoDB"
    )
    create_posts = (
        "CREATE TABLE `posts` (\n"
        "  `id` int(11) NOT NULL AUTO_INCREMENT,\n"
        "  `title` text,\n"
        "  PRIMARY KEY (`id`)\n"
        ") ENGINE=InnoDB"
    )
    cursor.fetchall.side_effect = [
        show_tables_result,
        [{"Table": "users", "Create Table": create_users}],
        [{"Table": "posts", "Create Table": create_posts}],
    ]
    db.load_schema()
    assert "users" in db.db_schema
    assert "posts" in db.db_schema
    assert "CREATE TABLE" in db.db_schema["users"]


# ---- CRUD operation tests ----


def test_select_simple():
    """select() generates correct SQL and params."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}]
    rows = db.select("users", "*", where={"name": "Alice"})
    call_args = cursor.execute.call_args_list[-1]
    sql = call_args[0][0]
    params = call_args[0][1]
    assert "SELECT * FROM users WHERE name=?" in sql
    assert params == ("Alice",)
    assert rows == [{"id": 1, "name": "Alice"}]


def test_select_no_where():
    """select() without where clause."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = []
    db.select("users", "*")
    call_args = cursor.execute.call_args_list[-1]
    sql = call_args[0][0]
    assert "SELECT * FROM users;" in sql


def test_select_with_limit_offset():
    """select() includes LIMIT and OFFSET."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = []
    db.select("users", "*", limit=10, offset=20)
    call_args = cursor.execute.call_args_list[-1]
    sql = call_args[0][0]
    assert "LIMIT 10" in sql
    assert "OFFSET 20" in sql


def test_insert():
    """insert() generates correct SQL and returns lastrowid."""
    db, cursor = _make_db()
    cursor.lastrowid = 42
    result = db.insert("users", {"name": "Bob", "age": 25})
    call_args = cursor.execute.call_args_list[-1]
    sql = call_args[0][0]
    assert "INSERT INTO users" in sql
    assert "name, age" in sql
    assert "?, ?" in sql
    assert result == 42


def test_update():
    """update() generates correct SQL."""
    db, cursor = _make_db()
    db.update("users", {"name": "Charlie"}, where={"id": 1})
    call_args = cursor.execute.call_args_list[-1]
    sql = call_args[0][0]
    params = call_args[0][1]
    assert "UPDATE users SET name=?" in sql
    assert "WHERE id=?" in sql
    assert params == ("Charlie", 1)


def test_delete():
    """delete() generates correct SQL."""
    db, cursor = _make_db()
    db.delete("users", where={"id": 1})
    call_args = cursor.execute.call_args_list[-1]
    sql = call_args[0][0]
    params = call_args[0][1]
    assert "DELETE FROM users WHERE id=?" in sql
    assert params == (1,)


def test_delete_no_where():
    """delete() without where deletes all rows."""
    db, cursor = _make_db()
    db.delete("users")
    call_args = cursor.execute.call_args_list[-1]
    sql = call_args[0][0]
    assert sql == "DELETE FROM users;"


# ---- Error handling tests ----


def test_execute_error_handling():
    """execute() catches db_module.Error and prints context."""
    db, cursor = _make_db()
    cursor.execute.side_effect = MOCK_MARIADB.Error("test error")
    with pytest.raises(MOCK_MARIADB.Error):
        db.execute("SELECT * FROM bad_table;")


def test_execute_error_with_values():
    """execute() prints values on error when detailed_exceptions=True."""
    db, cursor = _make_db()
    cursor.execute.side_effect = MOCK_MARIADB.Error("test error")
    with pytest.raises(MOCK_MARIADB.Error):
        db.execute("INSERT INTO t VALUES (?);", [42])


# ---- lookup / require tests ----


def test_lookup_found():
    """lookup() returns the row when exactly one match."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}]
    row = db.lookup("users", where={"id": 1})
    assert row == {"id": 1, "name": "Alice"}


def test_lookup_not_found():
    """lookup() returns None when no match."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = []
    row = db.lookup("users", where={"id": 999})
    assert row is None


def test_lookup_duplicate():
    """lookup() raises KeyError when multiple matches."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
    with pytest.raises(KeyError):
        db.lookup("users", where={"name": "dup"})


def test_require_found():
    """require() returns the row when exactly one match."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}]
    row = db.require("users", where={"id": 1})
    assert row == {"id": 1, "name": "Alice"}


def test_require_not_found():
    """require() raises KeyError when no match."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = []
    with pytest.raises(KeyError):
        db.require("users", where={"id": 999})


# ---- insert_unique tests ----


def test_insert_unique_no_duplicate():
    """insert_unique() inserts when no existing record matches."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = []
    cursor.lastrowid = 5
    db.insert_unique("users", {"name": "New"}, where={"name": "New"})
    # Should have called execute for both select and insert
    assert cursor.execute.call_count >= 2


def test_insert_unique_with_duplicate():
    """insert_unique() raises KeyError when duplicate exists."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = [{"id": 1, "name": "Existing"}]
    with pytest.raises(KeyError):
        db.insert_unique("users", {"name": "Existing"}, where={"name": "Existing"})


# ---- update_insert tests ----


def test_update_insert_existing():
    """update_insert() updates when a match exists."""
    db, cursor = _make_db()
    # First select returns one row, then update proceeds
    cursor.fetchall.return_value = [{"id": 1, "name": "Old"}]
    db.update_insert("users", {"name": "New"}, where={"id": 1})
    # Last execute call should be the UPDATE
    last_sql = cursor.execute.call_args_list[-1][0][0]
    assert "UPDATE" in last_sql


def test_update_insert_new():
    """update_insert() inserts when no match exists."""
    db, cursor = _make_db()
    cursor.fetchall.return_value = []
    cursor.lastrowid = 10
    db.update_insert("users", {"name": "New"}, where={"id": 99})
    last_sql = cursor.execute.call_args_list[-1][0][0]
    assert "INSERT" in last_sql


# ---- db_update_tables tests ----


def test_db_update_tables_creates_table():
    """db_update_tables creates tables from db_dict."""
    spec = pdict.DbDictDb()
    table = spec.add_table(pdict.DbDictTable("items"))
    table.add_column(pdict.Text("name"))

    cursor = _make_cursor()
    # load_schema returns empty (no tables)
    cursor.fetchall.return_value = []
    _make_conn(cursor)

    from qdbase.qdmariadb import QdMariaDB
    db = QdMariaDB(
        user="u", password="p", database="testdb",
        db_dict=spec, update_schema=True,
    )
    # The CREATE TABLE should have been executed
    create_calls = [
        c for c in cursor.execute.call_args_list
        if "CREATE TABLE" in str(c)
    ]
    assert len(create_calls) > 0


def test_db_update_tables_none_dict():
    """db_update_tables does nothing when db_dict is None."""
    db, cursor = _make_db(db_dict=None, update_schema=True)
    # Only the SHOW TABLES call from load_schema
    show_calls = [
        c for c in cursor.execute.call_args_list
        if "SHOW TABLES" in str(c)
    ]
    assert len(show_calls) >= 1


# ---- mariadb_to_pdict_table tests ----


def test_mariadb_to_pdict_table_basic():
    """Parse a basic MariaDB CREATE TABLE into pdict."""
    from qdbase.qdmariadb import mariadb_to_pdict_table

    sql = (
        "CREATE TABLE `users` (\n"
        "  `id` int(11) NOT NULL AUTO_INCREMENT,\n"
        "  `name` varchar(255) DEFAULT NULL,\n"
        "  `email` text,\n"
        "  PRIMARY KEY (`id`)\n"
        ") ENGINE=InnoDB"
    )
    t = mariadb_to_pdict_table(sql)
    assert t.name == "users"
    assert "id" in t.columns
    assert "name" in t.columns
    assert "email" in t.columns


def test_mariadb_to_pdict_table_unknown_type():
    """Unknown column type raises ValueError."""
    from qdbase.qdmariadb import mariadb_to_pdict_table

    sql = (
        "CREATE TABLE `bad` (\n"
        "  `data` blob\n"
        ")"
    )
    with pytest.raises(ValueError, match="Unknown MariaDB field type"):
        mariadb_to_pdict_table(sql)


# ---- close / commit tests ----


def test_close():
    """close() calls db_conn.close() and sets db_conn to None."""
    db, _cursor = _make_db()
    conn = db.db_conn
    db.close()
    conn.close.assert_called_once()
    assert db.db_conn is None


def test_commit():
    """commit() calls db_conn.commit()."""
    db, _cursor = _make_db()
    db.commit()
    db.db_conn.commit.assert_called()
