"""
qdbase.qdconf - Unified configuration management for QuickDev applications

Provides centralized access to configuration files in /conf/ directory with:
- Automatic file location (production and development paths)
- On-demand loading and caching of TOML, INI, and .env files
- Dictionary-like access with dot notation
- Comprehensive error handling

Example usage:
    conf = QdConf()

    # Access TOML config
    server = conf.get('email.MAIL_SERVER', 'localhost')
    port = conf['email.MAIL_PORT']

    # Access .env variables
    password = conf.get('denv.SMTP_PW')

    # Nested access
    color = conf.get('style.colors.header_color', '#000000')
"""

import os
import tomllib
from pathlib import Path
from configparser import ConfigParser
import logging

from qdbase import qdos


class QdConf:
    """
    Unified configuration manager for QuickDev applications.

    Locates and loads configuration files from /conf/ directory with caching.
    Supports TOML, INI, and .env files with dot-notation access.
    """

    def __init__(self, conf_dir=None, boot_mode=False):
        """
        Initialize configuration manager.

        Args:
            conf_dir: Optional explicit path to conf directory.
                     If None, auto-detects using cwd then fallbacks.
            boot_mode: If True, don't read any files (treat as empty).
                      Used during bootstrapping when config files don't exist yet.
        """
        self._cache = {}  # Cache for loaded files
        self._dirty = set()  # Set of filenames that have been modified
        self._boot_mode = boot_mode
        self._conf_dir = self._locate_conf_dir(conf_dir)

    def _locate_conf_dir(self, explicit_path=None):
        """
        Locate the conf directory.

        Search order:
        1. Explicit path if provided
        2. Current working directory + /conf
        3. Common QuickDev site locations

        Returns:
            Path object to conf directory
        """
        if explicit_path:
            path = Path(explicit_path)
            if path.exists() and path.is_dir():
                return path
            raise ValueError(f"Specified conf directory does not exist: {explicit_path}")

        # Try current working directory (production sites)
        cwd_conf = Path.cwd() / 'conf'
        if cwd_conf.exists():
            return cwd_conf

        # Try common development locations
        # (can be extended with more fallbacks if needed)
        parent_conf = Path.cwd().parent / 'conf'
        if parent_conf.exists():
            return parent_conf

        # Default to cwd/conf even if it doesn't exist yet
        # (allows creation later)
        return cwd_conf

    def _load_toml(self, filepath):
        """Load and parse a TOML file."""
        try:
            with open(filepath, 'rb') as f:
                return tomllib.load(f) or {}
        except tomllib.TOMLDecodeError as e:
            logging.error(f"TOML syntax error in {filepath}: {e}")
            raise ValueError(f"Invalid TOML syntax in {filepath}: {e}")
        except Exception as e:
            logging.error(f"Failed to load TOML {filepath}: {e}")
            raise

    def _load_ini(self, filepath):
        """Load and parse an INI file."""
        try:
            config = ConfigParser()
            config.read(filepath)
            # Convert to nested dict
            result = {}
            for section in config.sections():
                result[section] = dict(config.items(section))
            return result
        except Exception as e:
            logging.error(f"Failed to load INI {filepath}: {e}")
            raise

    def _load_env(self, filepath):
        """Load and parse a .env file."""
        try:
            env_vars = {}
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip().strip('"').strip("'")
                        env_vars[key.strip()] = value
            return env_vars
        except Exception as e:
            logging.error(f"Failed to load .env {filepath}: {e}")
            raise

    def _load_file(self, filename):
        """
        Load a configuration file with appropriate parser.

        Args:
            filename: Name of file (without extension) or special name 'denv'

        Returns:
            Dict containing parsed configuration
        """
        # In boot mode, don't read files - treat as empty
        if self._boot_mode:
            if filename not in self._cache:
                self._cache[filename] = {}
            return self._cache[filename]

        # Check cache first
        if filename in self._cache:
            return self._cache[filename]

        # Special handling for .env
        if filename == 'denv':
            filepath = self._conf_dir / '.env'
            if not filepath.exists():
                logging.warning(f"Environment file not found: {filepath}")
                return {}
            data = self._load_env(filepath)
            self._cache[filename] = data
            return data

        # Try different extensions for regular config files
        for ext in ['.toml', '.ini']:
            filepath = self._conf_dir / f"{filename}{ext}"
            if filepath.exists():
                if ext == '.toml':
                    data = self._load_toml(filepath)
                else:  # .ini
                    data = self._load_ini(filepath)

                self._cache[filename] = data
                logging.info(f"Loaded configuration from {filepath}")
                return data

        # File not found — this is normal during bootstrap when conf files
        # are being populated for the first time via __setitem__
        logging.debug(f"Configuration file not found: {self._conf_dir}/{filename}.(toml|ini)")
        return {}

    def _get_nested(self, data, keys):
        """
        Get value from nested dictionary using list of keys.

        Args:
            data: Dictionary to traverse
            keys: List of keys for nested access

        Returns:
            Value at nested location, or raises KeyError
        """
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current[key]  # Raises KeyError if not found
            else:
                raise KeyError(f"Cannot index non-dict with key '{key}'")
        return current

    def _set_nested(self, data, keys, value):
        """
        Set value in nested dictionary using list of keys.

        Creates intermediate dictionaries as needed.

        Args:
            data: Dictionary to modify
            keys: List of keys for nested access
            value: Value to set
        """
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                raise ValueError(f"Cannot set nested key '{key}': not a dict")
            current = current[key]
        current[keys[-1]] = value

    def get(self, key, default=None):
        """
        Get configuration value with optional default.

        Args:
            key: Dot-notation key (e.g., 'email.MAIL_SERVER')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            conf.get('email.MAIL_SERVER', 'localhost')
            conf.get('denv.SMTP_PW')
            conf.get('style.colors.header_color', '#000000')
        """
        try:
            return self[key]
        except (KeyError, FileNotFoundError):
            return default

    def __getitem__(self, key):
        """
        Get configuration value (raises KeyError if not found).

        Args:
            key: Dot-notation key (e.g., 'email.MAIL_SERVER')

        Returns:
            Configuration value

        Raises:
            KeyError: If key not found

        Example:
            server = conf['email.MAIL_SERVER']
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        parts = key.split('.')
        if len(parts) < 2:
            raise ValueError(f"Key must have at least two parts (file.key): {key}")

        filename = parts[0]
        remaining_keys = parts[1:]

        # Load file (from cache or disk)
        data = self._load_file(filename)

        # Navigate nested structure
        try:
            return self._get_nested(data, remaining_keys)
        except KeyError:
            raise KeyError(f"Configuration key not found: {key}")

    def __setitem__(self, key, value):
        """
        Set configuration value and mark file as dirty.

        Args:
            key: Dot-notation key (e.g., 'email.MAIL_SERVER')
            value: Value to set

        Example:
            conf['email.MAIL_SERVER'] = 'smtp.example.com'
            conf['style.colors.header_color'] = '#FF0000'
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        parts = key.split('.')
        if len(parts) < 2:
            raise ValueError(f"Key must have at least two parts (file.key): {key}")

        filename = parts[0]
        remaining_keys = parts[1:]

        # Load file if not already cached (creates empty dict if file doesn't exist)
        if filename not in self._cache:
            self._load_file(filename)
            if filename not in self._cache:
                self._cache[filename] = {}

        # Set the nested value
        self._set_nested(self._cache[filename], remaining_keys, value)

        # Mark file as dirty
        self._dirty.add(filename)

    def is_dirty(self, filename=None):
        """
        Check if configuration has been modified.

        Args:
            filename: Specific file to check, or None to check any

        Returns:
            True if file(s) have been modified
        """
        if filename:
            return filename in self._dirty
        return len(self._dirty) > 0

    def get_dirty_files(self):
        """
        Get list of modified configuration files.

        Returns:
            Set of filenames that have been modified
        """
        return self._dirty.copy()

    def reload(self, filename=None):
        """
        Reload configuration from disk, clearing cache.

        Args:
            filename: Specific file to reload, or None to clear all cache
        """
        if filename:
            self._cache.pop(filename, None)
            self._dirty.discard(filename)
        else:
            self._cache.clear()
            self._dirty.clear()

    def _get_file_extension(self, filename):
        """
        Determine the file extension for a configuration file.

        Checks existing files first, defaults to .toml for new files.

        Args:
            filename: Configuration filename (without extension)

        Returns:
            Extension including dot (e.g., '.toml', '.ini', '.env')
        """
        if filename == 'denv':
            return '.env'

        # Check for existing files
        for ext in ['.toml', '.ini']:
            filepath = self._conf_dir / f"{filename}{ext}"
            if filepath.exists():
                return ext

        # Default to .toml for new files
        return '.toml'

    def _write_toml(self, filepath, data):
        """Write data to a TOML file."""
        qdos.write_toml(filepath, data)

    def _write_ini(self, filepath, data):
        """Write data to an INI file."""
        config = ConfigParser()
        for section, values in data.items():
            if isinstance(values, dict):
                config[section] = {k: str(v) for k, v in values.items()}
            else:
                # Handle flat values by putting them in DEFAULT section
                if not config.has_section('DEFAULT'):
                    pass  # DEFAULT section always exists
                config['DEFAULT'][section] = str(values)
        with open(filepath, 'w', encoding='utf-8') as f:
            config.write(f)

    def _write_env(self, filepath, data):
        """Write data to a .env file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            for key, value in data.items():
                # Quote values that contain spaces or special characters
                if isinstance(value, str) and (' ' in value or '"' in value or "'" in value):
                    value = f'"{value}"'
                f.write(f"{key}={value}\n")

    def write_conf_file(self, filename):
        """
        Write a configuration file to disk.

        Args:
            filename: Configuration filename to write

        Returns:
            True if file was written, False if file not in cache

        Raises:
            ValueError: If file format is not supported
        """
        if filename not in self._cache:
            logging.warning(f"Cannot write {filename}: not in cache")
            return False

        data = self._cache[filename]
        ext = self._get_file_extension(filename)

        if filename == 'denv':
            filepath = self._conf_dir / '.env'
        else:
            filepath = self._conf_dir / f"{filename}{ext}"

        # Ensure conf directory exists
        self._conf_dir.mkdir(parents=True, exist_ok=True)

        if ext == '.env':
            self._write_env(filepath, data)
        elif ext == '.toml':
            self._write_toml(filepath, data)
        elif ext == '.ini':
            self._write_ini(filepath, data)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

        # Clear dirty flag for this file
        self._dirty.discard(filename)
        # Exit boot mode after first successful write
        self._boot_mode = False
        logging.info(f"Wrote configuration to {filepath}")
        return True

    def write_all_dirty_conf_files(self):
        """
        Write all modified configuration files to disk.

        Returns:
            List of filenames that were written
        """
        written = []
        for filename in list(self._dirty):  # Copy to avoid modification during iteration
            if self.write_conf_file(filename):
                written.append(filename)
        return written

    def get_conf_dir(self):
        """Get the path to the conf directory."""
        return self._conf_dir

    def __repr__(self):
        return f"QdConf(conf_dir={self._conf_dir}, cached_files={list(self._cache.keys())})"

    @property
    def boot_mode(self):
        """
        Return True if in bootstrap mode (files not read).

        In boot mode, QdConf doesn't read files from disk - all values
        come from what has been explicitly set. This is used during
        site initialization when config files don't exist yet.
        """
        return self._boot_mode

    @boot_mode.setter
    def boot_mode(self, value):
        """Set bootstrap mode."""
        self._boot_mode = bool(value)


# Convenience singleton instance
_instance = None

def get_conf():
    """
    Get global QdConf instance (singleton pattern).

    Returns:
        QdConf instance

    Example:
        from qdbase.qdconf import get_conf
        conf = get_conf()
        server = conf.get('email.MAIL_SERVER')
    """
    global _instance
    if _instance is None:
        _instance = QdConf()
    return _instance
