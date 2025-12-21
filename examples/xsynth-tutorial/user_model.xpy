#!/usr/bin/env python
"""
XSynth Tutorial: Generating a User Model

This .xpy file demonstrates how XSynth eliminates repetitive code.
We define field names once, and XSynth generates all the boilerplate.
"""

#$define FIELDS username, email, created_at, last_login
#$define TABLE_NAME users
#$define CLASS_NAME User

class $CLASS_NAME$:
    """User model with auto-generated fields and methods."""

    table_name = '$TABLE_NAME$'

    def __init__(self, $FIELDS$):
        """Initialize with all fields."""
        self.username = username
        self.email = email
        self.created_at = created_at
        self.last_login = last_login

    def to_dict(self):
        """Convert to dictionary - no need to list each field manually."""
        return {
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at,
            'last_login': self.last_login,
        }

    def __repr__(self):
        return f"$CLASS_NAME$(username={self.username!r}, email={self.email!r})"


def create_table_sql():
    """Generate SQL - field names defined once above."""
    return """
    CREATE TABLE $TABLE_NAME$ (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        last_login TEXT
    );
    """


# The power of XSynth:
# - Change field names in ONE place (the #$define)
# - XSynth regenerates __init__, to_dict(), SQL, etc.
# - No copy-paste errors
# - No forgetting to update one method when adding a field
