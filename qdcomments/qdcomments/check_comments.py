#!/usr/bin/env python3
"""
Check qdcomments commenting system configuration.

Usage:
    python -m qdcomments.check_comments           # Validate only
    python -m qdcomments.check_comments --test    # Validate and test
    python -m qdcomments.check_comments --fix     # Validate and fix issues
    python -m qdcomments.check_comments --conf /path/to/conf  # Specify conf directory

Checks:
    1. qdflask dependency available (User model)
    2. User table has comment_style and moderation_level columns
    3. Comments table exists with correct schema
    4. blocked_words.yaml exists and is valid YAML
"""

import sys
import os
import sqlite3
from pathlib import Path
from typing import Set, Optional

# Handle imports for both installed and development modes
try:
    from qdbase.qdcheck import CheckRunner, CheckResult, CheckStatus, CheckMode
    from qdbase.qdconf import QdConf
except ModuleNotFoundError:
    # Development mode - add parent paths for QuickDev package structure
    quickdev_path = os.path.join(os.path.dirname(__file__), '../../..')
    sys.path.insert(0, os.path.join(quickdev_path, 'qdbase'))
    from qdbase.qdcheck import CheckRunner, CheckResult, CheckStatus, CheckMode
    from qdbase.qdconf import QdConf


class CommentSystemChecker(CheckRunner):
    """Check runner for qdcomments commenting system."""

    service_name = "qdcomments"
    service_display_name = "Comment System"
    config_filename = "qdcomments.toml"

    # Expected columns in comments table
    EXPECTED_COMMENT_COLUMNS = {
        'id', 'user_id', 'content_type', 'content_id', 'content',
        'user_comment_style', 'user_moderation_level',
        'status', 'status_reason', 'parent_id',
        'created_at', 'updated_at', 'moderated_at', 'moderated_by_id'
    }

    # Required columns in users table for comments
    REQUIRED_USER_COLUMNS = {
        'comment_style', 'moderation_level'
    }

    def __init__(self, conf_dir: str = None, mode: CheckMode = CheckMode.VALIDATE,
                 db_path: str = None):
        """
        Initialize comment system checker.

        Args:
            conf_dir: Path to conf/ directory
            mode: Check mode (VALIDATE, TEST, CORRECT)
            db_path: Optional explicit database path
        """
        super().__init__(conf_dir=conf_dir, mode=mode)
        self._db_path = db_path

    def _run_checks(self):
        """Run all qdcomments checks."""
        self._check_qdflask_dependency()
        self._check_user_columns()
        self._check_comments_table()
        self._check_blocked_words()

        if self.mode == CheckMode.TEST:
            self._test_comment_creation()

    def _check_qdflask_dependency(self):
        """Check that qdflask is available (required dependency)."""
        try:
            from qdflask.models import db, User
            self.add_result(CheckResult(
                name="qdflask Dependency",
                status=CheckStatus.PASS,
                message="qdflask models available (User, db)"
            ))
        except ImportError as e:
            self.add_result(CheckResult(
                name="qdflask Dependency",
                status=CheckStatus.FAIL,
                message=f"qdflask not available: {e}",
                remediation="qdcomments requires qdflask - install with: pip install -e ./qdflask"
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

        # Look for common database names
        conf_dir = self.conf.get_conf_dir()
        parent_dir = conf_dir.parent if conf_dir else Path.cwd()

        for db_name in ['commercenode.db', 'app.db', 'comments.db']:
            for search_dir in [parent_dir, parent_dir / 'cnflask', conf_dir]:
                if search_dir:
                    db_path = search_dir / db_name
                    if db_path.exists():
                        return db_path

        return None

    def _check_user_columns(self):
        """Check that users table has comment-related columns."""
        db_path = self._get_database_path()

        if not db_path or not db_path.exists():
            self.add_result(CheckResult(
                name="User Columns",
                status=CheckStatus.SKIPPED,
                message="Database not available for schema check"
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
                    name="User Columns",
                    status=CheckStatus.WARNING,
                    message="Users table does not exist",
                    remediation="Initialize qdflask first with init_auth()"
                ))
                return

            # Get actual columns
            cursor = conn.execute("PRAGMA table_info(users)")
            actual_columns = {row[1] for row in cursor.fetchall()}
            conn.close()

            missing = self.REQUIRED_USER_COLUMNS - actual_columns
            if missing:
                if self.mode == CheckMode.CORRECT:
                    added = self._add_user_columns(db_path, missing)
                    if added:
                        self.add_result(CheckResult(
                            name="User Columns",
                            status=CheckStatus.CORRECTED,
                            message=f"Added missing columns to users: {sorted(added)}"
                        ))
                    else:
                        self.add_result(CheckResult(
                            name="User Columns",
                            status=CheckStatus.FAIL,
                            message=f"Could not add columns: {sorted(missing)}",
                            remediation="Run qdflask.check_users --fix"
                        ))
                else:
                    self.add_result(CheckResult(
                        name="User Columns",
                        status=CheckStatus.WARNING,
                        message=f"Users table missing columns: {sorted(missing)}",
                        remediation="Run qdflask.check_users --fix or use --fix here"
                    ))
            else:
                self.add_result(CheckResult(
                    name="User Columns",
                    status=CheckStatus.PASS,
                    message="Users table has comment_style and moderation_level"
                ))

        except sqlite3.Error as e:
            self.add_result(CheckResult(
                name="User Columns",
                status=CheckStatus.FAIL,
                message=f"Database error: {e}",
                details={'error': str(e)}
            ))

    def _add_user_columns(self, db_path: Path, missing: Set[str]) -> Set[str]:
        """Add missing columns to the users table."""
        column_defs = {
            'comment_style': "VARCHAR(1) DEFAULT 't'",
            'moderation_level': "VARCHAR(1) DEFAULT '1'",
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
                        pass
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

        return added

    def _check_comments_table(self):
        """Check that comments table exists with correct schema."""
        db_path = self._get_database_path()

        if not db_path or not db_path.exists():
            self.add_result(CheckResult(
                name="Comments Table",
                status=CheckStatus.WARNING,
                message="Database not available",
                remediation="Database will be created on first Flask app run"
            ))
            return

        try:
            conn = sqlite3.connect(str(db_path))

            # Check if comments table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
            )
            if not cursor.fetchone():
                conn.close()
                self.add_result(CheckResult(
                    name="Comments Table",
                    status=CheckStatus.WARNING,
                    message="Comments table does not exist",
                    remediation="Run Flask app to create tables via db.create_all()"
                ))
                return

            # Get actual columns
            cursor = conn.execute("PRAGMA table_info(comments)")
            actual_columns = {row[1] for row in cursor.fetchall()}
            conn.close()

            missing = self.EXPECTED_COMMENT_COLUMNS - actual_columns
            if missing:
                self.add_result(CheckResult(
                    name="Comments Table",
                    status=CheckStatus.WARNING,
                    message=f"Missing columns: {sorted(missing)}",
                    remediation="Run database migrations or recreate tables"
                ))
            else:
                self.add_result(CheckResult(
                    name="Comments Table",
                    status=CheckStatus.PASS,
                    message=f"All {len(self.EXPECTED_COMMENT_COLUMNS)} columns present"
                ))

        except sqlite3.Error as e:
            self.add_result(CheckResult(
                name="Comments Table",
                status=CheckStatus.FAIL,
                message=f"Database error: {e}",
                details={'error': str(e)}
            ))

    def _get_blocked_words_path(self) -> Path:
        """Get path to blocked_words.yaml file."""
        # Try to get from config
        try:
            path = self.conf.get('qdcomments.moderation.blocked_words_path',
                                 './blocked_words.yaml')
        except (KeyError, FileNotFoundError, ValueError):
            path = './blocked_words.yaml'

        conf_dir = self.conf.get_conf_dir()

        if not os.path.isabs(path):
            # Relative to conf directory
            return conf_dir / path if conf_dir else Path.cwd() / path
        return Path(path)

    def _check_blocked_words(self):
        """Check that blocked_words.yaml exists and is valid."""
        blocked_words_path = self._get_blocked_words_path()

        if blocked_words_path.exists():
            try:
                import yaml
                with open(blocked_words_path) as f:
                    data = yaml.safe_load(f)

                if data is None:
                    self.add_result(CheckResult(
                        name="Blocked Words",
                        status=CheckStatus.WARNING,
                        message=f"Empty file: {blocked_words_path}",
                        remediation="Add 'words:' key with list of blocked words"
                    ))
                elif not isinstance(data, dict):
                    self.add_result(CheckResult(
                        name="Blocked Words",
                        status=CheckStatus.WARNING,
                        message="Invalid format: expected YAML dictionary",
                        remediation="File should start with 'words:' key"
                    ))
                elif 'words' not in data:
                    self.add_result(CheckResult(
                        name="Blocked Words",
                        status=CheckStatus.WARNING,
                        message="Missing 'words' key in blocked_words.yaml",
                        remediation="Add 'words:' key with list of blocked words"
                    ))
                else:
                    words = data.get('words')
                    word_count = len(words) if words else 0
                    self.add_result(CheckResult(
                        name="Blocked Words",
                        status=CheckStatus.PASS,
                        message=f"Valid YAML with {word_count} blocked words"
                    ))

            except yaml.YAMLError as e:
                self.add_result(CheckResult(
                    name="Blocked Words",
                    status=CheckStatus.FAIL,
                    message=f"Invalid YAML syntax: {e}",
                    remediation="Fix YAML syntax errors in blocked_words.yaml"
                ))
            except Exception as e:
                self.add_result(CheckResult(
                    name="Blocked Words",
                    status=CheckStatus.FAIL,
                    message=f"Error reading file: {e}"
                ))
        else:
            if self.mode == CheckMode.CORRECT:
                try:
                    # Create default blocked_words.yaml
                    blocked_words_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(blocked_words_path, 'w') as f:
                        f.write("""# Blocked words for comment moderation
# Comments containing these words will be held for moderation

words:
  # Add blocked words here, one per line
  # - spam
  # - inappropriate

# Configuration
case_sensitive: false
whole_word_only: true
""")
                    self.add_result(CheckResult(
                        name="Blocked Words",
                        status=CheckStatus.CORRECTED,
                        message=f"Created template: {blocked_words_path}"
                    ))
                except OSError as e:
                    self.add_result(CheckResult(
                        name="Blocked Words",
                        status=CheckStatus.FAIL,
                        message=f"Could not create file: {e}",
                        remediation=f"Manually create {blocked_words_path}"
                    ))
            else:
                self.add_result(CheckResult(
                    name="Blocked Words",
                    status=CheckStatus.WARNING,
                    message=f"File not found: {blocked_words_path}",
                    remediation="Create blocked_words.yaml or use --fix"
                ))

    def _test_comment_creation(self):
        """Test comment model instantiation (mode=TEST only)."""
        try:
            # Try to import the Comment model
            from qdcomments.models import Comment

            # Verify it has expected attributes
            expected_attrs = ['user_id', 'content_type', 'content_id', 'content',
                              'status', 'get_for_content', 'get_pending_moderation']
            missing = [attr for attr in expected_attrs
                       if not hasattr(Comment, attr)]

            if missing:
                self.add_result(CheckResult(
                    name="Comment Model",
                    status=CheckStatus.FAIL,
                    message=f"Comment model missing attributes: {missing}"
                ))
            else:
                self.add_result(CheckResult(
                    name="Comment Model",
                    status=CheckStatus.PASS,
                    message="Comment model has expected attributes and methods"
                ))

        except ImportError as e:
            self.add_result(CheckResult(
                name="Comment Model",
                status=CheckStatus.FAIL,
                message=f"Could not import Comment model: {e}",
                remediation="Check qdflask dependency and PYTHONPATH"
            ))
        except Exception as e:
            self.add_result(CheckResult(
                name="Comment Model",
                status=CheckStatus.FAIL,
                message=f"Comment model test failed: {e}"
            ))


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Check qdcomments commenting system configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m qdcomments.check_comments              # Validate only
  python -m qdcomments.check_comments --test       # Validate + test model
  python -m qdcomments.check_comments --fix        # Validate + auto-fix issues
  python -m qdcomments.check_comments --conf ./conf  # Specify config directory
"""
    )
    parser.add_argument('--test', action='store_true',
                        help='Run functional tests')
    parser.add_argument('--fix', action='store_true',
                        help='Fix issues if possible')
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

    checker = CommentSystemChecker(conf_dir=args.conf, mode=mode, db_path=args.db)
    checker.run_all()
    checker.print_results()

    sys.exit(0 if checker.success else 1)


if __name__ == '__main__':
    main()
