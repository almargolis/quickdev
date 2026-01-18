#!/usr/bin/env python3
"""
qdo - QuickDev Operations utility

Discovers and runs qdo_* functions defined in repository packages.
Functions are registered by scanning /repos/ and stored in /conf/repos.db.

Usage:
    python qdo.py <function_name> [args...]
    python qdo.py --help
    python qdo.py --list
    python qdo.py --info <function_name>
    python qdo.py --scan

Examples:
    python qdo.py migrate_db --force
    python qdo.py --list
    python qdo.py --info migrate_db
"""

import os
import sys
import importlib.util
import argparse
from pathlib import Path

# Add parent directory to path for imports
THIS_MODULE_PATH = os.path.abspath(__file__)
QDUTILS_PATH = os.path.dirname(THIS_MODULE_PATH)
QDDEV_PATH = os.path.dirname(QDUTILS_PATH)

try:
    from qdcore import qdrepos
except ModuleNotFoundError:
    sys.path.insert(0, QDDEV_PATH)
    from qdcore import qdrepos


def get_site_root():
    """
    Determine the site root directory.

    Returns current working directory, assuming it's the site root.
    """
    return os.getcwd()


def list_functions(site_root):
    """
    List all available qdo_* functions.

    Args:
        site_root: Path to the site root directory
    """
    functions = qdrepos.get_qdo_functions(site_root)

    if not functions:
        print("No qdo_* functions found.")
        print("Run 'python qdo.py --scan' to scan repositories.")
        return

    print("Available qdo_* functions:")
    print("-" * 60)

    for func in functions:
        name = func['function_name'][4:]  # Remove 'qdo_' prefix
        params = func['parameters'] or ''
        docstring = func['docstring'] or ''

        # Get first line of docstring
        first_line = docstring.split('\n')[0].strip() if docstring else ''

        print(f"  {name}({params})")
        if first_line:
            print(f"      {first_line}")
        print()


def show_function_info(site_root, function_name):
    """
    Show detailed information about a qdo_* function.

    Args:
        site_root: Path to the site root directory
        function_name: Name of the function (without qdo_ prefix)
    """
    func = qdrepos.get_qdo_function(site_root, function_name)

    if not func:
        print(f"Function 'qdo_{function_name}' not found.")
        print("Run 'python qdo.py --list' to see available functions.")
        return

    print(f"Function: {func['function_name']}")
    print(f"Package:  {func['package']}")
    print(f"File:     {func['path']}")
    print(f"Call:     {func['function_name']}({func['parameters'] or ''})")
    print()

    if func['docstring']:
        print("Documentation:")
        print("-" * 40)
        print(func['docstring'])
    else:
        print("(No documentation available)")


def scan_repositories(site_root):
    """
    Scan repositories and update the database.

    Args:
        site_root: Path to the site root directory
    """
    print(f"Scanning repositories in {site_root}/repos/...")
    counts = qdrepos.scan_repos(site_root)

    print(f"Found:")
    print(f"  {counts['repositories']} repositories")
    print(f"  {counts['packages']} packages")
    print(f"  {counts['qdo_functions']} qdo_* functions")
    print()
    print(f"Database updated: {site_root}/conf/repos.db")


def load_and_run_function(site_root, function_name, args):
    """
    Load and execute a qdo_* function.

    Args:
        site_root: Path to the site root directory
        function_name: Name of the function (without qdo_ prefix)
        args: Arguments to pass to the function
    """
    func_info = qdrepos.get_qdo_function(site_root, function_name)

    if not func_info:
        print(f"Error: Function 'qdo_{function_name}' not found.")
        print("Run 'python qdo.py --list' to see available functions.")
        sys.exit(1)

    # Load the module containing the function
    module_path = func_info['path']
    function_name_full = func_info['function_name']

    try:
        spec = importlib.util.spec_from_file_location("qdo_module", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["qdo_module"] = module
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Error loading module {module_path}: {e}")
        sys.exit(1)

    # Get the function
    if not hasattr(module, function_name_full):
        print(f"Error: Function {function_name_full} not found in {module_path}")
        sys.exit(1)

    func = getattr(module, function_name_full)

    # Parse arguments
    # TODO: More sophisticated argument parsing based on function signature
    parsed_args = []
    parsed_kwargs = {}

    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            # Try to convert to appropriate type
            parsed_kwargs[key] = _convert_arg(value)
        else:
            parsed_args.append(_convert_arg(arg))

    # Run the function
    try:
        result = func(*parsed_args, **parsed_kwargs)
        if result is not None:
            print(result)
    except TypeError as e:
        print(f"Error calling function: {e}")
        print(f"Expected: {function_name_full}({func_info['parameters'] or ''})")
        sys.exit(1)
    except Exception as e:
        print(f"Error executing function: {e}")
        sys.exit(1)


def _convert_arg(value):
    """
    Convert a string argument to an appropriate Python type.

    Args:
        value: String value to convert

    Returns:
        Converted value (int, float, bool, or str)
    """
    # Boolean
    if value.lower() in ('true', 'yes', '1'):
        return True
    if value.lower() in ('false', 'no', '0'):
        return False

    # Integer
    try:
        return int(value)
    except ValueError:
        pass

    # Float
    try:
        return float(value)
    except ValueError:
        pass

    # String
    return value


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='QuickDev Operations - run qdo_* functions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --list                  List available functions
  %(prog)s --info migrate_db       Show function details
  %(prog)s --scan                  Scan repos and update database
  %(prog)s migrate_db              Run qdo_migrate_db()
  %(prog)s backup path=/tmp/bak    Run with keyword argument
'''
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available qdo_* functions'
    )
    parser.add_argument(
        '--info', '-i',
        metavar='FUNC',
        help='Show detailed information about a function'
    )
    parser.add_argument(
        '--scan', '-s',
        action='store_true',
        help='Scan repositories and update database'
    )
    parser.add_argument(
        '--site', '-S',
        metavar='PATH',
        help='Site root directory (default: current directory)'
    )
    parser.add_argument(
        'function',
        nargs='?',
        help='Function name (without qdo_ prefix)'
    )
    parser.add_argument(
        'args',
        nargs='*',
        help='Arguments to pass to the function'
    )

    args = parser.parse_args()

    # Determine site root
    site_root = args.site or get_site_root()

    # Handle commands
    if args.scan:
        scan_repositories(site_root)
    elif args.list:
        list_functions(site_root)
    elif args.info:
        show_function_info(site_root, args.info)
    elif args.function:
        load_and_run_function(site_root, args.function, args.args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
