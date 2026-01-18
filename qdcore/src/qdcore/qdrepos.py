"""
qdcore.qdrepos - Repository scanning and package discovery

Scans /repos/ directory to discover repositories, packages, and
qdo_* functions. Stores results in /conf/repos.db for quick lookup.
"""

import os
import ast
import sqlite3
import inspect
from pathlib import Path


# Database schema
SCHEMA = '''
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS packages (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    package TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL,
    dirname TEXT NOT NULL,
    isflask INTEGER DEFAULT 0,
    isflaskbp INTEGER DEFAULT 0,
    FOREIGN KEY (repo) REFERENCES repositories(name)
);

CREATE TABLE IF NOT EXISTS qdo (
    id INTEGER PRIMARY KEY,
    package TEXT NOT NULL,
    path TEXT NOT NULL,
    function_name TEXT NOT NULL,
    full_name TEXT UNIQUE NOT NULL,
    parameters TEXT,
    docstring TEXT,
    FOREIGN KEY (package) REFERENCES packages(package)
);

CREATE INDEX IF NOT EXISTS idx_qdo_function ON qdo(function_name);
'''


class RepoScanner:
    """
    Scans repositories for packages and qdo_* functions.
    """

    def __init__(self, site_root):
        """
        Initialize the repository scanner.

        Args:
            site_root: Path to the site root directory
        """
        self.site_root = Path(site_root)
        self.repos_path = self.site_root / 'repos'
        self.conf_path = self.site_root / 'conf'
        self.db_path = self.conf_path / 'repos.db'

    def scan_repos(self):
        """
        Scan all repositories and update the database.

        Creates/updates /conf/repos.db with information about:
        - Repositories found in /repos/
        - Packages within each repository
        - qdo_* functions found in packages

        Returns:
            dict with counts: repositories, packages, qdo_functions
        """
        # Ensure conf directory exists
        self.conf_path.mkdir(parents=True, exist_ok=True)

        # Create/connect to database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create schema
        cursor.executescript(SCHEMA)

        # Clear existing data for fresh scan
        cursor.execute('DELETE FROM qdo')
        cursor.execute('DELETE FROM packages')
        cursor.execute('DELETE FROM repositories')

        counts = {'repositories': 0, 'packages': 0, 'qdo_functions': 0}

        if not self.repos_path.exists():
            conn.commit()
            conn.close()
            return counts

        # Scan each repository
        for repo_dir in self.repos_path.iterdir():
            if not repo_dir.is_dir():
                continue
            if repo_dir.name.startswith('.'):
                continue

            # Add repository
            cursor.execute(
                'INSERT INTO repositories (name, path) VALUES (?, ?)',
                (repo_dir.name, str(repo_dir))
            )
            counts['repositories'] += 1

            # Scan for packages in this repository
            pkg_counts = self._scan_repository(cursor, repo_dir)
            counts['packages'] += pkg_counts['packages']
            counts['qdo_functions'] += pkg_counts['qdo_functions']

        conn.commit()
        conn.close()

        return counts

    def _scan_repository(self, cursor, repo_path):
        """
        Scan a single repository for packages.

        Args:
            cursor: Database cursor
            repo_path: Path to the repository

        Returns:
            dict with counts: packages, qdo_functions
        """
        counts = {'packages': 0, 'qdo_functions': 0}
        repo_name = repo_path.name

        # Look for packages - directories with __init__.py
        # Handles multiple layouts:
        # 1. repo/package/__init__.py (flat layout)
        # 2. repo/src/package/__init__.py (src layout at repo level)
        # 3. repo/pkgdir/src/package/__init__.py (src layout per package)

        for item in repo_path.iterdir():
            if not item.is_dir():
                continue
            if item.name.startswith('.') or item.name.startswith('_'):
                continue
            if item.name in ['tests', 'test', 'docs', 'build', 'dist']:
                continue
            if item.name.endswith('_tests'):
                continue

            # Check for flat layout: repo/package/__init__.py
            init_file = item / '__init__.py'
            if init_file.exists():
                self._add_package(cursor, repo_name, item.name, item, counts)
                continue

            # Check for src layout: repo/pkgdir/src/package/__init__.py
            src_pkg_path = item / 'src' / item.name
            if src_pkg_path.exists() and (src_pkg_path / '__init__.py').exists():
                self._add_package(cursor, repo_name, item.name, src_pkg_path, counts)
                continue

        # Also check repo/src/ for packages (less common)
        src_path = repo_path / 'src'
        if src_path.exists():
            for item in src_path.iterdir():
                if not item.is_dir():
                    continue
                if item.name.startswith('.') or item.name.startswith('_'):
                    continue
                init_file = item / '__init__.py'
                if init_file.exists():
                    self._add_package(cursor, repo_name, item.name, item, counts)

        return counts

    def _add_package(self, cursor, repo_name, package_name, package_path, counts):
        """
        Add a package to the database.

        Args:
            cursor: Database cursor
            repo_name: Name of the repository
            package_name: Name of the package
            package_path: Path to the package directory
            counts: Dict to update with counts
        """
        isflask, isflaskbp = self._detect_flask_package(package_path)

        cursor.execute(
            '''INSERT OR REPLACE INTO packages
               (repo, package, path, dirname, isflask, isflaskbp)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (repo_name, package_name, str(package_path), package_path.name,
             1 if isflask else 0, 1 if isflaskbp else 0)
        )
        counts['packages'] += 1

        # Scan for qdo_* functions
        qdo_count = self._scan_package_for_qdo(cursor, package_name, package_path)
        counts['qdo_functions'] += qdo_count

    def _detect_flask_package(self, package_path):
        """
        Detect if a package is a Flask app or blueprint.

        Args:
            package_path: Path to the package directory

        Returns:
            tuple: (isflask, isflaskbp)
        """
        isflask = False
        isflaskbp = False

        # Check __init__.py and common files for Flask indicators
        files_to_check = ['__init__.py', 'app.py', 'routes.py', 'views.py']

        for filename in files_to_check:
            filepath = package_path / filename
            if not filepath.exists():
                continue

            try:
                content = filepath.read_text()
                if 'Flask(' in content or 'flask.Flask' in content:
                    isflask = True
                if 'Blueprint(' in content or 'flask.Blueprint' in content:
                    isflaskbp = True
            except Exception:
                continue

        return isflask, isflaskbp

    def _scan_package_for_qdo(self, cursor, package_name, package_path):
        """
        Scan a package for qdo_* functions.

        Args:
            cursor: Database cursor
            package_name: Name of the package
            package_path: Path to the package directory

        Returns:
            Count of qdo functions found
        """
        count = 0

        # Scan all .py files in the package
        for py_file in package_path.rglob('*.py'):
            try:
                functions = self._extract_qdo_functions(py_file)
                for func_info in functions:
                    full_name = f"{package_name}.{func_info['name']}"
                    cursor.execute(
                        '''INSERT OR REPLACE INTO qdo
                           (package, path, function_name, full_name, parameters, docstring)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (package_name, str(py_file), func_info['name'],
                         full_name, func_info['parameters'], func_info['docstring'])
                    )
                    count += 1
            except Exception:
                # Skip files that can't be parsed
                continue

        return count

    def _extract_qdo_functions(self, filepath):
        """
        Extract qdo_* functions from a Python file using AST.

        Args:
            filepath: Path to the Python file

        Returns:
            List of dicts with function info
        """
        functions = []

        try:
            source = filepath.read_text()
            tree = ast.parse(source)
        except Exception:
            return functions

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('qdo_'):
                    func_info = {
                        'name': node.name,
                        'parameters': self._get_function_parameters(node),
                        'docstring': ast.get_docstring(node) or ''
                    }
                    functions.append(func_info)

        return functions

    def _get_function_parameters(self, func_node):
        """
        Extract parameter information from a function AST node.

        Args:
            func_node: AST FunctionDef node

        Returns:
            String describing the parameters
        """
        params = []
        args = func_node.args

        # Regular arguments
        for i, arg in enumerate(args.args):
            param_str = arg.arg
            # Check for default value
            default_index = i - (len(args.args) - len(args.defaults))
            if default_index >= 0 and default_index < len(args.defaults):
                default = args.defaults[default_index]
                try:
                    param_str += f"={ast.literal_eval(default)!r}"
                except Exception:
                    param_str += "=..."
            params.append(param_str)

        # *args
        if args.vararg:
            params.append(f"*{args.vararg.arg}")

        # **kwargs
        if args.kwarg:
            params.append(f"**{args.kwarg.arg}")

        return ', '.join(params)


def scan_repos(site_root):
    """
    Convenience function to scan repositories.

    Args:
        site_root: Path to the site root directory

    Returns:
        dict with counts: repositories, packages, qdo_functions
    """
    scanner = RepoScanner(site_root)
    return scanner.scan_repos()


def get_qdo_functions(site_root):
    """
    Get all qdo_* functions from the database.

    Args:
        site_root: Path to the site root directory

    Returns:
        List of dicts with function information
    """
    db_path = Path(site_root) / 'conf' / 'repos.db'
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT package, path, function_name, full_name, parameters, docstring
        FROM qdo ORDER BY function_name
    ''')

    functions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return functions


def get_qdo_function(site_root, function_name):
    """
    Get a specific qdo_* function by name.

    Args:
        site_root: Path to the site root directory
        function_name: Name of the function (with or without qdo_ prefix)

    Returns:
        Dict with function information, or None if not found
    """
    if not function_name.startswith('qdo_'):
        function_name = f'qdo_{function_name}'

    db_path = Path(site_root) / 'conf' / 'repos.db'
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT package, path, function_name, full_name, parameters, docstring
        FROM qdo WHERE function_name = ?
    ''', (function_name,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None
