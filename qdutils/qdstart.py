#!python
"""
    Create, repair or update the configuration of an QuickDev site.

    The QuickDev system uses QuickDev features, which creates a
    bootstraping challenge for QuickDev development.
    This impacts QuickDev core developers, not application
    developers using QuickDev.

    Some of the functions in this module are used by other
    QuickDev utililities such as apache.py.

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
QDUTILS_PATH = os.path.dirname(THIS_MODULE_PATH)
QDDEV_PATH = os.path.dirname(QDUTILS_PATH)
QDDEV_NAME = os.path.basename(QDDEV_PATH)
QDBASE_DIR_NAME = 'qdbase'
QDCORE_DIR_NAME = 'qdcore'
QDBASE_PATH = os.path.join(QDDEV_PATH, QDBASE_DIR_NAME)
QDCORE_PATH = os.path.join(QDDEV_PATH, QDCORE_DIR_NAME)

print(sys.version)
if sys.version_info[0] < 3:
    # stop here because Python v2 import exceptions are different.
    print("Python 3 or greater required.")
    sys.exit(-1)

try:
    import qdbase.cliargs as cliargs
except ModuleNotFoundError:
    """
    We should only get here if we are developing QuickDev and we don't
    have the environment setup.
    """
    sys.path.append(QDDEV_PATH)
    import qdbase.cliargs as cliargs
from qdbase import cliinput
from qdbase import exenv
from qdbase import pdict
try:
    import qdcore.qdsite as qdsite
except ModuleNotFoundError:
    """
    We should only get here if we are developing QuickDev and we don't
    have the environment setup.
    """
    sys.path.append(QDDEV_PATH)
    import qdcore.qdsite as qdsite


class QdStart():
    """Create or repair an QuickDev site. """
    __slots__ = ('conf_path', 'debug',
                 'err_ct', 'force',
                 'quiet', 'qdsite_info')

    def __init__(self, qdsite_dpath=None, no_site=False, python_version='python3', force=False, quiet=False, debug=0):
        """
        Call self.write_site_ini() frequently so we have saved
        any captured data before bailing after a subsequent test.
        """
        self.err_ct = 0
        self.debug = debug
        self.force = force
        if qdsite_dpath is not None:
            qdsite_dpath = os.path.abspath(qdsite_dpath)
            exenv.make_directory('site', qdsite_dpath, force=self.force, raise_ex=True)
        else:
            qdsite_dpath = os.getcwd()
        self.qdsite_info = qdsite.QdSite(qdsite_dpath=qdsite_dpath)
        print("Site Info: {}".format(self.qdsite_info))
        self.quiet = quiet
        if not self.check_conf_path():
            return
        self.qdsite_info.write_site_ini(debug=self.debug)
        if not self.check_python_venv(python_version):
            return
        self.qdsite_info.write_site_ini()
        if not self.validate_venv():
            return
        if not self.check_venv_shortcut():
            return
        self.qdsite_info.write_site_ini()
        print("Site check completed.")

    def check_conf_path(self):
        """Create site conf directory if it doesn't exist. """
        if not exenv.make_directory('Conf', self.qdsite_info.conf_dpath, force=self.force, quiet=self.quiet):
            return False
        for this in qdsite.CONF_SUBDIRECTORIES:
            this_path = os.path.join(self.qdsite_info.conf_dpath, this)
            if not exenv.make_directory('Conf', this_path, force=self.force, quiet=self.quiet):
                return False
        return True

    def check_python_venv(self, python_version):
        venv_dpath = os.environ.get(exenv.OS_ENV_VIRTUAL_ENV, None)
        if venv_dpath is not None:
            # TODO: check that this version is compatible with python_version.
            print("VENV: {}".format(venv_dpath))
            if cliinput.cli_input_yn("Do you want to use this VENV for this project?"):
                self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH] = venv_dpath
                return True
        venv_name = self.qdsite_info.ini_data[qdsite.CONF_PARM_ACRONYM] + ".venv"
        venv_dpath = os.path.join(self.qdsite_info.site_path, venv_name)
        if not os.path.isdir(venv_dpath):
            if cliinput.cli_input_yn("Create VENV '{}'?".format(venv_dpath)):
                cmd = [python_version, '-m', 'venv', venv_dpath]
                res = subprocess.run(cmd)
                if res.returncode == 0:
                    self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH] = venv_dpath
                    return True
                else:
                    self.error("Unable to create VENV.")
                    return False
            return False
        #
        # We get here if the virtual environment already exists.
        # Update the configuration variable in case it doesn't
        # have the current value.
        #
        self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH] = venv_dpath
        return True

    def check_venv_shortcut(self):
        venv_dpath = self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH]
        venv_bin_path = os.path.join(venv_dpath, qdsite.VENV_ACTIVATE_SUB_FPATH)
        if exenv.make_symlink_to_file(venv_bin_path, link_name='venv',
                                   error_func=self.error):
            return True
        else:
            self.error("Unable to create VENV shortcut.")
            return False

    def validate_venv(self):
        def check_site_package(site_packages_path, package_name, source_path):
            site_link = os.path.join(site_packages_path, package_name)
            print("Check link {} to {}".format(site_link, source_path))
            if not os.path.islink(site_link):
                os.symlink(source_path, site_link, target_is_directory=True)
        venv_dpath = self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH]
        lib_path = os.path.join(venv_dpath, 'lib')
        libs = os.listdir(lib_path)
        python_lib = None
        for this_lib in libs:
            if this_lib.startswith('python'):
                python_lib = this_lib
                break
        if python_lib is None:
            self.error("{} is not a valid venv.".format(venv_dpath))
            return False
        packages_path = os.path.join(lib_path, python_lib, 'site-packages')
        check_site_package(packages_path, QDBASE_DIR_NAME, QDBASE_PATH)
        check_site_package(packages_path, QDCORE_DIR_NAME, QDCORE_PATH)
        return True

    def error(self, msg):
        """Print an error message."""
        self.err_ct += 1
        print(msg)

def start_site(qdsite_dpath, no_site, quiet):
    print("START")
    QdStart(qdsite_dpath, no_site, quiet)

def edit_conf(qdsite_dpath):
    tdict = pdict.TupleDict()
    tdict.add_column(pdict.Text('acronym'))
    tdict.add_column(pdict.Text('guid', is_read_only=True))
    tdict.add_column(pdict.Text('website_subdir'))
    qdsite = qdsite.QdSite(qdsite_dpath=qdsite_dpath)
    editor = cliinput.CliForm(qdsite.ini_data, tdict=tdict)

def make_launch_files(cmd_name, qdsite_dpath=None):
    shell_fpath = os.getenv("SHELL", default='/bin/sh')
    qdsite_info = qdsite.QdSite(qdsite_dpath=qdsite_dpath)

    run_script_file_name = f"run_{cmd_name}"
    f = open(run_script_file_name, "w")
    f.write(f"#{shell_fpath}\n")
    f.write(f"cd {qdsite_info.qdsite_dpath}\n")
    activate_fpath = qdsite_info.get_venv_activate_fpath()
    if activate_fpath is not None:
        f.write(f"source {activate_fpath}\n")
    f.write(f"python {cmd_name}.py\n")
    f.close()
    run_script_fpath = os.path.abspath(run_script_file_name)

    f = open(f"{cmd_name}", "w")
    f.write(f"#{shell_fpath}\n")
    f.write(f"screen -d -m -S {cmd_name} {shell_fpath} {run_script_fpath}\n")
    f.close()

if __name__ == '__main__':
    menu = cliargs.CliCommandLine()
    exenv.command_line_site(menu)
    exenv.command_line_loc(menu)
    exenv.command_line_no_conf(menu)
    exenv.command_line_quiet(menu)
    exenv.command_line_verbose(menu)
    item = cliargs.CliCommandLineParameterItem(
            'p',
            help_description="Command to run.",
            value_type=cliargs.PARAMETER_STRING
    )
    menu.add_item(item)


    m = menu.add_item(cliargs.CliCommandLineActionItem(cliargs.DEFAULT_ACTION_CODE,
                                                   start_site,
                                                   help_description="Synthesize directory."))
    m.add_parameter(cliargs.CliCommandLineParameterItem(exenv.ARG_N_NO_SITE,
                                                    parameter_name='no_site',
                                                    default_value=False,
                                                    is_positional=False))
    m.add_parameter(cliargs.CliCommandLineParameterItem(exenv.ARG_Q_QUIET,
                                                    parameter_name='quiet',
                                                    is_positional=False))
    m.add_parameter(cliargs.CliCommandLineParameterItem(exenv.ARG_S_SITE,
                                                    parameter_name='qdsite_dpath',
                                                    default_none=True,
                                                    is_positional=False))
    m = menu.add_item(cliargs.CliCommandLineActionItem('e',
                                                   edit_conf,
                                                   help_description="Edit site conf file."))
    m.add_parameter(cliargs.CliCommandLineParameterItem(exenv.ARG_S_SITE,
                                                    parameter_name='qdsite_dpath',
                                                    default_none=True,
                                                    is_positional=False))
    m = menu.add_item(cliargs.CliCommandLineActionItem('x',
                                                   make_launch_files,
                                                   help_description="Make launch file."))
    m.add_parameter(cliargs.CliCommandLineParameterItem('p',
                                                    parameter_name='cmd',
                                                    is_positional=True))

    menu.cli_run()
