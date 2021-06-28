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


THIS_MODULE_PATH = os.path.abspath(__file__)
EZUTILS_PATH = os.path.dirname(THIS_MODULE_PATH)
EZDEV_PATH = os.path.dirname(EZUTILS_PATH)
EZCORE_DIR_NAME = 'ezcore'
EZCORE_PATH = os.path.join(EZDEV_PATH, EZCORE_DIR_NAME)
EZSTART_PATH = os.path.join(EZUTILS_PATH, 'ezstart.py')

try:
    from ezcore import ezconst
except ModuleNotFoundError:
    ezconst = None
if ezconst is None:
    sys.path.append(EZDEV_PATH)
    from ezcore import ezconst

from ezcore import cli
from ezcore import inifile
from ezcore import ezsite

class EzStart():
    """Create or repair an EzDev site. """
    __slots__ = ('conf_path',
                 'err_ct', 'ezdev_path', 'ezutils_path',
                 'quiet', 'site_info')

    def __init__(self, args):
        module_path = os.path.abspath(__file__)
        self.err_ct = 0
        self.ezutils_path = os.path.dirname(module_path)
        self.ezdev_path = os.path.dirname(self.ezutils_path)
        self.site_info = ezsite.EzSite(site_path=args.site_path)
        self.quiet = args.quiet
        if not self.check_site_path():
            return
        if not self.check_conf_path():
            return
        if not self.check_acronym():
            return
        if not self.check_python_venv():
            return
        if not self.validate_venv():
            return
        self.site_info.write_site_ini()

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
        return self.check_directory('Site', self.site_info.site_path)

    def check_conf_path(self):
        """Create site conf directory if it doesn't exist. """
        return self.check_directory('Conf', self.site_info.conf_path)

    def check_acronym(self):
        if 'acronym' in self.site_info.ini_info:
            print('Site acronym "{}"'.format(self.site_info.ini_info['acronym']))
            return True
        self.site_info.ini_info['acronym'] = cli.cli_input_symbol('Site Acronym')
        return True

    def check_python_venv(self):
        venv_path = os.environ.get('VIRTUAL_ENV', None)
        if venv_path is not None:
            print("VENV: {}".format(venv_path))
            if cli.cli_input_yn("Do you want to use this VENV for this project?"):
                self.site_info.ini_info['venv_path'] = venv_path
                return True
        venv_name = self.site_info.ini_info['acronym'] + ".venv"
        venv_path = os.path.join(self.site_path, venv_name)
        if not os.path.isdir(venv_path):
            if cli.cli_input_yn("Create VENV '{}'?".format(venv_path)):
                cmd = ['python', '-m', 'venv', venv_path]
                res = subprocess.run(cmd)
                if res.returncode == 0:
                    self.site_info.ini_info['venv_path'] = venv_path
                    return True
                else:
                    self.error("Unable to create VENV.")
                    return False
            return False

    def validate_venv(self):
        venv_path = self.site_info.ini_info['venv_path']
        lib_path = os.path.join(venv_path, 'lib')
        libs = os.listdir(lib_path)
        python_lib = None
        for this_lib in libs:
            if this_lib.startswith('python'):
                python_lib = this_lib
                break
        if python_lib is None:
            self.error("{} is not a valid venv.".format(venv_path))
            return False
        packages_path = os.path.join(lib_path, python_lib, 'site-packages')
        ezcore_path = os.path.join(packages_path, EZCORE_DIR_NAME)
        if not os.path.islink(ezcore_path):
            os.symlink(EZCORE_PATH, ezcore_path)
        return True

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
