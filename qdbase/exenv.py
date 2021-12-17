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
"""

import os
import pwd
import shutil
import sys

import werkzeug

from . import cliargs

try:
    from qdcore import qdsite
except:
    # exenv must always be importable because it is used
    # by xsynth. qdsite capabiliites are not required.
    qdsite = None

#
# Command line flags commonly used by QuickDev utilities.
# These functions help assure consistency.
#

ARG_D_DEBUG = 'd'
ARG_L_CONF_LOC = 'l'
ARG_N_NO_SITE = 'n'
ARG_Q_QUIET = 'q'
ARG_S_SITE = 's'
ARG_V_VERBOSE = 'v'
ARG_W_WEBSITE = 'w'

SYMLINK_TYPE_DIR = 'd'
SYMLINK_TYPE_FILE = 'f'

def safe_join(*args):
    args = list(args)
    if len(args) > 1:
        if args[1][0] == '/':
            args[1] = args[1][1:]
    return werkzeug.utils.safe_join(*args)

class ExenvGlobals():
    def __init__(self):
        self.init()

    def init(self, root='/'):
        "This is separated so test can call with an alternate root."
        self.root = root
        self.qdhost_dpath = os.path.join(root, 'etc/qdhost')
        self.qdhost_websites_subdir = 'websites'
        self.qdhost_websites_dpath = os.path.join(self.qdhost_dpath, self.qdhost_websites_subdir)
        self.qdhost_devsites_subdir = 'devsites'
        self.qdhost_devsites_dpath = os.path.join(self.qdhost_dpath, self.qdhost_devsites_subdir)
        self.qdhost_all_subdirs = [self.qdhost_websites_subdir, self.qdhost_devsites_subdir]
        self.devsites_dpath = os.path.join(root, 'var/www')

return_code = 0

def command_line_debug(menu):
    item = cliargs.CliCommandLineParameterItem(ARG_D_DEBUG,
                  help="Location of conf file or database.",
                  value_type=cliargs.PARAMETER_STRING
                  )
    menu.add_item(item)
    return item

def command_line_loc(menu):
    item = cliargs.CliCommandLineParameterItem(ARG_L_CONF_LOC,
                  help="Location of conf file or database.",
                  value_type=cliargs.PARAMETER_INTEGER
                  )
    menu.add_item(item)
    return item

def command_line_no_conf(menu):
    item = cliargs.CliCommandLineParameterItem(ARG_N_NO_SITE,
                  default_value=False,
                  help="Stand-alone operation. No conf file or database.",
                  value_type=cliargs.PARAMETER_BOOLEAN
                  )
    menu.add_item(item)
    return item

def command_line_quiet(menu):
    item = cliargs.CliCommandLineParameterItem(ARG_Q_QUIET,
                  default_value=False,
                  help="Display as few messages as possible.",
                  value_type=cliargs.PARAMETER_BOOLEAN
                  )
    menu.add_item(item)
    return item

def command_line_site(menu):
    item = cliargs.CliCommandLineParameterItem(ARG_S_SITE,
                  help="Specify site to configure.",
                  value_type=cliargs.PARAMETER_STRING
                  )
    menu.add_item(item)
    return item

def command_line_verbose(menu):
    item = cliargs.CliCommandLineParameterItem(ARG_V_VERBOSE,
                  help="Display more detailed messages than minimally needed.",
                  value_type=cliargs.PARAMETER_BOOLEAN
                  )
    menu.add_item(item)
    return item

def command_line_website(menu):
    item = cliargs.CliCommandLineParameterItem(ARG_W_WEBSITE,
                  help="Specify website to configure.",
                  value_type=cliargs.PARAMETER_STRING
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
    elif error_func is not None:
        error_func(msg)
    elif error_print:
        print(msg)

def make_directory(name, path, force=False, mode=511, quiet=False,
                    error_func=None, error_print=True, raise_ex=False):
    """
    Create a directory if it doesn't exist.

    The default mode 511 is the default of os.mkdir. It is specified here
    because os.mkdir doesn't accept None.

    force was added for pytest but could be useful in other cases.
    """

    global return_code
    return_code = 0
    if os.path.exists(path):
        if not os.path.isdir(path):
            err_msg = "'{}' is not a directory.".format(path)
            handle_error(err_msg, error_func, error_print, raise_ex)
            return_code = 101
            return False
    else:
        if force or cliargs.cli_input_yn("Create directory '{}'?".format(path)):
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
        print("{} directory: {}.".format(name, path))
    return True

#
# sys.platform recognized by qddev
#
PLATFORM_DARWIN = 'darwin'
PLATFORM_LINUX = 'linux'
ALL_PLATFORMS = [PLATFORM_DARWIN, PLATFORM_LINUX]

PYTHON_MIN_MAJOR = 3
PYTHON_MIN_MINOR = 6
PYTHON_MIN_VERSION = "{}.{}".format(PYTHON_MIN_MAJOR, PYTHON_MIN_MINOR)

# Check python version before imports because excepton classes
# have changed.

def save_org(source_path):
    """
    Save a system configuration file before making changes.
    """
    source_directory, source_filename = os.path.split(source_path)
    org_file_path = os.path.join(source_directory, source_filename+'.org')
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
        error_func=None):
    if (target_name is None) or (target_name == ''):
        target_path = os.path.join(target_directory)
        target_name = os.path.basename(target_path)
    else:
        target_path = os.path.join(target_directory, target_name)
    if (link_directory is None) or (link_directory == ''):
        link_directory = os.getcwd()
    if (link_name is None) or (link_name == ''):
        link_name = target_name
    link_path = os.path.join(link_directory, link_name)
    #
    # Make sure the link is valid before doing anything to any existing link
    #
    try:
        target_stat = os.stat(target_path)
    except BaseException:
        target_stat = None
    if target_stat is None:
        if error_func is not None:
            error_func("Symlink target '{}' does not exist".format(target_path))
        return False
    if os.path.islink(target_path):
        if error_func is not None:
            error_func(
                "Symlink target '{}' is a symlink. Symlink not created.".format(target_path))
        return False
    if target_type == SYMLINK_TYPE_DIR:
        if not os.path.isdir(target_path):
            if error_func is not None:
                error_func(
                    "Symlink target '{}' is not a directory. Symlink not created.".format(target_path))
            return False
    elif target_type == SYMLINK_TYPE_FILE:
        if not os.path.isfile(target_path):
            if error_func is not None:
                error_func(
                    "Symlink target '{}' is not a file. Symlink not created.".format(target_path))
            return False
    else:
        if error_func is not None:
            error_func(
                "Symlink '{}' type code invalid. Symlink not created.".format(target_path))
        return False
    #
    # Deal with any existing link or file
    #
    if os.path.islink(link_path):
        try:
            os.remove(link_path)
        except BaseException:
            if error_func is not None:
                error_func(
                    "Unable to remove existing symlink '{}'.".format(link_path))
            return False
    try:
        link_stat = os.stat(link_path)
    except BaseException:
        link_stat = None
    if not (link_stat is None):
        if error_func is not None:
            error_func(
                "File exists at symlink '{}'. It must be removed to continue.".format(link_path))
        return False
    #
    # Make the symlink
    #
    try:
        os.symlink(target_path, link_path)
    except BaseException:
        if error_func is not None:
            error_func(
                "Unable to create symlink '{}'.".format(target_path))
        return False
    return True

def make_symlink_to_file(
        target_directory,
        target_name=None,
        link_directory=None,
        link_name=None,
        error_func=None):
    return make_symlink(
        SYMLINK_TYPE_FILE,
        target_directory,
        target_name,
        link_directory,
        link_name,
        error_func=error_func)

def make_symlink_to_directory(
        target_directory,
        target_name=None,
        link_directory=None,
        link_name=None,
        error_func=None):
    return make_symlink(
        SYMLINK_TYPE_DIR,
        target_directory,
        target_name,
        link_directory,
        link_name,
        error_func=error_func)

class ExecutionUser(object):
    slots = ('effective_uid', 'effective_username', 'real_uid', 'real_username')
    def __init__(self, uid, euid):
        # This will be very OS dependent
        self.real_uid = uid
        self.effective_uid = euid
        self.real_username = pwd.getpwuid(self.real_uid)[0]
        self.effective_username = pwd.getpwuid(self.effective_uid)[0]

    def __repr__(self):
        res = "(uid:{}, uid_name:{}, euid:{}, euid_name:{})".format(
			self.real_uid, self.real_username, self.effective_uid, self.effective_username)
        return res

class ExecutionEnvironment():
    slots = (
                    'debug', 'error_ct',
                    'execution_cwd', 'execution_site', 'execution_user',
                    'main_module_name', 'main_module_object', 'main_module_package',
                    'main_module_path', 'platform',
                    'package_parent_directory', 'python_version'
                )
    def __init__(self):
        self.debug = 0                          # mainly used for pytest
        self.error_ct = 0
        self.execution_cwd = os.getcwd()
        self.execution_user = ExecutionUser(os.getuid(), os.geteuid())
        try:
            self.execution_site = qdsite.QdSite()
        except:
            """
            This non-specific except clause silently hides all sorts of
            errors. This is necessary during bootstrapping because qdsite
            or one of its imports may have errors that require XSynth for
            correction. A bug in virtfile.py once stopped XSynth from running
            but since virtfile.py is synthesised, that had to be handled
            here to fix the problem. Maybe this should be conditional on
            the state of the site.
            """
            self.execution_site = None

        self.main_module_name = None            # file name of python module running
        self.main_module_object = None          # imported object of this module
        self.main_module_package = None         # package object containing this module
        self.main_module_path = None            # FQN path + file name of module
        self.package_parent_directory = None    # package parent directory
        if not self.check_platform(verbose=False):
            raise Exception('Unsupported operating system platform.')
        if not self.check_python_version(verbose=False):
            raise Exception('Unsupported Python version.')

    def set_run_name(self, run_name):
        if self.debug > 0:
            print("exenv.set_run_name({}).".format(run_name))
        if run_name == "__main__":

            #
            # We get here if the program was directly launched. Normally this would only be used for a new site
            # but it might get called for a damaged site.
            #
            # When directly running, __import__() below returns the module, not the package -- since we
            # didn't mention the package. This is not a problem at this time. It might not be fixable until
            # after we create packagte symlinks, etc. Its possibly availabe in module[__package__] but I
            # haven't explored that. Best not to dig any more deeply into Python internals unless really
            # needed. Hopefully we can create the core configuration and then start more neatly via the
            # program stub.
            #
            wsConfigurationProgramPath = os.path.realpath(sys.argv[0])
            (wsBfslibPath, wsConfProgName) = os.path.split(
                wsConfigurationProgramPath)
            if wsConfProgName[-3:] == '.py':
                self.main_module_name = wsConfProgName[:-3]
            else:
                PrintError(
                    'Program name %s not in expected "module.py" format.' % (wsConfProgName))
                return
            self.main_module_object = __import__(self.main_module_name)
            self.main_module_package = None
        else:
            #
            # This is how we normally get here, through the program stub and bafExeController.
            #
            run_name_split = run_name.split('.')	# import name (no .py)
            self.main_module_name = run_name_split[-1]
            self.main_module_package = __import__(run_name)
            self.main_module_object = getattr(
                self.main_module_package, self.main_module_name)
        #
        # We know what program was executed. Lets capture the actual run state.
        # This information can be used as the defaults for a new configuration file or to help
        # validate an existing configuration file that we open.
        #
        wsModuleFilePath = self.main_module_object.__file__
        self.main_module_path = os.path.realpath(wsModuleFilePath)
        wsModulePackagePath = os.path.dirname(self.main_module_path)
        self.package_parent_directory = os.path.dirname(wsModulePackagePath[:-1])

    def check_platform(self, verbose=True):
        self.platform = sys.platform
        if verbose:
            print('Platform: {}.'.format(self.platform))
        if self.platform in ALL_PLATFORMS:
            return True
        else:
            return False

    def check_python_version(self, verbose=True):
        # This is both informational, when vervose, and diagnostic
        # Also check apache and operating system
        self.python_version = sys.version
        result = True
        if verbose:
            print('Python version {}.{} running.'.format(sys.version_info[0], sys.version_info[1]))
        if (sys.version_info[0] < PYTHON_MIN_MAJOR) or (sys.version_info[1] < PYTHON_MIN_MINOR):
            # uses index of version_info instead of name for compatibility with Python v2
            print('Python version {} or later required.'.format(PYTHON_MIN_VERSION))
            result = False
        return result

    def PrintError(self, parmMessage, IsWarningOnly=False):
        if IsWarningOnly:
            wsMsgPrefix = "Warning: "
        else:
            wsMsgPrefix = "Error:   "
            self.error_ct += 1
        print(wsMsgPrefix + parmMessage)


    def PrintWarning(self, parmMessage):
        PrintError(parmMessage, IsWarningOnly=True)

    def PrintStatus(self, parmMessage):
        wsMsgPrefix = "Status:  "
        print(wsMsgPrefix + parmMessage)

    def PrintException(self, parmException, parmTitle, parmInfo):
        wsExceptionType = parmException[0]
        wsExceptionValue = parmException[1]
        wsExceptionTraceback = parmException[2]
        wsImportException = traceback.format_exception(wsExceptionType, wsExceptionValue,
                                                       wsExceptionTraceback, 5)
        PrintStatus("******************************")
        PrintStatus("**** %10s EXCEPTION ****" % (parmTitle))
        PrintStatus(parmInfo)
        for wsThisLine in wsImportException:
            PrintStatus(wsThisLine)
        PrintStatus("******************************")

    def show(self):
        print('Platform:', self.platform)
        print('Python:', self.python_version)
        print('User:', self.execution_user)
        print('Site:', self.execution_site)

g = ExenvGlobals()
execution_env = ExecutionEnvironment()
