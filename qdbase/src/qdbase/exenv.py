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


from qdbase import cliargs
from qdbase import cliinput

# Configuration key constants for site.yaml
# These are used by both exenv (QdSite) and qdcore.qdrepos
CONF_SITE_DPATH = 'site.qdsite_dpath'
CONF_SITE_PREFIX = 'site.qdsite_prefix'
CONF_VENV_DPATH = 'site.venv_dpath'

from qdbase import qdos

try:
    from qdbase import qdconf
except (ModuleNotFoundError, ImportError):
    # Bootstrap mode - qdconf may not be available yet (requires pyyaml)
    qdconf = None

# Minimal QuickDev site structure constants
SITE_CONF_DIR_NAME = 'conf'
SITE_CONF_FILE_NAME = 'site.yaml'
SITE_REPOS_DIR_NAME = 'repos'
SITE_REPOS_DB_NAME = 'repos.db'
SITE_ENV_FILE_NAME = '.env'

CONF_ETC_ORG = "etc_org"

CONF_SUBDIRECTORIES = [CONF_ETC_ORG]

HDB_DEVSITES = "qdsites"
HDB_WEBSITES = "websites"

CONF_PARM_ACRONYM = "acronym"
CONF_PARM_UUID = "uuid"
CONF_PARM_HOST_NAME = "domain_name"
CONF_PARM_WEBSITE_SUBDIR = "website_subdir"
CONF_PARM_SITE_DPATH = "qdsite_dpath"
CONF_PARM_SITE_UDI = "site_udi"

VENV_ACTIVATE_SUB_FPATH = "bin/activate"


#
# Command line flags commonly used by QuickDev utilities.
# These functions help assure consistency.
#

ARG_D_DEBUG = "d"
ARG_L_CONF_LOC = "l"
ARG_N_NO_SITE = "n"
ARG_P_SITE_PREFIX = "p"
ARG_Q_QUIET = "q"
ARG_S_SITE_DPATH = "s"
ARG_V_VERBOSE = "v"
ARG_W_WEBSITE = "w"

SYMLINK_TYPE_DIR = "d"
SYMLINK_TYPE_FILE = "f"

OS_ENV_VIRTUAL_ENV = "VIRTUAL_ENV"

def identify_site(site=None):
    """
    Returns QdSite() object if a site can be identified using the site
    parameter or the current working directory.
    """
    if execution_env.execution_site is not None:
        if execution_env.execution_site.qdsite_valid:
            return execution_env.execution_site
        execution_env.execution_site.reload(qdsite_dpath=site)
        if execution_env.execution_site.qdsite_valid:
            return execution_env.execution_site
        return None
    return None  # we really shouldn't get here



def get_site_by_acronym(acronym):
    """
    Get a QdSite by its acronym/prefix.

    Note: This looks in the host's qdsites directory for a site configuration.
    """
    # Look for site configuration in host qdsites directory
    site_conf_dir = qdos.safe_join(g.qdhost_qdsites_dpath, acronym, 'conf')
    if site_conf_dir and os.path.isdir(site_conf_dir):
        conf = qdconf.QdConf(conf_dir=site_conf_dir)
        qdsite_dpath = os.path.dirname(site_conf_dir)
        return QdSite(qdsite_dpath=qdsite_dpath)
    return None


class QdSite:
    """
    QdSite is a container for core information regarding a site.

    QdSite only reflects existing information. It does not create
    site information or directories. Use QdStart to initialize
    or repair a site.

    A global instance is created within exenv.ExecutionEnvironment()
    which describes the site where the current program is executing,
    which could be an development site
    for QdDev itself or a host management site. Programs run from there
    may create additional instances for a site being configured.

    QdSite() is instanciated speculatively by exenv. We don't want to
    raise an exception here because failures can be caused just
    because we haven't yet pointed to the correct site directory.
    Problems are therefore flagged instead of raised.
    Check qdsite_valid and qdsite_errs for status.
    """

    __slots__ = (
        "conf_dpath",
        "host_site_data",
        "qdconf",
        "qdsite_errs",
        "qdsite_dpath",
        "qdsite_valid",
        "qdsite_dname",
        "qdsite_prefix",
    )

    def __init__(self, **argv):
        for this_slot in self.__slots__:
            setattr(self, this_slot, None)
        self.reload(**argv)

    def reload(self, **argv):
        for this_slot in self.__slots__:
            if this_slot == 'qdsite_dpath':
                continue
            setattr(self, this_slot, None)
        self.qdsite_errs = []

        if 'qdsite_dpath' in argv:
            self.qdsite_dpath = argv['qdsite_dpath']
        if self.qdsite_dpath is None:
            self.qdsite_dpath = os.getcwd()
        self.qdsite_dpath = os.path.abspath(self.qdsite_dpath)

        if not os.path.isdir(self.qdsite_dpath):
            self.qdsite_errs.append(f"Invalid qdsite path '{self.qdsite_dpath}'.")
            self.qdsite_valid = False
            return

        self.qdsite_dname = os.path.basename(self.qdsite_dpath)
        if self.qdsite_dname == "":
            self.qdsite_errs.append(
                f"Invalid qdsite directory name '{self.qdsite_dpath}'"
            )
            self.qdsite_valid = False
            return

        self.conf_dpath = os.path.join(self.qdsite_dpath, SITE_CONF_DIR_NAME)
        if not os.path.isdir(self.conf_dpath):
            self.qdsite_errs.append(f"Invalid qdsite conf path '{self.conf_dpath}'.")
            self.qdsite_valid = False
            return

        self.qdconf = qdconf.QdConf(conf_dir=self.conf_dpath)
        self.qdsite_prefix = self.qdconf.get(CONF_SITE_PREFIX, '')
        if self.qdsite_prefix == '':
            self.qdsite_errs.append(f"Invalid qdsite prefix '{self.qdsite_prefix}'.")
            self.qdsite_valid = False
            return

        self.qdsite_valid = True

    def __str__(self):
        if self.qdsite_valid:
            return f"SITE Valid {self.qdsite_dpath} prefix={self.qdsite_prefix}."
        else:
            return f"SITE Invalid {self.qdsite_errs}"

    @property
    def venv_dpath(self):
        """
        Return the path to the virtual environment directory.
        Uses <qdsite_prefix>.venv as the venv directory name.
        """
        if not self.qdsite_valid:
            return None
        return os.path.join(self.qdsite_dpath, f"{self.qdsite_prefix}.venv")

    def get_venv_activate_fpath(self):
        """
        This attempts to get the fpath to the VENV activate script.
        Uses <qdsite_prefix>.venv as the venv directory name.
        If the site hasn't been fully configured, it uses the current VENV
        if it finds one.
        """
        if self.venv_dpath and os.path.isdir(self.venv_dpath):
            return os.path.join(self.venv_dpath, VENV_ACTIVATE_SUB_FPATH)
        # Fallback to current VENV if site not fully configured
        venv_dpath = os.environ.get(OS_ENV_VIRTUAL_ENV, None)
        if venv_dpath is None:
            return None
        return os.path.join(venv_dpath, VENV_ACTIVATE_SUB_FPATH)


    def write_site_config(self):
        """
        Write site configuration to site.yaml.
        Creates conf directory if needed.
        """
        if qdconf is None:
            raise RuntimeError("Cannot write site config: qdconf module not available")

        if self.qdconf is None:
            self.qdconf = qdconf.QdConf(conf_dir=self.conf_dpath)

        self.qdconf[CONF_SITE_DPATH] = self.qdsite_dname
        self.qdconf[CONF_SITE_PREFIX] = self.qdsite_prefix
        self.qdconf.write_conf_file('site')

    @property
    def synthesis_db_path(self):
        return None



def check_venv(venv_dpath):  # pylint: disable=too-many-return-statements
    """
    Check if the specified venv_dpath is a (reasonably likely) virtual
    environment directory.

    Returns None if not a venv directory.
    Returns the Python version in the format "python3.7" if it is a venv.

    """
    if not os.path.isdir(venv_dpath):
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




#
# sys.platform recognized by qddev
#
PLATFORM_DARWIN = "darwin"
PLATFORM_LINUX = "linux"
ALL_PLATFORMS = [PLATFORM_DARWIN, PLATFORM_LINUX]

PYTHON_MIN_MAJOR = 3
PYTHON_MIN_MINOR = 6
PYTHON_MIN_VERSION = f"{PYTHON_MIN_MAJOR}.{PYTHON_MIN_MINOR}"

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



class ExecutionUser:  # pylint: disable=too-few-public-methods
    """
    This is a container for information about the operating system
    executing the application.
    """

    __slots__ = ("effective_uid", "effective_username", "real_uid", "real_username")

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

    __slots__ = (
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
            self.execution_site = QdSite()
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
            # after we create package symlinks, etc. It's possibly available in
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
        # This is both informational, when verbose, and diagnostic
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
qdsite_dpath = execution_env.execution_site.qdsite_dpath if execution_env.execution_site else None
