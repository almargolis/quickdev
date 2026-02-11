#!python
"""
Create, repair or update the configuration of an QuickDev exenv.

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
import pathlib

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
try:
    from qdcore import qdrepos
except ModuleNotFoundError:
    # Bootstrap: qdcore not installed yet, add to path
    sys.path.insert(0, QDCORE_SRC_PATH)
    from qdcore import qdrepos

from qdbase import cliinput
from qdbase import exenv
from qdbase import pdict

from qdbase import qdcheck
from qdbase import qdconf
from qdbase import qdos 

# pylint: enable=wrong-import-position


class QdStart:
    """
    Create or repair a QuickDev "standard" site.

    QuickDev has many useful functions that are useful for any application
    structure. QdStart and related services support a standardized
    and easily extensible application structure that enables composing
    applications from plug-ins and standardizes the application installation process.

    A QuickDev site is a file system directory that is the root of application
    execution. QuickDev imposes no restrictions on its location. For web application
    running under Apache on LINUX systems, the site directory will almost always
    be under /var/www/.

    A site will always have at least one sub-directory:
    ../site/conf/ contains information about the running application. This includes
    secrets needed to access system services, site and application specific
    constants that are referenced during operations and installer input used to
    determine that site's operation.
    ../site/repos/ is an optional sub-directory that contains repositories 
    used by the application. Most commonly git clones. The sub-directory is
    optional because repositories can also be specified on the QdStart
    command line.

    ../site/conf/qdsite.ini contains a relatively small set of values that are captured
    by QdStart.__init__() before scanning repos. This file is only used for re-running
    QdStart for repair or to re-install the site on a new computer.

    exenv.ExecutionEnvironment captures information about the actual state
    of the executiobn environment. The goal is to have this information in
    one place and a consistent format that "just works" accross applications,
    sites and operating environment. ExecutionEnvironment() is aware of 
    the QuickDev site structure but does not demand that it be implemented.
    If the components of a QuickDev site are detected, they are captured.
    If the te execution root is not a QuickDev site, it just notes that fact
    and documents other environmental details.
    
    qdos.py is another closely related
    module that helps applications remain OS independent. It also wraps
    common idioms around the OS functions.

    Installing an application involves activities like creating directories,
    writing site specific scripts and installing software. The QdStart system
    has capabilities to do those things. Its basic method of operation is to
    ask the installer questions to know what needs to be done. While there are
    a small number of hard coded questions, most come from qd_conf.yaml
    files that are found under /repos/ making the set of questions fully
    extensible. Optional plugins can have an "enabled" question that gets
    asked first to avoid asking questions or installing software that is not
    relevant to the site.

    The qd_conf.yaml files have two optional top-level sections:
    - "questions": Configuration questions to ask the installer
    - "answers": Pre-supplied answers that override user prompts

    One use of pre-supplied answers would be for an application that requires
    a service that is provided as an optional service in a different repository.
    The application can supply a "yes" to the plugin enabled question to make
    sure that it gets installed.

    QdStart includes parameters for:
    - answer_file_list: Additional YAML files with answers (loaded first, first answer wins)
    - repo_list: Additional directories to scan before /repos/

    All answers are documented in the /conf/ environment providing a
    complete memory of the installation process. A tool is provided to
    create a comprehensive answer file to support duplication of the
    installation process.
    """

    __slots__ = ("conf_dpath", "debug", "err_ct", 
                 "quiet", "qdsite_dpath", "qdsite_prefix",
                 "conf", "repos_db_fpath", "repo_scanner",
                 "venv_dpath")

    def __init__(  # pylint: disable=too-many-arguments
        self,
        qdsite_dpath=None,
        qdsite_prefix=None,
        venv_dpath=None,
        answer_file_list=None,
        repo_list=None,
        python_version="python3",
        quiet=False,
        debug=0,
    ):
        """
        Initialize and configure a QuickDev site.

        Args:
            qdsite_dpath: Path to site directory (uses cwd if None)
            answer_file_list: List of YAML files with pre-supplied answers
            repo_list: List of directories to scan before /repos/
            python_version: Python executable for venv creation
            force: Force operations without prompting
            quiet: Suppress informational output
            debug: Debug level (0=off, higher=more verbose)
        """
        print(f"QDStart: python_version='{python_version}'")
        self.conf = None
        self.debug = debug
        self.err_ct = 0
        self.qdsite_dpath = qdsite_dpath
        self.qdsite_prefix = qdsite_prefix
        self.quiet = quiet
        self.repo_scanner = None
        self.venv_dpath=venv_dpath

        # We can't do much until know the root directory,
        # site prefix and virtual environment, so we handle those 
        # separately from other questions and answers.
        if (self.qdsite_dpath is None) or (self.qdsite_prefix is None) or (self.venv_dpath is None):
            if answer_file_list:
                repo_scanner = qdrepos.RepoScanner(
                    self.qdsite_info.qdsite_dpath,
                    no_db=True
                )
                count = repo_scanner.load_answer_files(answer_file_list)
                if not self.quiet:
                    print(f"Loaded {count} answers from answer files")
                if self.qdsite_dpath is None:
                    if exenv.CONF_SITE_DPATH in repo_scanner.answer_cache:
                        self.qdsite_dpath = repo_scanner.answer_cache[exenv.CONF_SITE_DPATH]
                if self.qdsite_prefix is None:
                    if exenv.CONF_SITE_PREFIX in repo_scanner.answer_cache:
                        self.qdsite_prefix = repo_scanner.answer_cache[exenv.CONF_SITE_PREFIX]
                if self.venv_dpath is None:
                    if exenv.CONF_VENV_DPATH in repo_scanner.answer_cache:
                        self.venv_dpath = repo_scanner.answer_cache[exenv.CONF_VENV_DPATH]
        # We have checked the command line and answer files. If we don't have
        # answers, we will make reasonable assumptions. There would be something
        # to be said to get answer as to whether or not that is desired or to ask
        # for specific values. None of that would be very hard but I'll wait
        # to get some experience before adding it. Earlier versions asked more
        # questions but I found that I was just mindlessly saying yes, so I don't
        # think there is a need to ask a bunch of questions.
        if self.qdsite_dpath is None:
            self.qdsite_dpath = os.getcwd()
        self.qdsite_dpath = os.path.abspath(self.qdsite_dpath)
        qdos.make_directory("site", self.qdsite_dpath, force=True, raise_ex=True)

        self.conf_dpath = os.path.join(self.qdsite_dpath, 'conf')
        qdos.make_directory("conf", self.conf_dpath, force=True, raise_ex=True)

        if self.venv_dpath is None:
            if sys.prefix != sys.base_prefix:
                # a venv is active, use that
                self.venv_dpath = sys.prefix

        if self.qdsite_prefix is None:
            if self.venv_dpath is None:
                self.qdsite_prefix = pathlib.Path(self.qdsite_dpath).stem
            else:
                self.qdsite_prefix = pathlib.Path(self.venv_dpath).stem

        # create the venv if it doesn't exist
        if sys.prefix == sys.base_prefix:
            # no venv active, activazte it
            # might need to create it first

        self.qdsite_info = exenv.QdSite(qdsite_dpath=qdsite_dpath)
        print(f"Site Info: {self.qdsite_info}")

        self.repos_db_fpath = pathlib.Path(self.qdsite_info.conf_dpath) / 'repos.db'

        # Phase 1: Pre-venv operations (scanning, collecting questions/answers)
        # This phase runs before venv exists, using in-memory database if bootstrapping
        if not self._phase1_scan_and_collect(answer_file_list, repo_list):
            return

        # Phase 2: Create conf directory and venv
        if not self.check_conf_dpath():
            return

        # Create QdConf after conf directory exists (with boot_mode for new sites)
        self.conf = qdconf.QdConf(self.qdsite_info.conf_dpath, boot_mode=self.boot_mode)

        # In boot mode, set initial site_prefix and site_dname from directory name
        if self.boot_mode:
            qdsite_dname = os.path.basename(self.qdsite_info.qdsite_dpath)
            self.qdsite_info.qdsite_dname = qdsite_dname
            self.qdsite_info.qdsite_prefix = qdsite_dname
            self.qdsite_info.qdsite_valid = True
            self.qdsite_info.qdconf = self.conf  # Share the QdConf instance

        self.qdsite_info.write_site_config()

        if not self.check_python_venv(python_version):
            return
        self.qdsite_info.write_site_config()

        # Phase 3: Process questions (may affect which packages get installed)
        if not self.process_questions():
            return

        # Phase 4: Install packages (only enabled ones)
        if not self.configure_venv():
            return
        if not self.configure_applications():
            return

        if not self.check_venv_shortcut():
            return

        # Phase 5: Wrap-up - save database and config
        self._phase5_wrapup()
        print("Site check completed.")

    def _phase1_scan_and_collect(self, answer_file_list, repo_list):
        """
        Phase 1: Scan directories and collect questions/answers before venv.

        This phase runs without venv, using in-memory database if bootstrapping.

        Args:
            answer_file_list: List of YAML files with pre-supplied answers
            repo_list: List of directories to scan before /repos/

        Returns:
            True if successful
        """

        # Create scanner with in-memory database if in boot mode
        self.repo_scanner = qdrepos.RepoScanner(
            self.qdsite_info.qdsite_dpath,
            in_memory=self.boot_mode
        )

        # Load answer files first (first answer wins)
        if answer_file_list:
            count = self.repo_scanner.load_answer_files(answer_file_list)
            if not self.quiet:
                print(f"Loaded {count} answers from answer files")

        # Scan directories (repo_list first, then /repos/)
        counts = self.repo_scanner.scan_directories(repo_list)
        if not self.quiet:
            print(f"Scanned: {counts['repositories']} repos, "
                  f"{counts['packages']} packages, "
                  f"{counts['conf_answers']} answers, "
                  f"{counts['conf_questions']} questions")


        return True

    def _phase5_wrapup(self):
        """
        Phase 5: Wrap-up - save database and configuration.

        If in boot mode, backs up in-memory database to file.
        Saves any dirty configuration files.
        """
        # Backup in-memory database to file if in boot mode
        if self.boot_mode and self.repo_scanner:
            db_path = self.repo_scanner.backup_to_file()
            if db_path and not self.quiet:
                print(f"Saved repos.db to {db_path}")

        # Save site configuration
        self.qdsite_info.write_site_config()

        # Save any dirty conf files
        if self.conf and self.conf.is_dirty():
            written = self.conf.write_all_dirty_conf_files()
            if written and not self.quiet:
                print(f"Wrote config files: {', '.join(written)}")

    def check_conf_dpath(self):
        """Create site conf directory if it doesn't exist."""
        if not qdos.make_directory(
            "Conf", self.qdsite_info.conf_dpath, force=self.force, quiet=self.quiet
        ):
            return False
        for this in exenv.CONF_SUBDIRECTORIES:
            this_path = os.path.join(self.qdsite_info.conf_dpath, this)
            if not qdos.make_directory(
                "Conf", this_path, force=self.force, quiet=self.quiet
            ):
                return False
        return True

    def check_python_venv(self, python_version):
        """Validate Python VENV configuration.

        The venv path is derived from site_prefix: <site_prefix>.venv
        """
        # Check if we're already in a venv and offer to use it
        current_venv = os.environ.get(exenv.OS_ENV_VIRTUAL_ENV, None)
        expected_venv = self.qdsite_info.venv_dpath

        if current_venv is not None and current_venv == expected_venv:
            print(f"VENV: {current_venv} (active)")
            return True

        if current_venv is not None:
            print(f"Current VENV: {current_venv}")
            print(f"Expected VENV: {expected_venv}")

        # Create the venv if it doesn't exist
        if not os.path.isdir(expected_venv):
            if cliinput.cli_input_yn(f"Create VENV '{expected_venv}'?"):
                cmd = [python_version, "-m", "venv", expected_venv]
                print("Running", cmd)
                res = subprocess.run(cmd, check=False)
                if res.returncode == 0:
                    return True
                self.error("Unable to create VENV.")
                return False
            return False

        # Virtual environment already exists
        return True

    def check_venv_shortcut(self):
        """Validate Python VENV activate symlink."""
        venv_dpath = self.qdsite_info.venv_dpath
        venv_bin_path = os.path.join(venv_dpath, exenv.VENV_ACTIVATE_SUB_FPATH)
        if qdos.make_symlink_to_file(
            venv_bin_path, link_name="venv", error_func=self.error
        ):
            return True
        self.error("Unable to create VENV shortcut.")
        return False

    def configure_venv(self):
        """Install QuickDev packages in editable mode."""
        venv_dpath = self.qdsite_info.venv_dpath
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
        """
        Install enabled applications from repos/ directory.

        Only installs packages that:
        1. Have setup.py (installable)
        2. Are enabled (not disabled via "enabled: no" answer)
        """
        if not self.repo_scanner:
            return True

        venv_dpath = self.qdsite_info.venv_dpath
        pip_path = os.path.join(venv_dpath, "bin", "pip")

        # Get all installable packages and check enabled status
        packages = self.repo_scanner.get_installable_packages()

        for pkg in packages:
            pkg_name = pkg['package']
            pkg_path = pkg['path']
            enabled = pkg['enabled']

            # Skip quickdev packages (handled by configure_venv)
            if pkg['repo'] == 'quickdev':
                continue

            # Skip disabled packages
            if not enabled:
                if self.debug > 0:
                    print(f"  Skipping disabled package: {pkg_name}")
                continue

            # Install the package
            if os.path.exists(os.path.join(pkg_path, 'setup.py')):
                self._pip_install_editable(pip_path, pkg_path)

            # Also check for requirements.txt
            requirements_txt = os.path.join(pkg_path, 'requirements.txt')
            if os.path.exists(requirements_txt):
                self._pip_install_requirements(pip_path, requirements_txt)

        return True

    def handle_question(self, question):
        """
        Handle a single configuration question.

        Checks for pre-supplied answer first, then prompts user if needed.
        Stores the answer in QdConf.

        Args:
            question: Dict with conf_key, help, type from conf_questions table

        Returns:
            The answer value, or None if skipped
        """
        conf_key = question['conf_key']
        help_text = question.get('help', '')
        value_type = question.get('type', 'string')

        # Check for pre-supplied answer
        if conf_key in self.answers_cache:
            answer = self.answers_cache[conf_key]
            if not self.quiet:
                print(f"  {conf_key}: {answer} (from answers)")
            if self.conf:
                self.conf[conf_key] = answer
            return answer

        # Check if already answered in conf
        if self.conf:
            try:
                existing = self.conf[conf_key]
                if not self.quiet:
                    print(f"  {conf_key}: {existing} (existing)")
                return existing
            except KeyError:
                pass

        # Prompt user
        prompt = f"{conf_key}"
        if help_text:
            prompt = f"{help_text}\n{conf_key}"

        if value_type == 'boolean':
            answer = cliinput.cli_input_yn(prompt)
        else:
            answer = cliinput.cli_input_str(prompt)

        if answer is not None and self.conf:
            self.conf[conf_key] = answer

        return answer

    def _is_disabled_answer(self, answer):
        """Check if an answer represents a disabled/no value."""
        if answer is None:
            return False
        if isinstance(answer, bool):
            return not answer
        if isinstance(answer, str):
            return answer.lower() in ('false', 'no', '0', 'n')
        return False

    def process_questions(self):
        """
        Process all configuration questions.

        Handles "enabled" questions first to:
        1. Skip related questions for disabled plugins
        2. Mark packages as disabled in the database

        Returns:
            True if successful
        """
        if not self.repo_scanner:
            return True

        questions = self.repo_scanner.get_questions()
        if not questions:
            return True

        if not self.quiet:
            print("\nProcessing configuration questions...")

        # Separate enabled questions from others
        enabled_questions = [q for q in questions if q['conf_key'].endswith('.enabled')]
        other_questions = [q for q in questions if not q['conf_key'].endswith('.enabled')]

        # Process enabled questions first
        disabled_prefixes = set()
        for question in enabled_questions:
            answer = self.handle_question(question)
            if self._is_disabled_answer(answer):
                # Extract prefix to skip related questions
                prefix = question['conf_key'].rsplit('.enabled', 1)[0]
                disabled_prefixes.add(prefix)

                # Mark corresponding package as disabled
                # The prefix might be like "qdflask" or "myapp.plugin"
                package_name = prefix.split('.')[-1]
                self.repo_scanner.set_package_enabled(package_name, False)
                if not self.quiet:
                    print(f"  Disabled package: {package_name}")

        # Process other questions, skipping disabled plugins
        for question in other_questions:
            conf_key = question['conf_key']
            # Check if this question belongs to a disabled plugin
            skip = False
            for prefix in disabled_prefixes:
                if conf_key.startswith(prefix + '.'):
                    skip = True
                    break
            if not skip:
                self.handle_question(question)

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
    tdict.add_column(pdict.Text("site_dname"))
    tdict.add_column(pdict.Text("site_prefix"))
    qdsite_info = exenv.QdSite(qdsite_dpath=qdsite_dpath)
    # Create a dict for CliForm from QdSite properties
    conf_data = {
        'site_dname': qdsite_info.site_dname,
        'site_prefix': qdsite_info.site_prefix,
    }
    cliinput.CliForm(conf_data, tdict=tdict)
    # Update QdSite with any changes and save
    if qdsite_info.site_dname != conf_data.get('site_dname'):
        qdsite_info.site_dname = conf_data['site_dname']
    if qdsite_info.site_prefix != conf_data.get('site_prefix'):
        qdsite_info.site_prefix = conf_data['site_prefix']
    qdsite_info.write_site_config()


def make_launch_files(cmd_name, qdsite_dpath=None):
    """Write launch files for commands that run in background using screen."""
    shell_fpath = os.getenv("SHELL", default="/bin/sh")
    qdsite_info = exenv.QdSite(qdsite_dpath=qdsite_dpath)

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
        mode = qdcheck.CheckMode.CORRECT
    elif test:
        mode = qdcheck.CheckMode.TEST
    else:
        mode = qdcheck.CheckMode.VALIDATE

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

    for service_name in qdcheck.CHECK_REGISTRY:
        try:
            checker_class = qdcheck.get_checker_class(service_name)
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
        "z", help_description="Command to run.", value_type=cliargs.PARAMETER_STRING
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
            help_description="Initialize or repair site directory.",
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            exenv.ARG_Q_QUIET, parameter_name="quiet", is_positional=False
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            exenv.ARG_S_SITE_DPATH,
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
            exenv.ARG_P_SITE_PREFIX,
            parameter_name="qdsite_prefix",
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
            "a", parameter_name="answer_file_list", is_positional=False, 
            is_muliple=True, default_none=True, value_type=cliargs.PARAMETER_STRING
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "r", parameter_name="repo_list", is_positional=False, 
            is_muliple=True, default_none=True, value_type=cliargs.PARAMETER_STRING
        )
    )

    # Check services command
    m = menu.add_item(
        cliargs.CliCommandLineActionItem(
            "c", check_services, help_description="Check all service configurations."
        )
    )

    menu.cli_run()


if __name__ == "__main__":
    main()
