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
import sys

from . import cli

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
def command_line_loc(menu):
    menu.add_item(cli.CliCommandLineParameterItem('l',
                  help="Location of conf file or database.",
                  value_type=cli.PARAMETER_STRING
                  ))

def command_line_no_conf(menu):
    menu.add_item(cli.CliCommandLineParameterItem('n',
                  default_value=False,
                  help="Stand-alone operation. No conf file or database.",
                  value_type=cli.PARAMETER_BOOLEAN
                  ))

def command_line_quiet(menu):
    menu.add_item(cli.CliCommandLineParameterItem('q',
                  default_value=False,
                  help="Display as few messages as possible.",
                  value_type=cli.PARAMETER_BOOLEAN
                  ))

def command_line_site(menu):
    menu.add_item(cli.CliCommandLineParameterItem('s',
                  help="Specify site to configure.",
                  value_type=cli.PARAMETER_STRING
                  ))

def command_line_verbose(menu):
    menu.add_item(cli.CliCommandLineParameterItem('v',
                  help="Display more detailed messages than minimally needed.",
                  value_type=cli.PARAMETER_BOOLEAN
                  ))

def command_line_website(menu):
    menu.add_item(cli.CliCommandLineParameterItem('w',
                  help="Specify website to configure.",
                  value_type=cli.PARAMETER_STRING
                  ))

def make_directory(dir_name):
    # This needs a security profile and handle chown and chmod
    if not os.path.exists(dir_name):
        try:
            os.mkdir(dir_name)
        except PermissionError:
            print('Permission denied creating directory {}.'.format(dir_name))
            return False
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

#
# MakeSymlink
#
# Errors may result in going from having a symlink to having none.
#
# If calling with a full path, set name part to None or ''
#
def MakeSymlink(
        parmSymlinkType,
        parmSymlinkDirectory,
        parmSymlinkName,
        parmTargetDirectory,
        parmTargetName):
    if (parmSymlinkName is None) or (parmSymlinkName == ''):
        wsSymlinkPath = os.path.join(parmSymlinkDirectory)
    else:
        wsSymlinkPath = os.path.join(parmSymlinkDirectory, parmSymlinkName)
    if (parmTargetName is None) or (parmTargetName == ''):
        wsTargetPath = os.path.join(parmTargetDirectory)
    else:
        wsTargetPath = os.path.join(parmTargetDirectory, parmTargetName)
    #
    # Make sure the target is valid before doing anything to any existing link
    #
    try:
        wsTargetStat = os.stat(wsTargetPath)
    except BaseException:
        wsTargetStat = None
    if wsTargetStat is None:
        PrintError('Symlink target %s does not exist' % (wsTargetPath))
        return False
    if os.path.islink(wsTargetPath):
        PrintError(
            'Symlink target %s is a symlink. Symlink not created.' %
            (wsTargetPath))
        return False
    if parmSymlinkType == SymlinkTypeDir:
        if not os.path.isdir(wsTargetPath):
            PrintError(
                'Symlink target %s is not a directory. Symlink not created.' %
                (wsTargetPath))
            return False
    elif parmSymlinkType == SymlinkTypeFile:
        if not os.path.isfile(wsTargetPath):
            PrintError(
                'Symlink target %s is not a file. Symlink not created.' %
                (wsTargetPath))
            return False
    else:
        PrintError('Symlink %s type code invalid. Symlink not created.' %
                   (wsSymlinkPath))
        return FALSE
    #
    # Deal with any existing link or file
    #
    if os.path.islink(wsSymlinkPath):
        try:
            os.remove(wsSymlinkPath)
        except BaseException:
            PrintError('Unable to remove existing symlink %s' %
                       (wsSymlinkPath))
            return False
    try:
        wsSymlinkStat = os.stat(wsSymlinkPath)
    except BaseException:
        wsSymlinkStat = None
    if not (wsSymlinkStat is None):
        PrintError(
            'File exists at symlink %s. It must be removed to continue' %
            (wsSymlinkPath))
        return False
    #
    # Make the symlink
    #
    try:
        os.symlink(wsTargetPath, wsSymlinkPath)
    except BaseException:
        PrintError('Unable to create symlink %s.' % (wsSymlinkPath))
        return False
    return True

def MakeSymlinkToFile(
        parmSymlinkDirectory,
        parmSymlinkName,
        parmTargetDirectory,
        parmTargetName):
    return MakeSymlink(
        SymlinkTypeFile,
        parmSymlinkDirectory,
        parmSymlinkName,
        parmTargetDirectory,
        parmTargetName)

def MakeSymlinkToDirectory(
        parmSymlinkDirectory,
        parmSymlinkName,
        parmTargetDirectory,
        parmTargetName):
    return MakeSymlink(
        SymlinkTypeDir,
        parmSymlinkDirectory,
        parmSymlinkName,
        parmTargetDirectory,
        parmTargetName)

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
                    'qddev_dir',
                    'main_module_name', 'main_module_object', 'main_module_package',
                    'main_module_path', 'platform',
                    'package_parent_directory', 'python_version'
                )
    def __init__(self):
        self.debug = 0                          # mainly used for pytest
        self.error_ct = 0
        self.qddev_dir = '/etc/qddev'
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

execution_env = ExecutionEnvironment()
