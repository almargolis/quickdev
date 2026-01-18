#!python
"""
Create, repair or update the configuration of an QuickDev qdsite.

The qdstart utility is run by the site owner / user to update
things that they can control. qdstart objects and functions are
also used by the hosting utilities as they manage global
system resources.

The QuickDev system uses QuickDev features, which creates a
bootstraping challenge for QuickDev development.
This impacts QuickDev core developers, not application
developers using QuickDev.

Some of the functions in this module are used by other
QuickDev utilities such as apache.py.

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
# Navigate from qdutils/src/qdutils/qdstart.py to quickdev root
QDUTILS_PKG_PATH = os.path.dirname(THIS_MODULE_PATH)  # qdutils/src/qdutils
QDUTILS_SRC_PATH = os.path.dirname(QDUTILS_PKG_PATH)  # qdutils/src
QDUTILS_PATH = os.path.dirname(QDUTILS_SRC_PATH)       # qdutils
QDDEV_PATH = os.path.dirname(QDUTILS_PATH)             # quickdev root
QDDEV_NAME = os.path.basename(QDDEV_PATH)
QDBASE_DIR_NAME = "qdbase"
QDCORE_DIR_NAME = "qdcore"
QDBASE_PATH = os.path.join(QDDEV_PATH, QDBASE_DIR_NAME)
QDCORE_PATH = os.path.join(QDDEV_PATH, QDCORE_DIR_NAME)
# src/ layout paths for bootstrapping imports
QDBASE_SRC_PATH = os.path.join(QDBASE_PATH, "src")
QDCORE_SRC_PATH = os.path.join(QDCORE_PATH, "src")

# pylint: disable=wrong-import-position
# These imports are out of position because we want to
# have the above checks and definitions for the import
# process.

try:
    from qdbase import cliargs
except ModuleNotFoundError:
    # Bootstrap mode: packages use src/ layout, add src paths
    sys.path.insert(0, QDBASE_SRC_PATH)
    sys.path.insert(0, QDCORE_SRC_PATH)
    from qdbase import cliargs
from qdbase import cliinput
from qdbase import exenv
from qdbase import pdict

try:
    from qdcore import qdsite
except ModuleNotFoundError:
    # Bootstrap mode: add src paths if not already added
    if QDBASE_SRC_PATH not in sys.path:
        sys.path.insert(0, QDBASE_SRC_PATH)
        sys.path.insert(0, QDCORE_SRC_PATH)
    from qdcore import qdsite

from qdbase.qdcheck import CheckMode, CHECK_REGISTRY, get_checker_class

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
        print(f"QDStart: python_version='{python_version}'")
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
        if not self.configure_applications():
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
                print("Running", cmd)
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
        """Install QuickDev packages in editable mode."""
        venv_dpath = self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH]
        pip_path = os.path.join(venv_dpath, "bin", "pip")

        # Verify pip exists
        if not os.path.isfile(pip_path):
            self.error(f"pip not found at {pip_path}")
            return False

        # Install all quickdev packages that have setup.py
        packages = ['qdbase', 'qdcore', 'xsynth', 'qdflask', 'qdimages', 'qdcomments', 'qdutils']
        for pkg in packages:
            pkg_path = os.path.join(QDDEV_PATH, pkg)
            if os.path.exists(os.path.join(pkg_path, 'setup.py')):
                if not self._pip_install_editable(pip_path, pkg_path):
                    return False

        return True

    def configure_applications(self):
        """Discover and install applications from repos/ directory."""
        repos_path = os.path.join(self.qdsite_info.qdsite_dpath, "repos")
        if not os.path.isdir(repos_path):
            if self.debug > 0:
                print(f"No repos/ directory at {repos_path}")
            return True

        venv_dpath = self.qdsite_info.ini_data[qdsite.CONF_PARM_VENV_DPATH]
        pip_path = os.path.join(venv_dpath, "bin", "pip")

        for repo_name in os.listdir(repos_path):
            repo_path = os.path.join(repos_path, repo_name)
            if repo_name == "quickdev":
                continue  # Already handled by configure_venv
            if not os.path.isdir(repo_path):
                continue

            # Check for setup.py or requirements.txt
            setup_py = os.path.join(repo_path, "setup.py")
            requirements_txt = os.path.join(repo_path, "requirements.txt")

            if os.path.exists(setup_py):
                self._pip_install_editable(pip_path, repo_path)

            if os.path.exists(requirements_txt):
                self._pip_install_requirements(pip_path, requirements_txt)

        return True

    def _pip_install_editable(self, pip_path, package_path):
        """Install a package in editable mode."""
        pkg_name = os.path.basename(package_path)
        print(f"Installing: {pkg_name}")
        cmd = [pip_path, "install", "-e", package_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self.error(f"Failed to install {pkg_name}: {result.stderr}")
            return False
        return True

    def _pip_install_requirements(self, pip_path, requirements_path):
        """Install from requirements.txt."""
        print(f"Installing requirements: {os.path.basename(requirements_path)}")
        cmd = [pip_path, "install", "-r", requirements_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self.error(f"Failed to install requirements: {result.stderr}")
            return False
        return True

    def error(self, msg):
        """Print an error message."""
        self.err_ct += 1
        print(msg)


def start_site(qdsite_dpath, quiet):
    """CLI command to start a site."""
    print("START")
    QdStart(qdsite_dpath=qdsite_dpath, quiet=quiet)


def edit_conf(qdsite_dpath):
    """CLI command to edit the main site conf file."""
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


def check_services(qdsite_dpath=None, fix=False, test=False):
    """
    Run configuration checks for all enabled QuickDev services.

    This discovers and runs check modules for each QuickDev service
    package (qdflask, qdimages, qdcomments, etc.) that is installed
    and enabled.

    Args:
        qdsite_dpath: Path to site directory (uses cwd if None)
        fix: If True, attempt to auto-fix issues
        test: If True, run functional tests

    Returns:
        True if all checks passed, False otherwise
    """
    # Determine check mode
    if fix:
        mode = CheckMode.CORRECT
    elif test:
        mode = CheckMode.TEST
    else:
        mode = CheckMode.VALIDATE

    # Get conf directory
    if qdsite_dpath:
        conf_dir = os.path.join(os.path.abspath(qdsite_dpath), 'conf')
    else:
        conf_dir = os.path.join(os.getcwd(), 'conf')

    print("=" * 60)
    print("QuickDev Service Configuration Check")
    print("=" * 60)
    print(f"Mode: {mode.name}")
    print(f"Conf: {conf_dir}")
    print()

    total_errors = 0
    total_warnings = 0
    services_checked = 0

    for service_name in CHECK_REGISTRY:
        try:
            checker_class = get_checker_class(service_name)
            if checker_class is None:
                print(f"\u25cb {service_name}: Not installed (skipped)")
                continue

            # Run checks
            checker = checker_class(conf_dir=conf_dir, mode=mode)
            checker.run_all()

            if checker.results:
                checker.print_results()
                total_errors += checker.error_count
                total_warnings += checker.warning_count
                services_checked += 1
                print()

        except ModuleNotFoundError:
            print(f"\u25cb {service_name}: Not installed (skipped)")
        except Exception as e:
            print(f"\u2717 {service_name}: Check failed - {e}")
            total_errors += 1

    # Final summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Services checked: {services_checked}")
    print(f"Errors: {total_errors}")
    print(f"Warnings: {total_warnings}")

    if total_errors == 0:
        print("\n\u2713 All service checks passed")
        return True
    else:
        print(f"\n\u2717 {total_errors} issue(s) found")
        return False


def main():
    """Main entry point for qdstart CLI."""
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

    # Add parameters for check_services command
    menu.add_item(cliargs.CliCommandLineParameterItem(
        "fix", help_description="Fix issues if possible.", value_type=cliargs.PARAMETER_BOOLEAN
    ))
    menu.add_item(cliargs.CliCommandLineParameterItem(
        "test", help_description="Run functional tests.", value_type=cliargs.PARAMETER_BOOLEAN
    ))

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

    # Check services command
    m = menu.add_item(
        cliargs.CliCommandLineActionItem(
            "c", check_services, help_description="Check all service configurations."
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
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "fix",
            parameter_name="fix",
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "test",
            parameter_name="test",
        )
    )

    menu.cli_run()


if __name__ == "__main__":
    main()
