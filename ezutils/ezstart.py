#!python
"""
    Create, repair or update the configuration of an EzDev site.

    The EzDev system uses EzDev features, which creates a
    bootstraping challenge for EzDev development.
    This impacts EzDev core developers, not application
    developers using EzDev.
    *XPython has a stand-alone mode which can be used to
     translate the ezutils directory without any pre-configuration.
     It only uses non-xpy modules and only EzDev modules which are
     in the ezutils directory.
    *EzStart for an EzDev core development site may run before
     the virtual environment has been established. It has code
     to locate required packages if not visible.

"""

import argparse
import os
import subprocess
import sys

import cli
import ezconst
import inifile

PYTHON_MIN_MAJOR = 3
PYTHON_MIN_MINOR = 6
PYTHON_MIN_VERSION = "{}.{}".format(PYTHON_MIN_MAJOR, PYTHON_MIN_MINOR)

class EzStart():
    """Create or repair an EzDev site. """
    __slots__ = ('acronym',
                 'err_ct', 'ezdev_path', 'ezutils_path',
                 'python_version', 'quiet', 'site_path',
                 'venv_path')

    def __init__(self, args):
        module_path = os.path.abspath(__file__)
        self.ezutils_path = os.path.dirname(module_path)
        self.ezdev_path = os.path.dirname(self.ezutils_path)
        self.acronym = None
        self.err_ct = 0
        self.python_version = None
        self.quiet = args.quiet
        self.venv_path = None
        if args.site_path is None:
            self.site_path = os.getcwd()
        else:
            self.site_path = args.site_path
        self.site_path = os.path.abspath(self.site_path)
        if not self.check_site_path():
            return
        if not self.check_conf_path():
            return
        if not self.check_acronym():
            return
        if not self.check_python_version():
            return
        if not self.check_python_venv():
            return

    def check_directory(self, name, path):
        """Create a directory if it doesn't exist. """
        if os.path.exists(path):
            if not os.path.isdir(path):
                self.error("'{}' is not a directory.".format(path))
                return False
        else:
            if cli.cli_input_yn("Create directory '{}'?".format(path)):
                os.mkdir(path)
            else:
                return False
        if not self.quiet:
            print("{} directory: {}.".format(name, path))
        return True

    def check_site_path(self):
        """Create site directory if it doesn't exist. """
        return self.check_directory('Site', self.site_path)

    def check_conf_path(self):
        """Create site conf directory if it doesn't exist. """
        path = os.path.join(self.site_path, ezconst.SITE_CONF_DIR_NAME)
        return self.check_directory('Conf', path)

    def check_acronym(self):
        self.acronym = cli.cli_input_symbol('Site Acronym')
        return True

    def check_python_version(self):
        python_version = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
        err_msg = "EzDev requires Python version {} or later.".format(PYTHON_MIN_VERSION)
        print("Running Python Version: {}".format(python_version))
        if sys.version_info.major < PYTHON_MIN_MAJOR:
            self.error(err_msg)
            return False
        if (sys.version_info.major == PYTHON_MIN_MAJOR) \
             and (sys.version_info.minor < PYTHON_MIN_MINOR):
            self.error(err_msg)
            return False
        self.python_version = python_version
        return True

    def check_python_venv(self):
        venv_path = os.environ.get('VIRTUAL_ENV', None)
        if venv_path is not None:
            print("VENV: {}".format(venv_path))
            if cli.cli_input_yn("Do you want to use this VENV for this project?"):
                self.venv_path = venv_path
                return True
        venv_path = os.path.join(self.site_path, self.acronym)
        if cli.cli_input_yn("Create VENV '{}'?".format(venv_path)):
            cmd = ['python', '-m', 'venv', venv_path]
            res = subprocess.run(cmd)
            if res.returncode == 0:
                self.venv_path = venv_path
                return True
            else:
                self.error("Unable to create VENV.")
                return False
        return False

    def error(self, msg):
        """Print an error message."""
        self.err_ct += 1
        print(msg)

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('site_path',
                            action='store',
                            nargs='?',
                            default=None,
                            help='Path of site root directory.')
    arg_parser.add_argument('-q',
                            action='store_true',
                            dest='quiet',
                            help='Display as few messages as possible.')
    run_args = arg_parser.parse_args()
    ez = EzStart(run_args)
