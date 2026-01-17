#!/usr/bin/env python3
"""
Check qdflask user system configuration and database schema.

Usage:
    python -m qdflask.check_users           # Validate only
    python -m qdflask.check_users --test    # Validate and test
    python -m qdflask.check_users --fix     # Validate and fix issues
    python -m qdflask.check_users --conf /path/to/conf  # Specify conf directory

Checks:
    1. SECRET_KEY exists in conf/.env
    2. SECRET_KEY is strong (not default, 16+ chars)
    3. Database exists and is accessible
    4. User table schema matches expected columns
    5. At least one admin user exists
"""

import sys
import os
import sqlite3
from pathlib import Path
from typing import List, Set, Optional

# Handle imports for both installed and development modes
try:
    from qdbase.qdcheck import CheckRunner, CheckResult, CheckStatus, CheckMode
    from qdbase.qdconf import QdConf
except ModuleNotFoundError:
    # Development mode - add parent paths for QuickDev package structure
    # qdbase package is at quickdev/qdbase/qdbase/
    quickdev_path = os.path.join(os.path.dirname(__file__), '../../..')
    sys.path.insert(0, os.path.join(quickdev_path, 'qdbase'))
    from qdbase.qdcheck import CheckRunner, CheckResult, CheckStatus, CheckMode
    from qdbase.qdconf import QdConf


class UserSystemChecker(CheckRunner):
    """Check runner for qdflask user authentication system."""

    service_name = "qdflask"
    service_display_name = "Flask Authentication"
    config_filename = "qdflask.yaml"

    # Expected schema columns (from models.py)
    EXPECTED_COLUMNS = {
        'id', 'username', 'email_address', 'email_verified',
        'password_hash', 'role', 'created_at', 'last_login',
        'is_active', 'comment_style', 'moderation_level'
    }

    # Minimum required columns (older schema may lack newer fields)
    REQUIRED_COLUMNS = {
        'id', 'username', 'password_hash', 'role', 'is_active'
    }

    # Known weak/default secret keys to warn about
    WEAK_SECRET_KEYS = {
        'dev-secret-key', 'dev-secret-key-change-in-production',
        'changeme', 'secret', 'password', 'test', 'debug',
        'development', 'your-secret-key', 'change-me',
    }

    def __init__(self, conf_dir: str = None, mode: CheckMode = CheckMode.VALIDATE,
                 db_path: str = None):
        """
        Initialize user system checker.

        Args:
            conf_dir: Path to conf/ directory
            mode: Check mode (VALIDATE, TEST, CORRECT)
            db_path: Optional explicit database path
        """
        super().__init__(conf_dir=conf_dir, mode=mode)
        self._db_path = db_path

    def _run_checks(self):
        """Run all qdflask checks."""
        self._check_secret_key()
        self._check_database_access()
        self._check_user_schema()
        self._check_admin_exists()

        if self.mode == CheckMode.TEST:
            self._test_password_hashing()

    def _check_secret_key(self):
        """Check that SECRET_KEY exists in conf/.env and is strong."""
        secret_key = None

        # Try to get SECRET_KEY from conf/.env
        try:
            secret_key = self.conf.get('denv.SECRET_KEY')
        except (KeyError, FileNotFoundError, ValueError):
            pass

        # Also check environment variable
        if not secret_key:
            secret_key = os.environ.get('SECRET_KEY')

        if secret_key:
            # Check strength
            key_lower = secret_key.lower()

            if len(secret_key) < 16:
                self.add_result(CheckResult(
                    name="SECRET_KEY",
                    status=CheckStatus.WARNING,
                    message=f"SECRET_KEY is short ({len(secret_key)} chars)",
                    remediation="Generate a longer SECRET_KEY (32+ chars recommended)",
                    details={'length': len(secret_key)}
                ))
            elif key_lower in self.WEAK_SECRET_KEYS or 'secret' in key_lower:
                self.add_result(CheckResult(
                    name="SECRET_KEY",
                    status=CheckStatus.WARNING,
                    message="SECRET_KEY appears to be a default/weak value",
                    remediation="Generate a secure random SECRET_KEY: python -c \"import secrets; print(secrets.token_hex(32))\""
                ))
            else:
                self.add_result(CheckResult(
                    name="SECRET_KEY",
                    status=CheckStatus.PASS,
                    message=f"SECRET_KEY configured ({len(secret_key)} chars)",
                    details={'length': len(secret_key)}
                ))
        else:
            self._handle_missing_secret_key()

    def _handle_missing_secret_key(self):
        """Handle missing SECRET_KEY based on mode."""
        if self.mode == CheckMode.CORRECT:
            # Generate and suggest how to save
            import secrets
            new_key = secrets.token_hex(32)

            # Try to write to conf/.env
            env_path = self.conf.get_conf_dir() / '.env'
            try:
                # Append to existing .env or create new
                mode = 'a' if env_path.exists() else 'w'
                with open(env_path, mode) as f:
                    if mode == 'a':
                        f.write('\n')
                    f.write(f'SECRET_KEY={new_key}\n')

                self.add_result(CheckResult(
                    name="SECRET_KEY",
                    status=CheckStatus.CORRECTED,
                    message=f"Generated new SECRET_KEY in {env_path}",
                    details={'path': str(env_path), 'key_length': 64}
                ))
            except (IOError, OSError) as e:
                self.add_result(CheckResult(
                    name="SECRET_KEY",
                    status=CheckStatus.FAIL,
                    message=f"Could not write SECRET_KEY: {e}",
                    remediation=f"Add SECRET_KEY={new_key} to conf/.env manually"
                ))
        else:
            self.add_result(CheckResult(
                name="SECRET_KEY",
                status=CheckStatus.FAIL,
                message="SECRET_KEY not found in conf/.env or environment",
                remediation="Add SECRET_KEY=<random-string> to conf/.env"
            ))

    def _get_database_path(self) -> Optional[Path]:
        """Determine the database path."""
        if self._db_path:
            return Path(self._db_path)

        # Try DATABASE_URL from config
        try:
            db_url = self.conf.get('denv.DATABASE_URL')
            if db_url and db_url.startswith('sqlite:///'):
                return Path(db_url.replace('sqlite:///', ''))
        except (KeyError, FileNotFoundError, ValueError):
            pass

        # Check environment variable
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('sqlite:///'):
            return Path(db_url.replace('sqlite:///', ''))

        # Look for common database names in conf directory
        conf_dir = self.conf.get_conf_dir()
        parent_dir = conf_dir.parent if conf_dir else Path.cwd()

        for db_name in ['commercenode.db', 'app.db', 'users.db', 'flask.db']:
            # Check in common locations
            for search_dir in [parent_dir, parent_dir / 'cnflask', conf_dir]:
                if search_dir:
                    db_path = search_dir / db_name
                    if db_path.exists():
                        return db_path

        return None

    def _check_database_access(self):
        """Check database connectivity."""
        db_path = self._get_database_path()

        if not db_path:
            self.add_result(CheckResult(
                name="Database Access",
                status=CheckStatus.WARNING,
                message="No database file found",
                remediation="Set DATABASE_URL in conf/.env or create the database"
            ))
            return

        if not db_path.exists():
            if self.mode == CheckMode.CORRECT:
                self.add_result(CheckResult(
                    name="Database Access",
                    status=CheckStatus.WARNING,
                    message=f"Database not found: {db_path}",
                    remediation="Database will be created on first Flask app run"
                ))
            else:
                self.add_result(CheckResult(
                    name="Database Access",
                    status=CheckStatus.WARNING,
                    message=f"Database file not found: {db_path}",
                    remediation="Run the Flask app to create the database"
                ))
            return

        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("SELECT 1")
            conn.close()
            self.add_result(CheckResult(
                name="Database Access",
                status=CheckStatus.PASS,
                message=f"Database accessible: {db_path.name}",
                details={'path': str(db_path)}
            ))
        except sqlite3.Error as e:
            self.add_result(CheckResult(
                name="Database Access",
                status=CheckStatus.FAIL,
                message=f"Database connection failed: {e}",
                remediation="Check database file permissions and integrity",
                details={'path': str(db_path), 'error': str(e)}
            ))

    def _check_user_schema(self):
        """Verify User table has all expected columns."""
        db_path = self._get_database_path()

        if not db_path or not db_path.exists():
            self.add_result(CheckResult(
                name="User Schema",
                status=CheckStatus.SKIPPED,
                message="Database not available for schema check"
            ))
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()

            if not columns:
                self.add_result(CheckResult(
                    name="User Schema",
                    status=CheckStatus.WARNING,
                    message="Users table does not exist",
                    remediation="Run the Flask app to create database tables"
                ))
                return

            # Check for required columns
            missing_required = self.REQUIRED_COLUMNS - columns
            if missing_required:
                self.add_result(CheckResult(
                    name="User Schema",
                    status=CheckStatus.FAIL,
                    message=f"Missing required columns: {sorted(missing_required)}",
                    remediation="Database schema is incompatible - recreate or migrate"
                ))
                return

            # Check for expected columns (newer schema)
            missing_expected = self.EXPECTED_COLUMNS - columns
            if missing_expected:
                if self.mode == CheckMode.CORRECT:
                    # Attempt to add missing columns
                    added = self._add_missing_columns(db_path, missing_expected)
                    if added:
                        self.add_result(CheckResult(
                            name="User Schema",
                            status=CheckStatus.CORRECTED,
                            message=f"Added missing columns: {sorted(added)}",
                            details={'added': sorted(added)}
                        ))
                    else:
                        self.add_result(CheckResult(
                            name="User Schema",
                            status=CheckStatus.WARNING,
                            message=f"Could not add missing columns: {sorted(missing_expected)}",
                            remediation="Run migrations manually"
                        ))
                else:
                    self.add_result(CheckResult(
                        name="User Schema",
                        status=CheckStatus.WARNING,
                        message=f"Missing optional columns: {sorted(missing_expected)}",
                        remediation="Use --fix to add missing columns, or run migrations"
                    ))
            else:
                self.add_result(CheckResult(
                    name="User Schema",
                    status=CheckStatus.PASS,
                    message=f"All {len(self.EXPECTED_COLUMNS)} columns present",
                    details={'columns': sorted(columns)}
                ))

        except sqlite3.Error as e:
            self.add_result(CheckResult(
                name="User Schema",
                status=CheckStatus.FAIL,
                message=f"Schema check failed: {e}",
                details={'error': str(e)}
            ))

    def _add_missing_columns(self, db_path: Path, missing: Set[str]) -> Set[str]:
        """
        Add missing columns to the users table.

        Returns set of successfully added columns.
        """
        # Column definitions for migration
        column_defs = {
            'email_address': "VARCHAR(255)",
            'email_verified': "VARCHAR(1) DEFAULT 'N'",
            'comment_style': "VARCHAR(1) DEFAULT 't'",
            'moderation_level': "VARCHAR(1) DEFAULT '1'",
            'created_at': "DATETIME",
            'last_login': "DATETIME",
        }

        added = set()
        try:
            conn = sqlite3.connect(str(db_path))
            for col in missing:
                if col in column_defs:
                    try:
                        conn.execute(f"ALTER TABLE users ADD COLUMN {col} {column_defs[col]}")
                        added.add(col)
                    except sqlite3.Error:
                        pass  # Column might already exist or other issue
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

        return added

    def _check_admin_exists(self):
        """Verify at least one admin user exists."""
        db_path = self._get_database_path()

        if not db_path or not db_path.exists():
            self.add_result(CheckResult(
                name="Admin User",
                status=CheckStatus.SKIPPED,
                message="Database not available for admin check"
            ))
            return

        try:
            conn = sqlite3.connect(str(db_path))

            # Check if users table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            if not cursor.fetchone():
                conn.close()
                self.add_result(CheckResult(
                    name="Admin User",
                    status=CheckStatus.SKIPPED,
                    message="Users table does not exist yet"
                ))
                return

            # Count admin users
            cursor = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin'"
            )
            admin_count = cursor.fetchone()[0]
            conn.close()

            if admin_count == 0:
                self.add_result(CheckResult(
                    name="Admin User",
                    status=CheckStatus.WARNING,
                    message="No admin user exists",
                    remediation="Create admin: python -m qdflask.cli init-db --admin-password <password>"
                ))
            else:
                self.add_result(CheckResult(
                    name="Admin User",
                    status=CheckStatus.PASS,
                    message=f"{admin_count} admin user(s) configured"
                ))

        except sqlite3.Error as e:
            self.add_result(CheckResult(
                name="Admin User",
                status=CheckStatus.FAIL,
                message=f"Admin check failed: {e}",
                details={'error': str(e)}
            ))

    def _test_password_hashing(self):
        """Test password hashing functionality (mode=TEST only)."""
        try:
            from werkzeug.security import generate_password_hash, check_password_hash

            test_password = "test_password_123"
            hashed = generate_password_hash(test_password, method='pbkdf2:sha256')
            verified = check_password_hash(hashed, test_password)

            if verified:
                self.add_result(CheckResult(
                    name="Password Hashing",
                    status=CheckStatus.PASS,
                    message="Password hashing working correctly"
                ))
            else:
                self.add_result(CheckResult(
                    name="Password Hashing",
                    status=CheckStatus.FAIL,
                    message="Password verification failed",
                    remediation="Check Werkzeug installation"
                ))

        except ImportError:
            self.add_result(CheckResult(
                name="Password Hashing",
                status=CheckStatus.FAIL,
                message="Werkzeug not installed",
                remediation="pip install Werkzeug"
            ))
        except Exception as e:
            self.add_result(CheckResult(
                name="Password Hashing",
                status=CheckStatus.FAIL,
                message=f"Password hashing test failed: {e}"
            ))


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Check qdflask user system configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m qdflask.check_users              # Validate only
  python -m qdflask.check_users --test       # Validate + test functions
  python -m qdflask.check_users --fix        # Validate + auto-fix issues
  python -m qdflask.check_users --conf ./conf  # Specify config directory
"""
    )
    parser.add_argument('--test', action='store_true',
                        help='Run functional tests')
    parser.add_argument('--fix', action='store_true',
                        help='Fix issues if possible (e.g., generate SECRET_KEY)')
    parser.add_argument('--conf', metavar='DIR',
                        help='Path to conf directory')
    parser.add_argument('--db', metavar='PATH',
                        help='Path to database file')
    args = parser.parse_args()

    if args.fix:
        mode = CheckMode.CORRECT
    elif args.test:
        mode = CheckMode.TEST
    else:
        mode = CheckMode.VALIDATE

    checker = UserSystemChecker(conf_dir=args.conf, mode=mode, db_path=args.db)
    checker.run_all()
    checker.print_results()

    sys.exit(0 if checker.success else 1)


if __name__ == '__main__':
    main()
