#!/usr/bin/python
#############################################
#
#  bfsConfigure Module
#
#
#  FEATURES
#
#  Configures BFS run-time environment
#
#
#  WARNINGS
#
#
#  Copyright (C) 2009 by Albert B. Margolis - All Rights Reserved
#
#  08/09/2009: Start development
#  15 Aug 2009: Begin BFS V2.
# 		- Combine bfsConfigureBootstrap.py instead of two programs
#  03 Jun 2012: Rename bfsConfigure to bzConfigure and being to remove any specificity
# 			to BFS. All application specific details should
# 			come from other sources.
#
#
# This is a configuration program for all applications using the Biznode Application Framework (BAF).
#
# It mainly creates directories and makes links so the application can begin running and configure
# its own operations.
#
#
# TODO - LONGER TERM
#
# Need to clean up initial imports so error messages are displayed. Right now its hard to tell what went wrong.
#
# Create a resource container object. These can be added to bafConfigure so it needs less specific code for
# adding resouces. Hopefully it will make it easier to add resource classes and handle consistently.
#
# Need a check in MakePathInfo to make sure that there are no duplicate variable names. This will be even
# easer with the new resource object. MakePathInfo will just scan for the resouce collections and it will
# have properties need to finish PathInfo (like comment, name suffixes)
#
# While doing above, hopefully make DefineBaf() and DefineApp() clearer
#
# ResolveResource() should assign the pathInfo variable name.
#

import traceback
import sys
import stat
import os
import imp

import cliargs
import cliinput
import configutils

ConfigNoDependencies = 9


"""

*** comment out original code

#
# The following imports should never fail, they are critical for
# site bootstraping. That means they should have no site dependencies
# because the site does not exist at the start of the bootstrap process.
#
# They also need to be non-dependant on bafExeController or to
# at least live with the minimal set of substitute features
# probided by bafConfiguration.
#
from . import bafDataStore
from . import bafErTypes
from . import bafExpCodeWriter
from . import bafNv
from . import bafObject
from . import bafRdbms
from . import bafTupleDictionary

from . import bzCodeWriter
from . import bzDataEdit
from . import bzErrors
from . import bzTextFile
from . import bzUtil
from . import bafSerializer

StartupUnknown = 0
StartupStub = 3
StartupDirect = 4
StartupMode = StartupUnknown

#
# When creating or repairing a site this module bzConfigure may be run directly
# without the normal bafExeController / bafActionDef environment and without
# configuration files or application directory symlinks. The following code
# identifies this module enough to allow the configuration system to
# bootstrrap the site.
#


def bafConfigureModule(parmModuleResource):
    wsProgramObject = bafSiteExecutableResource(parmModuleResource, 'config')
    parmModuleResource.configuration.AddExecutable(wsProgramObject)


#
#
# This set of bfs imports need to be changed to a more general structure.
# bz should not have any applications specific code.
#
ImportException = None
try:
    # Almost all modules are dependent on bafExeController, so we try that separately and skip
    # a bunch of useless import attempts if it fails.
    #
    from . import bafExeController
except:
    bafExeController = None
    (wsExceptionType, wsExceptionValue, wsExceptionTraceback) = sys.exc_info()
    ImportException = traceback.format_exception(wsExceptionType, wsExceptionValue,
                                                 wsExceptionTraceback, 5)

if ImportException is not None:
    print("**** IMPORT EXCEPTION ****")
    for wsThisLine in ImportException:
        print(wsThisLine)
    print("**************************")


ParameterModule = 'Module'
try:
    #import sitelib.pathInfo as pathInfo
    import pathInfo
except:
    sitelib = None
    pathInfo = None

if bafExeController is not None:
    class PhaseOne(bafExeController.bafActionDef):
        def __init__(self, parmExeController):
            super(PhaseOne, self).__init__(
                parmDescription="Configure System", ExeController=parmExeController)
            self.SetDefaultCommandCodes(Selector='All', Switch='a')

        def Run(self):
            Main(ExeController=self)

    #
    # LocalAction() is a special class name that is recognized to not be an application action
    #
    class LocalAction(bafExeController.bafActionDef):
        def __init__(self, parmDescription, ExeController=None):
            super(LocalAction, self).__init__(
                parmDescriptioni=parmDescription, ExeController=ExeController)
            self.configuration = None

        def PrepareRun(self):
            self.configuration = bafConfiguration(
                ExeController=self.exeController)
            self.configuration.LoadCurrentConfiguration()
            if ConfigErrorCt > 0:
                PrintStatus('**** Config Unhappy.')
            # self.configuration.GetPackageList()
            self.aContext.AddOutlineItem(Title=self.description)

    class GeneratePathInfo(LocalAction):
        def __init__(self, parmExeController):
            super(GeneratePathInfo, self).__init__(
                "Generate PathInfo", ExeController=parmExeController)
            self.SetDefaultCommandCodes(Selector='PathIno', Switch='p')

        def Run(self):
            self.PrepareRun()
            MakePathInfo(self.configuration)
            print('DONE')

    class DatabaseManagement(bafExeController.bafActionDef):
        def __init__(self, parmExeController):
            super(DatabaseManagement, self).__init__(
                "Manage Site Databases", ExeController=parmExeController)
            self.SetDefaultCommandCodes(Switch='d')
            self.actionRequestTDict.DefinePositionalParameter('TableRefname')

        def Run(self):
            print("***", self.exeController.cgiGetDataRaw)
            print("***", self.exeController.cgiPostDataRaw)
            wsTableRefname = self.actionRequestTuple['TableRefname']
            print("TABLE:", wsTableRefname)
            wsDbTableInfo = self.exeController.GetDbTableInfo(wsTableRefname)
            if wsDbTableInfo is None:
                print("TABLE NOT DEFINED")
                return
            wsDbTableClassRefname = wsDbTableInfo['ModelClassRefname']
            wsTableDefinitionTDict = self.exeController.GetTDictByClassRefname(
                wsDbTableClassRefname)
            wsTable = self.exeController.OpenDbTable(wsTableRefname)
            if wsTable is not None:
                print("TABLE OPENED")
                wsTableDefinitionTDict.CompareTDict(wsTable.rdbmsTDict)
                return
            wsDbRefname = wsDbTableInfo['DbRefname']
            wsDb = self.exeController.OpenDb(wsDbRefname)
            wsDbTable = wsDb.CreateTable(
                wsTableDefinitionTDict, wsDbTableInfo['TableName'])
            print(wsDbTable._lastQuery)
            print(wsDbTable._lastErrorMsg)

TestImportProgName = 'testimport'
HelpProgName = 'help'

CoreExeControllerModuleName = 'bafExeController'
CoreExeControllerClassName = 'bafExeController'
CoreExeControllerRunMethodName = 'StartMain'
CoreTransitionalRunFunctionName = 'Main'
CoreBzUtilModuleName = 'bzUtil'
CoreRunDefaultCommandRefname = 'defaultCommandRefname'
CoreRunIsCgiYN = 'programIsCgiYN'
CoreRunIsSslYN = 'programIsSslYN'
CoreRunIsSecureSiteYN = 'programIsSecureSiteYN'
CoreRunRequireAdminLoginYN = 'programRequireAdminLoginYN'
CoreRunProgramName = 'executableFileName'
CoreRunCommandsCgi = 'executableCommandsCgi'
CoreRunCommandSwitchesCli = 'executableCommandSwitchesCli'
CoreAppConfigureModuleName = 'ConfigureApp'
CoreAppDefineCoreFunctionName = 'DefineAppCore'
CoreAppDefineFeaturesFunctionName = 'DefineAppFeatures'
SelfTestCommandFunc = 'SelfTest'

PackageInitModuleName = '__init__.py'
MakeTDictPrefix = 'MakeClassTDict_For_'
MakeTDictPrefixLen = len(MakeTDictPrefix)

SiteControlsImportName = 'siteControls'
SiteControlsModuleName = SiteControlsImportName + '.py'
SiteControlsModuleNameC = SiteControlsImportName + '.pyc'

BafSourceDirectoryRefname = 'BafSourceDirectory'
BafSourceDirectoryTitle = 'BAF Source Directory Path'
BafLibDirectoryRefname = 'BafLib'
BafLibDirectoryPurpose = 'BAF Python language library'
BafLibDirectoryName = 'pylib'
#
SiteRunDirectoryRefname = 'SiteRun'
SiteRunDirectoryTitle = 'Site Run Directory Path'
SiteSourceDirectoryRefname = 'SiteSource'
SiteSourceDirectoryTitle = 'Site Source DirectoryPath'
SiteConfDirectoryRefname = 'SiteConfDirectory'
SiteConfDirectoryPurpose = 'Configuration details of site'
SiteConfDirectoryName = 'conf'
SiteSynthesisDirectoryRefname = 'Synthesis'
SiteLibDirectoryRefname = 'Sitelib'
SiteLibDirectoryPurpose = 'Site Python Customization Modules'
SiteLibDirectoryName = 'sitelib'
SiteSynthesisDirectoryPurpose = 'Synthesised site details'
SiteSynthesisDirectoryName = 'synthesis'
SiteProgDirectoryRefname = 'PROG'
SiteProgDirectoryPurpose = 'Command program stubs of site'
SiteProgDirectoryName = 'prog'
SiteCgiDirectoryRefname = 'CGI'
SiteCgiDirectoryPurpose = 'CGI program stubs of site'
SiteCgiDirectoryName = 'cgi'
SiteCgiApacheName = 'cgi'
SiteMProgDirectoryRefname = 'Progm'
SiteMProgDirectoryPurpose = 'Model Description Modules Directory (generated modules)'
SiteMProgDirectoryName = 'progm'
SiteMCgiDirectoryRefname = 'Cgim'
SiteMCgiDirectoryPurpose = 'Model Generated CGI programs (generated, ?deprecated?)'
SiteMCgiDirectoryName = 'cgim'
SiteMCgiApacheName = 'cgim'
#
AppsIniFileRefname = 'AppsIni'
AppsIniFilePurpose = 'Identifes the apps used by this site.'
AppsIniFileName = 'apps.ini'
#
BootIniFileRefname = 'BootIni'
BootIniFilePurpose = 'Holds the minimum information need to bootstrap BAF program program.'
BootIniFileName = 'boot.ini'
#
SiteCodesPyRefname = 'SiteCodes'
SiteCodesPyPurpose = 'Python enumerations.'
SiteCodesPyFileName = 'siteCodes.py'
#
SiteControlsPyRefname = 'SiteControls'
SiteControlsPyPurpose = 'Python application controls.'
SiteControlsPyFileName = 'siteControls.py'
#
SiteFormatsPyRefname = 'SiteFormats'
SiteFormatsPyPurpose = 'Python application formats.'
SiteFormatsPyFileName = 'siteFormats.py'
#
SiteActionsPyRefname = 'SiteActions'
SiteActionsPyPurpose = 'Python application formats.'
SiteActionsPyFileName = 'siteActions.py'
#
SitePathInfoPyFileRefname = 'PathInfo'
SitePathInfoPyFilePurpose = 'Synthesized python file defining directories and files, etc for site.'
SitePathInfoPyFileName = 'pathInfo.py'
#
SiteWebInfoPyFileRefname = 'WebInfo'
SiteWebInfoPyFilePurpose = 'Synthesized python file defining databases, tables and data models for site.'
SiteWebInfoPyFileName = 'webInfo.py'
#
SiteTestImportPyFileRefname = 'TestImport'
SiteTestImportPyFilePurpose = 'Generated python program that imports all modules as a quick error check.'
SiteTestImportPyFileName = 'testimport'
#
SiteHelpPyFileRefname = 'Help'
SiteHelpPyFilePurpose = 'Generated python program that displays command line help.'
SiteHelpPyFileName = 'help'


def DefineBafCore(parmConfiguration):
    #
    # The following configuration details are required for all BAF applications and sites.
    # To the degree they are configurable, the informations comes from the BAF configuration
    # file created by this program.
    #
    wsBootIniVariable = parmConfiguration.AddBootIniVariable(BafSourceDirectoryRefname,
                                                             Prompt=BafSourceDirectoryTitle)
    wsBootIniVariable.ConfigureAsDirectoryPath()
    wsBafSourceDir = parmConfiguration.AddDirectory(BafSourceDirectoryRefname, BafSourceDirectoryTitle,
                                                    BootIniVariableName=BafSourceDirectoryRefname)
    wsBafSourceDir.ConfigureAsBafSource()
    #
    wsDir = wsBafSourceDir.AddSubDirectory(BafLibDirectoryRefname,
                                           BafLibDirectoryPurpose,
                                           DirName=BafLibDirectoryName)
    wsDir.ConfigureAsBafLib()
    #
    # Site Run Directory + BAF core subdirectories
    #
    wsBootIniVariable = parmConfiguration.AddBootIniVariable(SiteRunDirectoryRefname,
                                                             Prompt=SiteRunDirectoryTitle,
                                                             Hint='Usually WWW root path')
    wsBootIniVariable.ConfigureAsDirectoryPath()
    wsSiteRunDir = parmConfiguration.AddDirectory(SiteRunDirectoryRefname, SiteRunDirectoryTitle,
                                                  BootIniVariableName=SiteRunDirectoryRefname)
    wsSiteRunDir.ConfigureAsSiteRun()
    wsDir = wsSiteRunDir.AddSubDirectory(SiteProgDirectoryRefname,
                                         SiteProgDirectoryPurpose,
                                         DirName=SiteProgDirectoryName)
    wsDir.ConfigureAsSiteProg()
    wsFile = wsDir.AddFileResource(SiteTestImportPyFileRefname,
                                   SiteTestImportPyFilePurpose,
                                   FileName=SiteTestImportPyFileName)
    wsFile.ConfigureAsTestImportPy()
    wsFile = wsDir.AddFileResource(SiteHelpPyFileRefname,
                                   SiteHelpPyFilePurpose,
                                   FileName=SiteHelpPyFileName)
    wsFile.ConfigureAsHelpPy()
    #
    wsDir = wsSiteRunDir.AddSubDirectory(SiteCgiDirectoryRefname,
                                         SiteCgiDirectoryPurpose,
                                         DirName=SiteCgiDirectoryName)
    wsDir.ConfigureAsSiteCgi(SiteCgiApacheName)
    #
    wsDir = wsSiteRunDir.AddSubDirectory(SiteMProgDirectoryRefname,
                                         SiteMProgDirectoryPurpose,
                                         DirName=SiteMProgDirectoryName)
    wsDir.ConfigureAsSiteMProg()
    #
    wsDir = wsSiteRunDir.AddSubDirectory(SiteMCgiDirectoryRefname,
                                         SiteMCgiDirectoryPurpose,
                                         DirName=SiteMCgiDirectoryName)
    wsDir.ConfigureAsSiteMCgi(SiteMCgiApacheName)
    ##############
    #
    # Synthesis Directory
    #
    ##############
    #
    wsDir = wsSiteRunDir.AddSubDirectory(SiteSynthesisDirectoryRefname,
                                         SiteSynthesisDirectoryPurpose,
                                         DirName=SiteSynthesisDirectoryName)
    wsDir.ConfigureAsSiteSynthesis()
    #
    wsFile = wsDir.AddFileResource(SitePathInfoPyFileRefname,
                                   SitePathInfoPyFilePurpose,
                                   FileName=SitePathInfoPyFileName)
    wsFile.AssignGenerator(GeneratePathInfoFile)
    wsFile.ConfigureAsXxxInfoPy('sitePathInfoPyFile')
    #
    #
    wsFile = wsDir.AddFileResource(SiteWebInfoPyFileRefname,
                                   SiteWebInfoPyFilePurpose,
                                   FileName=SiteWebInfoPyFileName)
    wsFile.AssignGenerator(GenerateWebInfoFile)
    wsFile.ConfigureAsXxxInfoPy('siteWebInfoPyFile')
    ##############
    #
    # Sessions
    #
    ##############
    #
    if bafExeController is not None:
        # We can't create databases until we have a certain level of the site configured
        # in order to know how the site want to handle sessions and where to locate
        # the necessary classes.
        #
        wsDir = wsSiteRunDir.AddSubDirectory(
            'Sessions', 'Sessions', DirName='sessions')
        wsFile = wsDir.AddFileResource('SessionsDb', 'Sessions cooie database',
                                       FileName='sessions.db')
        wsDbResource = bafDatabaseResource(Configuration=parmConfiguration,
                                           Refname='SessionsDb',
                                           PathResource=wsFile,
                                           DbType=bafRdbms.DbTypeSqLite)
        wsDbResource.AddDbTable('sessions', ModelClassRefname='bafExeSession')
        parmConfiguration.AddDatabaseResource(wsDbResource)
    ##############
    #
    # Site Source Directory + BAF core subdirectories
    #
    ##############
    #
    wsBootIniVariable = parmConfiguration.AddBootIniVariable(SiteSourceDirectoryRefname,
                                                             Prompt=SiteSourceDirectoryTitle)
    wsBootIniVariable.ConfigureAsDirectoryPath()
    wsSiteSourceDir = parmConfiguration.AddDirectory(SiteSourceDirectoryRefname, SiteSourceDirectoryTitle,
                                                     BootIniVariableName=SiteSourceDirectoryRefname)
    wsSiteSourceDir.ConfigureAsSiteSource()
    #
    wsDir = wsSiteSourceDir.AddSubDirectory(SiteConfDirectoryRefname,
                                            SiteConfDirectoryPurpose,
                                            DirName=SiteConfDirectoryName)
    wsDir.ConfigureAsSiteConfDirectory()

    wsFile = wsDir.AddFileResource(BootIniFileRefname,
                                   BootIniFilePurpose,
                                   FileName=BootIniFileName)
    wsFile.ConfigureAsBootIniFile()

    wsFile = wsDir.AddFileResource(AppsIniFileRefname,
                                   AppsIniFilePurpose,
                                   FileName=AppsIniFileName)
    wsFile.ConfigureAsAppsIniFile()
    #
    wsDir = wsSiteSourceDir.AddSubDirectory(SiteLibDirectoryRefname,
                                            SiteLibDirectoryPurpose,
                                            DirName=SiteLibDirectoryName)
    wsDir.ConfigureAsPythonPackage()
    wsFile = wsDir.AddFileResource(SiteCodesPyRefname,
                                   SiteCodesPyPurpose,
                                   FileName=SiteCodesPyFileName)
    wsFile.ConfigureAsPythonModule(IsAutoCreate=True)
    #
    wsFile = wsDir.AddFileResource(SiteControlsPyRefname,
                                   SiteControlsPyPurpose,
                                   FileName=SiteControlsPyFileName)
    wsFile.ConfigureAsPythonModule(IsAutoCreate=True)
    #
    wsFile = wsDir.AddFileResource(SiteFormatsPyRefname,
                                   SiteFormatsPyPurpose,
                                   FileName=SiteFormatsPyFileName)
    wsFile.ConfigureAsPythonModule(IsAutoCreate=True)
    #
    wsFile = wsDir.AddFileResource(SiteActionsPyRefname,
                                   SiteActionsPyPurpose,
                                   FileName=SiteActionsPyFileName)
    wsFile.ConfigureAsPythonModule(IsAutoCreate=True)
    wsFile.AssignGenerator(GenerateSiteActionsFile)

#
# Define SiteDefinition DB
#


def MakeClassTDict_For_bafSiteModules(ExeController=None, InstanceClassName=None):
    wsTDict = bafTupleDictionary.bafTupleDictionary(
        Name='SiteModules',
        InstanceClassName=InstanceClassName,
        PrimaryDataPhysicalType=bafErTypes.Core_ObjectTypeCode,
        ExeController=ExeController)

    wsTDict.AddUdiElement()
    wsTDict.AddScalarElement('Name')
    wsTDict.CompleteDictionary()
    return wsTDict


def MakeSiteDefinintionDb(ExeController=None):
    wsModulesTDict = MakeClassTDict_For_bafSiteModules(
        ExeController=ExeController)
    wsDbPath = 'bfs.db'
    if os.path.isfile(wsDbPath):
        os.unlink(wsDbPath)
    wsDb = bafRdbms.bafRdbmsSqLite(Path=wsDbPath, ExeController=ExeController)
    wsDb.CreateTable(TDict=wsModulesTDict)


#
# Confiure Site
#
ConfigErrorCt = 0



#
# bafSiteCommandResource identifies a particular execution path for a site.
#
# It identifies a bafActionDef and optionally a trigger and preset data to execute.
# This allows actions to be somewhat generic while exposing commands that are more specific.
# The command override data is inserted by bafExeController just prior to bafAction
# execution. For web transactions this happens server side so there is no way for hostile
# remote clients to interfere with the overrides.
#
# It also identified a particular site site executable and switch / function code
# to initiate the action. The site executable is an operating system file and
# often a URI target.
#
#


class bafSiteCommandResource:
    def __init__(self, ActionResourceObject, SiteExecutableResourceObject,
                 CommandRefname=None, CommandSelector=None, CommandSwitch=None):
        # need a check that at least one of Func or Switch is provided
        self.actionResourceObject = ActionResourceObject
        self.commandRefname = CommandRefname
        self.selector = CommandSelector  # as actually used for this program
        self.switch = CommandSwitch		# as actually used for this program
        self.overrideData = {}
        self.overrideTrigger = None
        self.siteExecutableResourceObject = SiteExecutableResourceObject

    def ResolveResource(self):
        wsConfiguration = self.siteExecutableResourceObject.configuration
        if self.selector is None:
            self.selector = self.actionResourceObject.actionExeObject.defaultCommandSelector
        if self.switch is None:
            self.switch = self.actionResourceObject.actionExeObject.defaultCommandSwitch
        if (self.selector is None) and (self.switch is None):
            PrintError('No Selector or Switch specified for Command Name "%s" / "%s" in executable %s' % (
                self.actionResourceObject.actionClassName,
                self.commandRefname,
                self.siteExecutableResourceObject.executableFileName))
        if self.commandRefname is None:
            self.commandRefname = self.actionResourceObject.actionExeObject.defaultCommandRefname
        if self.commandRefname is None:
            # Maybe add a prefix for generics like add / del/ post, etc. RESTful
            wsDefaultCommandSelector = self.actionResourceObject.actionExeObject.defaultCommandSelector
            if not (bzUtil.Upper(wsDefaultCommandSelector) in ['ALL', 'ADD', 'DEL', 'DELETE', 'POST']):
                self.commandRefname = wsDefaultCommandSelector
        if (self.commandRefname is None) and (self.switch is not None):
            self.commandRefname = self.siteExecutableResourceObject.executableRefname + '_' + self.switch
        if self.commandRefname is None:
            # The above is pretty reasonable. This is probably an error, but other things break if there is no name.
            self.commandRefname = self.actionResourceObject.actionClassName
        if self.commandRefname in wsConfiguration.commandsByCommandRefname:
            # Command names must be globally unique (by site)
            wsFirstCommandResourceObject = wsConfiguration.commandsByCommandRefname[
                self.commandRefname]
            wsFirstExecutableResourceObject = wsFirstCommandResourceObject.siteExecutableResourceObject
            PrintError('Duplicate Command Name "%s" in executables %s and %s' % (
                self.commandRefname,
                self.siteExecutableResourceObject.executableFileName,
                wsFirstExecutableResourceObject.executableFileName))
        wsConfiguration.commandsByCommandRefname[self.commandRefname] = self
        if self.siteExecutableResourceObject.defaultCommandRefname == '':
            self.siteExecutableResourceObject.defaultCommandRefname = self.commandRefname

#
class bafActionResource:
    def __init__(self, parmModuleResourceObject, parmActionClassName, parmActionObject):
        self.actionClassName = parmActionClassName
        self.moduleResourceObject = parmModuleResourceObject
        self.actionExeObject = parmActionObject


class bzModuleOption:
    def __init__(self, parmOptionName, Switch='', DefaultValue='', ImpliedValue=''):
        self.name = parmOptionName
        self.switch = Switch
        self.defaultValue = DefaultValue
        self.impliedValue = ImpliedValue


class bzModuleConfiguration:
    def __init__(self):
        self.executableFileName = ''
        self.cgiName = ''
        self.options = bafNv.bafNvTuple()

    def DefineProgramName(self, parmProgramName):
        self.executableFileName = parmProgramName

    def DefineCgiName(self, parmCgiNaame):
        self.cgiName = parmCgiName

    def DefineBinaryOption(self, parmOptionName, Switch='', DefaultValue='N', ImpliedValue='Y'):
        wsOption = bzModuleOption(parmOptionName, Switch=Switch,
                                  DefaultValue=DefaultValue,
                                  ImpliedValue=ImpliedValue)
        self.options[parmOptionName] = wsOption


class bafPythonClassResource:
    # BAF TDicts are realy its class definitions. A class resource can be defined by either either
    # the python class or a MakeTDict function. If both are found, we match them up to one resource and
    # verify that they are consistent with eachother. Otherwise we can have a class that is defined by
    # just one or the other. bafTupleDictionary.AsPythonClass() generates a class from a TDict.
    # bafTupleDictionary.MakeTDictForObject() can make a TDict for any object so there is lots of help
    # to do whatever is needed.
    #
    def __init__(self, parmPythonModuleResourceObject, parmClassName, ClassObject=None, MakeTDictFunctionName=None):
        self.moduleResourceObject = parmPythonModuleResourceObject
        self.className = parmClassName
        self.classObject = ClassObject			# can be None
        self.classRefname = parmClassName			# may get changed later if dups found
        self.makeTDictFunctionName = MakeTDictFunctionName		# can be None

    def ResolveResource(self):
        # This mainly trys to verify that thre TDict and actual object are consistent.
        if self.makeTDictFunctionName is None:
            return
        wsBareTDict = None
        if self.classObject is not None:
            wsBareInstance = self.classObject()
            wsBareTDict = bafTupleDictionary.MakeTDictForObject(
                wsBareInstance,
                ExeController=self.moduleResourceObject.configuration.exeController,
                Name=self.className)
        #
        wsModelTDict = None
        if self.makeTDictFunctionName is not None:
            wsMakeTDictFunction = getattr(
                self.moduleResourceObject.moduleObject, self.makeTDictFunctionName)
            wsConfigurationException = None
            try:
                wsModelTDict = wsMakeTDictFunction(
                    ExeController=self.moduleResourceObject.configuration.exeController)
            except:
                wsConfigurationException = sys.exc_info()
            if wsConfigurationException is not None:
                wsModelTDict = None
                PrintException(wsConfigurationException, "TDICT",
                               'Unable to create TDict for class %s in module "%s"' % (
                                   self.className, self.moduleResourceObject.pythonModuleName))
        #
        # If we have both kinds of TDicts, make sure they are consistent
        #
        if (wsBareTDict is not None) and (wsModelTDict is not None):
            self.moduleResourceObject.configuration.exeController.errs.SetContext(
                'bafPythonClassResource()', self.className)
            wsModelTDict.CompareTDict(wsBareTDict, CompareNamesOnly=True)
            self.moduleResourceObject.configuration.exeController.errs.ClearContext()


class bafPythonModuleResource:
    def __init__(self, parmPythonPackageResourceObject, parmModuleName, parmImportModule):
        self.pythonPackageResourceObject = parmPythonPackageResourceObject
        self.moduleObject = parmImportModule
        self.configuration = parmPythonPackageResourceObject.configuration
        self.pythonPackageName = ''
        self.pythonModuleName = parmModuleName		# like bfsConfigure
        self.actionResourceObjects = bafNv.bafNvTuple()
        self.classResourceObjects = bafNv.bafNvTuple(
            Name='ClassResourceObjects')
        #
        # Scan python module properties for configuration properties.
        #
        wsModuleProperties = list(parmImportModule.__dict__.items())
        for (wsKey, wsValue) in wsModuleProperties:
            #
            # Create a catalog of the actions in this module
            #
            wsIsAction = False
            try:
                if issubclass(wsValue, bafExeController.bafActionDef):
                    print("*IS ACTION", wsKey)
                    wsIsAction = True
                else:
                    pass
                    #print "NOT ACTION", wsKey, wsValue.__class__.__name__
            except:
                pass
            if wsIsAction:
                if wsKey == 'bafActionDef':
                    continue				# make sure its not the base class
                if wsKey == 'bafExeController':
                    continue			# make sure its not the base class
                if wsKey == 'bfsExeController':
                    continue			# make sure its not the base class
                if wsKey == 'LocalAction':
                    continue				# make sure its not a local base class
                wsInitializationException = None
                try:
                    wsActionExeObject = wsValue(
                        self.configuration.exeController)
                except:
                    wsActionExeObject = None
                    wsInitializationException = sys.exc_info()
                if wsInitializationException is None:
                    # We were able to initialize action. It seems to be valid so now we register it.
                    if wsActionExeObject.actionRefname in self.configuration.actionsByActionRefname:
                        # Action names must be globally unique (by site)
                        wsFirstAction = self.configuration.actionsByActionRefname[
                            wsActionExeObject.actionRefname]
                        PrintError('Duplicate Action Reference Name "%s" in modules %s and %s' % (
                            wsActionExeObject.actionRefname,
                            self.pythonModuleName,
                            wsFirstAction.moduleResourceObject.pythonModuleName))
                    if wsKey in self.actionResourceObjects:
                        # This should be a syntax error, but Python doesn't complain about duplicate definitions.
                        # The first definintion is silently replaced.
                        PrintError('Duplicate Action Class Name "%s" in module %s' % (
                            wsKey, self.pythonModuleName))
                    wsActionResourceObject = bafActionResource(
                        self, wsKey, wsActionExeObject)
                    self.configuration.actionsByActionRefname[
                        wsActionExeObject.actionRefname] = wsActionResourceObject
                    self.actionResourceObjects[wsKey] = wsActionResourceObject
                else:
                    PrintException(wsInitializationException, "INITIALIZATION",
                                   'Unable to initialize module action "%s" in module "%s"' % (
                                                              wsKey, parmModuleName))
            if wsKey[:MakeTDictPrefixLen] == MakeTDictPrefix:
                if wsValue.__class__.__name__ == 'function':
                    wsClassName = wsKey[MakeTDictPrefixLen:]
                    if wsClassName in self.classResourceObjects:
                        wsClassResource = self.classResourceObjects[wsClassName]
                        if wsClassResource.makeTDictFunctionName is not None:
                            PrintError('Duplicate Make TDict Function "%s" in module %s' % (
                                wsKey, self.pythonModuleName))
                        wsClassResource.makeTDictFunctionName = wsKey
                    else:
                        wsClassResource = bafPythonClassResource(self, wsClassName,
                                                                 MakeTDictFunctionName=wsKey)
                        self.classResourceObjects.AppendDatum(
                            wsClassName, wsClassResource)
            #
            # wsSkipClasses are names of classes that get created in each module and therefore
            # cause Duplicate System Class errors.
            wsSkipClasses = [
                'BeautifulSoup'
            ]
            if isinstance(wsValue, type) and (not wsIsAction) and (wsKey not in wsSkipClasses):
                # This is a class.
                # We want a catalog of all classes in the system and their corresponding TDict.
                # This is used for Serializing and other smart processes.
                # Eventially, building a program may be more about building a database of
                # TDicts than writing conventional source code.
                if wsKey in self.classResourceObjects:
                    wsClassResource = self.classResourceObjects[wsKey]
                    if wsClassResource.classObject is not None:
                        PrintError('Duplicate class declaration "%s" in module %s' % (
                            wsKey, self.pythonModuleName))
                    wsClassResource.classObject = wsValue
                else:
                    wsClassResource = bafPythonClassResource(self, wsKey,
                                                             ClassObject=wsValue)
                    self.classResourceObjects.AppendDatum(
                        wsKey, wsClassResource)

        if 'bafConfigureModule' in parmImportModule.__dict__:
            print('bafPythonModuleResource()', 'bafConfigureModule',
                  self.actionResourceObjects.keys())
            wsBafConfigureModuleFunction = parmImportModule.__dict__[
                'bafConfigureModule']
            wsConfigurationException = None
            try:
                wsBafConfigureModuleFunction(self)
            except:
                wsConfigurationException = sys.exc_info()
            if wsConfigurationException is not None:
                PrintException(wsConfigurationException, "CONFIGURATION",
                               'Unable to execute module action in module "%s"' % (
                                   parmModuleName))
            if self.configuration.verbose:
                PrintStatus("Python Module %s configured using BafConfigureModule()" % (
                    self.pythonModuleName))
        else:
            if self.configuration.verbose:
                PrintStatus("Python Module %s configured without BafConfigureModule()" % (
                    self.pythonModuleName))

    def ResolveResource(self):
        self.pythonPackageName = self.pythonPackageResourceObject.resolvedName  # like bfslib
        for (wsThisClassName, wsThisClassResource) in list(self.classResourceObjects.items()):
            if wsThisClassResource.classRefname in self.configuration.pythonClasses:
                # These class refnames must globally unique.
                # The following message isn't too informative. Expand if it comes up.
                PrintError('Duplicate System Class Name "%s" in module %s' % (
                    wsThisClassName, self.pythonModuleName))
            else:
                self.configuration.pythonClasses[wsThisClassResource.classRefname] = wsThisClassResource
                wsThisClassResource.ResolveResource()


class bafPythonPackageResource:
    def __init__(self, parmDirectoryObject):
        self.directory = parmDirectoryObject
        self.configuration = parmDirectoryObject.configuration
        self.referenceName = parmDirectoryObject.referenceName
        self.resolvedName = ''
        self.parentPath = ''
        self.pythonPackagePath = ''
        self.pythonModules = {}
        self.pythonModuleList = []

    def ResolveResource(self):
        self.resolvedName = self.directory.resolvedName
        self.parentPath = os.path.dirname(self.directory.resolvedPath)
        self.pythonPackagePath = self.directory.resolvedPath
        if self.configuration.verbose:
            PrintStatus("Resolving Python Package %s @ %s" %
                        (self.resolvedName, self.pythonPackagePath))
        #
        # Scan directory to auto configure modules and programs
        #
        self.pythonModules = {}
        if StartupMode == StartupDirect:
            # Don't try to load modules in direct mode because it will fail and generate
            # a bunch of errors. We just want to keep going cleanly so we can create
            # library symlinks and program stubs. We'll deal with programs in the next pass.
            #
            # The exception is the BAF Source library. All of those should load (import) because they don't
            # need the python library symlinks. The main reason to do this is to create the program stub
            # for the config program. Otherwise we would never get past (StartupMode == StartupDirect) mode.
            if not self.directory.isBafLibDirectory:
                return
        try:
            wsPackageFiles = os.listdir(self.pythonPackagePath)
        except:
            # Can happen during site initialization because directory doesn't exist yet
            wsPackageFiles = []
        for wsThisFileName in wsPackageFiles:
            if wsThisFileName[-3:] != '.py':
                continue
            if wsThisFileName == PackageInitModuleName:
                continue
            wsModuleName = wsThisFileName[:-3]
            if StartupMode == StartupDirect:
                # Only the BafLib package is imported in this mode and it is the current directory
                # so we don't have to specify the package.
                wsImportName = wsModuleName
            else:
                # This is the normal program mode where all packages are accessed through a
                # directory symlink.
                wsImportName = self.resolvedName + '.' + wsModuleName
            wsImportException = None
            try:
                wsImportPackage = __import__(wsImportName)
            except:
                wsImportException = sys.exc_info()
            if wsImportException is not None:
                PrintException(wsImportException, "IMPORT",
                               'Unable to import package file %s.' % (wsImportName))
                continue
            if StartupMode == StartupDirect:
                # __import__ returns different things depending on wheather or not we are referencing
                # a package directory.
                wsImportModule = wsImportPackage
            else:
                wsImportModule = getattr(wsImportPackage, wsModuleName)
            wsModuleResourceObject = bafPythonModuleResource(
                self, wsModuleName, wsImportModule)
            if wsModuleName in self.pythonModules:
                PrintError('Duplicate package module "%s"' % (wsImportName))
            if wsModuleName in self.configuration.pythonModules:
                PrintError('Duplicate system module "%s"' % (wsImportName))
                wsDuplicateModule = self.configuration.pythonModules[wsModuleName]
                PrintStatus('Also defined in "%s.%s".' % (
                    wsDuplicateModule.pythonPackageName, wsDuplicateModule.pythonModuleName))
            self.pythonModules[wsModuleName] = wsModuleResourceObject
            self.configuration.pythonModules[wsModuleName] = wsModuleResourceObject
        self.pythonModuleList = sorted(self.pythonModules.keys())


class bafDatabaseResource:
    def __init__(self, Configuration=None, Refname=None, ServerName=None, DbName=None, UserName=None, Password=None,
                 DbType=bafRdbms.DbTypeUnknown,
                 PathResource=None
                 ):
        self.configuration = Configuration
        self.dbConnection = None
        self.dbRefname = Refname
        self.serverName = ServerName
        self.dbName = DbName
        self.dbType = DbType
        self.userName = UserName
        self.password = Password
        self.multiTable = False			# bafRdbmsFiles
        self.dbTableResourcesByRefname = bafNv.bafNvTuple()
        self.pathResource = PathResource			# bafFileResource
        self.resolvedPath = None

    def __repr__(self):
        return "DB Resource %s: %s %s %s %s %s" % (
            self.dbRefname,
            self.dbType,
            self.serverName,
            self.dbName,
            self.userName,
            self.password
        )

    def AddDbTable(self, parmTableName, ModelClassRefname=None, TableRefname=None):
        wsTableResource = bafDbTableResource(
            Configuration=self.configuration,
            ModelClassRefname=ModelClassRefname,
            TableName=parmTableName,
            TableRefname=TableRefname,
            DbResource=self
        )
        self.dbTableResourcesByRefname.AppendDatum(
            wsTableResource.dbTableRefname, wsTableResource)
        self.configuration.AddDbTableResource(wsTableResource)

    def ResolveResource(self):
        # try:
        if self.dbType == bafRdbms.DbTypeSqLite:
            self.ResolveResourceSqLite()
        elif self.dbType == bafRdbms.DbTypeFiles:
            self.ResolveResourceFiles()
        else:
            self.ResolveResourceMysql()
        # except:
         # PrintError("bafDatabaseResource.ResolveResource exception for %s" % (self.dbRefname))

    def ResolveResourceFiles(self):
        self.resolvedPath = self.pathResource.resolvedPath
        self.dbConnection = bafRdbms.bafRdbmsFiles(
            ExeController=self.configuration.exeController,
            Path=self.resolvedPath,
            MultiTable=self.multiTable,
            Debug=0
        )
        self.ResolveCommon()

    def ResolveResourceSqLite(self):
        self.resolvedPath = self.pathResource.resolvedPath
        self.dbConnection = bafRdbms.bafRdbmsSqLite(
            ExeController=self.configuration.exeController,
            Path=self.resolvedPath,
            Debug=0
        )
        self.ResolveCommon()

    def ResolveResourceMysql(self):
        self.dbConnection = bafRdbms.bafRdbmsMySql(
            Db=self.dbName,
            ExeController=self.configuration.exeController,
            Host=self.serverName,
            Password=self.password,
            User=self.userName,
            Debug=0
        )
        self.ResolveCommon()

    def ResolveCommon(self):
        for wsThisTableName in list(self.dbConnection.tables.keys()):
            if wsThisTableName not in self.dbTableResourcesByRefname:
                # Add tables that were not explicitly defined by the application
                wsDbTable = self.dbConnection.OpenTable(wsThisTableName)
                if wsDbTable.IsOpen():
                    if wsThisTableName in self.configuration.dbTables:
                        # another database aready grabbed this name
                        wsTableRefname = self.dbRefname + '_' + wsThisTableName
                    else:
                        wsTableRefname = wsThisTableName
                    self.AddDbTable(wsThisTableName,
                                    TableRefname=wsTableRefname)
        for wsThisTableResource in list(self.dbTableResourcesByRefname.values()):
            if wsThisTableResource.modelClassRefname is None:
                continue
            if wsThisTableResource.modelClassRefname not in self.configuration.pythonClasses:
                PrintError("Db Table %s.%s model class %s not defined" % (
                    self.dbRefname,
                    wsThisTableResource.dbTableRefname,
                    wsThisTableResource.modelClassRefname
                ))


class bafDbTableResource:
    def __init__(self,
                 Configuration=None,
                 TableRefname=None,
                 DbResource=None,
                 ModelClassRefname=None,
                 TableName=None,
                 DataDirResourceName=None,
                 DataExt=None
                 ):
        self.configuration = Configuration
        self.dataDirResourceName = DataDirResourceName
        self.dataExt = DataExt
        self.dbResource = DbResource
        self.dbTableRefname = TableRefname
        self.dbTableName = TableName
        self.modelClassRefname = ModelClassRefname		# This is to get a detailed TDict
        if self.dbTableRefname is None:
            self.dbTableRefname = TableName

    def ResolveResource(self):
        pass


class bafFileResource:
    def __init__(self, parmConfiguration, parmRefname, parmDirectory, FileName=None, BootIniVariableName=None, Purpose=''):
        self.configuration = parmConfiguration
        self.directory = parmDirectory
        self.definitionBootIniVariableName = BootIniVariableName
        self.definitionName = FileName
        self.definitionPurpose = Purpose
        self.generatorAction = None
        self.isAutoCreate = False
        self.isPythonModule = False
        self.isRunDirSymlinkFile = False
        self.referenceName = parmRefname
        self.resolvedName = ''
        self.resolvedNameBase = ''
        self.resolvedNameExt = ''
        self.resolvedPath = ''

    def ResolveResource(self):
        if self.definitionBootIniVariableName:
            wsName = self.configuration.GetBootIniVariableValue(
                self.definitionBootIniVariableName)
        else:
            wsName = self.definitionName
        self.resolvedPath = os.path.join(self.directory.resolvedPath, wsName)
        if self.resolvedPath:
            self.resolvedName = os.path.basename(self.resolvedPath)
            (self.resolvedNameBase, self.resolvedNameExt) = bzUtil.BreakFileName(
                self.resolvedName)

    def AssignGenerator(self, parmGeneratorAction):
        self.generatorAction = parmGeneratorAction

    def ConfigureAsXxxInfoPy(self, parmCoreElement):
        self.isRunDirSymlinkFile = True
        self.isPythonModule = True
        self.configuration.AssignResourceAttribute(parmCoreElement, self)

    def ConfigureAsTestImportPy(self):
        self.isPythonModule = True
        self.configuration.AssignResourceAttribute(
            'siteTestImportPyFile', self)

    def ConfigureAsHelpPy(self):
        self.isPythonModule = True
        self.configuration.AssignResourceAttribute('siteHelpPyFile', self)

    def ConfigureAsAppsIniFile(self):
        self.configuration.AssignResourceAttribute('appsIniFile', self)

    def ConfigureAsBootIniFile(self):
        self.configuration.AssignResourceAttribute('bootIniFile', self)

    def ConfigureAsPythonModule(self, IsAutoCreate=False, IsRunDirSymlinkFile=False):
        self.isPythonModule = True
        self.isAutoCreate = IsAutoCreate
        self.isRunDirSymlinkFile = IsRunDirSymlinkFile
        if not self.directory.isPythonPackageDirectory:
            PrintError("Directory %s for module %s is not configured as a Python Package" % (
                self.directory.referenceName, self.referenceName))
        if self.directory.pythonPackageResource is None:
            PrintError("Directory %s for module %s does not reference a Python Package resource" % (
                self.directory.referenceName, self.referenceName))


class bafConstantResource:
    def __init__(self, parmConfiguration, parmRefname, Value=None, BootIniVariableName=None, Purpose=''):
        self.configuration = parmConfiguration
        self.referenceName = parmRefname
        self.definitionBootIniVariableName = BootIniVariableName
        self.definitionValue = Value
        self.definitionPurpose = Purpose
        self.resolvedValue = None

    def ResolveResource(self):
        if self.definitionBootIniVariableName:
            self.resolvedValue = self.configuration.GetBootIniVariableValue(
                self.definitionBootIniVariableName)
        else:
            self.resolvedValue = self.definitionValue

#
# bafApacheSiteResource
#
# There would be something to be said for having a full hierarchy of domain -> host -> port resources.
#	that will be left for future work.
#
# There would be something to be said for warning aabout duplicate domain/host/port values during configuration.
# This should not be blocked because it is handy during development. In particular it allows testing when
# Apache SSL services are not available during development but can be turned on by just flipping a bit.
#


class bafApacheSiteResource:
    def __init__(self, parmConfiguration, parmRefname, HostBootIniVariableName=None, DomainBootIniVariableName=None, IsSsl=False):
        self.configuration = parmConfiguration
        self.domainBootIniVariableName = DomainBootIniVariableName
        self.hostBootIniVariableName = HostBootIniVariableName
        self.isSsl = IsSsl
        self.apacheSiteRefname = parmRefname
        self.resolvedUri = ''

    def ResolveResource(self):
        wsHost = self.configuration.GetBootIniVariableValue(
            self.hostBootIniVariableName)
        wsDomain = self.configuration.GetBootIniVariableValue(
            self.domainBootIniVariableName)
        if self.isSsl:
            self.resolvedUri = "https://%s.%s" % (wsHost, wsDomain)
        else:
            self.resolvedUri = "http://%s.%s" % (wsHost, wsDomain)


class bafDirectoryResource:
    def __init__(self, parmConfiguration, parmRefname, Purpose='', Path=None, BootIniVariableName=None, ParentDirectory=None):
        self.apacheSiteResource = None
        self.configuration = parmConfiguration
        self.parentDirectory = ParentDirectory  # reference name of parent
        self.referenceName = parmRefname
        self.definitionBootIniVariableName = BootIniVariableName
        self.definitionPath = Path
        self.definitionPurpose = Purpose
        self.definitionUriName = ''
        self.resolvedPath = ''
        self.resolvedName = ''
        self.resolvedUri = ''
        self.isApacheCgiDirectory = False
        self.isApacheRootDocumentDirectory = False
        self.isApacheDocumentDirectory = False
        self.isAutoCreate = False			# create directory if it doesn't exist
        self.isBafSourceDirectory = False			# Core configuration component
        self.isBafLibDirectory = False			# Core configuration component
        self.isAppSourceDirectory = False			# Core configuration component
        self.isAppDataDirectory = False			# Core configuration component
        self.isSiteRunDirectory = False			# Core configuration component
        self.isSiteSourceDirectory = False			# Core configuration component
        self.isSiteRunConvenienceDirectory = False
        self.isConfigured = False
        self.isPythonProgramRunDirectory = False
        self.isPythonPackageDirectory = False
        self.pythonPackageResource = None				# if isPythonPackageDirectory

    def ResolveResource(self):
        self.resolvedPath = ''
        self.resolvedName = ''
        self.resolvedUri = ''
        wsName = ''
        if self.definitionBootIniVariableName:
            wsName = self.configuration.GetBootIniVariableValue(
                self.definitionBootIniVariableName)
        else:
            wsName = self.definitionPath
        if not wsName:
            wsName = self.referenceName
        if self.parentDirectory is None:
            self.resolvedPath = wsName
        else:
            wsParent = self.configuration.directories[self.parentDirectory]
            if (wsParent.resolvedPath != '') and (wsName != ''):
                # leave resolvedPath empty if parent not defined so the directory doesn't get processed.
                self.resolvedPath = os.path.join(wsParent.resolvedPath, wsName)
            if wsParent.isSiteSourceDirectory or wsParent.isSiteRunDirectory:
                self.isAutoCreate = True
        if self.resolvedPath:
            self.resolvedPath = os.path.realpath(self.resolvedPath)
            self.resolvedName = os.path.basename(self.resolvedPath)
        if self.resolvedPath == '':
            PrintError('Invalid directory location for directory reference name "%s"' % (
                self.referenceName))
            return
        if self.apacheSiteResource is not None:
            if self.isApacheRootDocumentDirectory:
                wsWebDirName = ''
            else:
                wsWebDirName = self.definitionUriName + '/'
            self.resolvedUri = self.apacheSiteResource.resolvedUri + '/' + wsWebDirName
        if self.configuration.verbose:
            PrintStatus("Resolving Directory Resource %s to %s." % (
                self.referenceName,
                self.resolvedPath))

    def AddSubDirectory(self, parmRefname, parmPurpose, DirName=None, BootIniVariableName=None):
        # DirName is a string default value
        return self.configuration.AddDirectory(parmRefname, parmPurpose,
                                               ParentDirectory=self.referenceName, Path=DirName,
                                               BootIniVariableName=BootIniVariableName)

    def AddFileResource(self, parmRefname, parmPurpose, FileName=None, BootIniVariableName=None):
        return self.configuration.AddFileResource(parmRefname, parmPurpose, self,
                                                  FileName=FileName, BootIniVariableName=BootIniVariableName)

    def ConfigureAsApacheRoot(self, Site):
        self.apacheSiteResource = Site
        self.isApacheRootDocumentDirectory = True
        self.isApacheDocumentDirectory = True

    def ConfigureAsApacheSecondary(self, parmApacheUriName, Site):
        self.apacheSiteResource = Site
        self.isApacheDocumentDirectory = True
        self.definitionUriName = parmApacheUriName

    def ConfigureAsApacheCgi(self, parmApacheUriName, Site):
        self.apacheSiteResource = Site
        self.isApacheCgiDirectory = True
        self.definitionUriName = parmApacheUriName

    def ConfigureAsAppData(self):
        self.isSiteRunConvenienceDirectory = True
        self.isAppDataDirectory = True
        self.isConfigured = False

    def ConfigureAsAppLib(self):
        self.configuration.AssignResourceAttribute('appLibDirectory', self)
        self.ConfigureAsPythonPackage()

    def ConfigureAsAppSource(self):
        self.configuration.AssignResourceAttribute('appSourceDirectory', self)
        self.isSiteRunConvenienceDirectory = True
        self.isAppSourceDirectory = True
        self.isConfigured = True

    def ConfigureAsBafSource(self):
        self.configuration.AssignResourceAttribute('bafSourceDirectory', self)
        self.isSiteRunConvenienceDirectory = True
        self.isBafSourceDirectory = True
        self.isConfigured = True

    def ConfigureAsSiteSource(self):
        self.configuration.AssignResourceAttribute('siteSourceDirectory', self)
        self.isSiteRunConvenienceDirectory = True
        self.isSiteSourceDirectory = True
        self.isConfigured = True

    def ConfigureAsSiteRun(self):
        self.configuration.AssignResourceAttribute('siteRunDirectory', self)
        self.isSiteRunConvenienceDirectory = True
        self.isSiteRunDirectory = True
        self.isConfigured = True

    def ConfigureAsBafLib(self):
        self.configuration.AssignResourceAttribute('bafLibDirectory', self)
        self.isBafLibDirectory = True
        self.ConfigureAsPythonPackage()

    def ConfigureAsSiteLib(self):
        self.configuration.AssignResourceAttribute('siteLibDirectory', self)
        self.ConfigureAsPythonPackage()

    def ConfigureAsSiteSynthesis(self):
        # This directory contains python code but it is never used directly,
        # only through symlinks so it is neither a package nor a run directory.
        self.configuration.AssignResourceAttribute(
            'siteSynthesisDirectory', self)

    def ConfigureAsSiteProg(self):
        self.configuration.AssignResourceAttribute('siteProgDirectory', self)
        self.ConfigureAsPythonProgramRun()

    def ConfigureAsSiteMProg(self):
        self.configuration.AssignResourceAttribute('siteMProgDirectory', self)
        self.ConfigureAsPythonPackage()

    def ConfigureAsSiteCgi(self, parmApacheUriName, Site=None):
        self.configuration.AssignResourceAttribute('siteCgiDirectory', self)
        self.ConfigureAsPythonProgramRun()
        self.ConfigureAsApacheCgi(parmApacheUriName, Site=Site)

    def ConfigureAsSiteMCgi(self, parmApacheUriName, Site=None):
        self.configuration.AssignResourceAttribute('siteMCgiDirectory', self)
        self.ConfigureAsPythonProgramRun()
        self.ConfigureAsApacheCgi(parmApacheUriName, Site=Site)

    def ConfigureAsPythonProgramRun(self):
        self.isPythonProgramRunDirectory = True

    def ConfigureAsPythonPackage(self):
        self.isPythonPackageDirectory = True
        self.pythonPackageResource = self.configuration.AddPythonPackage(self)

    def ConfigureAsSiteConfDirectory(self):
        if self.configuration.siteConfDirectoryResource is not None:
            PrintError("%s: Duplicate siteConfig. Already defined as %s" % (
                self.referenceName, self.configuration.siteConfDirectory.referenceName))
        self.configuration.siteConfDirectory = self


class bafAppResource(object):
    def __init__(self,
                 Configuration=None,
                 DefineFeaturesFunction=None,
                 Prefix=None):
        self.configuration = Configuration
        self.defineFeaturesFunction = DefineFeaturesFunction
        self.appPrefix = Prefix


class bafTask:
    def __init__(self, parmPhase, parmAction):
        self.phase = parmPhase
        self.action = parmAction


class bafConfiguration:
    def __init__(self, ExeController=None, Verbose=False):
        #
        # Hopefully this works no matter how broken the existing configuration is.
        # Capture whatever configuration information can be found but provide an opportunity
        # to correct it in case its wrong.
        #
        # This must be able to run before the BAF environment is configured, so it writes directly
        # to the console and is fairly verbose.
        #
        # The various resources are stored in dictionaries. This provess also creates
        # a corresponding list of sorted names which can be used to make more human
        # readable lists. Should add .sorteditems or .sorted values to bafNv to eliminate.
        #
        if ExeController is None:
            self.exeController = self
            self.codes = bafNv.bafNvTuple()		# psuedo exeController implementation
            self.errs = bzErrors.bzErrors()
            self.errs.SetConsoleMode()
        else:
            self.exeController = ExeController.exeController
        self.actionsByActionRefname = bafNv.bafNvTuple()
        self.pythonClasses = bafNv.bafNvTuple()
        self.apps = bafNv.bafNvTuple()
        self.commandsByCommandRefname = None				# initialized by ResolveAllResources()
        self.constants = bafNv.bafNvTuple()
        self.dbs = bafNv.bafNvTuple()
        self.dbTables = bafNv.bafNvTuple()
        self.directories = bafNv.bafNvTuple()
        self.directoryList = []
        self.files = bafNv.bafNvTuple()
        self.pythonPackages = {}
        self.pythonPackageList = []
        self.apacheSites = bafNv.bafNvTuple()
        self.pythonModules = {}
        self.pythonModuleList = []
        self.env.main_module_name = ''
        self.env.main_module_package = None
        self.executables = bafNv.bafNvTuple()
        self.executableRefnames = []
        self.tasks = []
        self.verbose = Verbose
        #
        # The following are pointers to the core directories and files that are essential for the
        # BAF evironment. The actual names can be varied for applications or sites through the
        # configuration process. The variables let this configuration code be a bit more
        # readable by providing constant names.
        #
        # might not need applib/baflib/sitelib directory. Might be located through modules, etc.
        # search for usage after code is stable again. Eventually applib stuff needs to be an array
        # so a site can integrate several applications.
        #
        self.appLibDirectoryResource = None
        self.bafLibDirectoryResource = None
        self.siteLibDirectoryResource = None
        self.siteConfDirectoryResource = None
        self.bafSourceDirectoryResource = None
        self.appSourceDirectoryResource = None
        self.appLibDirectoryResource = None
        self.siteSourceDirectoryResource = None
        self.siteRunDirectoryResource = None
        self.siteProgDirectoryResource = None
        self.siteMProgDirectoryResource = None
        self.siteSynthesisDirectoryResource = None
        self.siteCgiDirectoryResource = None
        self.siteMCgiDirectoryResource = None
        self.sitePathInfoPyFileResource = None
        self.siteDatabaseInfoPyFileResource = None
        self.siteWebInfoPyFileResource = None
        self.siteTestImportPyFileResource = None
        self.siteHelpPyFileResource = None
        self.appsIniFileResource = None
        self.bootIniFileResource = None
        #
        self.bootIniFilePath = None
        self.bootIniFileIsLoaded = False

    # BafConfiguration.AddExecutable()
    # This will generally be called from a module's bafConfigureModule action.
    def AddExecutable(self, parmSiteExecutableResourceObject):
        if parmSiteExecutableResourceObject.executableFileName in self.executables:
            PrintError('Duplicate system program  "%s" in %s.%s' % (
                parmSiteExecutableResourceObject.executableFileName,
                parmSiteExecutableResourceObject.primaryModuleResourceObject.pythonPackageName,
                parmSiteExecutableResourceObject.primaryModuleresourceObject.pythonModuleName))
        self.executables[parmSiteExecutableResourceObject.executableFileName] = parmSiteExecutableResourceObject

    def InitializeAppCore(self, parmAppPrefix, parmAppLibDirectory):
        if not os.path.isdir(parmAppLibDirectory):
            PrintError("App %s directory %s not not a directory." %
                       (parmAppPrefix, parmAppLibDirectory))
            return False
        if parmAppPrefix in self.apps:
            PrintError("Duplicate App definition %s for directory %s." %
                       (parmAppPrefix, parmAppLibDirectory))
            return False
        wsAppPrefixC = bzUtil.Upper(parmAppPrefix[0]) + parmAppPrefix[1:]
        wsAppLibDirPath = os.path.realpath(parmAppLibDirectory)
        wsAppLibDirName = os.path.basename(wsAppLibDirPath)
        wsAppSourceDirPath = os.path.dirname(wsAppLibDirPath)
        wsAppModulePath = os.path.join(
            wsAppLibDirPath, CoreAppConfigureModuleName + '.py')
        if not os.path.exists(wsAppModulePath):
            PrintError("App %s configuration module %s does not exist." %
                       (parmAppPrefix, wsAppModulePath))
            return False
        if not os.path.isfile(wsAppModulePath):
            PrintError("App %s configuration module %s is not a file." %
                       (parmAppPrefix, wsAppModulePath))
            return False
        wsConfigurationException = None
        try:
            wsAppModuleObject = imp.load_source(
                CoreAppConfigureModuleName, wsAppModulePath)
        except:
            wsConfigurationException = sys.exc_info()
        if wsConfigurationException is not None:
            PrintException(wsConfigurationException, "CONFIGURATION",
                           'Unable to load App configuration module "%s"' % (
                               wsAppModulePath))
            return False
        wsAppDefineCoreFunction = getattr(
            wsAppModuleObject, CoreAppDefineCoreFunctionName, None)
        wsAppDefineFeaturesFunction = getattr(
            wsAppModuleObject, CoreAppDefineFeaturesFunctionName, None)

        #
        # The app has been identified, now integrate.
        #
        # In order to minimize side effects, there would be something to be said for creating a new
        # configuration type object with just the things we want the app to know about and fiddle with
        # and then copy any new things here. This will become a priority if BAF use expands beyond me.
        #
        self.MakeBootIniSubTDict(parmAppPrefix)
        wsAppSourceDirRefname = wsAppPrefixC + 'AppSourceDirectory'
        wsAppSourceDirTitle = wsAppPrefixC + ' App Source Directory Path'
        wsAppSourceDir = self.AddDirectory(wsAppSourceDirRefname, wsAppSourceDirTitle,
                                           Path=wsAppSourceDirPath)
        wsAppSourceDir.ConfigureAsAppSource()
        wsDir = wsAppSourceDir.AddSubDirectory('Applib', 'APP Python Code',
                                               DirName=wsAppLibDirName)
        wsDir.ConfigureAsAppLib()

        wsAppDefineCoreFunction(parmAppPrefix, self)
        wsAppResource = bafAppResource(
            Configuration=self,
            DefineFeaturesFunction=wsAppDefineFeaturesFunction,
            Prefix=parmAppPrefix)
        self.apps.AppendDatum(parmAppPrefix, wsAppResource)
        return True

    def LoadCurrentConfiguration(self):
        # This used to be the last part of __init__(). It was broken into two pieces so the startup
        # code could print some of the directory names, etc. before loading so the user has some
        # context for answering configuration questions or uderstanding error messages.
        #
        # First define core defininitions for BAF and any apps. The core generally defines
        # the TDict for boot.ini and BAF/app resources. The resource definitions can reference
        # boot.ini variables but actual values are determined until ResolveResource() is run
        # --- after boot.ini is actually loaded.
        #
        self.InitializeBafCore()
        self.appsIniFileIsLoaded = bafSerializer.LoadIniFile(
            self.appsIniData, Path=self.appsIniFilePath, ExeController=self.exeController)
        if self.appsIniFileIsLoaded:
            PrintStatus("App INI file '%s' loaded" % (self.appsIniFilePath))
            for (wsThisAppPrefix, wsThisAppLibDirectory) in list(self.appsIniData.items()):
                PrintStatus("App '%s' loading ..." % (wsThisAppPrefix))
                self.InitializeAppCore(wsThisAppPrefix, wsThisAppLibDirectory)
                PrintStatus("App '%s' loaded." % (wsThisAppPrefix))
        # After initializing BAF and app core, bootIniFileTDict is populated so we can load the boot.ini file
        self.bootIniFileIsLoaded = bafSerializer.LoadIniFile(
            self.bootIniData, Path=self.bootIniFilePath, ExeController=self.exeController)
        #
        wsAskAboutEditingIni = True
        if not self.bootIniFileIsLoaded:
            PrintStatus("Unable to load boot.ini file '%s'." %
                        (self.bootIniFilePath))
        if self.bootIniFileIsLoaded:
            PrintStatus("Boot INI file '%s' loaded" % (self.bootIniFilePath))
        else:
            PrintStatus(
                "Unable to load boot.ini file '%s' -- using default values." % (self.bootIniFilePath))
            self.SetBootIniVariableValue(
                BafSourceDirectoryRefname, self.env.package_parent_directory)
            self.SetBootIniVariableValue(
                SiteRunDirectoryRefname, self.env.execution_cwd)
            wsAskAboutEditingIni = True
        #
        for wsThisAppResource in list(self.apps.values()):
            # This creates empty tuples in bootIniData for new apps.
            # The TDict is automagically assigned so bzDataEdit knows what to check.
            if wsThisAppResource.appPrefix not in self.bootIniData:
                self.bootIniData.MakeChildTuple(
                    Name=wsThisAppResource.appPrefix)
        if wsAskAboutEditingIni:
            if bzDataEdit.ConsoleAskYesNo('Do you want to edit the boot.ini file?'):
                wsEditer = bzDataEdit.bzDataEditNew(self.bootIniData,
                                                    ExeController=self.exeController,
                                                    Debug=1)
                wsEditer.ConsoleDataEntry()
                if bzDataEdit.ConsoleAskYesNo('Save?'):
                    self.SaveConfiguration()
        for wsThisAppResource in list(self.apps.values()):
            if wsThisAppResource.defineFeaturesFunction is not None:
                wsThisAppResource.defineFeaturesFunction(wsThisAppResource)
        self.ResolveAllResources()		# uses config file if loaded, else defaults
        #
        self.directoryList = sorted(self.directories.keys())
        self.pythonPackageList = sorted(self.pythonPackages.keys())
        self.pythonModuleList = sorted(self.pythonModules.keys())
        self.executableRefnames = sorted(self.executables.keys())
        #
        if ConfigErrorCt > 0:
            # Stop here because further configuration would be wrong or meaningless
            return
        # self.DisplayConfiguration()
        if not self.CheckConfiguration():
            PrintError(
                "Configuration not complete enough to proceed ... exiting")
            return
        #
        # self.ScrubAndCopyConfigData()

    def SaveConfiguration(self):
        print("CCC", self.bootIniData)
        bafSerializer.WriteIniFile(
            self.bootIniData, Path=self.bootIniFilePath, ExeController=self.exeController)

    def AssignResourceAttribute(self, parmResourceRefname, parmResourceObject):
        wsAttrName = parmResourceRefname + 'Resource'
        wsCurrentValue = getattr(self, wsAttrName)
        if wsCurrentValue is not None:
            PrintError("%s: Duplicate %s. Already defined as %s" % (
                parmElementObject.referenceName, parmResourceRefname, wsCurrentValue.referenceName))
        setattr(self, wsAttrName, parmResourceObject)

    def DisplayConfiguration(self):
        for (wsThisDirectoryName, wsThisDirectory) in list(self.directories.items()):
            print(wsThisDirectoryName, wsThisDirectory.resolvedPath)
        for (wsThisFileName, wsThisFile) in list(self.files.items()):
            print(wsThisFileName, wsThisFile.resolvedPath)

    def GetCodeObject(self, parmCodeRefname):
        # After initializing BAF and app core, bootIniFileTDict is populated so we can load the boot.ini file
        # psuedo exeController implementation
        return bafErTypes.Core_GetCodeObject(self, parmCodeRefname)

    def InitializeBafCore(self):
        #
        # The goal is for nothing to be hard-wired. Since core programs are hard-wired, not generated,
        # there has to be a few fixed elements to get the system started.
        #
        # import sitelib.pathInfo as pathInfo
        #
        # If the configuration is essentially intact sitelib can be almost anywhere because the appropriate
        # link provides the mapping. The module has to be called pathInfo, which is generated.
        #
        # PathInfo must have a property of BootIniFile which provides the fully qualified
        # path to the configuaration file. At this point its somewhat hardwired that it be in
        # a configuration file in the Site Source directory. Its nice to keep it restricted but there
        # isn't really a strong requirement for that. It just needs to be pointed to by
        # sitelib.pathInfo.BootIniFile. On the other hand, there doesn't really seem to be a good reason
        # to move or rename it since that could be confusing in recovery situations.
        #
        self.appsIniData = bafDataStore.bafTupleObject(ExeController=self.exeController,
                                                       Name='AppsIni',
                                                       IsTDictDynamic=True)
        self.bootIniTDict = bafTupleDictionary.bafTupleDictionary(
            ExeController=self.exeController, Name='BootIni')
        self.bootIniData = bafDataStore.bafTupleObject(ExeController=self.exeController,
                                                       IsHierarchy=True,
                                                       Name='BootIni',
                                                       IsTDictDynamic=True,
                                                       TDict=self.bootIniTDict)
        self.bootIniActiveSubTDict = self.bootIniTDict
        DefineBafCore(self)
        try:
            # not the right name, probably needs to use getattr
            self.bootIniFilePath = pathInfo.BootIniFile
        except:
            self.bootIniFilePath = None
        try:
            # not the right name, probably needs to use getattr
            self.appsIniFilePath = pathInfo.AppsIniFile
        except:
            self.appsIniFilePath = None
        if self.bootIniFilePath is None:
            PrintStatus("boot.ini location not known.")
            if bzDataEdit.ConsoleAskYesNo('Do you want to search for an existing boot.ini file?'):
                self.bootIniFilePath = bzDataEdit.ConsoleChooseDirectoryItem()

    def CheckConfiguration(self):
        # This probably needs to evelove beyond a simple yes/no result.
        # Maybe contingent.
        wsResult = True
        for wsThisDirectory in list(self.directories.values()):
            if not wsThisDirectory.isSiteRunConvenienceDirectory:
                continue
            if wsThisDirectory.resolvedPath == '':
                PrintError("Directory %s not resolved" %
                           (wsThisDirectory.referenceName))
                wsResult = False
                continue
            if not os.path.isdir(wsThisDirectory.resolvedPath):
                PrintError("Directory %s Path %s not not a directory" % (
                    wsThisDirectory.referenceName, wsThisDirectory.resolvedPath))
                wsResult = False
                continue
        return wsResult

    def GenerateAllFiles(self):
        for wsThisFile in list(self.files.values()):
            if wsThisFile.generatorAction is not None:
                PrintStatus("Generating file %s" % (wsThisFile.referenceName))
                wsThisFile.generatorAction(wsThisFile)

    def ResolveAllResources(self):
        # Initialize
        self.commandsByCommandRefname = bafNv.bafNvTuple()
        #
        # First resolve resources that are just dependent on BootIniData
        #
        for wsThisConstant in list(self.constants.values()):
            wsThisConstant.ResolveResource()
        for wsThisPort in list(self.apacheSites.values()):
            wsThisPort.ResolveResource()
        for wsThisDirectory in list(self.directories.values()):
            if wsThisDirectory.parentDirectory is None:
                wsThisDirectory.ResolveResource()
        #
        # Top level directories are dependent only on constants.
        # Sub directories, files, etc are dependent on top level
        # directories so they have to be resolved after them.
        #
        # Programs are dependant on both directories (packages)
        # and sites in order to resolve program paths.
        #
        for wsThisDirectory in list(self.directories.values()):
            if wsThisDirectory.parentDirectory is not None:
                wsThisDirectory.ResolveResource()
        for wsThisPythonPackage in list(self.pythonPackages.values()):
            wsThisPythonPackage.ResolveResource()
        for wsThisPythonModule in list(self.pythonModules.values()):
            wsThisPythonModule.ResolveResource()
        for wsThisProgram in list(self.executables.values()):
            wsThisProgram.ResolveResource()
        for wsThisFile in list(self.files.values()):
            wsThisFile.ResolveResource()
        for wsThisDb in list(self.dbs.values()):
            # This need to be after file resourced because SqLite databases are also file resourcess.
            # We need the resolved path to locate the database. We also need classes resolved first.
            wsThisDb.ResolveResource()
        for wsThisDbTable in list(self.dbTables.values()):
            wsThisDbTable.ResolveResource()

    def PerformTasks(self, parmPhase):
        for wsThisTask in self.tasks:
            if wsThisTask.phase != parmPhase:
                continue
            wsThisTask.action(self)

    def ScheduleTask(self, parmPhase, parmAction):
        wsTask = bafTask(parmPhase, parmAction)
        self.tasks.append(wsTask)

    def SetCgiFilePermissions(self, parmFilePath):
        # This is just a placeholder during bootstrapping when bafConfiguration
        # acts like bafExeController.
        pass

    def MakeBootIniSubTDict(self, parmRefname):
        # Key subsets are always in the main tree. Limit to two levels for now.
        # Can expand later by adding optional paramter definining target.
        if self.bootIniData._tdict.HasElement(parmRefname):
            PrintError('boot.ini Duplicate Subset reference name "%s"' %
                       (parmRefname))
            return
        self.bootIniActiveSubTDict = self.bootIniTDict.MakeChildDictionary(
            Name=parmRefname)

    def AddBootIniVariable(self, parmRefname, Prompt=None, DefaultValue=None, Hint=None):
        if self.bootIniActiveSubTDict.HasElement(parmRefname):
            PrintError(
                'boot.ini Duplicate variable reference name "%s"' % (parmRefname))
            return
        wsIniElement = self.bootIniActiveSubTDict.DefineValueParameter(parmRefname,
                                                                       Prompt=Prompt,
                                                                       Hint=Hint)
        wsIniElement.AssignDefaultValue(DefaultValue)
        return wsIniElement

    def AddDirectory(self, parmRefname, parmPurpose, ParentDirectory=None, Path=None,
                     BootIniVariableName=None):
        wsDirectoryObject = bafDirectoryResource(self, parmRefname, Purpose=parmPurpose,
                                                 ParentDirectory=ParentDirectory,
                                                 Path=Path,
                                                 BootIniVariableName=BootIniVariableName)
        self.directories[parmRefname] = wsDirectoryObject
        return wsDirectoryObject

    def AddConstantResource(self, parmRefname, Value=None, BootIniVariableName=None, Purpose=''):
        if parmRefname in self.constants:
            PrintError('Duplicate constant reference name "%s"' %
                       (parmRefname))
            return None
        wsConstantObject = bafConstantResource(self, parmRefname,
                                               Value=Value,
                                               BootIniVariableName=BootIniVariableName,
                                               Purpose=Purpose)
        self.constants[parmRefname] = wsConstantObject

    def AddFileResource(self, parmRefname, parmPurpose, parmDirectory, FileName=None, BootIniVariableName=None):
        # parmDirectory is a  bafConfigureDirectory object
        if parmRefname in self.files:
            PrintError('Duplicate file reference name "%s"' % (parmRefname))
            return None
        #
        wsFileObject = bafFileResource(self, parmRefname, parmDirectory,
                                       FileName=FileName,
                                       BootIniVariableName=BootIniVariableName,
                                       Purpose=parmPurpose)
        self.files[parmRefname] = wsFileObject
        return wsFileObject

    def AddDatabaseResource(self, parmResource):
        self.dbs.AppendDatum(parmResource.dbRefname, parmResource)

    def AddDbTableResource(self, parmResource):
        # This is a global resource to make sure we have site wide unique
        # dbTableRefname.
        self.dbTables.AppendDatum(parmResource.dbTableRefname, parmResource)

    def AddPythonPackage(self, parmDirectory):
        wsModuleProperties = list(self.env.main_module_object.__dict__.items())
        wsPackageObject = bafPythonPackageResource(parmDirectory)
        if wsPackageObject.referenceName in self.pythonPackages:
            PrintError('Duplicate package reference name "%s"' %
                       (wsPackageObject.referenceName))
        self.pythonPackages[wsPackageObject.referenceName] = wsPackageObject
        return wsPackageObject

    def AddApacheSiteResource(self, parmRefname, HostBootIniVariableName=None, DomainBootIniVariableName=None, IsSsl=False):
        if parmRefname in self.apacheSites:
            PrintError('Duplicate internet port ref name "%s"' % (parmRefname))
            return None
        #
        wsApacheSiteResourceObject = bafApacheSiteResource(self, parmRefname=parmRefname, HostBootIniVariableName=HostBootIniVariableName,
                                                           DomainBootIniVariableName=DomainBootIniVariableName,
                                                           IsSsl=IsSsl)
        self.apacheSites[parmRefname] = wsApacheSiteResourceObject
        return wsApacheSiteResourceObject

    def GetBootIniVariableValue(self, parmKeyName):
        try:
            return self.bootIniData[parmKeyName]
        except:
            PrintError('Unable to access boot.ini variable "%s"' %
                       (parmKeyName))
            return None

    def SetBootIniVariableValue(self, parmKeyName, parmValue):
        self.bootIniData[parmKeyName] = parmValue


Apache2SiteConfigPath = '/etc/apache2/sites-available/'


def MakeApacheSiteConfig():
    wsF = open(Apache2SiteConfigPath + pathInfo.PublicWebsite, "w")
    wsF.write("# This script file generated by BFS configuration process\n")
    MakeApacheVirtualHost(wsF, pathInfo.PublicWebsite)
    wsF.close()
    wsF = open(Apache2SiteConfigPath + pathInfo.SecureWebsite, "w")
    wsF.write("# This script file generated by BFS configuration process\n")
    MakeApacheVirtualHost(wsF, pathInfo.SecureWebsite, IsSsl=True)
    MakeApacheVirtualHost(wsF, pathInfo.SecureWebsite)
    wsF.close()


def MakeApacheDirectory(parmF, parmDirectory, parmDirectoryType):
    # THIS IS NOT COMPLETE. parmDirectory was string of path. Now directory object.
    # need to use .definitionUriName and may need to fiddle with slashes.
    # DON'T FORGET THAT root is also marked as a directory.
    #
    parmF.write("  <Directory %s>\n" % (parmDirectory))
    if parmDirectory.isApacheRootDocumentDirectory:
        parmF.write("    Options FollowSymLinks\n")
    elif parmDirectory.isApacheDocumentDirectory:
        parmF.write("    Options Indexes FollowSymLinks MultiViews\n")
    elif parmDirectory.isApacheCgiDirectory:
        parmF.write("    Options ExecCGI -MultiViews +SymLinksIfOwnerMatch\n")
    parmF.write("    AllowOverride None\n")
    parmF.write("    Order allow,deny\n")
    parmF.write("    allow from all\n")
    if parmDirectory.isApacheDocumentDirectory:
        parmF.write(
            "    # This directive allows us to have apache2's default start page\n")
        parmF.write(
            "    # in /apache2-default/, but still have / go to the right place\n")
        parmF.write("    # RedirectMatch $ /apache2-default/\n")
        parmF.write("    #php_value mysql.default_user smgr\n")
        parmF.write("    #php_value mysql.default_password x3Pz45aBc\n")
        parmF.write("    #php_value mysql.default_host localhost\n")
    parmF.write("  </Directory>\n")


def MakeApacheVirtualHost(parmF, parmWebsite, IsSsl=False):
    parmF.write("\n")
    if IsSsl:
        wsVirtualHost = "76.74.236.45:443"
        wsSslEngine = "on"
    else:
        wsVirtualHost = "*"
        wsSslEngine = "off"
    parmF.write("<VirtualHost %s>\n" % (wsVirtualHost))
    parmF.write("  ServerAdmin webmaster@localhost\n")
    parmF.write("  ServerName %s\n" % (parmWebsite))
    if parmWebsite == pathInfo.PublicWebsite:
        parmF.write("  ServerAlias %s \n" % (pathInfo.Domain))
    parmF.write("  SSLEngine %s\n" % (wsSslEngine))
    if IsSsl:
        parmF.write("  SSLCACertificatePath /etc/apache2/certs\n")
        parmF.write(
            "  SSLCertificateFile /etc/apache2/certs/cart.hobbyengineering.com.cert.2009\n")
        parmF.write(
            "  SSLCertificateKeyFile /etc/apache2/certs/cart.hobbyengineering.com.key.2009\n")
    parmF.write("  SuexecUserGroup %s %s\n" %
                (pathInfo.WebUsrGrp, pathInfo.WebUsrGrp))
    parmF.write("\n")

    # This directory stuff is just roughly converted, so original commented
    # below as a reminder. MakeApacheDirectory() needs to be cleaned up.
    # This new stuff is the propper structure but no complete.
    wsApacheDirectories = []
    for wsDirectoryReference in parmConfiguration.directoryList:
        wsDirectoryObject = parmConfiguration.directories[wsDirectoryReference]
        if wsDirectoryObject.isApacheRootDocumentDirectory:
            # Make the root and html. Not sure what is difference right now!
            pass
        elif wsDirectoryObject.isApacheDocumentDirectory:
            wsDirectories.append(wsDirectoryObject)
        elif wsDirectoryObject.isApacheCgiDirectory:
            wsDirectories.append(wsDirectoryObject)

    for wsThisDirectoryObject in wsApacheDirectories:
        # make them !!
        pass

    #parmF.write("  DocumentRoot %s\n" % (pathInfo.HtmlPath))
    #MakeApacheDirectory(parmF, "/", ApacheDirectoryTypeRoot)
    #MakeApacheDirectory(parmF, pathInfo.HtmlPath, ApacheDirectoryTypeHtml)
    # parmF.write("\n")
    #parmF.write("  Alias /specs/ /exports/Catalog/DataSheets/\n")
    #parmF.write("  Alias /pics/  /exports/Catalog/Pics/\n")
    #parmF.write("  Alias /work/ %s\n" % (pathInfo.TempfilesPath))
    # parmF.write("\n")
    #parmF.write("  ScriptAlias /cgi/ %s\n" % (pathInfo.CgiPath))
    #MakeApacheDirectory(parmF, pathInfo.CgiPath, ApacheDirectoryTypeCgi)
    # parmF.write("\n")
    #parmF.write("  ScriptAlias /cgim/ %s\n" % (pathInfo.CgimPath))
    #MakeApacheDirectory(parmF, pathInfo.CgimPath, ApacheDirectoryTypeCgi)
    # parmF.write("\n")
    parmF.write("  ErrorLog /var/log/apache2/error.log\n")
    parmF.write("\n")
    parmF.write(
        "  # Possible values include: debug, info, notice, warn, error, crit,\n")
    parmF.write("  # alert, emerg.\n")
    parmF.write("  LogLevel warn\n")
    parmF.write("\n")
    parmF.write("  CustomLog /var/log/apache2/access.log combined\n")
    parmF.write("  ServerSignature On\n")
    parmF.write("\n")
    parmF.write("</VirtualHost>\n")



def OpenResourceOutputFile(parmResource):
    wsName = parmResource.resolvedNameBase
    wsPath = parmResource.resolvedPath
    wsF = OpenTextFile(wsPath, "w")
    if wsF is None:
        PrintError("Unable to write file '%s'." % (wsPath))
        return None

    wsF.write("#\n")
    wsF.write("# %s\n" % (wsName))
    wsF.write("# %s'\n" % (wsPath))
    wsF.write("#\n")
    return wsF


def GenerateSiteActionsFile(parmResource):
    wsConfiguration = parmResource.configuration			# typing shortcut
    wsF = OpenResourceOutputFile(parmResource)
    if wsF is None:
        return
    #
    wsF.write("#\n")
    wsF.write("# Actions\n")
    wsF.write("#\n")
    wsActionRefnames = sorted(
        list(wsConfiguration.actionsByActionRefname.keys()))
    for wsThisActionRefname in wsActionRefnames:
        wsActionResourceObject = wsConfiguration.actionsByActionRefname[wsThisActionRefname]
        wsModuleObject = wsActionResourceObject.moduleResourceObject
        wsActionExeObject = wsActionResourceObject.actionExeObject
        wsActionVariableName = wsThisActionRefname + \
            bafErTypes.SiteActionsVariableSuffix
        wsValueDict = {
            'PackageName':	wsModuleObject.pythonPackageName,
            'ModuleName':	wsModuleObject.pythonModuleName,
            'ClassName':	wsActionExeObject.actionClassName
        }
        wsF.write("%s = %s" % (wsActionVariableName,
                               bafExpCodeWriter.MakePythonDictLiteral(wsValueDict)))
    wsF.write("#\n")
    #
    wsF.write("#\n")
    wsF.write("# Triggers\n")
    wsF.write("#\n")
    for wsThisActionRefname in wsActionRefnames:
        wsActionResourceObject = wsConfiguration.actionsByActionRefname[wsThisActionRefname]
        wsModuleObject = wsActionResourceObject.moduleResourceObject
        wsActionExeObject = wsActionResourceObject.actionExeObject
        # for wsThisTrigger in wsActionExeObject.cmdTriggers.values():
        #  wsTriggerVariableName	= wsThisActionRefname + '_' +  wsThisTrigger.name + bafErTypes.SiteTriggersVariableSuffix
        #  wsValueDict			= {
        #				'PackageName':		wsModuleObject.pythonPackageName,
        #				'ModuleName':		wsModuleObject.pythonModuleName,
        #				'ClassName':		wsActionExeObject.actionClassName,
        #				'TriggerMethodName':	wsThisTrigger.triggerMethodName
        #			}
        #wsF.write("%s = %s" % (wsTriggerVariableName, bafExpCodeWriter.MakePythonDictLiteral(wsValueDict)))
    #
    wsF.write("#\n")
    wsF.write("# Commands\n")
    wsF.write("#\n")
    wsCommandRefnames = list(wsConfiguration.commandsByCommandRefname.keys())
    wsCommandRefnames.sort()
    for wsThisCommandRefname in wsCommandRefnames:
        wsCommandResourceObject = wsConfiguration.commandsByCommandRefname[wsThisCommandRefname]
        wsActionResourceObject = wsCommandResourceObject.actionResourceObject
        wsExecutableResourceObject = wsCommandResourceObject.siteExecutableResourceObject
        wsModuleObject = wsActionResourceObject.moduleResourceObject
        wsActionExeObject = wsActionResourceObject.actionExeObject
        wsCommandVariableName = wsCommandResourceObject.commandRefname + \
            bafErTypes.SiteCommandsVariableSuffix
        wsValueDict = {
            'PackageName':		wsModuleObject.pythonPackageName,
            'ModuleName':		wsModuleObject.pythonModuleName,
            'ClassName':		wsActionExeObject.actionClassName,
            'ActionRefname':	wsActionExeObject.actionRefname,
            'TriggerMethod':	'',
            'ImportPath':		wsExecutableResourceObject.resolvedImportPath,
            'Uri':			wsExecutableResourceObject.resolvedUri,
            'Selector':		wsCommandResourceObject.selector,
            'Switch':		wsCommandResourceObject.switch
        }
        wsF.write("%s = %s" % (wsCommandVariableName,
                               bafExpCodeWriter.MakePythonDictLiteral(wsValueDict)))
    wsF.write("#\n")
    #
    wsF.write("#\n")
    wsF.write("# Other Classes\n")
    wsF.write("#\n")
    wsClassRefnames = list(wsConfiguration.pythonClasses.keys())
    wsClassRefnames.sort()
    for wsThisClassRefname in wsClassRefnames:
        wsClassResourceObject = wsConfiguration.pythonClasses[wsThisClassRefname]
        if wsClassResourceObject.classObject is None:
            wsIsDynamic = True
        else:
            wsIsDynamic = False
        wsModuleObject = wsClassResourceObject.moduleResourceObject
        wsClassVariableName = wsClassResourceObject.classRefname + \
            bafErTypes.SiteClassesVariableSuffix
        wsValueDict = {
            'PackageName':		wsModuleObject.pythonPackageName,
            'ModuleName':		wsModuleObject.pythonModuleName,
            'ClassName':		wsClassResourceObject.className,
            'IsDynamic':		wsIsDynamic
        }
        if wsClassResourceObject.makeTDictFunctionName is not None:
            wsValueDict['MakeTDictFunctionName'] = wsClassResourceObject.makeTDictFunctionName
        wsF.write("%s = %s" % (wsClassVariableName,
                               bafExpCodeWriter.MakePythonDictLiteral(wsValueDict)))
    wsF.write("#\n")
    #
    #
    wsF.write("#\n")
    CloseTextFile(wsConfiguration, wsF, parmResource.resolvedPath)


def GenerateWebInfoFile(parmResource):
    wsConfiguration = parmResource.configuration			# typing shortcut
    wsCode = bzCodeWriter.bzCodeWriter(
        ExeController=wsConfiguration.exeController)
    wsCode.ConfigureAsPython()
    if wsCode.Open(parmResource.resolvedPath) is None:
        PrintError("Unable to open %s file '%s'" %
                   (parmResource.referenceName, parmResource.resolvedPath))
        return
    #
    wsCode.WriteComment("")
    wsCode.WriteComment("Apache Site Resources")
    wsCode.WriteComment("")
    # These cookie details should probably be variables but this is quick and dirty
    wsCode.WriteLiteralAssignment('CookiesPath', '/')
    wsCode.WriteLiteralAssignment('CookiesExpireDays', 7)
    wsCode.WriteComment("")
    for wsThisApacheSiteResourceObject in wsConfiguration.apacheSites.sortedvalues():
        # Uri prefix removed to maintain compatibiity with existing hobby engineering site. Once this
        # configuration process is working, its probably a good idea to put it back.
        wsPathInfoVariableName = wsThisApacheSiteResourceObject.apacheSiteRefname
        wsCode.WriteLiteralAssignment(
            wsPathInfoVariableName, wsThisApacheSiteResourceObject.resolvedUri)
    #
    wsCode.WriteComment("")
    wsCode.WriteComment("Apache Directory Resources")
    wsCode.WriteComment("")
    for wsDirectoryReference in wsConfiguration.directoryList:
        wsDirectoryObject = wsConfiguration.directories[wsDirectoryReference]
        if wsDirectoryObject.apacheSiteResource is None:
            continue
        wsPathInfoVariableName = 'Uri' + wsDirectoryObject.referenceName
        wsCode.WriteLiteralAssignment(
            wsPathInfoVariableName, wsDirectoryObject.resolvedUri)
    #
    wsCode.WriteComment("")
    wsCode.WriteComment("Apache CGI Programs")
    wsCode.WriteComment("")
    for wsThisExecutableRefname in wsConfiguration.executableRefnames:
        wsExecutableResourceObject = wsConfiguration.executables[wsThisExecutableRefname]
        if wsExecutableResourceObject.apacheSiteResource is not None:
            wsPathInfoVariableName = 'UriCgi' + wsExecutableResourceObject.executableRefname
            wsCode.WriteLiteralAssignment(
                wsPathInfoVariableName, wsExecutableResourceObject.resolvedUri)
            # for wsThisSiteCommandResource in wsExecutableResourceObject.executablesCommands:
            #  wsCode.WriteLiteralAssignment(wsThisSiteCommandResource.referenceName,
            #		"%s?%s=%s" % (wsExecutableResourceObject.resolvedUri, bafExeController.CoreCommandSelectorCgiKeyword,
            #				wsThisSiteCommandResource.selector))
    #
    if not wsCode.Close():
        PrintError("Unable to close or set permissions for  %s file '%s'" %
                   (parmResource.referenceName, parmResource.resolvedPath))

#
# MakePathInfo
#


def GeneratePathInfoFile(parmResource):
    # Directory names in p:athInfo.py end with a slash because
    #	- I started and prefer it that way
    #	- bzUtil.py and existing code expect it that way and are easy to read
    #
    # Most directory variables within this module lack the slash because
    #	they use the native Python os actions
    #
    # pathInfo.py should be as small as practical. It should contain only:
    #	- information needed to initialize the apllication, before
    #		databases have been created or populated.
    #	- information needed to recover from errors when databases
    #		are not available
    #     - constatn data: pathInfo.py should hardly ever have to be
    #		updated
    #
    # pathInfo has a mapping of application reference names / actional names to physical databases
    #	and tables. Right now thatis is a 1:1 mapping and the only difference between reference
    #	names and table names is capitalization which doesn't matter because the lookup
    #	is not case senstive. To fully implement we need more site configuration to identify
    #	local details AND all code must be converted to clearly use reference names instead of table
    #	names. This will happen as we go to tables created from the model instead of the model
    #	derived from the tables. For now, the two names are treated confusingly interchangeable.
    #
    # All the variable names in this module need to be provided by constants not by literals.
    #
    # These constants need to come for the application definition
    wsConfiguration = parmResource.configuration			# typing shortcut
    wsBootIniData = wsConfiguration.bootIniData			# typing shortcut

    wsF = OpenResourceOutputFile(parmResource)
    if wsF is None:
        PrintError("Unable to open %s file '%s'" %
                   (parmResource.referenceName, parmResource.resolvedPath))
        return

    wsF.write("#\n")
    wsF.write("import pylib.bafNv      as bafNv\n")
    wsF.write("#\n")

    #
    # Write DB access information. This needs to be more generic and more secure
    #	and not hard wired for one app, BFS.
    #
    # Also needs reverse lookups for symbols instead of using literal codes.
    #
    # ErDatabaseTypeFiles databases will end up with 'NONE' for user, password, etc.
    #	that should be changed to simply NONE by the codewriter. Its OK for now.
    #
    wsF.write("DbNames              = bafNv.bafNvTuple()\n")

    for wsThis in list(wsConfiguration.dbs.values()):
        wsSchemaFilePath = wsThis.dbRefname + '.xpdi'
        # wsObjectWriter			= bafObject.bafObjectUnloader(
#						ExeController=wsConfiguration.exeController,
#						FileName=wsSchemaFilePath,
#						Source=wsThis.dbConnection.schema)
#   wsConfiguration.exeController.SetCgiFilePermissions(wsSchemaFilePath)
        wsValueDict = {
            'DbRefname':		wsThis.dbRefname,
            'ServerName':		wsThis.serverName,
            'DbName':		wsThis.dbName,
            'UserName':		wsThis.userName,
            'Password':		wsThis.password,
            'DbType':		wsThis.dbType,
            'Path':			wsThis.resolvedPath
        }
        wsF.write("DbNames['%s'] = %s" % (wsThis.dbRefname,
                                          bafExpCodeWriter.MakePythonDictLiteral(wsValueDict)))

    #
    # Write DB table information. This is intermediate DTD that is not used too much and needs to go away
    # after migrating to MDDL and other model based capabilities are implemented. This is driven by
    # DTD created by bfsDbGen.
    #
    wsF.write("#\n")
    wsF.write("TableNames              = bafNv.bafNvTuple()\n")
    for wsThis in list(wsConfiguration.dbTables.values()):
        wsDataDirPath = ''
        if wsThis.dbResource.dbType == bafRdbms.DbTypeFiles:
            wsDataDirPath = wsConfiguration.directories[wsThis.dataDirResourceName].resolvedPath
        wsValueDict = {
            'DbRefname':		wsThis.dbResource.dbRefname,
            'DbTableRefname':	wsThis.dbTableRefname,
            'TableName':		wsThis.dbTableName,
            'DataDirPath':		wsDataDirPath,
            'DataExt':		wsThis.dataExt,
            'ModelClassRefname':	wsThis.modelClassRefname
        }
        wsF.write("TableNames['%s'] = %s" % (
            wsThis.dbTableRefname, bafExpCodeWriter.MakePythonDictLiteral(wsValueDict)))
    wsF.write("#\n")

    wsF.write("#\n")
    wsF.write("# Constant Resources\n")
    wsF.write("#\n")
    for wsThisConstantResourceObject in wsConfiguration.constants.sortedvalues():
        wsPathInfoVariableName = wsThisConstantResourceObject.referenceName
        wsF.write("%-20s  = '%s'\n" % (wsPathInfoVariableName,
                                       wsThisConstantResourceObject.resolvedValue))

    wsF.write("#\n")
    wsF.write("# Package Resources\n")
    wsF.write("#\n")
    for wsPackageReference in wsConfiguration.pythonPackageList:
        wsPackageObject = wsConfiguration.pythonPackages[wsPackageReference]
        wsPathInfoVariableName = wsPackageObject.referenceName + 'PackageName'
        wsF.write("%-20s  = '%s'\n" %
                  (wsPathInfoVariableName, wsPackageObject.resolvedName))
    for wsThisFileResource in list(wsConfiguration.files.values()):
        if not wsThisFileResource.isPythonModule:
            continue
        wsPackageResource = wsThisFileResource.directory.pythonPackageResource
        if wsPackageResource is not None:
            wsF.write("%-20s  = ('%s', '%s')\n" % (wsThisFileResource.resolvedNameBase + 'ModuleName',
                                                   wsPackageResource.resolvedName,
                                                   wsThisFileResource.resolvedNameBase))

    wsF.write("#\n")
    wsF.write("# File System Directory Resources\n")
    wsF.write("#\n")
    for wsDirectoryReference in wsConfiguration.directoryList:
        wsDirectoryObject = wsConfiguration.directories[wsDirectoryReference]
        wsPathInfoVariableName = wsDirectoryObject.referenceName + 'Path'
        wsF.write("%-20s  = '%s'\n" % (wsPathInfoVariableName,
                                       bzUtil.CleanSlashes(wsDirectoryObject.resolvedPath)))

    wsF.write("#\n")
    wsF.write("# File Resources\n")
    wsF.write("#\n")
    for wsThisFileResourceObject in wsConfiguration.files.sortedvalues():
        wsPathInfoVariableName = wsThisFileResourceObject.referenceName + 'File'
        wsF.write("%-20s  = '%s'\n" % (wsPathInfoVariableName,
                                       wsThisFileResourceObject.resolvedPath))

    # This should really be more generalized to allow any number of levels,
    # but this is good enough for now and this whole PathInfo generation should probably
    # be generalized as part of generalizing all resources ...
    wsBootIniChildRecordVariables = []
    wsF.write("#\n")
    wsF.write("# BootIni Variables []\n")
    wsF.write("#\n")
    for (wsBootIniDataName, wsBootIniDataValue) in list(wsConfiguration.bootIniData.items()):
        if isinstance(wsBootIniDataValue, bafDataStore.bafTupleObject):
            wsBootIniChildRecordVariables.append(
                (wsBootIniDataName, wsBootIniDataValue))
        else:
            wsVariableName = "INI_" + wsBootIniDataName
            wsF.write("%-20s  = '%s'\n" % (wsVariableName, wsBootIniDataValue))
    for (wsThisBootIniSection, wsThisBootIniChildRecord) in wsBootIniChildRecordVariables:
        wsF.write("# BootIni Variables [%s]\n" %
                  (wsThisBootIniChildRecord._path))
        for (wsBootIniChildDataName, wsBootIniChildDataValue) in list(wsThisBootIniChildRecord.items()):
            wsVariableName = "INI_" + wsThisBootIniSection + "_" + wsBootIniChildDataName
            wsF.write("%-20s  = '%s'\n" %
                      (wsVariableName, wsBootIniChildDataValue))

    wsF.write("#\n")
    CloseTextFile(wsConfiguration, wsF, parmResource.resolvedPath)


def OpenTextFile(parmPath, parmMode):
    wsF = bzTextFile.OpenBzTextFile(parmPath, parmMode, Temp=True)
    return wsF


def CloseTextFile(parmConfiguration, parmF, parmPath):
    if parmF is None:
        PrintError("CloseTextFile() file '%s' not open" % (parmPath))
        return
    else:
        parmF.TempClose()

    try:
        parmConfiguration.exeController.SetCgiFilePermissions(parmPath)
    except:
        # We can get here for a variety of reasons during start-up.
        # Just try and do the best possible configuaration at this point.
        os.chmod(parmPath, stat.S_IRUSR | stat.S_IXUSR)
        if StartupMode != StartupDirect:
            PrintError('Unable to set permissions for %s' % (parmPath))


def MakeDirectoriesAndLinks(parmConfiguration):
    #
    # Create directory if needed.
    # Set direcotry permissions.
    # Create links needed for program program directories,
    #		plus some conventory WWW Root links
    #
    # First make the Site Run Directory (WWW root) convenience Links
    for wsThisDirectory in list(parmConfiguration.directories.values()):
        if not wsThisDirectory.isSiteRunConvenienceDirectory:
            # Only make links to base directories
            continue
        if wsThisDirectory.isSiteRunDirectory:
            # don't make a link to itself
            continue
        MakeSymlinkToDirectory(parmConfiguration.siteRunDirectoryResource.resolvedPath, wsThisDirectory.referenceName,
                               wsThisDirectory.resolvedPath, '')
    #
    # Now make all other needed directories and create any needed links
    #
    for wsThisDirectoryKeyName in parmConfiguration.directoryList:
        wsDirectoryObject = parmConfiguration.directories[wsThisDirectoryKeyName]
        if not wsDirectoryObject.resolvedPath:
            PrintError("%s: path not defined" %
                       (wsDirectoryObject.referenceName))
            continue
        else:
            PrintStatus("%s: Path '%s'" % (
                wsDirectoryObject.referenceName, wsDirectoryObject.resolvedPath))
        if os.path.exists(wsDirectoryObject.resolvedPath):
            if not os.path.isdir(wsDirectoryObject.resolvedPath):
                PrintError("%s: Path '%s' exists but is not a directory" % (
                    wsDirectoryObject.referenceName, wsDirectoryObject.resolvedPath))
        else:
            if wsDirectoryObject.isAutoCreate:
                os.mkdir(wsDirectoryObject.resolvedPath)
                if not os.path.isdir(wsDirectoryObject.resolvedPath):
                    PrintError("%s: Unable to create directory '%s'" % (
                        wsDirectoryObject.referenceName, wsDirectoryObject.resolvedPath))
            else:
                PrintError("%s: directory '%s' does not exists" % (
                    wsDirectoryObject.referenceName, wsDirectoryObject.resolvedPath))
        #
        # Configure Python Run directories
        #
        # Need symlinks to python packages and synthesized modules
        #
        # Package directories need these during configuration for __import__() to work
        #
        if wsDirectoryObject.isPythonProgramRunDirectory:
            for wsPythonPackageResourceObject in list(parmConfiguration.pythonPackages.values()):
                wsPythonPackageDirectoryObject = wsPythonPackageResourceObject.directory
                if wsPythonPackageDirectoryObject.referenceName == wsDirectoryObject.referenceName:
                    # don't reference itself
                    continue
                MakeSymlinkToDirectory(wsDirectoryObject.resolvedPath, wsPythonPackageDirectoryObject.resolvedName,
                                       wsPythonPackageDirectoryObject.resolvedPath, '')
            for wsThisFileResourceObject in list(parmConfiguration.files.values()):
                if wsThisFileResourceObject.isRunDirSymlinkFile:
                    MakeSymlinkToFile(wsDirectoryObject.resolvedPath, wsThisFileResourceObject.resolvedName,
                                      wsThisFileResourceObject.resolvedPath, '')
        #
        # Configure Python Package directories
        #
        # Need __init__.py file
        #
        if wsDirectoryObject.isPythonPackageDirectory:
            wsInitModulePath = os.path.join(
                wsDirectoryObject.resolvedPath, PackageInitModuleName)
            if not os.path.exists(wsInitModulePath):
                wsF = OpenTextFile(wsInitModulePath, "w")
                CloseTextFile(parmConfiguration, wsF, wsInitModulePath)
    #
    # Now make needed files
    #
    # This is pretty crude now, but it would be fairly easy to add a mechanism to
    # put more into the files, using code from the packages / directories since
    # those are all identified at this point.
    #
    for wsThisFileResourceObject in list(parmConfiguration.files.values()):
        wsFilePath = wsThisFileResourceObject.resolvedPath
        if os.path.exists(wsFilePath):
            if os.path.isfile(wsFilePath):
                continue						# Good!
            else:
                PrintWarning(
                    "File name '%s' exists but is not a file." % (wsFilePath))
        else:
            if wsThisFileResourceObject.isAutoCreate:
                wsF = OpenTextFile(wsFilePath, "w")
                if wsThisFileResourceObject.isPythonModule:
                    wsF.write('pass\n')
                CloseTextFile(parmConfiguration, wsF, wsInitModulePath)
            else:
                PrintWarning("File '%s' does not exist." % (wsFilePath))


def MakeModuleAndProgramStubs(parmConfiguration, Verbose=False):
    if Verbose:
        PrintStatus("Making %d Stubs" % (len(parmConfiguration.executables)))
    MakePythonExecutionStub(parmConfiguration)						# testimport
    for wsThisProgramObject in list(parmConfiguration.executables.values()):
        if Verbose:
            PrintStatus("Making Stub: %s" % (
                wsThisProgramObject.primaryModuleResourceObject.pythonModuleName))
        MakePythonExecutionStub(parmConfiguration, wsThisProgramObject)
    MakePythonExecutionStub(parmConfiguration, IsHelp=True)				# help


def ScanForProblems(parmConfiguration):
    #
    # Check executable directories and look for extra stuff.
    # That could possibly signify a configuration failure or break-in.
    # Right now just look at file names, it would be even better to look at file
    # types and contents.
    #
    wsExpectedPackageAndFileLinks = []
    for wsThisPackageKeyName in parmConfiguration.pythonPackageList:
        wsPackageObject = parmConfiguration.pythonPackages[wsThisPackageKeyName]
        wsExpectedPackageAndFileLinks.append(wsPackageObject.resolvedName)
        # wsExpectedPackageAndFileLinks.append(PathInfoModuleName.lower())
        # wsExpectedPackageAndFileLinks.append(PathInfoModuleNameC.lower())
    for wsThisDirectoryKeyName in parmConfiguration.directoryList:
        wsDirectoryObject = parmConfiguration.directories[wsThisDirectoryKeyName]
        if wsDirectoryObject.isApacheCgiDirectory:
            if "progm" in wsDirectoryObject.resolvedPath:
                continue
            if "cgim" in wsDirectoryObject.resolvedPath:
                continue
            wsFileNameList = os.listdir(wsDirectoryObject.resolvedPath)
            for wsThisFileName in wsFileNameList:
                wsThisFileNameLc = wsThisFileName.lower()
                if wsThisFileNameLc in wsExpectedPackageAndFileLinks:
                    continue
                if wsThisFileNameLc in parmConfiguration.executables:
                    continue
                PrintError('Unexpected file "%s" in executable directory "%s"' % (
                    wsThisFileName, wsDirectoryObject.resolvedPath),
                    IsWarningOnly=True)


def Main(ExeController=None):
    global StartupMode
    # It is called Main() so it can use the "old style" startup style as a bootstrap
    # until more of the environment is configured.
    #
    # We might get here because a password was changed or other routine
    # DB problem. Need to be as non-destructive as possible of pathInfo data.
    #
    if StartupMode == StartupUnknown:
        # We didn't start with __name__ == "__main__" so we must have been called
        # by the program stub.
        StartupMode = StartupStub
    #
    PrintStatus('Biznode Application Framework - Application Configuration')
    PrintStatus('System Timestamp is ' + bzUtil.NowYMDHM())
    if StartupMode == StartupStub:
        PrintStatus('Startup Mode Normal')
    elif StartupMode == StartupDirect:
        PrintStatus('Startup Mode Direct')
    else:
        PrintStatus('Startup Mode Unknown')
    PrintStatus('ExeController class: ' + ExeController.__class__.__name__)
    #
    #
    wsVerbose = False
    wsVerbose = True
    wsConfiguration = bafConfiguration(
        ExeController=ExeController, Verbose=wsVerbose)
    if ConfigErrorCt > 0:
        PrintStatus(
            '**** %d errors. Unable to initialize configuration.' % (ConfigErrorCt))
        return
    #
    # Initialize The Site
    # Always create links because lack of links can be the cause of
    # the configuration initialization errors.
    #
    PrintStatus('Boot INI Path: ' + repr(wsConfiguration.bootIniFilePath))
    wsConfiguration.LoadCurrentConfiguration()
    MakeDirectoriesAndLinks(wsConfiguration)
    PrintStatus('Running BAF Source Path: ' +
                wsConfiguration.env.package_parent_directory)
    PrintStatus('Running Site Run Path: ' + wsConfiguration.env.execution_cwd)
    wsConfiguration.exeController.errs.PrintText()
    if ConfigErrorCt > 0:
        PrintStatus('**** %d errors. Unable to continue.' % (ConfigErrorCt))
        return
    if not bzDataEdit.ConsoleAskYesNo('Do you want to configure this site?'):
        return

    wsConfiguration.SaveConfiguration()
    wsConfiguration.GenerateAllFiles()
    MakeSiteDefinintionDb(ExeController=ExeController)
    MakeModuleAndProgramStubs(wsConfiguration, Verbose=wsVerbose)
    wsConfiguration.PerformTasks(ConfigNoDependencies)
    #MakeApacheSiteConfig(wsConfData, wsConfiguration)
    ScanForProblems(wsConfiguration)
    PrintStatus('Initialization successful.')


def InitializeNormalMode():
    PrintStatus('BFS System - Application Initialization Normal Mode')
    MakePathInfo(pathInfo.PathInfoModulePath, pathInfo.__dict__)
    PrintStatus('Initialization Normal Mode successful.')
    sys.exit(0)

"""

#
# cnutils/configure.py
#
# 10/5/2019 Clone BAF pylib/bzConfigure.py
#

SymlinkTypeDir = 1
SymlinkTypeFile = 2


cli_options = []
cli_options.append(("d", "lib", "symlink library"))

if __name__ == "__main__":
    # StartupMode = StartupDirect
    # Main()
    env = configutils.ExecutionEnvironment(__name__)
    if not env.check_version():
        sys.exit(-1)
    resp = cliinput.cli_input("Do you want to initialize or repair this site?", "yn")
    if resp.lower() == "y":
        print("yes")
    else:
        print("no")
    cli.cli_run()
