#
# configutils.py - Configuration Utilities
#
# This code was originally removed from configure.py because
# that module was getting too big.

import os
import pwd
import sys

def make_directory(dir_name):
    # This needs a security profile and handle chown and chmod
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)

#
# sys.platform recognized by commercenode
#
platform_darwin = 'darwin'
commercenode_dir = '/etc/commercenode'


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

execution_user = ExecutionUser(os.getuid(), os.geteuid())

class ExecutionEnvironment(object):
    slots = (
                    'error_ct', 'execution_cwd',
                    'main_module_name', 'main_module_object', 'main_module_package',
                    'main_module_path',
                    'package_parent_directory'
                )
    def __init__(self, run_name):
        self.error_ct = 0
        self.execution_cwd = None               # current working directory where run
        self.main_module_name = None            # file name of python module running
        self.main_module_object = None          # imported object of this module
        self.main_module_package = None         # package object containing this module
        self.main_module_path = None            # FQN path + file name of module
        self.package_parent_directory = None    # package parent directory
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
            wsMyModuleImportNameSplit = run_name.split('.')	# import name (no .py)
            self.main_module_name = wsMyModuleImportNameSplit[-1]
            self.main_module_package = __import__(wsMyModuleImportName)
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
        self.execution_cwd = os.getcwd()

    def check_version(self, verbose=True):
        # This is both informational, when vervose, and diagnostic
        # Also check apache and operating system
        result = True
        if verbose:
            print('Python version {}/{} running.'.format(sys.version_info[0], sys.version_info[1]))
        if (sys.version_info[0] < 3) or (sys.version_info[1] < 6):
            # uses index of version_info instead of name for compatibility with Python v2
            print('Python version 3.6 or later required')
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

if __name__ == "__main__":
    print(execution_user)
