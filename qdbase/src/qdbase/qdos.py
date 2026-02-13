"""
qdbase.qdos - OS action wrappers for QuickDev

Provides wrapped versions of common OS operations with better
error handling and user interaction support.
"""

import os
import re

from qdbase import cliinput

try:
    import werkzeug
except ModuleNotFoundError:
    werkzeug = None

# Symlink type constants
SYMLINK_TYPE_DIR = "d"
SYMLINK_TYPE_FILE = "f"

# Global return code for error tracking
return_code = 0

def handle_error(msg, error_func, error_print, raise_ex):
    """
    Print error message.

    Note that only one of the print nodes is executed. This makes it a little
    terser to call the client procedure.
    """
    if raise_ex:
        raise ValueError(msg)
    if error_func is not None:
        error_func(msg)
    elif error_print:
        print(msg)



def make_directory(
    name,  # pylint: disable=unused-argument
    path,
    force=False,
    mode=511,
    quiet=False,
    error_func=None,
    error_print=True,
    raise_ex=False,
):  # pylint: disable=too-many-arguments
    """
    Create a directory if it doesn't exist.

    The default mode 511 is the default of os.mkdir. It is specified here
    because os.mkdir doesn't accept None.

    force was added for pytest but could be useful in other cases.
    """

    global return_code  # pylint: disable=global-statement, invalid-name
    return_code = 0  # pylint: disable=global-statement, invalid-name
    if os.path.exists(path):
        if not os.path.isdir(path):
            err_msg = f"'{path}' is not a directory."
            handle_error(err_msg, error_func, error_print, raise_ex)
            return_code = 101
            return False
    else:
        if force or cliinput.cli_input_yn(f"Create directory '{path}'?"):
            try:
                os.mkdir(path, mode=mode)
            except PermissionError:
                err_msg = "Permission error. Use sudo."
                handle_error(err_msg, error_func, error_print, raise_ex)
                return_code = 102
                return False
        else:
            return_code = 102
            return False
    if not quiet:
        print(f"{name} directory: {path}.")
    return True



def safe_join(*args):
    """
    extension of os.path.join() that is less susceptible to
    malicious input. This is an extension of werkzeug.utils.safe_join()
    that neatly handles a chroot type setup without detracting
    from safety.

    Falls back to a basic implementation when werkzeug is not installed.
    """
    args = list(args)
    if len(args) > 1:
        if args[1][0] == "/":
            args[1] = args[1][1:]
    if werkzeug is not None:
        return werkzeug.utils.safe_join(*args)  # pylint: disable=no-value-for-parameter
    # Fallback when werkzeug is not installed
    if len(args) == 0:
        return None
    base = args[0]
    for path in args[1:]:
        if os.path.isabs(path):
            return None
        joined = os.path.join(base, path)
        real_base = os.path.realpath(base)
        real_joined = os.path.realpath(joined)
        # Check that joined path is within base directory
        # Handle root directory "/" as a special case
        if real_base == "/":
            if not real_joined.startswith("/"):
                return None
        elif not real_joined.startswith(real_base + os.sep) and real_joined != real_base:
            return None
        base = joined
    return base

#
# make_symlink
#
# Errors may result in going from having a symlink to having none.
#
# If calling with a full path, set name part to None or ''
#
def make_symlink(
    target_type,
    target_directory,
    target_name=None,
    link_directory=None,
    link_name=None,
    error_func=None,
):  # pylint: disable=too-many-arguments, too-many-return-statements, too-many-branches
    """
    This is an extension of os.symlink() with more
    flexibility describing paths and handling
    exceptions.
    """
    if (target_name is None) or (target_name == ""):
        target_path = os.path.join(target_directory)
        target_name = os.path.basename(target_path)
    else:
        target_path = os.path.join(target_directory, target_name)
    if (link_directory is None) or (link_directory == ""):
        link_directory = os.getcwd()
    if (link_name is None) or (link_name == ""):
        link_name = target_name
    link_path = os.path.join(link_directory, link_name)
    #
    # Make sure the link is valid before doing anything to any existing link
    #
    try:
        target_stat = os.stat(target_path)
    except FileNotFoundError:
        target_stat = None
    if target_stat is None:
        if error_func is not None:
            error_func(f"Symlink target '{target_path}' does not exist")
        return False
    if os.path.islink(target_path):
        if error_func is not None:
            error_func(
                f"Symlink target '{target_path}' is a symlink. Symlink not created."
            )
        return False
    if target_type == SYMLINK_TYPE_DIR:
        if not os.path.isdir(target_path):
            if error_func is not None:
                error_func(
                    f"Symlink target '{target_path}' is not a directory. Symlink not created."
                )
            return False
    elif target_type == SYMLINK_TYPE_FILE:
        if not os.path.isfile(target_path):
            if error_func is not None:
                error_func(
                    f"Symlink target '{target_path}' is not a file. Symlink not created."
                )
            return False
    else:
        if error_func is not None:
            error_func(
                f"Symlink '{target_path}' type code invalid. Symlink not created."
            )
        return False
    #
    # Deal with any existing link or file
    #
    if os.path.islink(link_path):
        try:
            os.remove(link_path)
        except FileNotFoundError:
            if error_func is not None:
                error_func(f"Unable to remove existing symlink '{link_path}'.")
            return False
    try:
        link_stat = os.stat(link_path)
    except FileNotFoundError:
        link_stat = None
    if link_stat is not None:
        if error_func is not None:
            error_func(
                f"File exists at symlink '{link_path}'. It must be removed to continue."
            )
        return False
    #
    # Make the symlink
    #
    try:
        os.symlink(target_path, link_path)
    except FileNotFoundError:
        if error_func is not None:
            error_func(f"Unable to create symlink '{target_path}'.")
        return False
    return True


def make_symlink_to_file(
    target_directory,
    target_name=None,
    link_directory=None,
    link_name=None,
    error_func=None,
):
    """
    This is an extension of os.symlink() specifically
    for symlinks to files.
    """
    return make_symlink(
        SYMLINK_TYPE_FILE,
        target_directory,
        target_name,
        link_directory,
        link_name,
        error_func=error_func,
    )


def write_toml(filepath, data):
    """
    Write a dictionary to a TOML file.

    Handles strings, booleans, integers, floats, lists of scalars,
    nested dicts (TOML tables), and lists of dicts (TOML arrays of
    tables). None values are skipped.

    Args:
        filepath: Path to the output file
        data: Dictionary to serialize
    """
    lines = []
    _write_toml_table(lines, data, [])
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        if lines:
            f.write('\n')


def _toml_key(key):
    """Format a key for TOML, quoting if necessary."""
    if re.match(r'^[A-Za-z0-9_-]+$', key):
        return key
    return '"' + key.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _toml_value(value):
    """Format a scalar value for TOML."""
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        escaped = (value
                   .replace('\\', '\\\\')
                   .replace('"', '\\"')
                   .replace('\n', '\\n')
                   .replace('\t', '\\t'))
        return f'"{escaped}"'
    if isinstance(value, list):
        items = [_toml_value(item) for item in value if item is not None]
        return '[' + ', '.join(items) + ']'
    raise TypeError(f"Unsupported TOML value type: {type(value)}")


def _write_toml_table(lines, data, key_path):
    """
    Recursively write a TOML table.

    Emits scalars first, then sub-tables, then arrays of tables.
    """
    scalars = []
    sub_tables = []
    arrays_of_tables = []

    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, dict):
            sub_tables.append((key, value))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            arrays_of_tables.append((key, value))
        else:
            scalars.append((key, value))

    # Emit table header if we have a key_path and there are scalars
    if key_path and scalars:
        header = '.'.join(_toml_key(k) for k in key_path)
        if lines and lines[-1] != '':
            lines.append('')
        lines.append(f'[{header}]')

    # Emit scalars
    for key, value in scalars:
        lines.append(f'{_toml_key(key)} = {_toml_value(value)}')

    # Emit sub-tables
    for key, value in sub_tables:
        _write_toml_table(lines, value, key_path + [key])

    # Emit arrays of tables
    for key, value in arrays_of_tables:
        for item in value:
            full_key = key_path + [key]
            header = '.'.join(_toml_key(k) for k in full_key)
            if lines and lines[-1] != '':
                lines.append('')
            lines.append(f'[[{header}]]')
            for item_key, item_value in item.items():
                if item_value is None:
                    continue
                if isinstance(item_value, dict):
                    _write_toml_table(lines, item_value,
                                      full_key + [item_key])
                else:
                    lines.append(
                        f'{_toml_key(item_key)} = {_toml_value(item_value)}')


def make_symlink_to_directory(
    target_directory,
    target_name=None,
    link_directory=None,
    link_name=None,
    error_func=None,
):
    """
    This is an extension of os.symlink() specifically
    for symlinks to directories.
    """
    return make_symlink(
        SYMLINK_TYPE_DIR,
        target_directory,
        target_name,
        link_directory,
        link_name,
        error_func=error_func,
    )

