"""
Identify and normalize the program execution environment.

Modules may run under a variety of operating system and
operating modes. This module provides a standard way
for a program to know how it is running and normalizes
some services so that most code doesn't have to consider
how it is running.

The global execution_env object created at the bottom
of this module provide a standardized way for an
QuickDev program to know how it is running and where to
find things. This module is obviously Python specific.
When QuickDev is extended to support other languages a
similar structure will be created so all QuickDev programs
can have a similar structure regardless of language.

Some of this code has been brought forward from an
earlier iteration of my framework. There may be some
overlap with newer code and unused artifacts.

This is used by XSynth in stand-alone mode, so it can't
use XSynth features.
"""

import os
import pwd
import shutil
import sys
import traceback

try:
    import werkzeug
except ModuleNotFoundError:
    werkzeug = None

from . import cliargs
from . import cliinput

try:
    from qdcore import qdsite
except ModuleNotFoundError:
    # exenv must always be importable because it is used
    # by xsynth. qdsite capabiliites are not required.
    qdsite = None  # pylint: disable=invalid-name

#
# Command line flags commonly used by QuickDev utilities.
# These functions help assure consistency.
#

ARG_D_DEBUG = "d"
ARG_L_CONF_LOC = "l"
ARG_N_NO_SITE = "n"
ARG_Q_QUIET = "q"
ARG_S_SITE = "s"
ARG_V_VERBOSE = "v"
ARG_W_WEBSITE = "w"

SYMLINK_TYPE_DIR = "d"
SYMLINK_TYPE_FILE = "f"

OS_ENV_VIRTUAL_ENV = "VIRTUAL_ENV"


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


def check_venv(venv_dpath):  # pylint: disable=too-many-return-statements
    """
    Check if the specified venv_dpath is a (reasonably likely) virtual
    environment directory.

    Returns None if not a venv directory.
    Returns the Python version in the format "python3.7" if it is a venv.

    """
    if not os.path.isfile(venv_dpath):
        return None
    if not os.path.isfile(os.path.join(venv_dpath, "pyvenv.cfg")):
        return None
    if not os.path.isdir(os.path.join(venv_dpath, "bin")):
        return None
    if not os.path.isdir(os.path.join(venv_dpath, "include")):
        return None
    lib_dpath = os.path.join(venv_dpath, "lib")
    if not os.path.isdir(lib_dpath):
        return None
    for this in os.listdir(lib_dpath):
        if this.startswith("python"):
            return this
    return None


class ExenvGlobals:  # pylint: disable=too-many-instance-attributes, too-few-public-methods
    """
    This is a container for global application environment
    variables. This supports a chroot-like alternate
    path root. This is used for pytest.
    """

    def __init__(self):
        self.init()

    def init(self, root="/"):
        "This is separated so test can call with an alternate root."
        self.root = root
        self.qdhost_dpath = os.path.join(root, "etc/qdhost")
        self.qdhost_db_fpath = os.path.join(self.qdhost_dpath, "db.sql")
        self.qdhost_websites_subdir = "websites"
        self.qdhost_websites_dpath = os.path.join(
            self.qdhost_dpath, self.qdhost_websites_subdir
        )
        self.qdhost_qdsites_subdir = "qdsites"
        self.qdhost_qdsites_dpath = os.path.join(
            self.qdhost_dpath, self.qdhost_qdsites_subdir
        )
        self.qdhost_all_subdirs = [
            self.qdhost_websites_subdir,
            self.qdhost_qdsites_subdir,
        ]
        self.qdsites_dpath = os.path.join(root, "var/www")


return_code = 0  # pylint: disable=invalid-name


def command_line_debug(menu):
    """
    Define this common command line flag.
    """
    item = cliargs.CliCommandLineParameterItem(
        ARG_D_DEBUG,
        default_value=False,
        help_description="Display debug messages.",
        value_type=cliargs.PARAMETER_BOOLEAN,
    )
    menu.add_item(item)
    return item


def command_line_loc(menu):
    """
    Define this common command line flag.
    """
    item = cliargs.CliCommandLineParameterItem(
        ARG_L_CONF_LOC,
        help_description="Location of site base directory.",
        value_type=cliargs.PARAMETER_INTEGER,
    )
    menu.add_item(item)
    return item


def command_line_no_conf(menu):
    """
    Define this common command line flag.
    """
    item = cliargs.CliCommandLineParameterItem(
        ARG_N_NO_SITE,
        default_value=False,
        help_description="Stand-alone operation. No conf file or database.",
        value_type=cliargs.PARAMETER_BOOLEAN,
    )
    menu.add_item(item)
    return item


def command_line_quiet(menu):
    """
    Define this common command line flag.
    """
    item = cliargs.CliCommandLineParameterItem(
        ARG_Q_QUIET,
        default_value=False,
        help_description="Display as few messages as possible.",
        value_type=cliargs.PARAMETER_BOOLEAN,
    )
    menu.add_item(item)
    return item


def command_line_site(menu):
    """
    Define this common command line flag.
    """
    item = cliargs.CliCommandLineParameterItem(
        ARG_S_SITE,
        help_description="Specify site to configure.",
        value_type=cliargs.PARAMETER_STRING,
    )
    menu.add_item(item)
    return item


def command_line_verbose(menu):
    """
    Define this common command line flag.
    """
    item = cliargs.CliCommandLineParameterItem(
        ARG_V_VERBOSE,
        help_description="Display more detailed messages than minimally needed.",
        value_type=cliargs.PARAMETER_BOOLEAN,
    )
    menu.add_item(item)
    return item


def command_line_website(menu):
    """
    Define this common command line flag.
    """
    item = cliargs.CliCommandLineParameterItem(
        ARG_W_WEBSITE,
        help_description="Specify website to configure.",
        value_type=cliargs.PARAMETER_STRING,
    )
    menu.add_item(item)
    return item


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


#
# sys.platform recognized by qddev
#
PLATFORM_DARWIN = "darwin"
PLATFORM_LINUX = "linux"
ALL_PLATFORMS = [PLATFORM_DARWIN, PLATFORM_LINUX]

PYTHON_MIN_MAJOR = 3
PYTHON_MIN_MINOR = 6
PYTHON_MIN_VERSION = "{PYTHON_MIN_MAJOR}.{PYTHON_MIN_MINOR}"

# Check python version before imports because excepton classes
# have changed.


def save_org(source_path):
    """
    Save a system configuration file before making changes.
    """
    source_directory, source_filename = os.path.split(source_path)
    org_file_path = os.path.join(source_directory, source_filename + ".org")
    if not os.path.exists(org_file_path):
        shutil.copy2(source_path, org_file_path)


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
                "Symlink '{target_path}' type code invalid. Symlink not created."
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


class ExecutionUser:  # pylint: disable=too-few-public-methods
    """
    This is a container for information about the operating system
    executing the application.
    """

    slots = ("effective_uid", "effective_username", "real_uid", "real_username")

    def __init__(self, uid, euid):
        # This will be very OS dependent
        self.real_uid = uid
        self.effective_uid = euid
        self.real_username = pwd.getpwuid(self.real_uid)[0]
        self.effective_username = pwd.getpwuid(self.effective_uid)[0]

    def __repr__(self):
        res = (
            f"(uid:{self.real_uid},"
            f" uid_name:{self.real_username},"
            f" euid:{self.effective_uid},"
            f" euid_name:{self.effective_username})"
        )
        return res


class ExecutionEnvironment:  # pylint: disable=too-many-instance-attributes
    """
    This is a container for information about the
    program file / application being executed.
    """

    slots = (
        "debug",
        "error_ct",
        "execution_cwd",
        "execution_site",
        "execution_user",
        "main_module_name",
        "main_module_object",
        "main_module_package",
        "main_module_path",
        "platform",
        "package_parent_directory",
        "python_version",
    )

    def __init__(self):
        self.debug = 0  # mainly used for pytest
        self.error_ct = 0
        self.execution_cwd = os.getcwd()
        self.execution_user = ExecutionUser(os.getuid(), os.geteuid())
        try:
            self.execution_site = qdsite.QdSite()
        except:  # pylint: disable=bare-except
            # This non-specific except clause silently hides all sorts of
            # errors. This is necessary during bootstrapping because qdsite
            # or one of its imports may have errors that require XSynth for
            # correction. A bug in virtfile.py once stopped XSynth from running
            # but since virtfile.py is synthesised, that had to be handled
            # here to fix the problem. Maybe this should be conditional on
            # the state of the site.
            self.execution_site = None

        self.main_module_name = None  # file name of python module running
        self.main_module_object = None  # imported object of this module
        self.main_module_package = None  # package object containing this module
        self.main_module_path = None  # FQN path + file name of module
        self.package_parent_directory = None  # package parent directory
        if not self.check_platform(verbose=False):
            raise Exception("Unsupported operating system platform.")
        if not self.check_python_version(verbose=False):
            raise Exception("Unsupported Python version.")

    def set_run_name(self, run_name):
        """
        Set the __name__ of the main module being executed.
        """
        if self.debug > 0:
            print(f"exenv.set_run_name({run_name}).")
        if run_name == "__main__":
            #
            # We get here if the program was directly launched.
            # Normally this would only be used for a new site
            # but it might get called for a damaged site.
            #
            # When directly running, __import__() below returns the module,
            # not the package -- since we
            # didn't mention the package. This is not a problem at this time.
            # It might not be fixable until
            # after we create packagte symlinks, etc. Its possibly availabe in
            # module[__package__] but I
            # haven't explored that. Best not to dig any more deeply
            # into Python internals unless really
            # needed. Hopefully we can create the core configuration
            # and then start more neatly via the
            # program stub.
            #
            configuration_program_path = os.path.realpath(sys.argv[0])
            conf_prog_name = os.path.split(configuration_program_path)[1]
            if conf_prog_name[-3:] == ".py":
                self.main_module_name = conf_prog_name[:-3]
            else:
                self.print_error(
                    f'Program name {conf_prog_name} not in expected "module.py" format.'
                )
                return
            self.main_module_object = __import__(self.main_module_name)
            self.main_module_package = None
        else:
            #
            # This is how we normally get here, through the program stub and bafExeController.
            #
            run_name_split = run_name.split(".")  # import name (no .py)
            self.main_module_name = run_name_split[-1]
            self.main_module_package = __import__(run_name)
            self.main_module_object = getattr(
                self.main_module_package, self.main_module_name
            )
        #
        # We know what program was executed. Lets capture the actual run state.
        # This information can be used as the defaults for a new configuration file or to help
        # validate an existing configuration file that we open.
        #
        module_file_path = self.main_module_object.__file__
        self.main_module_path = os.path.realpath(module_file_path)
        module_package_path = os.path.dirname(self.main_module_path)
        self.package_parent_directory = os.path.dirname(module_package_path[:-1])

    def check_platform(self, verbose=True):
        """
        Check the operating system platform.
        """
        self.platform = sys.platform
        if verbose:
            print(f"Platform: {self.platform}.")
        return bool(self.platform in ALL_PLATFORMS)

    def check_python_version(self, verbose=True):
        """
        Check the python version being executed.
        """
        # This is both informational, when vervose, and diagnostic
        # Also check apache and operating system
        self.python_version = sys.version
        result = True
        if verbose:
            print(
                f"Python version {sys.version_info[0]}.{sys.version_info[1]} running."
            )
        if (sys.version_info[0] < PYTHON_MIN_MAJOR) or (
            sys.version_info[1] < PYTHON_MIN_MINOR
        ):
            # uses index of version_info instead of name for compatibility with Python v2
            print(f"Python version {PYTHON_MIN_VERSION} or later required.")
            result = False
        return result

    def print_error(self, msg, is_warning_only=False):
        """
        Print an error message.
        """
        if is_warning_only:
            msg_prefix = "Warning: "
        else:
            msg_prefix = "Error:   "
            self.error_ct += 1
        print(msg_prefix + msg)

    def print_warning(self, msg):
        """
        Print a warning message.
        """
        self.print_error(msg, is_warning_only=True)

    def print_status(self, msg):  # pylint: disable=no-self-use
        """
        Print an informational status message.
        """
        msg_prefix = "Status:  "
        print(msg_prefix + msg)

    def print_exception(self, exception_info, title, details):
        """
        Print details about an exception.
        """
        # There are a bunch of changes in Python 3.5 and 3.10
        # This probably doesn't work
        exception_type = exception_info[0]
        exception_value = exception_info[1]
        exception_traceback = exception_info[2]
        import_exception = traceback.format_exception(
            exception_type, exception_value, exception_traceback, limit=5
        )
        self.print_status("******************************")
        self.print_status(f"**** {title} EXCEPTION ****")
        self.print_status(details)
        for this_line in import_exception:
            self.print_status(this_line)
        self.print_status("******************************")

    def show(self):
        """
        Print information about the execution environment.
        """
        print("Platform:", self.platform)
        print("Python:", self.python_version)
        print("User:", self.execution_user)
        print("Site:", self.execution_site)


g = ExenvGlobals()
execution_env = ExecutionEnvironment()
