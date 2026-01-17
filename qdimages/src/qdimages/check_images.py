#!/usr/bin/env python3
"""
Check qdimages image management configuration.

Usage:
    python -m qdimages.check_images           # Validate only
    python -m qdimages.check_images --test    # Validate and test
    python -m qdimages.check_images --fix     # Validate and fix issues
    python -m qdimages.check_images --conf /path/to/conf  # Specify conf directory

Checks:
    1. Storage directories exist and are writable
    2. Required Python packages (Pillow, xxhash)
    3. Optional packages (rembg for background removal)
    4. Database tables exist with correct schema
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


class ImageSystemChecker(CheckRunner):
    """Check runner for qdimages image management system."""

    service_name = "qdimages"
    service_display_name = "Image Management"
    config_filename = "qdimages.yaml"

    # Expected tables and their required columns
    EXPECTED_TABLES = {
        'images': {
            'id', 'xxhash', 'dir1', 'dir2', 'sequence_num', 'filename',
            'format', 'width', 'height', 'file_size', 'keywords',
            'created_at', 'updated_at'
        },
        'directory_sequence': {
            'id', 'dir1', 'dir2', 'next_sequence'
        },
        'image_exif': {
            'id', 'image_id', 'tag_name', 'tag_value'
        },
        'source_tracking': {
            'id', 'image_id', 'source_image_id', 'transformations'
        }
    }

    def __init__(self, conf_dir: str = None, mode: CheckMode = CheckMode.VALIDATE,
                 db_path: str = None):
        """
        Initialize image system checker.

        Args:
            conf_dir: Path to conf/ directory
            mode: Check mode (VALIDATE, TEST, CORRECT)
            db_path: Optional explicit database path
        """
        super().__init__(conf_dir=conf_dir, mode=mode)
        self._db_path = db_path

    def _run_checks(self):
        """Run all qdimages checks."""
        self._check_required_packages()
        self._check_optional_packages()
        self._check_storage_directories()
        self._check_database_tables()

        if self.mode == CheckMode.TEST:
            self._test_image_processing()

    def _check_required_packages(self):
        """Check that required Python packages are installed."""
        packages = {
            'PIL': 'Pillow',
            'xxhash': 'xxhash',
        }

        all_present = True
        missing = []

        for import_name, package_name in packages.items():
            try:
                __import__(import_name)
            except ImportError:
                all_present = False
                missing.append(package_name)

        if all_present:
            self.add_result(CheckResult(
                name="Required Packages",
                status=CheckStatus.PASS,
                message=f"All required packages installed ({', '.join(packages.values())})"
            ))
        else:
            self.add_result(CheckResult(
                name="Required Packages",
                status=CheckStatus.FAIL,
                message=f"Missing packages: {', '.join(missing)}",
                remediation=f"pip install {' '.join(missing)}"
            ))

    def _check_optional_packages(self):
        """Check optional packages for enhanced functionality."""
        import importlib.util

        # Check if rembg is installed without importing it
        # (importing rembg triggers onnxruntime warnings)
        rembg_spec = importlib.util.find_spec('rembg')

        if rembg_spec is not None:
            self.add_result(CheckResult(
                name="Background Removal",
                status=CheckStatus.PASS,
                message="rembg package available"
            ))
        else:
            self.add_result(CheckResult(
                name="Background Removal",
                status=CheckStatus.WARNING,
                message="rembg not installed (background removal disabled)",
                remediation="pip install rembg (optional)"
            ))

    def _get_storage_paths(self) -> dict:
        """Get storage paths from config or defaults."""
        conf_dir = self.conf.get_conf_dir()
        site_root = conf_dir.parent if conf_dir else Path.cwd()

        paths = {}

        # Try to get from config, fall back to defaults
        try:
            images_path = self.conf.get('qdimages.storage.images_base_path', './images')
        except (KeyError, FileNotFoundError, ValueError):
            images_path = './images'

        try:
            temp_images_path = self.conf.get('qdimages.storage.temp_images_path', './temp_images')
        except (KeyError, FileNotFoundError, ValueError):
            temp_images_path = './temp_images'

        try:
            temp_dir = self.conf.get('qdimages.storage.temp_directory', '/tmp/qdimages_temp')
        except (KeyError, FileNotFoundError, ValueError):
            temp_dir = '/tmp/qdimages_temp'

        # Resolve relative paths
        if not os.path.isabs(images_path):
            images_path = site_root / images_path
        else:
            images_path = Path(images_path)

        if not os.path.isabs(temp_images_path):
            temp_images_path = site_root / temp_images_path
        else:
            temp_images_path = Path(temp_images_path)

        paths['images'] = images_path
        paths['temp_images'] = temp_images_path
        paths['temp_directory'] = Path(temp_dir)

        return paths

    def _check_storage_directories(self):
        """Check that storage directories exist and are writable."""
        paths = self._get_storage_paths()

        for name, path in paths.items():
            if path.exists():
                # Check if writable
                if os.access(path, os.W_OK):
                    self.add_result(CheckResult(
                        name=f"Storage: {name}",
                        status=CheckStatus.PASS,
                        message=f"Directory exists and writable: {path}"
                    ))
                else:
                    self.add_result(CheckResult(
                        name=f"Storage: {name}",
                        status=CheckStatus.FAIL,
                        message=f"Directory not writable: {path}",
                        remediation=f"chmod u+w {path}"
                    ))
            else:
                if self.mode == CheckMode.CORRECT:
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        self.add_result(CheckResult(
                            name=f"Storage: {name}",
                            status=CheckStatus.CORRECTED,
                            message=f"Created directory: {path}"
                        ))
                    except OSError as e:
                        self.add_result(CheckResult(
                            name=f"Storage: {name}",
                            status=CheckStatus.FAIL,
                            message=f"Could not create directory: {e}",
                            remediation=f"mkdir -p {path}"
                        ))
                else:
                    self.add_result(CheckResult(
                        name=f"Storage: {name}",
                        status=CheckStatus.WARNING,
                        message=f"Directory does not exist: {path}",
                        remediation=f"mkdir -p {path} (or use --fix)"
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

        for db_name in ['commercenode.db', 'app.db', 'qdimages.db']:
            for search_dir in [parent_dir, parent_dir / 'cnflask', conf_dir]:
                if search_dir:
                    db_path = search_dir / db_name
                    if db_path.exists():
                        return db_path

        return None

    def _check_database_tables(self):
        """Check that database tables exist with correct schema."""
        db_path = self._get_database_path()

        if not db_path:
            self.add_result(CheckResult(
                name="Database Tables",
                status=CheckStatus.WARNING,
                message="No database found",
                remediation="Database will be created on first Flask app run"
            ))
            return

        if not db_path.exists():
            self.add_result(CheckResult(
                name="Database Tables",
                status=CheckStatus.WARNING,
                message=f"Database file not found: {db_path}",
                remediation="Database will be created on first Flask app run"
            ))
            return

        try:
            conn = sqlite3.connect(str(db_path))

            # Check each expected table
            tables_found = 0
            tables_missing = []

            for table_name, expected_columns in self.EXPECTED_TABLES.items():
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                if cursor.fetchone():
                    # Table exists, check columns
                    cursor = conn.execute(f"PRAGMA table_info({table_name})")
                    actual_columns = {row[1] for row in cursor.fetchall()}

                    missing_cols = expected_columns - actual_columns
                    if missing_cols:
                        self.add_result(CheckResult(
                            name=f"Table: {table_name}",
                            status=CheckStatus.WARNING,
                            message=f"Missing columns: {sorted(missing_cols)}",
                            remediation="Run database migrations"
                        ))
                    else:
                        tables_found += 1
                else:
                    tables_missing.append(table_name)

            conn.close()

            if tables_missing:
                self.add_result(CheckResult(
                    name="Database Tables",
                    status=CheckStatus.WARNING,
                    message=f"Missing tables: {tables_missing}",
                    remediation="Run Flask app to create tables via db.create_all()"
                ))
            elif tables_found == len(self.EXPECTED_TABLES):
                self.add_result(CheckResult(
                    name="Database Tables",
                    status=CheckStatus.PASS,
                    message=f"All {tables_found} tables present with correct schema"
                ))

        except sqlite3.Error as e:
            self.add_result(CheckResult(
                name="Database Tables",
                status=CheckStatus.FAIL,
                message=f"Database error: {e}",
                details={'error': str(e)}
            ))

    def _test_image_processing(self):
        """Test image processing functionality (mode=TEST only)."""
        try:
            from PIL import Image
            import xxhash
            import io

            # Create a small test image
            img = Image.new('RGB', (100, 100), color='red')

            # Test saving to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_bytes = buffer.getvalue()

            # Test xxhash
            hash_value = xxhash.xxh64(img_bytes).hexdigest()

            if len(hash_value) == 16:
                self.add_result(CheckResult(
                    name="Image Processing",
                    status=CheckStatus.PASS,
                    message="Image creation and hashing working correctly"
                ))
            else:
                self.add_result(CheckResult(
                    name="Image Processing",
                    status=CheckStatus.FAIL,
                    message="xxhash produced unexpected output"
                ))

        except Exception as e:
            self.add_result(CheckResult(
                name="Image Processing",
                status=CheckStatus.FAIL,
                message=f"Image processing test failed: {e}"
            ))


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Check qdimages image management configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m qdimages.check_images              # Validate only
  python -m qdimages.check_images --test       # Validate + test functions
  python -m qdimages.check_images --fix        # Validate + auto-fix issues
  python -m qdimages.check_images --conf ./conf  # Specify config directory
"""
    )
    parser.add_argument('--test', action='store_true',
                        help='Run functional tests')
    parser.add_argument('--fix', action='store_true',
                        help='Fix issues if possible (e.g., create directories)')
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

    checker = ImageSystemChecker(conf_dir=args.conf, mode=mode, db_path=args.db)
    checker.run_all()
    checker.print_results()

    sys.exit(0 if checker.success else 1)


if __name__ == '__main__':
    main()
