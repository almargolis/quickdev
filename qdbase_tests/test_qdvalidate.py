from qdbase import pdict
from qdbase.qdvalidate import validate_field, validate_record, _get_choice_values


# --- validate_field tests ---

def test_validate_field_no_constraints():
    """A column with no constraints accepts any non-null value."""
    col = pdict.Text("name")
    assert validate_field("hello", col) == []


def test_validate_field_max_length_pass():
    col = pdict.Text("name", max_length=10)
    assert validate_field("short", col) == []


def test_validate_field_max_length_fail():
    col = pdict.Text("name", max_length=5)
    errors = validate_field("too long value", col)
    assert len(errors) == 1
    assert "maximum length" in errors[0]


def test_validate_field_min_length_pass():
    col = pdict.Text("name", min_length=3)
    assert validate_field("abc", col) == []


def test_validate_field_min_length_fail():
    col = pdict.Text("name", min_length=3)
    errors = validate_field("ab", col)
    assert len(errors) == 1
    assert "at least 3 characters" in errors[0]


def test_validate_field_max_value_pass():
    col = pdict.Number("price", max_value=100)
    assert validate_field(50, col) == []


def test_validate_field_max_value_fail():
    col = pdict.Number("price", max_value=100)
    errors = validate_field(150, col)
    assert len(errors) == 1
    assert "at most 100" in errors[0]


def test_validate_field_min_value_pass():
    col = pdict.Number("quantity", min_value=0)
    assert validate_field(5, col) == []


def test_validate_field_min_value_fail():
    col = pdict.Number("quantity", min_value=0)
    errors = validate_field(-1, col)
    assert len(errors) == 1
    assert "at least 0" in errors[0]


def test_validate_field_pattern_pass():
    col = pdict.Text("code", pattern=r'^[A-Z]{3}$')
    assert validate_field("ABC", col) == []


def test_validate_field_pattern_fail():
    col = pdict.Text("code", pattern=r'^[A-Z]{3}$')
    errors = validate_field("abc", col)
    assert len(errors) == 1
    assert "pattern" in errors[0]


def test_validate_field_choices_string_list_pass():
    col = pdict.Text("status", choices=['active', 'inactive'])
    assert validate_field("active", col) == []


def test_validate_field_choices_string_list_fail():
    col = pdict.Text("status", choices=['active', 'inactive'])
    errors = validate_field("unknown", col)
    assert len(errors) == 1
    assert "must be one of" in errors[0]


def test_validate_field_choices_tuple_list_pass():
    col = pdict.Text("status", choices=[('a', 'Active'), ('i', 'Inactive')])
    assert validate_field("a", col) == []


def test_validate_field_choices_tuple_list_fail():
    col = pdict.Text("status", choices=[('a', 'Active'), ('i', 'Inactive')])
    errors = validate_field("Active", col)
    assert len(errors) == 1
    assert "must be one of" in errors[0]


def test_validate_field_required_empty_string():
    col = pdict.Text("name", is_create_required=True)
    errors = validate_field("", col)
    assert len(errors) == 1
    assert "required" in errors[0]


def test_validate_field_required_none():
    col = pdict.Text("name", is_create_required=True)
    errors = validate_field(None, col)
    assert len(errors) == 1
    assert "required" in errors[0]


def test_validate_field_required_skipped_on_update():
    col = pdict.Text("name", is_create_required=True)
    assert validate_field(None, col, is_update=True) == []


def test_validate_field_multiple_errors():
    col = pdict.Text("code", min_length=5, pattern=r'^[A-Z]+$')
    errors = validate_field("ab", col)
    assert len(errors) == 2


def test_validate_field_none_no_constraints():
    """None value with no required/allow_nulls constraints just returns empty."""
    col = pdict.Text("optional")
    assert validate_field(None, col) == []


# --- validate_record tests ---

def test_validate_record_valid():
    db = pdict.DbDictDb()
    t = db.add_table(pdict.DbDictTable("items"))
    t.add_column(pdict.Text("name", is_create_required=True, max_length=50))
    t.add_column(pdict.Number("quantity", min_value=0))

    errors = validate_record({"name": "Widget", "quantity": 5}, t)
    assert errors == {}


def test_validate_record_missing_required():
    db = pdict.DbDictDb()
    t = db.add_table(pdict.DbDictTable("items"))
    t.add_column(pdict.Text("name", is_create_required=True))

    errors = validate_record({"quantity": 5}, t)
    assert "name" in errors
    assert "required" in errors["name"][0]


def test_validate_record_missing_required_skipped_on_update():
    db = pdict.DbDictDb()
    t = db.add_table(pdict.DbDictTable("items"))
    t.add_column(pdict.Text("name", is_create_required=True))

    errors = validate_record({}, t, is_update=True)
    assert errors == {}


def test_validate_record_constraint_violation():
    db = pdict.DbDictDb()
    t = db.add_table(pdict.DbDictTable("items"))
    t.add_column(pdict.Text("name", max_length=5))
    t.add_column(pdict.Number("quantity", min_value=0))

    errors = validate_record({"name": "too long name", "quantity": -1}, t)
    assert "name" in errors
    assert "quantity" in errors


def test_validate_record_skips_primary_key():
    db = pdict.DbDictDb()
    t = db.add_table(pdict.DbDictTable("items"))
    t.add_column(pdict.Text("name"))

    errors = validate_record({"id": 1, "name": "test"}, t)
    assert "id" not in errors


# --- _get_choice_values tests ---

def test_get_choice_values_string_list():
    assert _get_choice_values(['a', 'b', 'c']) == ['a', 'b', 'c']


def test_get_choice_values_tuple_list():
    assert _get_choice_values([('a', 'Active'), ('i', 'Inactive')]) == ['a', 'i']


def test_get_choice_values_empty():
    assert _get_choice_values([]) == []
