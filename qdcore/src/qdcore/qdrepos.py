"""
qdcore.qdrepos - Repository scanning and package discovery

Scans /repos/ directory to discover repositories, packages, and
qdo_* functions. Stores results in /conf/repos.db for quick lookup.

Supports both persistent and in-memory database modes for bootstrapping.
"""

import json
import os
import ast
import re
import sqlite3
import tomllib
from pathlib import Path

from qdbase import exenv 


# Database schema
SCHEMA = '''
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL,
    editable INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS packages (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    package TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL,
    dirname TEXT NOT NULL,
    isflask INTEGER DEFAULT 0,
    isflaskbp INTEGER DEFAULT 0,
    has_setup INTEGER DEFAULT 0,
    setup_path TEXT,
    enabled INTEGER DEFAULT 1,
    editable INTEGER DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS flask_init (
    id INTEGER PRIMARY KEY,
    package TEXT NOT NULL,
    module TEXT NOT NULL,
    function TEXT NOT NULL,
    priority INTEGER DEFAULT 50,
    params_json TEXT,
    yaml_path TEXT NOT NULL,
    FOREIGN KEY (package) REFERENCES packages(package),
    UNIQUE(package, module, function)
);

CREATE INDEX IF NOT EXISTS idx_qdo_function ON qdo(function_name);
CREATE INDEX IF NOT EXISTS idx_flask_init_priority ON flask_init(priority);
'''

CONF_TYPE_BASENAME = 'basename'
CONF_TYPE_BOOLEAN = 'boolean'
CONF_TYPE_DIRECTORY_PATH = 'dpath'
CONF_TYPE_FILE_PATH = 'fpath'
CONF_TYPE_RANDOM_FILL = 'random_fill'
CONF_TYPE_STRING = 'string'
VALID_CONF_TYPES = [CONF_TYPE_BASENAME, CONF_TYPE_BOOLEAN,
                    CONF_TYPE_DIRECTORY_PATH, CONF_TYPE_FILE_PATH,
                    CONF_TYPE_RANDOM_FILL, CONF_TYPE_STRING]


class ConfQuestion:
    __slots__ = ('conf_type', 'conf_key', 'conf_help', 'yaml_path')

    def __init__(self, conf_type, conf_key, conf_help, yaml_path=''):
        self.conf_type = conf_type
        self.conf_key = conf_key
        self.conf_help = conf_help
        self.yaml_path = yaml_path

    @classmethod
    def from_row(cls, row):
        """Create from sqlite3.Row."""
        return cls(row['conf_type'], row['conf_key'],
                   row['conf_help'], row['yaml_path'])

    @classmethod
    def from_toml(cls, conf_key, question_dict, yaml_path=''):
        """Create from a qd_conf.toml question dict."""
        conf_type = question_dict.get('conf_type', CONF_TYPE_STRING)
        conf_help = question_dict.get('help', '')
        return cls(conf_type, conf_key, conf_help, yaml_path)

    @property
    def is_boolean(self):
        return self.conf_type == CONF_TYPE_BOOLEAN

    @property
    def is_directory(self):
        return self.conf_type == CONF_TYPE_DIRECTORY_PATH

    @property
    def is_random_fill(self):
        return self.conf_type == CONF_TYPE_RANDOM_FILL

    @property
    def is_enabled_question(self):
        return self.conf_key.endswith('.enabled')

    @property
    def package_prefix(self):
        """'qdflask' from 'qdflask.enabled' or 'qdflask.roles'."""
        return self.conf_key.rsplit('.', 1)[0]

    @staticmethod
    def create_table(cursor):
        """Create conf_questions table + index."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conf_questions (
                id INTEGER PRIMARY KEY,
                yaml_path TEXT NOT NULL,
                conf_key TEXT UNIQUE NOT NULL,
                conf_help TEXT,
                conf_type TEXT
            )
        ''')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_conf_questions_key '
            'ON conf_questions(conf_key)'
        )

    def select_by_key(self, cursor):
        cursor.execute(
            'SELECT conf_key FROM conf_questions WHERE conf_key = ?',
            (self.conf_key,)
        )

    def insert(self, cursor):
        cursor.execute(
            '''INSERT INTO conf_questions
               (yaml_path, conf_key, conf_help, conf_type)
               VALUES (?, ?, ?, ?)''',
            (self.yaml_path, self.conf_key, self.conf_help, self.conf_type)
        )

    def build_prompt(self):
        """Build user prompt string from conf_help and conf_key."""
        if self.conf_help:
            return f"{self.conf_help}\n{self.conf_key}: "
        return f"{self.conf_key}: "


# Answer source types for resolve()
SOURCE_CONSTANT = "constant"      # From qd_conf.toml answers section
SOURCE_CONFIGURED = "configured"  # From existing conf/*.toml
SOURCE_PROMPT = "prompt"          # Will need to prompt user

_REF_PATTERN = re.compile(r'<([a-zA-Z_][a-zA-Z0-9_.]+)>')


def expand_answer_refs(value, answer_cache, conf=None):
    """
    Expand <conf_key> references in an answer value.

    Symbolic references like "<trellis.content_dpath>/users.db" are
    expanded by looking up the referenced conf_key in answer_cache
    first, then conf. Unresolvable references are left as-is.

    Args:
        value: The answer string potentially containing <conf_key> refs
        answer_cache: Dict of pre-supplied answers from qd_conf.toml
        conf: QdConf instance for checking existing config, or None

    Returns:
        String with references expanded where possible
    """
    if not isinstance(value, str) or '<' not in value:
        return value

    def replacer(match):
        ref_key = match.group(1)
        if ref_key in answer_cache:
            return str(answer_cache[ref_key])
        if conf:
            try:
                return str(conf[ref_key])
            except (KeyError, ValueError):
                pass
        return match.group(0)

    return _REF_PATTERN.sub(replacer, value)


def has_unresolved_refs(value):
    """Return True if the string still contains <conf_key> references."""
    return isinstance(value, str) and bool(_REF_PATTERN.search(value))


class ConfAnswer:
    __slots__ = ('conf_key', 'conf_value', 'yaml_path', 'source')

    def __init__(self, conf_key, conf_value, yaml_path='', source=''):
        self.conf_key = conf_key
        self.conf_value = conf_value
        self.yaml_path = yaml_path
        self.source = source

    @classmethod
    def from_row(cls, row):
        """Create from sqlite3.Row."""
        return cls(row['conf_key'], row['conf_value'], row['yaml_path'])

    @classmethod
    def resolve(cls, question, answer_cache, conf=None):
        """
        Resolve a ConfQuestion to a ConfAnswer.

        Checks sources in priority order:
        1. answer_cache -> SOURCE_CONSTANT
        2. conf -> SOURCE_CONFIGURED
        3. Not found -> SOURCE_PROMPT (conf_value is None)

        Args:
            question: ConfQuestion object
            answer_cache: Dict of pre-supplied answers from qd_conf.toml
            conf: QdConf instance for checking existing config, or None

        Returns:
            ConfAnswer with conf_value and source set
        """
        conf_key = question.conf_key

        if conf_key in answer_cache:
            return cls(conf_key, answer_cache[conf_key],
                       source=SOURCE_CONSTANT)

        if conf:
            try:
                existing = conf[conf_key]
                return cls(conf_key, existing, source=SOURCE_CONFIGURED)
            except KeyError:
                pass

        return cls(conf_key, None, source=SOURCE_PROMPT)

    @staticmethod
    def create_table(cursor):
        """Create conf_answers table + index."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conf_answers (
                id INTEGER PRIMARY KEY,
                yaml_path TEXT NOT NULL,
                conf_key TEXT UNIQUE NOT NULL,
                conf_value TEXT
            )
        ''')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_conf_answers_key '
            'ON conf_answers(conf_key)'
        )

    def select_by_key(self, cursor):
        cursor.execute(
            'SELECT conf_key FROM conf_answers WHERE conf_key = ?',
            (self.conf_key,)
        )

    def insert(self, cursor):
        cursor.execute(
            '''INSERT OR IGNORE INTO conf_answers
               (yaml_path, conf_key, conf_value)
               VALUES (?, ?, ?)''',
            (self.yaml_path, self.conf_key, self.db_value)
        )

    def update_value(self, cursor):
        """Update conf_value in database."""
        cursor.execute(
            '''UPDATE conf_answers SET conf_value = ?
               WHERE conf_key = ?''',
            (self.db_value, self.conf_key)
        )

    def expand_refs(self, answer_cache, conf=None):
        """Expand <conf_key> references in conf_value, in place."""
        self.conf_value = expand_answer_refs(
            self.conf_value, answer_cache, conf
        )

    @property
    def has_unresolved_refs(self):
        return has_unresolved_refs(self.conf_value)

    @property
    def is_disabled(self):
        """Check if this answer represents a disabled/no value."""
        if self.conf_value is None:
            return False
        if isinstance(self.conf_value, bool):
            return not self.conf_value
        if isinstance(self.conf_value, str):
            return self.conf_value.lower() in ('false', 'no', '0', 'n')
        return False

    @property
    def db_value(self):
        """conf_value as string for database storage."""
        return str(self.conf_value) if self.conf_value is not None else ''


EDITABLE_PREFIX = 'e::'


class RepoSpec:
    """Parsed repository specification with optional editable flag."""
    __slots__ = ("path", "editable")

    def __init__(self, path, editable=False):
        self.path = path
        self.editable = editable

    @classmethod
    def parse(cls, entry):
        if isinstance(entry, cls):
            return entry
        entry = str(entry)
        if entry.startswith(EDITABLE_PREFIX):
            return cls(path=entry[len(EDITABLE_PREFIX):], editable=True)
        return cls(path=entry, editable=False)

    def __repr__(self):
        prefix = EDITABLE_PREFIX if self.editable else ''
        return f"RepoSpec('{prefix}{self.path}')"


class RepoScanner:
    """
    Scans repositories for packages and qdo_* functions.

    Supports both persistent database (file-based) and in-memory database
    for bootstrapping scenarios where the conf directory doesn't exist yet.
    """

    def __init__(self, site_root, in_memory=False, no_db=False):
        """
        Initialize the repository scanner.

        Args:
            site_root: Path to the site root directory
            in_memory: If True, use in-memory database (for bootstrapping)
        """
        self.answer_cache = {}
        self.site_root = Path(site_root)
        self.repos_path = self.site_root / 'repos'
        self.conf_path = self.site_root / 'conf'
        self.db_path = self.conf_path / 'repos.db'
        self.in_memory = in_memory
        self._conn = None
        self.connect(in_memory=self.in_memory, no_db=no_db)

    def connect(self, in_memory=False, no_db=False):
        """Get or create database connection."""
        if self._conn is not None:
            return self._conn
        self.in_memory = in_memory
        self.no_db = no_db
        if self.no_db:
            self._conn = None
            return self._conn
        if self.in_memory:
            self._conn = sqlite3.connect(':memory:')
        else:
            self.conf_path.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
        cursor = self._conn.cursor()
        cursor.executescript(SCHEMA)
        ConfQuestion.create_table(cursor)
        ConfAnswer.create_table(cursor)
        self._conn.commit()

        # Migrate older databases that lack the editable column
        try:
            cursor.execute(
                'ALTER TABLE repositories ADD COLUMN editable INTEGER DEFAULT 0'
            )
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute(
                'ALTER TABLE packages ADD COLUMN editable INTEGER DEFAULT 0'
            )
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute(
                'ALTER TABLE packages ADD COLUMN setup_path TEXT'
            )
        except sqlite3.OperationalError:
            pass
        self._conn.commit()

        # Add default site questions if they don't exist
        self._add_default_questions(cursor)
        return self._conn

    def _add_default_questions(self, cursor):
        """Add default site configuration questions if they don't exist."""
        default_questions = [
            ConfQuestion(CONF_TYPE_BASENAME, exenv.CONF_SITE_PREFIX,
                         "A very short acronym for this site."),
            ConfQuestion(CONF_TYPE_DIRECTORY_PATH, exenv.CONF_SITE_DPATH,
                         "Path to site root directory.")
        ]

        for this_question in default_questions:
            this_question.select_by_key(cursor)
            if cursor.fetchone() is None:
                this_question.insert(cursor)
        self._conn.commit()

    def backup_to_file(self, db_path=None):
        """
        Backup in-memory database to file.

        Only meaningful when in_memory=True.

        Args:
            db_path: Optional path for database file. Defaults to conf/repos.db

        Returns:
            Path to the saved database file
        """
        if not self.in_memory or self._conn is None:
            return None

        if db_path is None:
            self.conf_path.mkdir(parents=True, exist_ok=True)
            db_path = self.db_path

        # Use SQLite backup API
        file_conn = sqlite3.connect(str(db_path))
        self._conn.backup(file_conn)
        file_conn.close()

        return db_path

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def load_answer_files(self, answer_file_list):
        """
        Load answers from TOML files before scanning directories.

        First answer found wins - subsequent answers for same key are ignored.

        Args:
            answer_file_list: List of paths to TOML files containing answers

        Returns:
            Count of answers loaded
        """
        if not answer_file_list:
            return 0

        if self._conn is None:
            cursor = None
        else:
            cursor = self._conn.cursor()
        count = 0

        for toml_path in answer_file_list:
            toml_path = Path(toml_path)
            if not toml_path.exists():
                raise FileNotFoundError(
                    f"Answer file not found: {toml_path}")
            count += self._load_answers_from_toml(cursor, toml_path)

        if self._conn is not None:
            self._conn.commit()
        return count

    def update_answer(self, answer_key, answer_value):
        """Update an existing answer in both cache and database."""
        answer = ConfAnswer(answer_key, answer_value)
        self.answer_cache[answer_key] = answer.db_value
        if self._conn is not None:
            cursor = self._conn.cursor()
            answer.update_value(cursor)
            self._conn.commit()

    def post_answer(self, answer_key, answer_value, cursor, yaml_path_str):
        if answer_key in self.answer_cache:
            return 0
        answer = ConfAnswer(answer_key, answer_value, yaml_path=yaml_path_str)
        self.answer_cache[answer_key] = answer.db_value
        if cursor is None:
            return 1
        answer.insert(cursor)
        return 1

    def _load_answers_from_toml(self, cursor, toml_path):
        """
        Load answers from a single TOML file.

        Supports both flat format (key = value) and nested format.
        First answer found wins.

        Args:
            cursor: Database cursor
            toml_path: Path to TOML file

        Returns:
            Count of answers loaded
        """
        with open(toml_path, 'rb') as f:
            try:
                data = tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                error_msg = str(e)
                msg = f"TOML syntax error in {toml_path}"
                # Extract line number from message like "(at line 5, column 1)"
                match = re.search(r'at line (\d+)', error_msg)
                if match:
                    line_num = int(match.group(1))
                    msg += f", line {line_num}"
                    try:
                        with open(toml_path, 'r') as tf:
                            lines = tf.readlines()
                            if 0 < line_num <= len(lines):
                                msg += f":\n  {lines[line_num - 1].rstrip()}"
                    except (OSError, UnicodeDecodeError):
                        pass
                msg += f"\n{error_msg}"
                raise ValueError(msg) from e

        if not data or not isinstance(data, dict):
            return 0

        count = 0
        toml_path_str = str(toml_path)

        def traverse(obj, key_parts):
            nonlocal count
            if isinstance(obj, dict):
                # Check if this is a leaf or container
                has_nested = any(isinstance(v, dict) for v in obj.values())
                if has_nested:
                    for k, v in obj.items():
                        traverse(v, key_parts + [k])
                else:
                    # All values are leaves
                    for k, v in obj.items():
                        conf_key = '.'.join(key_parts + [k])
                        count += self.post_answer(conf_key, v, cursor, toml_path_str)
            else:
                # Leaf value
                conf_key = '.'.join(key_parts)
                count += self.post_answer(conf_key, obj, cursor, toml_path_str)

        traverse(data, [])
        return count

    def scan_directories(self, dir_list=None):
        """
        Scan a list of directories for repositories/packages.

        Scans directories in dir_list first, then /repos/ if it exists.

        Args:
            dir_list: Optional list of directories to scan before /repos/

        Returns:
            dict with counts: repositories, packages, qdo_functions, etc.
        """
        cursor = self._conn.cursor()

        counts = {
            'repositories': 0,
            'packages': 0,
            'qdo_functions': 0,
            'conf_answers': 0,
            'conf_questions': 0,
            'installable_packages': []
        }

        # Scan directories from dir_list first
        if dir_list:
            for entry in dir_list:
                repo_spec = RepoSpec.parse(entry)
                dir_path = Path(repo_spec.path)
                if not dir_path.exists() or not dir_path.is_dir():
                    continue
                self._scan_single_directory(
                    cursor, dir_path, counts,
                    editable=repo_spec.editable
                )

        # Then scan /repos/ if it exists (always non-editable)
        if self.repos_path.exists():
            for repo_dir in sorted(self.repos_path.iterdir()):
                if not repo_dir.is_dir():
                    continue
                if repo_dir.name.startswith('.'):
                    continue
                self._scan_single_directory(cursor, repo_dir, counts)

        self._conn.commit()
        return counts

    def _scan_single_directory(self, cursor, dir_path, counts, editable=False):
        """
        Scan a single directory (may be a repo or a package).

        Args:
            cursor: Database cursor
            dir_path: Path to directory
            counts: Dict to update with counts
            editable: If True, packages are installed in editable mode
        """
        dir_name = dir_path.name
        editable_int = 1 if editable else 0

        # Check if already registered as repository
        cursor.execute('SELECT name FROM repositories WHERE name = ?', (dir_name,))
        if cursor.fetchone() is None:
            cursor.execute(
                'INSERT INTO repositories (name, path, editable) VALUES (?, ?, ?)',
                (dir_name, str(dir_path), editable_int)
            )
            counts['repositories'] += 1

        # Scan for packages and config files
        pkg_counts = self._scan_repository(cursor, dir_path, editable=editable)
        counts['packages'] += pkg_counts['packages']
        counts['qdo_functions'] += pkg_counts['qdo_functions']
        counts['conf_answers'] += pkg_counts['conf_answers']
        counts['conf_questions'] += pkg_counts['conf_questions']
        counts['installable_packages'].extend(pkg_counts.get('installable_packages', []))

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
        return self.scan_directories()

    def _scan_repository(self, cursor, repo_path, editable=False):
        """
        Scan a single repository for packages.

        Args:
            cursor: Database cursor
            repo_path: Path to the repository
            editable: If True, packages are installed in editable mode

        Returns:
            dict with counts: packages, qdo_functions, conf_answers, conf_questions
        """
        counts = {
            'packages': 0,
            'qdo_functions': 0,
            'conf_answers': 0,
            'conf_questions': 0,
            'installable_packages': []
        }
        repo_name = repo_path.name

        # Walk directory tree and find any directory with __init__.py
        for dirpath, dirnames, filenames in os.walk(repo_path):
            # Skip hidden directories and common non-package directories
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith('.')
                and not d.startswith('_')
                and d not in ('build', 'dist', 'node_modules', '.git')
                and not (Path(dirpath) / d / 'pyvenv.cfg').exists()
            ]

            dir_path = Path(dirpath)

            if '__init__.py' in filenames:
                package_name = dir_path.name
                setup_path = self._add_package(
                    cursor, repo_name, package_name, dir_path, counts,
                    editable=editable
                )
                if setup_path:
                    counts['installable_packages'].append({
                        'name': package_name,
                        'path': str(setup_path),
                        'repo': repo_name,
                        'editable': 1 if editable else 0
                    })

            # Check for qd_conf.toml
            if 'qd_conf.toml' in filenames:
                toml_path = dir_path / 'qd_conf.toml'
                qa_counts = self._scan_qd_conf_toml(cursor, toml_path)
                counts['conf_answers'] += qa_counts['answers']
                counts['conf_questions'] += qa_counts['questions']

        return counts

    def _scan_qd_conf_toml(self, cursor, toml_path):
        """
        Scan a qd_conf.toml file with "questions" and "answers" sections.

        Args:
            cursor: Database cursor
            toml_path: Path to the TOML file

        Returns:
            dict with counts: answers, questions
        """
        counts = {'answers': 0, 'questions': 0}

        try:
            with open(toml_path, 'rb') as f:
                data = tomllib.load(f)
        except Exception:
            return counts

        if not data or not isinstance(data, dict):
            return counts

        # Process "answers" section if present
        if 'answers' in data and isinstance(data['answers'], dict):
            counts['answers'] = self._process_answers_section(
                cursor, data['answers'], str(toml_path)
            )

        # Process "questions" section if present
        if 'questions' in data and isinstance(data['questions'], dict):
            counts['questions'] = self._process_questions_section(
                cursor, data['questions'], str(toml_path)
            )

        # Process "flask" section if present
        if 'flask' in data and isinstance(data['flask'], dict):
            package_name = Path(toml_path).parent.name
            flask_counts = self._process_flask_section(
                cursor, data['flask'], package_name, str(toml_path)
            )
            counts['flask_init'] = flask_counts.get('init_functions', 0)

        return counts

    def _process_flask_section(self, cursor, flask_data, package_name,
                               yaml_path_str):
        """
        Process the "flask" section of a qd_conf.yaml file.

        Extracts init_function and post_init declarations and stores
        them in the flask_init table. Stores config_module and
        site_blueprints as conf_answers.

        Args:
            cursor: Database cursor
            flask_data: Dict from "flask" section
            package_name: Name of the owning package
            yaml_path_str: String path to YAML file

        Returns:
            dict with counts: init_functions
        """
        counts = {'init_functions': 0}

        # Process init_function
        init_func = flask_data.get('init_function')
        if init_func and isinstance(init_func, dict):
            module = init_func.get('module', '')
            function = init_func.get('function', '')
            priority = init_func.get('priority', 50)
            params = init_func.get('params')
            params_json = json.dumps(params) if params else None

            if module and function:
                cursor.execute(
                    '''INSERT OR REPLACE INTO flask_init
                       (package, module, function, priority, params_json,
                        yaml_path)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (package_name, module, function, priority, params_json,
                     yaml_path_str)
                )
                counts['init_functions'] += 1

        # Process post_init list (additional init calls for this package)
        post_init = flask_data.get('post_init')
        if post_init and isinstance(post_init, list):
            for entry in post_init:
                if not isinstance(entry, dict):
                    continue
                module = entry.get('module', '')
                function = entry.get('function', '')
                priority = entry.get('priority', 90)
                params = entry.get('params')
                params_json = json.dumps(params) if params else None

                if module and function:
                    cursor.execute(
                        '''INSERT OR REPLACE INTO flask_init
                           (package, module, function, priority, params_json,
                            yaml_path)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (package_name, module, function, priority,
                         params_json, yaml_path_str)
                    )
                    counts['init_functions'] += 1

        # Store config_module as a conf_answer
        config_module = flask_data.get('config_module')
        if config_module:
            self.post_answer(
                'flask.config_module', config_module, cursor, yaml_path_str
            )

        # Store site_blueprints as a JSON conf_answer
        site_blueprints = flask_data.get('site_blueprints')
        if site_blueprints and isinstance(site_blueprints, list):
            self.post_answer(
                'flask.site_blueprints', json.dumps(site_blueprints),
                cursor, yaml_path_str
            )

        return counts

    def _process_answers_section(self, cursor, answers_data, yaml_path_str):
        """
        Process the "answers" section of a qd_conf.yaml file.

        Args:
            cursor: Database cursor
            answers_data: Dict from "answers" section
            yaml_path_str: String path to YAML file

        Returns:
            Count of answers added
        """
        count = 0

        def traverse(obj, key_parts):
            nonlocal count
            if isinstance(obj, dict):
                for k, v in obj.items():
                    traverse(v, key_parts + [k])
            else:
                # Leaf value - insert into database (first answer wins)
                conf_key = '.'.join(key_parts)
                count += self.post_answer(conf_key, obj, cursor, yaml_path_str)

        traverse(answers_data, [])
        return count

    def _process_questions_section(self, cursor, questions_data, yaml_path_str):
        """
        Process the "questions" section of a qd_conf.toml file.

        Args:
            cursor: Database cursor
            questions_data: Dict from "questions" section
            yaml_path_str: String path to TOML file

        Returns:
            Count of questions added
        """
        count = 0

        def is_question_leaf(obj):
            """Check if this dict is a question definition (has help or conf_type)."""
            if not isinstance(obj, dict):
                return False
            return 'help' in obj or 'conf_type' in obj

        def traverse(obj, key_parts):
            nonlocal count
            if is_question_leaf(obj):
                conf_key = '.'.join(key_parts)
                question = ConfQuestion.from_toml(
                    conf_key, obj, yaml_path=yaml_path_str
                )
                question.select_by_key(cursor)
                if cursor.fetchone() is None:
                    question.insert(cursor)
                    count += 1
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    traverse(v, key_parts + [k])

        traverse(questions_data, [])
        return count

    def _add_package(self, cursor, repo_name, package_name, package_path, counts,
                     editable=False):
        """
        Add a package to the database.

        Args:
            cursor: Database cursor
            repo_name: Name of the repository
            package_name: Name of the package
            package_path: Path to the package directory
            counts: Dict to update with counts
            editable: If True, package should be installed in editable mode

        Returns:
            Path to setup.py directory if installable, None otherwise
        """
        isflask, isflaskbp = self._detect_flask_package(package_path)

        # Check for setup.py or pyproject.toml in package, parent, or
        # grandparent directory.
        # Flat layout:  repo/package/__init__.py + repo/setup.py (parent)
        # src/ layout:  repo/src/package/__init__.py + repo/setup.py (grandparent)
        has_setup = False
        setup_path = None
        parent_path = package_path.parent
        grandparent_path = parent_path.parent
        for candidate in (parent_path, grandparent_path, package_path):
            if ((candidate / 'setup.py').exists()
                    or (candidate / 'pyproject.toml').exists()):
                has_setup = True
                setup_path = candidate
                break

        editable_int = 1 if editable else 0
        setup_path_str = str(setup_path) if setup_path else None
        cursor.execute(
            '''INSERT OR REPLACE INTO packages
               (repo, package, path, dirname, isflask, isflaskbp, has_setup,
                setup_path, enabled, editable)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (repo_name, package_name, str(package_path), package_path.name,
             1 if isflask else 0, 1 if isflaskbp else 0, 1 if has_setup else 0,
             setup_path_str, 1, editable_int)
        )
        counts['packages'] += 1

        # Scan for qdo_* functions
        qdo_count = self._scan_package_for_qdo(cursor, package_name, package_path)
        counts['qdo_functions'] += qdo_count

        return setup_path

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

    def get_answers(self):
        """
        Get all answers from the database.

        Returns:
            Dict mapping conf_key to conf_value
        """
        cursor = self._conn.cursor()
        answers = {}

        cursor.execute('SELECT conf_key, conf_value FROM conf_answers')
        for row in cursor.fetchall():
            answers[row[0]] = row[1]

        return answers

    def get_questions(self):
        """
        Get all questions from the database.

        Returns:
            List of ConfQuestion objects
        """
        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.cursor()

        cursor.execute('''
            SELECT conf_key, conf_help, conf_type, yaml_path
            FROM conf_questions
            ORDER BY conf_key
        ''')

        questions = [ConfQuestion.from_row(row) for row in cursor.fetchall()]
        self._conn.row_factory = None
        return questions

    def get_installable_packages(self):
        """
        Get all packages with has_setup=1 (installable).

        Returns:
            List of dicts with package, setup_path, repo, enabled, editable
        """
        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.cursor()

        cursor.execute('''
            SELECT package, setup_path, repo, enabled, editable
            FROM packages
            WHERE has_setup = 1
            ORDER BY package
        ''')

        packages = [dict(row) for row in cursor.fetchall()]
        self._conn.row_factory = None
        return packages

    def get_flask_init_sequence(self):
        """
        Get the ordered sequence of Flask init calls for enabled packages.

        Joins flask_init with packages to filter by enabled status,
        ordered by priority ascending.

        Returns:
            List of dicts with module, function, priority, params (parsed
            from JSON), package
        """
        if self._conn is None:
            return []

        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.cursor()

        cursor.execute('''
            SELECT fi.module, fi.function, fi.priority, fi.params_json,
                   fi.package
            FROM flask_init fi
            JOIN packages p ON fi.package = p.package
            WHERE p.enabled = 1
            ORDER BY fi.priority ASC, fi.package ASC
        ''')

        results = []
        for row in cursor.fetchall():
            entry = dict(row)
            # Parse params_json back to dict
            if entry['params_json']:
                entry['params'] = json.loads(entry['params_json'])
            else:
                entry['params'] = None
            del entry['params_json']
            results.append(entry)

        self._conn.row_factory = None
        return results

    def set_package_enabled(self, package_name, enabled):
        """
        Set the enabled flag for a package.

        Args:
            package_name: Name of the package
            enabled: Boolean or truthy value
        """
        cursor = self._conn.cursor()
        cursor.execute(
            'UPDATE packages SET enabled = ? WHERE package = ?',
            (1 if enabled else 0, package_name)
        )
        self._conn.commit()


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
