"""
qdcore.qdrepos - Repository scanning and package discovery

Scans /repos/ directory to discover repositories, packages, and
qdo_* functions. Stores results in /conf/repos.db for quick lookup.
"""

import os
import ast
import sqlite3
import inspect
import yaml
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

CREATE TABLE IF NOT EXISTS conf_answers (
    id INTEGER PRIMARY KEY,
    yaml_path TEXT NOT NULL,
    conf_key TEXT NOT NULL,
    conf_value TEXT,
    UNIQUE(yaml_path, conf_key)
);

CREATE TABLE IF NOT EXISTS conf_questions (
    id INTEGER PRIMARY KEY,
    yaml_path TEXT NOT NULL,
    conf_key TEXT NOT NULL,
    help TEXT,
    type TEXT,
    UNIQUE(yaml_path, conf_key)
);

CREATE INDEX IF NOT EXISTS idx_qdo_function ON qdo(function_name);
CREATE INDEX IF NOT EXISTS idx_conf_answers_key ON conf_answers(conf_key);
CREATE INDEX IF NOT EXISTS idx_conf_questions_key ON conf_questions(conf_key);
'''

class ConfQuestions:
    def __init__(self, conf_type, conf_key, conf_help, yaml_path=None):
        self.conf_type = conf_type
        self.conf_key = conf_key
        self.conf_help = conf_help
        self.yaml_path = yaml_path

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
        cursor.execute('DELETE FROM conf_answers')
        cursor.execute('DELETE FROM conf_questions')

        counts = {
            'repositories': 0,
            'packages': 0,
            'qdo_functions': 0,
            'conf_answers': 0,
            'conf_questions': 0
        }

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
            counts['conf_answers'] += pkg_counts['conf_answers']
            counts['conf_questions'] += pkg_counts['conf_questions']

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
            dict with counts: packages, qdo_functions, conf_answers, conf_questions
        """
        counts = {'packages': 0, 'qdo_functions': 0, 'conf_answers': 0, 'conf_questions': 0}
        repo_name = repo_path.name

        # Walk directory tree and find any directory with __init__.py
        for dirpath, dirnames, filenames in os.walk(repo_path):
            # Skip hidden directories and common non-package directories
            dirnames[:] = [d for d in dirnames
                          if not d.startswith('.')
                          and not d.startswith('_')
                          and d not in ('build', 'dist', 'node_modules', '.git')]

            dir_path = Path(dirpath)

            if '__init__.py' in filenames:
                package_name = dir_path.name
                self._add_package(cursor, repo_name, package_name, dir_path, counts)

            # Check for conf yaml files
            if 'qd_conf_answers.yaml' in filenames:
                yaml_path = dir_path / 'qd_conf_answers.yaml'
                counts['conf_answers'] += self._scan_conf_answers(cursor, yaml_path)

            if 'qd_conf_questions.yaml' in filenames:
                yaml_path = dir_path / 'qd_conf_questions.yaml'
                counts['conf_questions'] += self._scan_conf_questions(cursor, yaml_path)

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

    def _scan_conf_answers(self, cursor, yaml_path):
        """
        Scan a qd_conf_answers.yaml file and insert into conf_answers table.

        Args:
            cursor: Database cursor
            yaml_path: Path to the YAML file

        Returns:
            Count of entries added
        """
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception:
            return 0

        if not data or not isinstance(data, dict):
            return 0

        count = 0
        yaml_path_str = str(yaml_path)

        def traverse(obj, key_parts):
            nonlocal count
            if isinstance(obj, dict):
                for k, v in obj.items():
                    traverse(v, key_parts + [k])
            else:
                # Leaf value - insert into database
                conf_key = '.'.join(key_parts)
                conf_value = str(obj) if obj is not None else ''
                cursor.execute(
                    '''INSERT OR REPLACE INTO conf_answers
                       (yaml_path, conf_key, conf_value)
                       VALUES (?, ?, ?)''',
                    (yaml_path_str, conf_key, conf_value)
                )
                count += 1

        traverse(data, [])
        return count

    def _scan_conf_questions(self, cursor, yaml_path):
        """
        Scan a qd_conf_questions.yaml file and insert into conf_questions table.

        Args:
            cursor: Database cursor
            yaml_path: Path to the YAML file

        Returns:
            Count of entries added
        """
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception:
            return 0

        if not data or not isinstance(data, dict):
            return 0

        count = 0
        yaml_path_str = str(yaml_path)

        def is_question_leaf(obj):
            """Check if this dict is a question definition (has help or type)."""
            if not isinstance(obj, dict):
                return False
            return 'help' in obj or 'type' in obj

        def traverse(obj, key_parts):
            nonlocal count
            if is_question_leaf(obj):
                # This is a question definition
                conf_key = '.'.join(key_parts)
                help_text = obj.get('help', '')
                type_text = obj.get('type', '')
                cursor.execute(
                    '''INSERT OR REPLACE INTO conf_questions
                       (yaml_path, conf_key, help, type)
                       VALUES (?, ?, ?, ?)''',
                    (yaml_path_str, conf_key, help_text, type_text)
                )
                count += 1
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    traverse(v, key_parts + [k])

        traverse(data, [])
        return count


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
