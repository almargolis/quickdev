"""
qdbase.qdconf - Unified configuration management for QuickDev applications

Provides centralized access to configuration files in /conf/ directory with:
- Automatic file location (production and development paths)
- On-demand loading and caching of YAML, INI, and .env files
- Dictionary-like access with dot notation
- Comprehensive error handling

Example usage:
    conf = QdConf()

    # Access YAML config
    server = conf.get('email.MAIL_SERVER', 'localhost')
    port = conf['email.MAIL_PORT']

    # Access .env variables
    password = conf.get('denv.SMTP_PW')

    # Nested access
    color = conf.get('style.colors.header_color', '#000000')
"""

import os
import yaml
from pathlib import Path
from configparser import ConfigParser
import logging


class QdConf:
    """
    Unified configuration manager for QuickDev applications.

    Locates and loads configuration files from /conf/ directory with caching.
    Supports YAML, INI, and .env files with dot-notation access.
    """

    def __init__(self, conf_dir=None):
        """
        Initialize configuration manager.

        Args:
            conf_dir: Optional explicit path to conf directory.
                     If None, auto-detects using cwd then fallbacks.
        """
        self._cache = {}  # Cache for loaded files
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

    def _load_yaml(self, filepath):
        """Load and parse a YAML file."""
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logging.error(f"YAML syntax error in {filepath}: {e}")
            raise ValueError(f"Invalid YAML syntax in {filepath}: {e}")
        except Exception as e:
            logging.error(f"Failed to load YAML {filepath}: {e}")
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
        for ext in ['.yaml', '.yml', '.ini']:
            filepath = self._conf_dir / f"{filename}{ext}"
            if filepath.exists():
                if ext in ['.yaml', '.yml']:
                    data = self._load_yaml(filepath)
                else:  # .ini
                    data = self._load_ini(filepath)

                self._cache[filename] = data
                logging.info(f"Loaded configuration from {filepath}")
                return data

        # File not found
        logging.warning(f"Configuration file not found: {self._conf_dir}/{filename}.(yaml|yml|ini)")
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

    def reload(self, filename=None):
        """
        Reload configuration from disk, clearing cache.

        Args:
            filename: Specific file to reload, or None to clear all cache
        """
        if filename:
            self._cache.pop(filename, None)
        else:
            self._cache.clear()

    def get_conf_dir(self):
        """Get the path to the conf directory."""
        return self._conf_dir

    def __repr__(self):
        return f"QdConf(conf_dir={self._conf_dir}, cached_files={list(self._cache.keys())})"


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
