#!python
"""
    Create, repair or update the configuration of an QuickDev qdsite.

    The qdstart utility is run by the site owner / user to update
    things that they can control. qdstart objecs and functions are
    also used by the hosting utilities as they manage global
    system resources.

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

if sys.version_info[0] < 3:
    # stop here because Python v2 import exceptions are different.
    print(f"Python 3 or greater required. Running {sys.version}.")
    sys.exit(-1)


THIS_MODULE_PATH = os.path.abspath(__file__)
QDUTILS_PATH = os.path.dirname(THIS_MODULE_PATH)
QDDEV_PATH = os.path.dirname(QDUTILS_PATH)
QDDEV_NAME = os.path.basename(QDDEV_PATH)
QDBASE_DIR_NAME = "qdbase"
QDCORE_DIR_NAME = "qdcore"
QDBASE_PATH = os.path.join(QDDEV_PATH, QDBASE_DIR_NAME)
QDCORE_PATH = os.path.join(QDDEV_PATH, QDCORE_DIR_NAME)

# pylint: disable=wrong-import-position
# These imports are out of position because we want to
# have the above checks and definitions for the import
# process.

try:
    from qdbase import cliargs
except ModuleNotFoundError:
    # We should only get here if we are developing QuickDev and we don't
    # have the environment setup.
    sys.path.append(QDDEV_PATH)
    from qdbase import cliargs
from qdbase import cliinput
from qdbase import exenv
from qdbase import pdict

from qdcore import qdsite

# pylint: enable=wrong-import-position


class QdStart:
    """Create or repair an QuickDev site."""

    __slots__ = ("conf_path", "debug", "err_ct", "force", "quiet", "qdsite_info")

    def __init__(  # pylint: disable=too-many-arguments
        self,
        qdsite_dpath=None,
        python_version="python3",
        force=False,
        quiet=False,
        debug=0,
    ):
        """
        Call self.write_site_ini() frequently so we have saved
        any captured data before bailing after a subsequent test.
        """
        self.err_ct = 0
        self.debug = debug
        self.force = force
        if qdsite_dpath is not None:
            qdsite_dpath = os.path.abspath(qdsite_dpath)
            exenv.make_directory("site", qdsite_dpath, force=self.force, raise_ex=True)
        else:
            qdsite_dpath = os.getcwd()
        self.qdsite_info = qdsite.QdSite(qdsite_dpath=qdsite_dpath)
        print(f"Site Info: {self.qdsite_info}")
        self.quiet = quiet
        if not self.check_conf_path():
            return
        self.qdsite_info.write_site_ini(debug=self.debug)
        if not self.check_python_venv(python_version):
            return
        self.qdsite_info.write_site_ini()
        if not self.configure_venv():
            return
        if not self.check_venv_shortcut():
            return
        self.qdsite_info.write_site_ini()
        print("Site check completed.")

    def check_conf_path(self):
        """Create site conf directory if it doesn't exist."""
        if not exenv.make_directory(
            "Conf", self.qdsite_info.conf_dpath, force=self.force, quiet=self.quiet
        ):
            return False
        for this in qdsite.CONF_SUBDIRECTORIES:
            this_path = os.path.join(self.qdsite_info.conf_dpath, this)
            if not exenv.make_directory(
                "Conf", this_path, force=self.force, quiet=self.quiet
            ):
                return False
        return True

    def check_python_venv(self, python_version):
        """Validate Python VENV configuration."""
        venv_dpath = os.environ.get(exenv.OS_ENV_VIRTUAL_ENV, None)
        if venv_dpath is not None:
            # TODO: check that this version is compatible with python_version.
            print(f"VENV: {venv_dpath}")
            if cliinput.cli_input_yn("Do you want to use this VENV for this project?"):
                self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH] = venv_dpath
                return True
        venv_name = self.qdsite_info.ini_data[qdsite.CONF_PARM_ACRONYM] + ".venv"
        venv_dpath = os.path.join(self.qdsite_info.qdsite_dpath, venv_name)
        if not os.path.isdir(venv_dpath):
            if cliinput.cli_input_yn(f"Create VENV '{venv_dpath}'?"):
                cmd = [python_version, "-m", "venv", venv_dpath]
                res = subprocess.run(cmd, check=False)
                if res.returncode == 0:
                    self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH] = venv_dpath
                    return True
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
        """Validate Python VENV activate symlink."""
        venv_dpath = self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH]
        venv_bin_path = os.path.join(venv_dpath, qdsite.VENV_ACTIVATE_SUB_FPATH)
        if exenv.make_symlink_to_file(
            venv_bin_path, link_name="venv", error_func=self.error
        ):
            return True
        self.error("Unable to create VENV shortcut.")
        return False

    def configure_venv(self):
        """Configure the virtual environment with QuickDev packages and utilities."""

        def check_site_package(site_packages_path, package_name, source_path):
            """Configure one QuickDev package."""
            site_link = os.path.join(site_packages_path, package_name)
            print(f"Check link {site_link} to {source_path}")
            if not os.path.islink(site_link):
                os.symlink(source_path, site_link, target_is_directory=True)

        venv_dpath = self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH]
        lib_path = os.path.join(venv_dpath, "lib")
        libs = os.listdir(lib_path)
        python_lib = None
        for this_lib in libs:
            if this_lib.startswith("python"):
                python_lib = this_lib
                break
        if python_lib is None:
            self.error(f"{venv_dpath} is not a valid venv.")
            return False
        packages_path = os.path.join(lib_path, python_lib, "site-packages")
        check_site_package(packages_path, QDBASE_DIR_NAME, QDBASE_PATH)
        check_site_package(packages_path, QDCORE_DIR_NAME, QDCORE_PATH)
        return True

    def error(self, msg):
        """Print an error message."""
        self.err_ct += 1
        print(msg)


def start_site(qdsite_dpath, quiet):
    """CLI command to start a site."""
    print("START")
    QdStart(qdsite_dpath, quiet)


def edit_conf(qdsite_dpath):
    """CLI command to edit hte main site conf file."""
    tdict = pdict.TupleDict()
    tdict.add_column(pdict.Text("acronym"))
    tdict.add_column(pdict.Text("guid", is_read_only=True))
    tdict.add_column(pdict.Text("website_subdir"))
    qdsite_info = qdsite.QdSite(qdsite_dpath=qdsite_dpath)
    cliinput.CliForm(qdsite_info.ini_data, tdict=tdict)


def make_launch_files(cmd_name, qdsite_dpath=None):
    """Write launch files for commands that run in background using screen."""
    shell_fpath = os.getenv("SHELL", default="/bin/sh")
    qdsite_info = qdsite.QdSite(qdsite_dpath=qdsite_dpath)

    run_script_file_name = f"run_{cmd_name}"
    with open(run_script_file_name, "w", encoding="utf-8") as f:
        f.write(f"#{shell_fpath}\n")
        f.write(f"cd {qdsite_info.qdsite_dpath}\n")
        activate_fpath = qdsite_info.get_venv_activate_fpath()
        if activate_fpath is not None:
            f.write(f"source {activate_fpath}\n")
        f.write(f"python {cmd_name}.py\n")
    run_script_fpath = os.path.abspath(run_script_file_name)

    with open(f"{cmd_name}", "w", encoding="utf-8") as f:
        f.write(f"#{shell_fpath}\n")
        f.write(f"screen -d -m -S {cmd_name} {shell_fpath} {run_script_fpath}\n")


if __name__ == "__main__":
    menu = cliargs.CliCommandLine()
    exenv.command_line_site(menu)
    exenv.command_line_loc(menu)
    exenv.command_line_no_conf(menu)
    exenv.command_line_quiet(menu)
    exenv.command_line_verbose(menu)
    item = cliargs.CliCommandLineParameterItem(
        "p", help_description="Command to run.", value_type=cliargs.PARAMETER_STRING
    )
    menu.add_item(item)

    m = menu.add_item(
        cliargs.CliCommandLineActionItem(
            cliargs.DEFAULT_ACTION_CODE,
            start_site,
            help_description="Synthesize directory.",
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            exenv.ARG_Q_QUIET, parameter_name="quiet", is_positional=False
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            exenv.ARG_S_SITE,
            parameter_name="qdsite_dpath",
            default_none=True,
            is_positional=False,
        )
    )
    m = menu.add_item(
        cliargs.CliCommandLineActionItem(
            "e", edit_conf, help_description="Edit site conf file."
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            exenv.ARG_S_SITE,
            parameter_name="qdsite_dpath",
            default_none=True,
            is_positional=False,
        )
    )
    m = menu.add_item(
        cliargs.CliCommandLineActionItem(
            "x", make_launch_files, help_description="Make launch file."
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "p", parameter_name="cmd", is_positional=True
        )
    )

    menu.cli_run()
