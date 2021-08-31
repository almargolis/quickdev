#!python
"""
    Create, repair or update the configuration of an QuickDev site.

    The QuickDev system uses QuickDev features, which creates a
    bootstraping challenge for QuickDev development.
    This impacts QuickDev core developers, not application
    developers using QuickDev.
    *XSynth has a stand-alone mode which can be used to
     translate the qdutils directory without any pre-configuration.
     It only uses non-xpy modules and only QuickDev modules which are
     in the qdutils directory.
    *QdStart for an QuickDev core development site may run before
     the virtual environment has been established. It has code
     to locate required packages if not visible.

"""

import os
import subprocess
import sys


THIS_MODULE_PATH = os.path.abspath(__file__)
QDBASE_PATH = os.path.dirname(THIS_MODULE_PATH)
QDDEV_PATH = os.path.dirname(QDBASE_PATH)
QDBASE_DIR_NAME = 'qdbase'
QDBASE_PATH = os.path.join(QDDEV_PATH, QDBASE_DIR_NAME)
QDSTART_PATH = os.path.join(QDBASE_PATH, 'qdstart.py')

try:
    from qdbase import qdconst
except ModuleNotFoundError:
    qdconst = None
if qdconst is None:
    sys.path.append(QDDEV_PATH)
    from qdbase import qdconst

from qdbase import cli
from qdbase import inifile
from qdbase import qdsite

def check_directory(name, path, quiet=False):
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
    if not quiet:
        print("{} directory: {}.".format(name, path))
    return True


class QdStart():
    """Create or repair an QuickDev site. """
    __slots__ = ('conf_path',
                 'err_ct',
                 'quiet', 'site_info')

    def __init__(self, args):
        self.err_ct = 0
        self.site_info = qdsite.EzSite(site_path=args.site_path)
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

    def check_site_path(self):
        """Create site directory if it doesn't exist. """
        return check_directory('Site', self.site_info.site_path, quiet=self.quiet)

    def check_conf_path(self):
        """Create site conf directory if it doesn't exist. """
        if not check_directory('Conf', self.site_info.conf_path, quiet=self.quiet):
            return False
        for this in qdsite.CONF_SUBDIRECTORIES:
            this_path = os.path.join(self.site_info.conf_path, this)
            if not check_directory('Conf', this_path, quiet=self.quiet):
                return False
        return True

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

    def save_org(self, source_path):
        """
        Save a system configuration file before making changes.
        """
        source_directory, source_filename = os.path.split(source_path)
        org_file_path = os.path.join(self.site_info.conf_path, CONF_ETC_ORG, source_filename)
        if not os.path.exists(org_path):
            shutil.copy2(source_path, org_file_path)

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
        qdbase_path = os.path.join(packages_path, QDBASE_DIR_NAME)
        if not os.path.islink(qdbase_path):
            os.symlink(QDBASE_PATH, qdbase_path)
        return True

    def error(self, msg):
        """Print an error message."""
        self.err_ct += 1
        print(msg)

if __name__ == '__main__':
    menu = cli.CliCommandLine()
    exenv.command_line_site(menu)
    exenv.command_line_loc(menu)
    exenv.command_line_no_conf(menu)
    exenv.command_line_quiet(menu)
    exenv.command_line_verbose(menu)

    m = menu.add_item(cli.CliCommandLineActionItem(cli.DEFAULT_ACTION_CODE,
                                                   synth_site,
                                                   help="Synthesize directory."))
    m.add_parameter(cli.CliCommandLineParameterItem('n', parameter_name='no_site',
                                                    default_value=False,
                                                    is_positional=False))
    m.add_parameter(cli.CliCommandLineParameterItem('q', parameter_name='quiet',
                                                    is_positional=False))
