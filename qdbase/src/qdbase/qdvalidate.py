"""
Shared field validation for pdict Column definitions.

Used by qdrestful (API validation) and qdforms (form validation).
Validates values against Column constraints: length, range, pattern, choices.
"""

import re


def validate_field(value, col, is_update=False):
    """
    Validate a value against a pdict Column's constraints.

    Args:
        value: The value to validate (already type-coerced)
        col: A pdict Column instance
        is_update: If True, skip required-field checks

    Returns:
        List of error message strings (empty list = valid)
    """
    errors = []

    if value is None or (isinstance(value, str) and value.strip() == ''):
        if not is_update and col.is_create_required:
            errors.append(f"Field '{col.name}' is required")
        return errors

    if col.max_length is not None and isinstance(value, str):
        if len(value) > col.max_length:
            errors.append(
                f"Field '{col.name}' exceeds maximum length of {col.max_length}"
            )

    if col.min_length is not None and isinstance(value, str):
        if len(value) < col.min_length:
            errors.append(
                f"Field '{col.name}' must be at least {col.min_length} characters"
            )

    if col.max_value is not None and isinstance(value, (int, float)):
        if value > col.max_value:
            errors.append(
                f"Field '{col.name}' must be at most {col.max_value}"
            )

    if col.min_value is not None and isinstance(value, (int, float)):
        if value < col.min_value:
            errors.append(
                f"Field '{col.name}' must be at least {col.min_value}"
            )

    if col.pattern is not None and isinstance(value, str):
        if not re.search(col.pattern, value):
            errors.append(
                f"Field '{col.name}' does not match required pattern"
            )

    if col.choices is not None:
        valid_values = _get_choice_values(col.choices)
        if value not in valid_values:
            errors.append(
                f"Field '{col.name}' must be one of: {', '.join(str(v) for v in valid_values)}"
            )

    return errors


def validate_record(data, table_dict, is_update=False):
    """
    Validate all fields in a data dict against a table definition.

    Args:
        data: Dict of field_name -> value
        table_dict: pdict DbDictTable
        is_update: If True, skip required-field checks for missing fields

    Returns:
        Dict of field_name -> [error messages], only for fields with errors.
        Empty dict means all valid.
    """
    all_errors = {}

    for col_name, col in table_dict.columns.items():
        if col.is_primary_key:
            continue
        if col_name in data:
            field_errors = validate_field(data[col_name], col, is_update=is_update)
            if field_errors:
                all_errors[col_name] = field_errors
        elif not is_update and col.is_create_required:
            all_errors[col_name] = [f"Field '{col_name}' is required"]

    return all_errors


def _get_choice_values(choices):
    """
    Extract valid values from a choices list.

    Choices can be:
    - List of strings: ['active', 'inactive']
    - List of tuples: [('a', 'Active'), ('i', 'Inactive')]

    Returns:
        List of valid stored values
    """
    if not choices:
        return []
    if isinstance(choices[0], (list, tuple)):
        return [c[0] for c in choices]
    return list(choices)
