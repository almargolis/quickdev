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
import secrets
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
from qdcore import flaskapp
from qdcore.qdrepos import (ConfAnswer, SOURCE_CONSTANT, SOURCE_CONFIGURED,
                            SOURCE_PROMPT, expand_answer_refs,
                            has_unresolved_refs)

# pylint: enable=wrong-import-position


class QdStart:
    """
    Create or repair a QuickDev "standard" site.

    QuickDev has many capabilities that work with any application structure.
    QdStart and related services support a standardized, easily extensible
    application structure that enables composing applications from plug-ins
    and standardizes the installation process.

    Site Directory Structure
    ------------------------
    A QuickDev site is a file system directory that serves as the root of
    application execution. QuickDev imposes no restrictions on its location.
    For web applications running under Apache on Linux, the site directory
    will almost always be under /var/www/.

    A site always has at least one subdirectory:
      ../site/conf/   - Contains information about the running application:
                        secrets for system services, site-specific constants,
                        and installer answers that determine the site's behavior.
      ../site/repos/  - Optional. Contains repositories (typically git clones)
                        used by the application. Repositories can also be
                        specified on the QdStart command line.

    Site Configuration
    ------------------
    ../site/conf/site.toml contains a small set of core values captured by
    QdStart before scanning repos. This file is primarily used when re-running
    QdStart for repair or to reinstall the site on a new computer.

    These values are also accessible through exenv.QdSite, which is the
    preferred way to access site information at runtime. When QdStart makes
    changes, it updates and rewrites the site configuration.

    exenv.QdSite captures information about the actual state of the execution
    environment. The goal is to have this information in one place with a
    consistent format that works across applications, sites, and operating
    environments. QdSite is aware of the QuickDev site structure but does not
    require it. If the components of a QuickDev site are detected, they are
    captured; otherwise it notes that fact and documents other environmental
    details.

    Question-Driven Installation
    ----------------------------
    Installing an application involves creating directories, writing
    site-specific scripts, and installing software. QdStart drives this
    process by asking the installer questions. While there are a small
    number of built-in questions, most come from qd_conf.toml files found
    in repositories, making the question set fully extensible. Optional
    plug-ins can have an "enabled" question that is asked first, allowing
    QdStart to skip irrelevant questions and software.

    The qd_conf.toml files have two optional top-level sections:
      - "questions": Configuration questions to ask the installer
      - "answers": Pre-supplied answers that override user prompts

    One use of pre-supplied answers: an application that requires a service
    provided as an optional plug-in in a different repository can supply
    "yes" to that plug-in's enabled question to ensure it gets installed.

    QdStart accepts parameters for:
      - answer_file_list: Additional TOML files with answers (loaded first;
        first answer wins)
      - repo_list: Additional directories to scan before repos/

    All answers are saved in conf/, providing a complete record of the
    installation. A tool is provided to generate a comprehensive answer
    file for reproducing the installation on another machine.

    Phases of Operation
    -------------------
    QdStart.__init__ executes in five phases:
      1. Scan and collect - Scan repos for packages, questions, and answers
      2. Configure site   - Create conf directory and virtual environment
      3. Process questions - Ask installer questions (enabled flags first)
      4. Install packages  - pip install enabled packages
      5. Wrap-up           - Persist repos.db and configuration
    """

    __slots__ = ("boot_mode", "conf", "debug", "err_ct",
                 "quiet", "qdsite_dpath", "qdsite_info", "qdsite_prefix",
                 "repos_db_fpath", "repo_scanner",
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
            qdsite_prefix: Short name / acronym for the site
            venv_dpath: Path to virtual environment (auto-detected if None)
            answer_file_list: List of TOML files with pre-supplied answers
            repo_list: List of directories to scan before /repos/
            python_version: Python executable for venv creation
            quiet: Suppress informational output
            debug: Debug level (0=off, higher=more verbose)
        """
        # --- (a) Initialize simple attributes ---
        self.boot_mode = False
        self.conf = None
        self.debug = debug
        self.err_ct = 0
        self.qdsite_dpath = qdsite_dpath
        self.qdsite_info = None
        self.qdsite_prefix = qdsite_prefix
        self.quiet = quiet
        self.repo_scanner = None
        self.repos_db_fpath = None
        self.venv_dpath = venv_dpath

        # --- (b) Lock qdsite_dpath ---
        if self.qdsite_dpath is None:
            self.qdsite_dpath = os.getcwd()
        self.qdsite_dpath = os.path.abspath(self.qdsite_dpath)
        qdos.make_directory("site", self.qdsite_dpath, force=True, raise_ex=True)

        # --- (c) Determine boot_mode ---
        conf_dpath = os.path.join(self.qdsite_dpath, 'conf')
        self.repos_db_fpath = os.path.join(conf_dpath, 'repos.db')
        self.boot_mode = (
            not os.path.isdir(conf_dpath)
            or not os.path.isfile(self.repos_db_fpath)
        )

        # --- (d) Create QdSite ---
        # QdSite sets qdsite_valid=False if conf/ is missing — expected in boot_mode
        self.qdsite_info = exenv.QdSite(qdsite_dpath=self.qdsite_dpath)
        if not self.quiet:
            print(f"Site Info: {self.qdsite_info}")

        # --- (e) Create RepoScanner ---
        # in_memory avoids writing repos.db before conf/ exists
        self.repo_scanner = qdrepos.RepoScanner(
            self.qdsite_dpath,
            in_memory=self.boot_mode
        )

        # --- (f) Load answer files if provided ---
        if answer_file_list:
            try:
                count = self.repo_scanner.load_answer_files(answer_file_list)
            except (FileNotFoundError, ValueError) as e:
                print(f"\nError loading answer files:\n  {e}")
                sys.exit(1)
            if not self.quiet:
                print(f"Loaded {count} answers from answer files")

        # --- (g) Scan directories ---
        counts = self.repo_scanner.scan_directories(repo_list)
        if not self.quiet:
            print(f"Scanned: {counts['repositories']} repos, "
                  f"{counts['packages']} packages, "
                  f"{counts['conf_answers']} answers, "
                  f"{counts['conf_questions']} questions")

        # --- (h) Materialize if boot_mode ---
        if self.boot_mode:
            if not self.check_conf_dpath():
                return
            self.repo_scanner.backup_to_file()
            self.conf = qdconf.QdConf(self.qdsite_info.conf_dpath, boot_mode=True)
            qdsite_dname = os.path.basename(self.qdsite_dpath)
            self.qdsite_info.conf_dpath = conf_dpath
            self.qdsite_info.qdsite_dname = qdsite_dname
            self.qdsite_info.qdsite_prefix = (
                self.qdsite_prefix if self.qdsite_prefix else qdsite_dname
            )
            self.qdsite_info.qdsite_valid = True
            self.qdsite_info.qdconf = self.conf
            self.qdsite_info.write_site_config()
            # Reload QdSite so it picks up new conf/
            self.qdsite_info.reload(qdsite_dpath=self.qdsite_dpath)

        # --- (i) Non-boot: load existing config ---
        if not self.boot_mode:
            self.conf = qdconf.QdConf(self.qdsite_info.conf_dpath)

        # --- (j) Stash qdsite_prefix and venv_dpath ---
        if self.qdsite_prefix is None:
            self.qdsite_prefix = self.qdsite_info.qdsite_prefix
        if self.venv_dpath is None:
            # Only adopt the active venv if it lives inside the site dir.
            # A foreign venv (e.g. quickdev's qd.venv) should not be used
            # for the site — check_python_venv will create the site's own.
            if sys.prefix != sys.base_prefix:
                site_abs = os.path.abspath(self.qdsite_dpath)
                venv_abs = os.path.abspath(sys.prefix)
                if venv_abs.startswith(site_abs + os.sep):
                    self.venv_dpath = sys.prefix
            if self.venv_dpath is None and self.qdsite_info.venv_dpath:
                self.venv_dpath = self.qdsite_info.venv_dpath

        # --- (k) Remaining phases ---
        if not self.check_python_venv(python_version):
            return
        self.qdsite_info.write_site_config()

        # Phase 3: Process questions (may affect which packages get installed)
        if not self.process_questions():
            return

        # Phase 4: Install packages (only enabled ones)
        if not self.configure_applications():
            return

        # Phase 4b: Generate Flask app files if any Flask packages enabled
        if not self.generate_flask_files():
            return

        if not self.check_venv_shortcut():
            return

        # Phase 5: Wrap-up - save database and config
        self._phase5_wrapup()
        print("Site check completed.")

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
        """Create site conf directory and subdirectories if they don't exist."""
        if not qdos.make_directory(
            "Conf", self.qdsite_info.conf_dpath, force=True, quiet=self.quiet
        ):
            return False
        for subdir in exenv.CONF_SUBDIRECTORIES:
            subdir_path = os.path.join(self.qdsite_info.conf_dpath, subdir)
            if not qdos.make_directory(
                "Conf", subdir_path, force=True, quiet=self.quiet
            ):
                return False
        return True

    def check_python_venv(self, python_version):
        """Validate Python VENV configuration.

        QuickDev sites must run in a virtual environment.
        If a venv is already active, use it. Otherwise create the
        expected venv (<site_prefix>.venv) automatically.
        """
        current_venv = os.environ.get(exenv.OS_ENV_VIRTUAL_ENV, None)
        expected_venv = self.qdsite_info.venv_dpath

        # Use the active venv only if it lives inside the site directory.
        # A foreign venv (e.g. quickdev's own) should not be adopted.
        if current_venv is not None:
            site_abs = os.path.abspath(self.qdsite_dpath)
            venv_abs = os.path.abspath(current_venv)
            if venv_abs.startswith(site_abs + os.sep):
                if not self.quiet:
                    label = "(active, matches site)" if current_venv == expected_venv else "(active)"
                    print(f"VENV: {current_venv} {label}")
                self.venv_dpath = current_venv
                return True

        # No active venv — use expected if it already exists
        if os.path.isdir(expected_venv):
            if not self.quiet:
                print(f"VENV: {expected_venv} (exists)")
            self.venv_dpath = expected_venv
            return True

        # Create the expected venv
        if not self.quiet:
            print(f"Creating VENV: {expected_venv}")
        cmd = [python_version, "-m", "venv", expected_venv]
        res = subprocess.run(cmd, check=False)
        if res.returncode != 0:
            self.error(f"Unable to create VENV at {expected_venv}.")
            return False
        self.venv_dpath = expected_venv
        return True

    def check_venv_shortcut(self):
        """Validate Python VENV activate symlink in the site directory."""
        venv_bin_path = os.path.join(self.venv_dpath, exenv.VENV_ACTIVATE_SUB_FPATH)
        if qdos.make_symlink_to_file(
            venv_bin_path, link_name="venv",
            link_directory=self.qdsite_dpath,
            error_func=self.error
        ):
            return True
        self.error("Unable to create VENV shortcut.")
        return False

    def generate_flask_files(self):
        """
        Generate qd_create_app.py and .wsgi files at site root.

        Called after Phase 4 (install packages) so that all packages
        are installed and their qd_conf.toml has been scanned.

        Only generates files if at least one Flask init function is
        declared for an enabled package.

        Returns:
            True if successful or no Flask packages, False on error
        """
        if not self.repo_scanner:
            return True

        init_sequence = self.repo_scanner.get_flask_init_sequence()
        if not init_sequence:
            return True

        if not self.quiet:
            print("\nGenerating Flask application files...")

        generator = flaskapp.FlaskAppGenerator(
            repo_scanner=self.repo_scanner,
            qdsite_dpath=self.qdsite_dpath,
            venv_dpath=self.venv_dpath,
            qdsite_prefix=self.qdsite_prefix,
            conf=self.conf
        )

        app_path = generator.generate_create_app()
        if app_path and not self.quiet:
            print(f"  Created: {app_path}")

        wsgi_path = generator.generate_wsgi()
        if wsgi_path and not self.quiet:
            print(f"  Created: {wsgi_path}")

        return True

    def configure_applications(self):
        """
        Install enabled application packages.

        Only installs packages that:
        1. Have setup.py (installable)
        2. Are enabled (not disabled via "enabled: no" answer)

        Editable vs normal install is controlled by the e:: prefix
        on the repo_list entry that discovered the package.
        """
        if not self.repo_scanner:
            return True

        pip_path = os.path.join(self.venv_dpath, "bin", "pip")

        # Verify pip exists
        if not os.path.isfile(pip_path):
            self.error(f"pip not found at {pip_path}")
            return False

        # Get all installable packages and check enabled status
        packages = self.repo_scanner.get_installable_packages()

        for pkg in packages:
            pkg_name = pkg['package']
            setup_path = pkg['setup_path']
            enabled = pkg['enabled']

            # Skip disabled packages
            if not enabled:
                if not self.quiet:
                    print(f"  Skipping disabled package: {pkg_name}")
                continue

            # Install the package
            if pkg.get('editable', 0):
                self._pip_install_editable(pip_path, setup_path)
            else:
                self._pip_install_normal(pip_path, setup_path)

            # Also check for requirements.txt
            requirements_txt = os.path.join(setup_path, 'requirements.txt')
            if os.path.exists(requirements_txt):
                self._pip_install_requirements(pip_path, requirements_txt)

        return True

    def handle_question(self, question):
        """
        Handle a single configuration question.

        Uses ConfAnswer.resolve() to check for pre-supplied or existing
        answers, then prompts the user if needed. Stores the answer
        in QdConf.

        Args:
            question: ConfQuestion object

        Returns:
            ConfAnswer with the resolved answer
        """
        conf_key = question.conf_key
        answer = ConfAnswer.resolve(
            question, self.repo_scanner.answer_cache, self.conf
        )

        if answer.source == SOURCE_CONSTANT:
            answer.expand_refs(self.repo_scanner.answer_cache, self.conf)
            if not self.quiet:
                print(f"  {conf_key}: {answer.conf_value} (from answers)")
            self.repo_scanner.update_answer(conf_key, answer.conf_value)
            if self.conf:
                self.conf[conf_key] = answer.conf_value
            self._ensure_directory(question, answer.conf_value)
            return answer

        if answer.source == SOURCE_CONFIGURED:
            if not self.quiet:
                print(f"  {conf_key}: {answer.conf_value} (existing)")
            self._ensure_directory(question, answer.conf_value)
            return answer

        # Prompt user (or auto-generate for random_fill)
        if question.is_random_fill:
            answer.conf_value = secrets.token_hex(32)
            if not self.quiet:
                print(f"  {conf_key}: (generated)")
        elif question.is_boolean:
            prompt = question.build_prompt()
            answer.conf_value = cliinput.cli_input_yn(prompt)
        else:
            prompt = question.build_prompt()
            answer.conf_value = cliinput.cli_input(prompt)

        if answer.conf_value is not None and self.conf:
            self.conf[conf_key] = answer.conf_value
        self._ensure_directory(question, answer.conf_value)

        return answer

    def _ensure_directory(self, question, value):
        """Create directory if question type is dpath and value is set."""
        if not value or not question.is_directory:
            return
        qdos.make_directory(
            question.conf_key, value, force=True, quiet=self.quiet)

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
        enabled_questions = [q for q in questions if q.is_enabled_question]
        other_questions = [q for q in questions if not q.is_enabled_question]

        # Process enabled questions first
        disabled_prefixes = set()
        for question in enabled_questions:
            answer = self.handle_question(question)
            if answer.is_disabled:
                # Extract prefix to skip related questions
                prefix = question.package_prefix
                disabled_prefixes.add(prefix)

                # Mark corresponding package as disabled
                # The prefix might be like "qdflask" or "myapp.plugin"
                package_name = prefix.split('.')[-1]
                self.repo_scanner.set_package_enabled(package_name, False)
                if not self.quiet:
                    print(f"  Disabled package: {package_name}")

        # Process other questions, skipping disabled plugins
        for question in other_questions:
            # Check if this question belongs to a disabled plugin
            skip = False
            for prefix in disabled_prefixes:
                if question.conf_key.startswith(prefix + '.'):
                    skip = True
                    break
            if not skip:
                self.handle_question(question)

        # Second pass: expand symbolic refs that couldn't be resolved
        # during the first pass due to ordering (e.g. qdflask.user_db_path
        # references trellis.content_dpath which was prompted later).
        self._expand_conf_refs(questions, disabled_prefixes)

        return True

    def _expand_conf_refs(self, questions, disabled_prefixes):
        """
        Expand any remaining <conf_key> references in conf values.

        Called after all questions are processed so that prompted
        values are available for expansion.
        """
        if not self.conf or not self.repo_scanner:
            return
        for question in questions:
            # Skip disabled plugins
            skip = False
            for prefix in disabled_prefixes:
                if question.conf_key.startswith(prefix + '.'):
                    skip = True
                    break
            if skip:
                continue
            try:
                current = self.conf[question.conf_key]
            except KeyError:
                continue
            if has_unresolved_refs(current):
                expanded = expand_answer_refs(
                    current, self.repo_scanner.answer_cache, self.conf
                )
                if expanded != current:
                    self.conf[question.conf_key] = expanded
                    if not self.quiet:
                        print(f"  {question.conf_key}: {expanded} (expanded)")

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

    def _pip_install_normal(self, pip_path, package_path):
        """Install a package in normal (non-editable) mode."""
        pkg_name = os.path.basename(package_path)
        print(f"Installing: {pkg_name}")
        cmd = [pip_path, "install", package_path]
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


def start_site(qdsite_dpath, quiet, repo_list=None, answer_file_list=None):
    """CLI command to start a site."""
    print("START")
    QdStart(qdsite_dpath=qdsite_dpath, quiet=quiet,
            repo_list=repo_list, answer_file_list=answer_file_list)


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


def plan_site(qdsite_dpath, quiet, repo_list=None, answer_file_list=None):
    """
    Show a planning report for a site.

    Scans repos and collects questions/answers without executing any
    installation phases. Groups questions by answer source:
    - Application constants (from qd_conf.toml answers section)
    - Previously answered (from existing conf/*.toml files)
    - Will be prompted (no pre-existing answer)

    Args:
        qdsite_dpath: Path to site directory (uses cwd if None)
        quiet: Suppress informational output (unused, kept for CLI compat)
        repo_list: List of directories to scan
        answer_file_list: List of TOML files with pre-supplied answers
    """
    if qdsite_dpath is None:
        qdsite_dpath = os.getcwd()
    qdsite_dpath = os.path.abspath(qdsite_dpath)

    # Lightweight setup: scan repos and collect questions/answers
    repo_scanner = qdrepos.RepoScanner(qdsite_dpath, in_memory=True)

    if answer_file_list:
        try:
            repo_scanner.load_answer_files(answer_file_list)
        except (FileNotFoundError, ValueError) as e:
            print(f"\nError loading answer files:\n  {e}")
            return

    counts = repo_scanner.scan_directories(repo_list)

    # Load existing conf if available
    conf_dpath = os.path.join(qdsite_dpath, 'conf')
    conf = None
    if os.path.isdir(conf_dpath):
        conf = qdconf.QdConf(conf_dpath)

    questions = repo_scanner.get_questions()
    if not questions:
        print("No configuration questions found.")
        return

    # Separate enabled questions from others (same logic as process_questions)
    enabled_questions = [q for q in questions if q.is_enabled_question]
    other_questions = [q for q in questions if not q.is_enabled_question]

    # Resolve each question and group by source
    constants = []
    configured = []
    prompts = []
    disabled_prefixes = set()

    for question in enabled_questions:
        answer = ConfAnswer.resolve(
            question, repo_scanner.answer_cache, conf
        )
        entry = {
            'conf_key': question.conf_key,
            'help': question.conf_help,
            'value': answer.conf_value,
            'source': answer.source,
            'conf_type': question.conf_type,
        }
        if answer.source == SOURCE_CONSTANT:
            constants.append(entry)
        elif answer.source == SOURCE_CONFIGURED:
            configured.append(entry)
        else:
            prompts.append(entry)

        # Track disabled plugins to skip their sub-questions
        if answer.is_disabled:
            disabled_prefixes.add(question.package_prefix)

    for question in other_questions:
        skip = False
        for prefix in disabled_prefixes:
            if question.conf_key.startswith(prefix + '.'):
                skip = True
                break
        if skip:
            continue

        answer = ConfAnswer.resolve(
            question, repo_scanner.answer_cache, conf
        )
        entry = {
            'conf_key': question.conf_key,
            'help': question.conf_help,
            'value': answer.conf_value,
            'source': answer.source,
            'conf_type': question.conf_type,
        }
        if answer.source == SOURCE_CONSTANT:
            constants.append(entry)
        elif answer.source == SOURCE_CONFIGURED:
            configured.append(entry)
        else:
            prompts.append(entry)

    # Display report
    print("=" * 60)
    print("QdStart Planning Report")
    print("=" * 60)
    print(f"Site: {qdsite_dpath}")
    print(f"Scanned: {counts['repositories']} repos, "
          f"{counts['packages']} packages")
    print()

    # Build a combined lookup for expanding refs in the report:
    # all constants + configured values
    all_known = dict(repo_scanner.answer_cache)
    for entry in constants + configured:
        all_known[entry['conf_key']] = entry['value']

    if constants:
        print(f"Application Constants ({len(constants)}):")
        print("-" * 40)
        for entry in constants:
            raw = entry['value']
            expanded = expand_answer_refs(raw, all_known, conf)
            if has_unresolved_refs(str(raw)):
                print(f"  {entry['conf_key']}: {raw}")
                if expanded != str(raw):
                    print(f"    -> {expanded}")
            else:
                print(f"  {entry['conf_key']}: {raw}")
            if entry['help']:
                print(f"    {entry['help']}")
        print()

    if configured:
        print(f"Previously Answered ({len(configured)}):")
        print("-" * 40)
        for entry in configured:
            print(f"  {entry['conf_key']}: {entry['value']}")
            if entry['help']:
                print(f"    {entry['help']}")
        print()

    if prompts:
        print(f"Will Be Prompted ({len(prompts)}):")
        print("-" * 40)
        for entry in prompts:
            if entry.get('conf_type') == qdrepos.CONF_TYPE_RANDOM_FILL:
                print(f"  {entry['conf_key']} (auto-generated)")
            else:
                print(f"  {entry['conf_key']}")
            if entry['help']:
                print(f"    {entry['help']}")
        print()

    if disabled_prefixes:
        print(f"Disabled: {', '.join(sorted(disabled_prefixes))}")
        print()

    total = len(constants) + len(configured) + len(prompts)
    print(f"Total: {total} questions "
          f"({len(constants)} constants, "
          f"{len(configured)} configured, "
          f"{len(prompts)} to prompt)")


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
    menu.add_item(cliargs.CliCommandLineParameterItem(
        "a", help_description="Answer file(s) to load.",
        is_multiple=True, default_none=True, value_type=cliargs.PARAMETER_STRING
    ))
    menu.add_item(cliargs.CliCommandLineParameterItem(
        "r", help_description="Repository directories to scan.",
        is_multiple=True, default_none=True, value_type=cliargs.PARAMETER_STRING
    ))
    menu.add_item(cliargs.CliCommandLineParameterItem(
        exenv.ARG_P_SITE_PREFIX,
        help_description="Site prefix / acronym.",
        default_none=True, value_type=cliargs.PARAMETER_STRING
    ))

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
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "a", parameter_name="answer_file_list", is_positional=False,
            is_multiple=True, default_none=True, value_type=cliargs.PARAMETER_STRING
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "r", parameter_name="repo_list", is_positional=False,
            is_multiple=True, default_none=True, value_type=cliargs.PARAMETER_STRING
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

    # Check services command
    m = menu.add_item(
        cliargs.CliCommandLineActionItem(
            "c", check_services, help_description="Check all service configurations."
        )
    )

    # Planning report command
    m = menu.add_item(
        cliargs.CliCommandLineActionItem(
            "plan", plan_site, help_description="Show planning report."
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
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "a", parameter_name="answer_file_list", is_positional=False,
            is_multiple=True, default_none=True, value_type=cliargs.PARAMETER_STRING
        )
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "r", parameter_name="repo_list", is_positional=False,
            is_multiple=True, default_none=True, value_type=cliargs.PARAMETER_STRING
        )
    )

    menu.cli_run()


if __name__ == "__main__":
    main()
