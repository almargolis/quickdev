#
# bafExeController - program start-up environment
#
#   Provides a platform independent program environment for programs.
#

from . import bafDataStore
from . import bafObject
from . import bafTupleDictionary
from . import bafErTypes
from . import bafNv

from . import bzCmdArgs
from . import bzConsole
from . import bzContent
from . import bzDataEdit
from . import bzErrors
from . import bzFileDb
from . import bzHtml
from . import bzLex
from . import bzMime
from . import bafRdbms
from . import bzStyles
from . import bzTextFile
from . import bzUtil

import codecs
import grp
import json
import os
import pwd
import string
import sys
import syslog
import time
import types

ModeCgi					= 'W'
ModeConsole				= 'C'
ModeDaemon				= 'D'
ModeUnknown				= 'U'

MAGICKEY				= "S1l0gram"
SIGNATURE_SEED				= "tyhH0bbie987zxcvb"
CGI_KEY_FILTER				= bzUtil.LETTERSANDNUMBERS+"-_."

CoreCommandSelectorCgiKeyword		= 'FUNC'
CoreCommandMConvKeyword			= 'MCONV'
CoreCommandReservedGetParms		= [CoreCommandSelectorCgiKeyword, CoreCommandMConvKeyword]

CommandLineStateScan			= 0
CommandLineStateEqSign			= 1
CommandLineStateValue			= 2

ContentIndexTableName			= 'ContentIndex'		# this should really be from pathInfo, etc.
ContentSourceCatalogSku			= 'ProdPage'
ContentTypeProductPage			= 'ProdPage'
ContentTypeProductImage100		= '100px'
ContentTypeProductImage200		= '200px'

GlobalCommands_HelpSwitch		= 'h'
GlobalCommands_HelpFunctionCode		= 'HELP'
GlobalCommands_ConsoleHtmlSwitch	= 'x'
GlobalCommands_PromptSelectorSwitch	= 'z'

SessionUrlKey				= "SC"
ActivityIdCookieKey			= "ActivityId"
SessionCookieKey			= "Session"
SessionFormKey				= "zSession"

SessionCookiesEnabled			= 'E'
SessionCookiesDisabled			= 'D'
SessionCookiesUnknown			= 'U'

CookieStatusNewNormal			= 'A'
CookieStatusSetNormal			= 'B'
CookieStatusNewOffline			= 'C'
CookieStatusSetOffline			= 'D'

RestfulVerb_Unknown			= "?"
RestfulVerb_Post			= "POST"
RestfulVerb_Get				= "GET"
RestfulVerb_Put				= "POST"
RestfulVerb_Delete			= "DELETE"

SESSION_COOKIE_NAME = "qd_session_id"

HTMLPERMISSIONS				= 0o744
DIRPERMISSIONS				= 0o755
CGIPERMISSIONS				= 0o700

TriggerMethodNamePrefix			= 'Trigger'
TriggerDataSelector			= 'S'
TriggerDataForm				= 'F'

def bafConfigureModule(parmModuleResource):
  from . import bzConfigure			as bzConfigure
  wsConfiguration			= parmModuleResource.configuration
  wsSiteExecutableResourceObject	= bzConfigure.bafSiteExecutableResource(parmModuleResource,
						ExecutableName='login.cgi')
  # This probably shouldn't be a literal 'SecureWebsite'
  wsSiteExecutableResourceObject.ConfigureAsCgi(SiteRefname='SecureWebsite')
  wsSiteExecutableResourceObject.AddCommand('AdminLoginAction')
  parmModuleResource.configuration.AddExecutable(wsSiteExecutableResourceObject)

#
# IsCgi() and IsSLL() are probably not needed any more and
# may not be functional.
#

def IsCgi():
  wsCgiGatewayInterface = bzUtil.GetEnv("GATEWAY_INTERFACE")
  if wsCgiGatewayInterface == "":
    return False
  else:
    return True

def IsSsl():
  wsServerPort = bzUtil.GetEnv("SERVER_PORT")
  wsServerHttps = bzUtil.GetEnv("HTTPS")
  if (wsServerPort == "443"): wsServerHttps = "on"    # force Apache 1.2 SUEXEC bug
  if (wsServerPort == "443") and (wsServerHttps == "on"):
    return True
  else:
    return False


#
# Around 1964 IBM announced the System 360 Series of computers including a
# new operating system dubbed OS/360. Among the promised features was the
# ability to run programs on any computer in the series without modification.
# That was an ambitious goal that was never quite delivered.
#
# IBM probably wasn't the first developer to set that goal and they definately
# weren't the last. The most recent major candidate who's objective of
# "Write Once, Run Anywere" was delivered more like "Write Once, Run In Some Places."
#
# The BZ System is my attempt to work toward that goal.
#
# Everything is the BZ System is an object.
#
# The "main" program objects in BZ System applications is are considered clients.
# ActionHelper objects are considered services. Services include I/O managers and
# formatters, data structures, etc.
# This naming is taken from the persepctive of the software system.
# The "main" program is the client and the helper objects provide services
# to the client.
#
# pylib is an abstract library of data definitions and low level services.
# All modules in pylib are named bzXXXXXX as are the classes defined in
# the module. The intent is that pylib capabilities are not application
# specific.
#
# Class bafActionDef is used within client modules to expose their user actionality.
#
# All client actions descend from bafActionDef. Many service objects have a
# property called exeAction which identifies the client and provides access to
# co-services. This minimizes the need for global variables and allows
# clients to provide a unique environment if needed. Higher level services may
# require assignment of exeAction during initialization because they are expected to
# be used only in the context of an application. Lower level services may make
# exeAction optional in order to simplify use of the services in ad-hoc,
# stand-alone programs.
#
# One of the critical services mapped through exeAction is a standardized error
# handling and logging service. The error system provides a standard way to
# capture error messages and related output. This interacts with the security
# system to prevent the leakage of sensitive trace/debugging information to
# non-priveledged users for PCI DSS compiance while making that information
# easily available when needed for trouble shooting. If a service reaches a
# critical error state, it should will use the exeAction error display
# if assigned or raise an exception if no exeAction is assigned.
#
# All BFS actionality is coded within modules that are not directly executed
# by users. These modules modules reside in the bfslib directory.
#
# BFS executable programs are stubs created in the prog and cgi directories by the
# BFS configuration system. This helps assure that all programs use a common system
# of start-up security and data handling.
#
# BFS programs use a flexible UI that allows any program to be executed from the
# web, command line or a test fixture without modification and with little or no
# UI conditional programming. The only reason to have a separate cgi directory
# is to help prevent the possibility of certain actions from being executed via
# the web.
#
# Each BFS module can generate any number of executable programs (including none).
# Executable programs are defined by specially named variables in the module global
# address space.
#
# Each possible action of an executable program is defined by a bfsCommand object.
#
# Executable commands are actions. They take input data, perform
# some action and return a result.
#
# Each invocation of an executable program executes one command.
#
# A mechanism is provided in each program environment to identify the
# particular command to be invoked. If an executable exposes just one
# command, that command is executed without requiring a selector.
#
# The command program environment has x sepearate data spaces. The are
# defined by the HTTP/HTML protocols but fully emulated in all runtime
# environments so programs do not have to condition data access based on
# runtime environment. A mechanism is provided to capture data for
# analysis and testing. The data spaces are:
#   Get: generally command line data
#   Post: generally user form input data
#   Cookies: generally user state data
# Get and Post data are scrubbed of certain characters to minimize the
# opportunity for injection/scripting type system attacks. GetRaw and
# PostRaw contain the original data for applications that require them.
#
# The runtime environment uses this information for
#	- configure the environment so the same command can be used as CGI,
#		command line or in a test fixture with stored input.
#	- documentation and help
#

#
# An Action is the basic unit of program for BAF sites.
#
# An Action definition is alot like a class definition: a description of
# the action instigation data and rules (code) describing what to do with
# that data.
#
# Each action must have a globally unique reference name within the site.
# With this Python implementation, that is defined as the class name.
# It may be defined differently for other implementations.
#
# Within a RESTful implementation, bafActions are RESTful endpoints
# and bafCommandTriggers are RESTful/HTTP methods. A bafActionDef
# can service both computer-to-computer API services and interactive
# browser services. If the payload for a POST request is an HTML form.
# the name of the submit button clicked is used to map to
# PUT, PATCH or DELETE triggers/verbs that are not supported by browsers.
# Actions can have multiple triggers per RESTful method as a browser
# user convenience. These essentially imply frequently used data
# values or patterns, saving the user from repetative typing.
#
# In order to support CLI operations and API testing from browsers,
# payload data, including buttons/triggers, can be provided as named
# parameters. Therefore, any operations can be performed as a browswer
# GET URL or CLI command, although in some cases this can impractical
# due to difficulty of typing or CLI or URL lenght limitations.
# This can also result in sensitive data being cached or logged.
# This universal translation can be restricted in production environments.
#
# Not all bafActions are RESTful. RESTFUL works well for CRUD type
# operations, not so well for batch process operations. bafActions
# support non-RESTful browser applications and CLI-only processes.
#
# POST
# GET
# PUT
# PATCH
# DELETE
#

OutputHtml			= 'H'
OutputJson			= 'J'
OutputXml			= 'X'

class bafActionDef(object):
  __slots__ = (
			'actionClassName',
			'actionRequestTDict',
			'actionRequestTuple',
			'actionRefname',
			'actionSwitch',
			'actionUseStandardPage',
			'cmdDisplayFields',
			'cmdFormCt',
			'cmdFormFocusField',
			'cmdPayloadTuple',
			'cmdPayloadTupleStoreName',
			'cmdPayloadTDict',
			'cmdOutputFormat',
			'cmdPrimaryTableReferenceName',
			'cmdSelectionKey',
			'confirmationCommand',
			'confirmationNeeded',
			'debug',
			'description',
			'defaultCommandSelector',
			'defaultCommandRefname',
			'defaultCommandSwitch',
			'exeController',
			'inPrograms',
			'isAutoGenerateCommand',
			'isConfirmed',
			'isMeYN',
			'isOldStyleCgi',
			'runCommandLine',
			'runCommandRefname',
			'runExecutableInfo',
			'runIsInvalidCommand',
			'runTriggerInfo'
		)

  def __init__(self, parmDescription=None, ActionRefname=None, ExeController=None):
    self.actionClassName			= self.__class__.__name__
    self.actionRefname				= ActionRefname
    if self.actionRefname is None:
      self.actionRefname			= self.actionClassName
    self.exeController				= ExeController
    self.debug					= 0
    #
    # These describe the context of the executing action.
    #
    self.inPrograms				= []					# list of module programs where allowed, [] for all
    self.defaultCommandSelector			= None
    self.defaultCommandRefname			= None
    self.defaultCommandSwitch			= None
    self.description				= parmDescription
    self.confirmationCommand			= ''
    self.confirmationNeeded			= False
    self.isAutoGenerateCommand			= True
    self.isMeYN					= 'N'
    self.isOldStyleCgi				= False
    self.isConfirmed				= False
    #
    # Initial Data
    #
    # There are several redundant data stores (I think).
    # All new work uses actionRequestTDict/Store/Ct. Need to add Raw for cgi (maybe even command line)
    #
    self.actionRequestTDict			= bafTupleDictionary.bafTupleDictionary(
							Name='ActionRequest',
							PrimaryDataPhysicalType=bafErTypes.Core_MapBafTypeCode)
    self.actionRequestTuple			= None
    self.actionUseStandardPage			= True
    self.cmdPayloadTuple			= None
    self.cmdPayloadTupleStoreName		= None
    self.cmdPayloadTDict			= None
    self.cmdFormFocusField			= None
    self.cmdDisplayFields			= None
    self.cmdPrimaryTableReferenceName		= ""
    self.cmdSelectionKey			= ""
    self.cmdFormCt				= None
    self.cmdOutputFormat			= OutputHtml
    self.FindTriggers()
    #
    # A CommandObject is an ActionObject with the run variables initialized for a particular command execution.
    #
    self.runCommandLine				= None
    self.runCommandRefname			= None		# the command being executed
    self.runExecutableInfo			= None
    self.runTriggerInfo				= None
    self.runIsInvalidCommand			= False

  def Run(self):
    # This is mainly a place holder. It should only get called if bafExeController.CreateCommandObject() creates an
    # error action
    self.exeController.errs.AddUserInfoMessage('Default Action Executed')
    self.exeController.errs.AddUserInfoMessage("Mode: {CgiMode}, Type: {CmdType}".format(
						CgiMode=self.exeController.mode,
						CmdType=self.cmdType
						))

  def AssignFormFocus(self, parmFormField):
    self.cmdFormFocusField			= parmFormField

  def Triggers(self):
    wsTriggers					= []
    for wsThis in self.actionRequestTDict.Elements():
      if wsThis.roleType != bafErTypes.Core_TriggerRoleCode:
        continue
      if wsThis.processMethodName is None:
        continue
      wsTriggers.append(wsThis)
    return wsTriggers

  def FindTriggers(self):
    for wsThisKey in dir(self):
      wsThisAttrib				= getattr(self, wsThisKey, None)
      if not isinstance(wsThisAttrib, types.MethodType):
        continue
      wsParts					= wsThisKey.split('_')
      if len(wsParts) < 3:
        continue
      if wsParts[0] != TriggerMethodNamePrefix:
        continue
      wsTriggerDataSource			= wsParts[1][0]
      if wsTriggerDataSource not in [TriggerDataSelector, TriggerDataForm]:
        continue
      wsFormCt					= wsParts[1][1:]
      wsTriggerOrder				= ""
      if len(wsFormCt) > 1:
        wsTriggerOrder				= wsFormCt[1:]
        wsFormCt				= wsFormCt[0]
      if wsFormCt in ["", "0"]:
        wsFormCt				= None
      else:
        wsFormCt				= bzUtil.Int(wsFormCt)
      wsTriggerOrder				= bzUtil.Int(wsTriggerOrder)
      wsCaption					= wsParts[2]
      wsName					= wsParts[2]
      for wsThisPart in wsParts[3:]:
        wsCaption				+= ' ' + wsThisPart
        wsName					+= wsThisPart
      wsTriggerInfo				= self.AddTrigger(
							TriggerName=wsName,
							TriggerMethodName=wsThisKey,
							FormCt=wsFormCt,
							Caption=wsCaption,
							Order=wsTriggerOrder,
							DataSource=wsTriggerDataSource)

  def AddTrigger(self, TriggerName=None, TriggerMethodName=None, Caption=None,
							FormCt=None, ID=None, Order=0,
							DataSource=TriggerDataSelector):
    wsTrigger					= self.actionRequestTDict.AddScalarElementBoolean(
							TriggerName,
							Caption=Caption,
							DisplayOrder=Order,
							FormCt=FormCt,
							RoleType=bafErTypes.Core_TriggerRoleCode
						)
    # ID=ID, never used, so drop when moving from trigger class to tuple element
    # DataSource=DataSource probably not needed / maybe a bad idea
    wsTrigger.processMethodName			= TriggerMethodName
    return wsTrigger

  def SetDebugLevel(self, parmDebugLevel):
    self.debug					= parmDebugLevel

  def CreatePayloadTDict(self):
    self.cmdPayloadTDict				= bafTupleDictionary.bafTupleDictionary(
							Name='ActionForm',
							PrimaryDataPhysicalType=bafErTypes.Core_MapBafTypeCode)

  #
  # The following are convenience action to configure certain kinds of common commands.
  # They are followed by corresponding DoCmdXXX actions that implement the commands.
  # This both reduces code volume and assures consistency.
  # A few of these are are executed from the global runtime object.
  # Individual modules don't have to specifically implement help, security and other
  # actions that must be done in every module.
  #
  def ConfigureAsConfirmed(self, State=True):
    self.isConfirmed				= State

  def ConfigureAsConfirmationNeeded(self, State=True):
    self.confirmationNeeded			= State

  def SaveState(self):
    wsStateFn					= os.path.join(self.exeController.pathInfo.DataPath, 'ExState')
    wsExecutionState				= {
							'Request':	self.actionRequestTuple,
							'Payload':	self.cmdPayloadTuple
						}
    wsDumper					= bafObject.bafObjectDumper(FileName=wsStateFn, ExeController=self.exeController, Source=wsExecutionState, SourceName=None)
    return
    wsExecutionState			= {}
    if self.actionRequestTuple is None:
      wsExecutionState['Request']		= None
    else:
      wsExecutionState['Request']		= list(self.actionRequestTuple.items()),
    if self.cmdPayloadTuple is None:
      wsExecutionState['Payload']		= None
    else:
      wsExecutionState['Payload']		= list(self.cmdPayloadTuple.items())
    wsF						= codecs.open(wsStateFn, mode='w', encoding='utf-8')
    wsF.write(json.dumps(wsExecutionState))
    wsF.close()

  # bafActionDef
  # Calls of Execute() should be wrapped in an except clause.
  #
  # This does the function work of the action.
  #
  # CmdTypeCustom actions do what they need and disply what they need with little
  # automatically done here.
  #
  # Other actions work with little or no specific code in the action. The primary
  # definition of the action is the data model or models.
  #
  # The actionRequestTDict is used to determine which record is to be processed.
  # It also defines the command line.
  #
  # The cmdPayloadTDict model defines the record being processed. It is often a
  # database record definition and part of a schema.
  #
  def Execute(self):
    #
    # Initialize Output Page
    #
    #print "EEE", self.cmdType, self.exeController.printHtml, self.actionUseStandardPage
    if self.actionUseStandardPage:
      if self.exeController.siteFormatsModule is None:
        wsStandardDocsFunction			= None
      else:
        wsStandardDocsFunction			= getattr(self.exeController.siteFormatsModule, 'MakeStandardDocumentFormat', None)
      if wsStandardDocsFunction is None:
        wsBodySegment				= self.exeController.aContext.NewOutline(OutlineName='Content')
        self.exeController.aContext.DefineBodySegment(wsBodySegment)
      else:
        wsStandardDocsFunction(self.exeController.aContext)
    #
    # The actionRequestTDict data is always marshalled.
    #
    self.actionRequestTuple			= bafDataStore.bafTupleObject()
    self.actionRequestTDict.SafeCopy(self.actionRequestTuple,
							self.exeController.cgiGetDataRaw,
							Source2=self.exeController.cgiPostDataRaw)
    self.actionRequestTDict.ValidateTuple(self.actionRequestTuple, ExeController=self.exeController)
    if self.cmdType == CmdTypeCustom:
      self.Run()
      return
    #
    # Check Trigger
    #
    self.runTriggerInfo				= None
    if self.actionRequestTDict.HasElement(self.exeController.cgiButtonName):
      self.runTriggerInfo			= self.actionRequestTDict.Element(self.exeController.cgiButtonName)
    #elif (self.exeController.mode != ModeCgi) and (len(self.cmdTriggers) == 1):
      # need to rejigger - triggers are now just a data element so problem can go away
      #pass
      # This from the command line where we don't have buttons, so assume the only option.
      # If cgi, the default action is to fall through and display a blank form.
    #
    # A trigger has been identified. That tells us which data model to
    # use. The default is the selector model. Now validate the data.
    #
    # bzContent looks at self.cmdPayloadTuple and self.actionRequestTuple to identify
    # the default data store. That is why self.cmdPayloadTuple has an inital value of None.
    #
    # The trigger also gives us some default values for display/show
    # processing. We intialize them here, but they may get changed
    # by the trigger method.
    #
    if not self.exeController.errs.HasCriticalMessages():
      if self.cmdPayloadTDict is not None:
        self.cmdPayloadTuple			= bafDataStore.bafTupleObject()
        self.cmdPayloadTDict.SafeCopy(self.cmdPayloadTuple, self.exeController.cgiGetDataRaw, Source2=self.exeController.cgiPostDataRaw)
        self.cmdPayloadTDict.ValidateTuple(self.cmdPayloadTuple, ExeController=self.exeController)
    if not self.exeController.errs.HasCriticalMessages():
      if 'ValidateActionData' in dir(self):
        self.ValidateActionData()
    #
    # The data is validated, so now we can run the trigger method
    #
    if (self.runTriggerInfo is None) and (not self.exeController.printHtml):
      # No trigger method identified.
      # If interactive mode, send an HTML form for the actionRequestTDict below.
      # Otherwise lack of a trigger is a hard error errror -- we don't know what to do.
      self.exeController.errs.AddDevCriticalMessage("Execute() unable to identify trigger for command type '%s'." % (repr(self.cmdType)))
      return
    #
    self.SaveState()
    wsTriggerResult				= False
    if self.runTriggerInfo is not None:
      if not self.exeController.errs.HasCriticalMessages():
        # Errors were found, don't do the work of the action/trigger
        wsTriggerMethod				= getattr(self, self.runTriggerInfo.processMethodName, None)
        if wsTriggerMethod is not None:
          # This trigger has a method, do that
          wsTriggerResult			= wsTriggerMethod(self.runTriggerInfo)
    # Not sure what is needed here. In reality, hte triggers are not returning a result,
    # so we end up displaying the form. Which is what I want at the moment. This is a little
    # ugly because I am trying to handle headless/API type calls and interative calls with the
    # same loop. I am now thinking that is a bad idea. They are different enough to need
    # separate paths.
    #if self.exeController.printHtml:
    self.exeController.aContext.WriteTitle(Title=self.description)
    self.exeController.aContext.StartForm(TDict=self.actionRequestTDict,
							FormCt=self.cmdFormCt,
							FormFocusField=self.cmdFormFocusField,
							DataContainer=self.actionRequestTuple,
							CommandObject=self)
    return
    #
    # The above may be correct for selector stuff. The stuff below is just leftovers.
    # If there is a form model, we are probably ready to display the form here,
    # like the selector form just above. Otherwise we may be silently done or something.
    # API mode may be different.
    #
    if self.confirmationNeeded and (not self.isConfirmed):
      # This might be deprecated. Or maybe just for bfsOps command lines.
      # Maybe should be done differently. Its old code.
      self.MakeConfirmationCommand()
      self.DisplayConfirmationData()
      return
    if self.cmdType == CmdTypeActionHelp:
      self.DoCmdTypeActionHelp()
    else:
      self.exeController.errs.AddDevCriticalMessage("Execute() unknown command type '%s'." % (repr(self.cmdType)))

  def SetDefaultCommandCodes(self, Switch=None, Selector=None, CommandRefname=None):
    if Switch == "":
      Switch					= None
    if Selector == "":
      Selector					= None
    self.defaultCommandSelector			= Selector
    self.defaultCommandRefname			= CommandRefname
    self.defaultCommandSwitch			= Switch

  def MakeConfirmationCommand(self):
    # Need to deal with optional fields and value pairs
    wsConfirmationCommand			= self.actionCode
    for wsThisActionErdElement in self.actionRequestTDict.ElementsByIx():
      wsActionDataFieldName			= wsThisActionErdElement._name
      if wsActionDataFieldName in self.actionRequestTuple:
        wsActionDataFieldData			= self.actionRequestTuple[wsActionDataFieldName]
      else:
        wsActionDataFieldData			= ''
      if wsThisActionErdElement.isValueParameter:
        wsActionDataFieldData			= wsThisActionErdElement._name + '=' + bzLex.ConditionallyQuoteString(wsActionDataFieldData)
      wsConfirmationCommand			+= ' ' + wsActionDataFieldData
    self.confirmationCommand			= wsConfirmationCommand
CmdTypeCustom				= 'C'
CmdTypeActionHelp			= 'H'
CmdTypeQuickForm			= 'Q'
CmdTypeRestful				= 'R'

class bafActionCustom(bafActionDef):
  def __init__(self, ExeController=None):
    super(bafActionCustom, self).__init__(ExeController=ExeController)
    
  def ConfigureAsActionHelpAction(self):
    self.actionUseStandardPage			= True
    self.cmdType				= CmdTypeActionHelp

  def ConfigureAsLookupAction(self, parmPrimaryTableReferenceName, parmTableKey, DisplayFields=[]):
    self.actionUseStandardPage			= True
    self.ConfigureAsQuickFormAction()
    self.cmdPrimaryTableReferenceName		= parmPrimaryTableReferenceName
    self.cmdSelectionKey			= parmTableKey
    self.cmdDisplayFields			= DisplayFields
    wsKeyElement				= self.actionRequestTDict.DefinePositionalParameter(parmTableKey)
    wsKeyElement.AssignDefaultValue("")
    self.AddTrigger('Lookup', 'CmdTypeLookupTriggerMethod')

  def ConfigureAsQuickFormAction(self, DataStoreName=None, FormCt=1):
    self.actionUseStandardPage			= True
    self.cmdPayloadTupleStoreName			= DataStoreName
    self.cmdType				= CmdTypeQuickForm
    self.cmdFormCt				= FormCt

  def ConfigureAsRestfulAction(self, EndpointTDictRefname=None):
    self.cmdType				= CmdTypeRestful

  def DoCmdTypeActionHelp(self):
    self.aContext.StartRectangularData()
    wsSwitchList				= sorted(list(self.runExecutableInfo.executableCommandSwitchesCli.keys()))
    for wsThisSwitch in wsSwitchList:
      wsCommandSelector				= self.runExecutableInfo.executableCommandSwitchesCli[wsThisSwitch]
      wsActionObject				= self.CreateActionObject(CommandSelector=wsCommandSelector)
      wsRow					= [wsThisSwitch, wsCommandSelector, '', wsActionObject.description]
      self.aContext.StoreTableRow(wsRow)
      for wsThisParameter in wsActionObject.actionRequestTDict.ElementsByIx:
        wsActionHelp				= wsThisParameter.hint
        if not wsActionHelp:
          wsActionHelp				= ""
        wsRow					= ['', '', wsThisParameter._name, wsActionHelp]
        self.aContext.StoreTableRow(wsRow)

  def CmdTypeLookupTriggerMethod(self, parmTriggerInfo):
    #
    # The matching/selection logic is a cludge becase DTD isn't implemented.
    # When DTD is avaialble, these lookups will follow from the definition.
    # Partno and Loc are both confusions. Not sure if that is signifcant, beyond that this
    # can't be fixed until after DTD for confusion is implemented.
    #
    wsLookupValue				= self.actionRequestTuple.GetDatum(self.cmdSelectionKey)
    if wsLookupValue is None:
      return
    wsResults					= bafDataStore.MakeLookupQuery(self.exeController,
								self.cmdPrimaryTableReferenceName,
								self.cmdSelectionKey, wsLookupValue,
								Debug=0)
    if wsResults:
      self.exeController.aContext.WriteArray(wsResults, DisplayFields=self.cmdDisplayFields)
    return


#
# bafExeController and support
#
class AdminLoginAction(bafActionDef):
  def __init__(self, parmExeController):
    self.Init("Login", ExeController=parmExeController)
    self.SetDefaultCommandCodes(Selector='Login', Switch='l')
    self.ConfigureAsQuickFormAction()
    wsUserIdElement				= self.actionRequestTDict.DefinePositionalParameter('UserId')
    wsUserIdElement.SetLength(MaxLength=30)
    wsPasswordElement				= self.actionRequestTDict.DefinePositionalParameter('Password')
    wsPasswordElement.isPassword		= True
    wsPasswordElement.SetLength(MaxLength=30)
    wsTriggerInfo				= self.AddTrigger('login', 'VerifyLoginTrigger')

  def VerifyLoginTrigger(self, parmTriggerInfo):
    self.exeController.driver.AddCookie(SESSION_COOKIE_NAME, "")
    wsUserId					= self.actionRequestTuple['UserId']
    wsPassword					= self.actionRequestTuple['Password']
    if self.exeController.Login(wsUserId, wsPassword):
      self.exeController.driver.WriteReferral('/ops.html')
    else:
      self.exeController.errs.AddUserCriticalMessage("invalid login %s " % (self.exeController.lastLoginError))

def MakeClassTDict_For_bafExeSession(ExeController=None, InstanceClassName=None):
  wsTDict					= bafTupleDictionary.bafTupleDictionary(
								InstanceClassName=InstanceClassName,
								PrimaryDataPhysicalType=bafErTypes.Core_ObjectTypeCode,
								ExeController=ExeController)

  wsTDict.AddUdiElement('SessionId')
  wsTDict.AddScalarElement('IpAddress')
  wsElement					= wsTDict.AddScalarElement('SessionCookie')
  wsElement.ConfigureAsNotBlank()
  wsElement.ConfigureAsUnique()
  wsTDict.AddScalarElement('Browser')
  wsTDict.AddScalarElement('SessionCreated', PhysicalType=bafErTypes.Core_TimestampTypeCode)
  wsTDict.AddScalarElement('LastLoginTime', PhysicalType=bafErTypes.Core_TimestampTypeCode)
  wsTDict.AddScalarElement('LastLogoutTime', PhysicalType=bafErTypes.Core_TimestampTypeCode)
  wsTDict.AddScalarElement('LastLoginUser')
  wsTDict.AddScalarElement('LastLoginPriv')
  return wsTDict


def MakeClassTDict_For_bafExeController(ExeController=None, InstanceClassName=None):
  wsTDict					= bafTupleDictionary.bafTupleDictionary(
								InstanceClassName=InstanceClassName,
								PrimaryDataPhysicalType=bafErTypes.Core_ObjectTypeCode,
								ExeController=ExeController)
  wsTDict.AddScalarElementsFromList(bafExeController.__slots__)
  return wsTDict

#
# Which came first, the program or the process?
#
# bafExeController is the magical action which is the root of all other actions at runtime.
#
# It deals with the mess of determining the actual runtime environment and translating it into a highly
# consistent format so application actions don't need conditional code to deal with the environment.
#
# No user work is done by the bafExeController actions. It is the implied action of program initialization.
# It creates an instance of the requested trigger action class. This leads to a action scheem that makes it
# relatively easy for actions to launch actions.
#
# The goal is create a system reminiscent of the original UNIX architecture where actionality is
# divided into smallish, well defined units that can be strung together to achieve complex
# actionality.
#
# exeController.cgi is the old style html driver which has lots of hard coded Hobby Engineering
# features. exeController.driver is the modern, site independent output driver.
#
# for actions where isOldStyleCgi is True, we need:
#	cgi, catHtml, catMarkup
# get rid of these after everything is transitioned
#
#
class bafExeController(object):

  __slots__ = (
				'activityId',
				'aContext',
				'args',
				'codes',
				'cgi', 'catHtml', 'catMarkup',
				'cgiButtonName',
				'cgiButtonSuffix',
				'cgiButtonMultiple',
				'cgiContentType',
				'cgiGatewayInterface',
				'cgiGetDataRaw',
				'cgiHttpCookie',
				'cgiMimeInfo',
				'cgiPostDataBlob',
				'cgiPostDataBlobLen',
				'cgiPostDataRaw',
				'cgiRestfulVerb',
				'cgiQueryString',
				'cgiRemoteAddr',
				'cgiScriptName',
				'cgiScriptPath',
				'cgiUserAgent',
				'cookieDataRaw',
				'cookiesEnabled',
				'dbs',
				'driver',
				'driverClass',
				'errs',
				'isCgi',
				'isSsl',
				'lastLoginError',
				'mddlSchemas',
				'mode',
				'pathInfo',
				'printBodyOnly',
				'printHtml',
				'redirectURL',
				'serverPort',
				'sessionCookie',
				'sessionCookieStatus',
				'sessionId',
				'serverHttps',
				'siteControls',
				'siteFormatsModule',
				'tableSchemas',
				'tDictsByClass',
				'webInfo'
		)

  #
  # Old style modules use self.cgi to access bfsHtml / bzHtml.
  # New style modiles use self.driver to access bzHtml5 and
  #			all site specific info is access via
  #			sitelib modules.
  #
  # self.errs.SetConsoleMode() set below. It stays that way if created
  # stand-alone. For normal site execution, it may get revised in
  # StartMain().
  #
  def __init__(self, QueryString=None, PostDataBlob=None, ScriptPath=""):
    self.args					= bzCmdArgs.args
    self.codes					= bafNv.bafNvTuple()
    self.cgi					= None			# for isOldStyleCgi mode
    self.catHtml				= None			# for isOldStyleCgi mode
    self.catMarkup				= None			# for isOldStyleCgi mode
    self.cgiButtonName				= ""
    self.cgiButtonSuffix			= ""
    self.cgiButtonMultiple			= False
    self.cgiPostDataBlobLen			= 0
    self.cgiGetDataRaw				= None
    self.cgiPostDataRaw				= None
    self.cgiRestfulVerb				= RestfulVerb_Unknown
    self.dbs					= bafNv.bafNvTuple()
    self.errs					= bzErrors.bzErrors()
    self.errs.SetConsoleMode()
    self.tableSchemas				= bafNv.bafNvTuple()
    self.tDictsByClass				= {}
    self.mddlSchemas				= bafNv.bafNvTuple()
    import pathInfo
    self.pathInfo				= pathInfo
    import webInfo
    self.webInfo				= webInfo
    self.GetCgiEnvironment(QueryString=QueryString, PostDataBlob=PostDataBlob, ScriptPath=ScriptPath)
    #
    self.lastLoginError				= 0
    #
    # UI Environment
    #
    self.aContext				= None
    self.driver					= None
    self.driverClass				= None
    self.printBodyOnly				= False
    #
    wsImportSpecs				= getattr(pathInfo, 'siteControlsModuleName', None)
    if wsImportSpecs is None:
      self.siteControls				= None
    else:
      try:
        wsPackage				= __import__(wsImportSpecs[0] + '.' + wsImportSpecs[1])
        self.siteControls			= getattr(wsPackage, wsImportSpecs[1], None)
      except:
        self.siteControls			= None
    #
    wsImportSpecs				= getattr(pathInfo, 'siteFormatsModuleName', None)
    if wsImportSpecs is None:
      self.siteFormatsModule			= None
    else:
      try:
        wsPackage				= __import__(wsImportSpecs[0] + '.' + wsImportSpecs[1], None)
        self.siteFormatsModule			= getattr(wsPackage, wsImportSpecs[1])
      except:
        self.errs.AddTraceback()
        self.siteFormatsModule			= None

  #
  # bafExeController HTML / UI Methods
  #
  def GetCgiEnvironment(self, QueryString=None, PostDataBlob=None, ScriptPath=""):
    self.cgiGatewayInterface			= bzUtil.GetEnv("GATEWAY_INTERFACE")
    self.serverPort				= bzUtil.GetEnv("SERVER_PORT")
    self.serverHttps				= bzUtil.GetEnv("HTTPS")
    if self.cgiGatewayInterface == "":
      self.mode					= ModeConsole
      self.printHtml				= False
      self.isCgi				= False
      self.isSsl				= False
    else:
      self.mode					= ModeCgi
      self.printHtml				= True
      self.isCgi				= True
      if (self.serverPort == "443"):
        self.serverHttps			= "on"				# force Apache 1.2 SUEXEC bug
      if (self.serverPort == "443") and (self.serverHttps == "on"):
        self.isSsl				= True
      else:
        self.isSsl				= None
    #
    # CGI mode
    #
    # Collect cgi data
    #
    if QueryString:
      self.cgiQueryString			= QueryString
      self.cgiRemoteAddr			= ""
      self.cgiUserAgent				= ""
      self.cgiScriptPath			= ScriptPath
      self.redirectURL				= ""
    else:
      self.cgiQueryString			= bzUtil.GetEnv("QUERY_STRING")
      self.cgiRemoteAddr			= bzUtil.GetEnv("REMOTE_ADDR")
      self.cgiUserAgent				= bzUtil.GetEnv("HTTP_USER_AGENT")
      self.cgiScriptPath			= bzUtil.GetEnv("SCRIPT_FILENAME")
      self.redirectURL				= bzUtil.GetEnv("REDIRECT_URL")

    #
    # Collect cookies
    #
    self.activityId				= None
    self.sessionId				= None
    self.sessionCookie				= None
    self.sessionCookieStatus			= None
    self.cookiesEnabled				= SessionCookiesUnknown		# at this time we have no idea
    self.cookieDataRaw				= bafNv.bafNvTuple()
    self.cookieDataRaw.AssignDefaultValue(None)
    self.cgiHttpCookie				= bzUtil.GetEnv("HTTP_COOKIE")
    wsCgiCookieLines				= string.splitfields(self.cgiHttpCookie, ";")
    for wsCgiCookie in wsCgiCookieLines:
      wsPos = string.find(wsCgiCookie, "=")
      if wsPos < 0:
        continue								# no equal sign
      wsFldName					= string.strip(wsCgiCookie[:wsPos])
      wsFldValue				= string.strip(wsCgiCookie[wsPos+1:])
      self.cookieDataRaw[wsFldName]		= bzHtml.CgiUnquote(wsFldValue)
      self.cookiesEnabled			= SessionCookiesEnabled

    self.cgiScriptName				= bzUtil.GetFileName(self.cgiScriptPath)

    if PostDataBlob is not None:
      self.cgiRestfulVerb			= RestfulVerb_Post
      self.cgiPostDataBlobLen			= len(FormData)
      self.CgiPostDataBlob			= PostDataBlob
    else:
      self.cgiRestfulVerb			= bzUtil.GetEnv("REQUEST_METHOD")
      self.cgiPostDataBlobLen			= int(bzUtil.GetEnv("CONTENT_LENGTH", 0))
      if (self.cgiRestfulVerb == RestfulVerb_Post) \
			and (self.cgiPostDataBlobLen > 0):
        #self.cgiPostDataBlob			= sys.stdin.read(self.cgiPostDataBlobLen)
        wsUnicodeReader				= codecs.getreader("utf-8")(sys.stdin)
        self.cgiPostDataBlob			= wsUnicodeReader.read(self.cgiPostDataBlobLen)
      else:
        self.cgiPostDataBlob			= ""

    #wsF = codecs.open('D-POST-BLOB', mode='w', encoding='utf-8')
    #wsF.write(self.cgiPostDataBlob)
    #wsF.close()

    wsContentType      				= bzUtil.GetEnv("CONTENT_TYPE", "")
    self.cgiMimeInfo				= bzMime.bzMime(bzMime.ContentTypeKeyword + ": " + wsContentType)
    self.cgiContentType				= self.cgiMimeInfo.mimeType
    if self.cgiContentType == bzMime.ContentTypeBrowserForm:
      self.cgiPostDataRaw			= self.cgiMimeInfo.DecodeCgiBlob(self.cgiPostDataBlob)
    else:
      # Content-Type: application/x-www-form-urlencoded (bzMime.ContentTypeApplicationForm)
      self.cgiPostDataRaw			= bafNv.bafNvTuple()
      wsCgiFormDataLines           		= self.cgiPostDataBlob.split("&")
      for wsCgiFormLine in wsCgiFormDataLines:
        wsPos					= wsCgiFormLine.find("=")
        if wsPos < 0:								# no equal sign
          self.cgiPostDataRaw[wsCgiFormLine]	= True
        else:
          wsFldName				= wsCgiFormLine[:wsPos]
          wsFldValue				= wsCgiFormLine[wsPos+1:]
          self.cgiPostDataRaw[wsFldName]	= bzHtml.CgiUnquote(wsFldValue)

   # wsF = codecs.open('D-POST-BLOB', mode='w', encoding='utf-8')
   # wsF.write(self.actionRequestTuple['HeaderHtml'])
   # wsF.close()

    self.cgiGetDataRaw				= bafNv.bafNvTuple()
    self.cgiGetDataRaw.AssignDefaultValue(None)
    if self.cgiQueryString != "":
      wsCgiQueryList				= string.splitfields(self.cgiQueryString, "&")
      wsQueryListCt				= 0
      for wsCgiQuery in wsCgiQueryList:
        wsPos					= string.find(wsCgiQuery, "=")
        if wsPos < 0:								# no equal sign
          if wsQueryListCt == 0:						# 1st is value of script name
           self.cgiGetDataRaw[self.cgiScriptName] = wsCgiQuery
          else:								# rest are flags
           self.cgiGetDataRaw[wsCgiQuery] = True
        else:									# name=value
          wsFldName				= wsCgiQuery[:wsPos]
          wsFldValue				= wsCgiQuery[wsPos+1:]
          self.cgiGetDataRaw[wsFldName]	= bzHtml.CgiUnquote(wsFldValue)
          wsQueryListCt += 1

    self.cgiButtonName				= ""
    self.cgiButtonSuffix			= ""
    self.cgiButtonMultiple			= False

    for (wsKey, wsData) in list(self.cgiPostDataRaw.items()):
      wsSafeKey					= bzUtil.Filter(wsKey, CGI_KEY_FILTER)
      if wsSafeKey[:bzHtml.ButtonPrefixLen] == bzHtml.ButtonPrefix:
        if self.cgiButtonName:
          self.cgiButtonMultiple		= True
        else:
          self.cgiButtonName			= wsSafeKey[bzHtml.ButtonPrefixLen:]
          if self.cgiButtonName[-bzHtml.ButtonSuffixLen:] in bzHtml.ButtonSuffixes:
            self.cgiButtonSuffix		= self.cgiButtonName[-bzHtml.ButtonSuffixLen:]
            self.cgiButtonName			= self.cgiButtonName[:-bzHtml.ButtonSuffixLen]

  def FilterCgiData(self, parmUnfilteredData):
    wsFilteredData				= bafNv.bafNvTuple()
    wsFilteredData.AssignDefaultValue(None)
    for (wsKey, wsData) in list(parmUnfilteredData.items()):
      wsKey					= bzUtil.Filter(wsKey, bzUtil.LETTERSANDNUMBERS+"-_.")
      wsData					= bzUtil.FilterMultiLineText(wsData, parmExcept="<>")
      wsFilteredData[wsKey]			= wsData
    return wsFilteredData

  def SetCatalogOutputToCgi(self):
   # This is needed only for actions where isOldStyleCgi = True
   self.catHtml					= self.cgi

  #
  # bafExeController Action Management Methods
  #

  def GetCommandObject(self, parmCommandRefname):
    if parmCommandRefname is None:
      self.errs.AddDevCriticalMessage("GetCommandObject(): No command refname provided.")
      return None
    import sitelib.siteActions as siteActions
    wsCommandVariableName			= parmCommandRefname + bafErTypes.SiteCommandsVariableSuffix
    wsCommandDefinition				= getattr(siteActions, wsCommandVariableName, None)
    if wsCommandDefinition is None:
      self.errs.AddDevCriticalMessage("GetCommandObject(): Undefined command refname '%s' provided." % (parmCommandRefname))
      return None
    wsActionPackageName				= wsCommandDefinition['PackageName']
    wsActionModuleName				= wsCommandDefinition['ModuleName']
    wsActionClassName				= wsCommandDefinition['ClassName']
    wsActionPackage				= __import__(wsActionPackageName + '.' + wsActionModuleName)
    wsActionModule				= getattr(wsActionPackage, wsActionModuleName)
    wsActionClass				= getattr(wsActionModule, wsActionClassName)
    try:
      wsCommandObject				= wsActionClass(self)
    except:
      self.errs.AddTraceback()
      self.errs.AddDevCriticalMessage("Unable to create action %s.%s" % (wsCommandDefinition['ModuleName'], wsCommandDefinition['ClassName']))
      return None
    wsCommandObject.actionRequestTDict.CompleteDictionary()
    wsCommandObject.runCommandRefname		= parmCommandRefname
    return wsCommandObject

  def CreateCommandObject(self, CommandRefname=None, CommandMap=None, CommandSelector=None, ExecutableInfo=None):
    def MakeErrorCommand():
      # This could easily be too simple minded. This creates a simple action that can be used so
      # we have a way to interact with the user when we don't have a valid action.
      # That can happen because of a bug whihc we need to report. It could also happen because
      # malicius user did something invalid on purpose. We need to be careful not to give away
      # too much information or escalte privileges.
      wsErrorCommand				= bafActionDef()
      wsErrorCommand.Init('Invalid Command', ExeController=self)
      wsErrorCommand.runIsInvalidCommand	= True
      return wsErrorCommand
    #
    #print "AAA", CommandRefname, CommandMap, CommandSelector, ExecutableInfo
    if CommandRefname is None:
      # We need a CommandRefname. We get called with either CommandRefname or
      # CommandMap and CommandSelector so we can look it up here.
      if CommandMap is not None:
        if CommandSelector in CommandMap:
          CommandRefname			= CommandMap[CommandSelector]
    wsCommandObject				= self.GetCommandObject(CommandRefname)
    if wsCommandObject is None:
      wsCommandObject				= MakeErrorCommand()
    wsCommandObject.runExecutableInfo		= ExecutableInfo
    return wsCommandObject

  def GetCommandObjectFromCommandLine(self, parmCommandLine, CommandMap={}):
    wsCommandTokens				= bzLex.Split(parmCommandLine, ExeAction=self)
    # self.errs.AddUserInfoMessage("Tokens: %s --- CommandMap: %s" % (`wsCommandTokens`, `CommandMap`))
    if len(wsCommandTokens) < 1:
      return None
    wsCommandSelector				= bzUtil.Upper(wsCommandTokens[0].text)
    wsCommandObject				= self.CreateCommandObject(CommandMap=CommandMap,
							CommandSelector=wsCommandSelector)
    if wsCommandObject.runIsInvalidCommand:
      return None
    self.GetCommandDataFromLexTokens(wsCommandTokens, wsCommandObject)
    wsCommandObject.runCommandLine		= parmCommandLine
    return wsCommandObject

  def GetCommandDataFromConsoleCli(self, parmCommandObject):
    # Command / Action data is processed from cgiGetDataRaw and cgiPostDataRaw
    # This method populates those from the command line.
    # For HTTP/CGI transactions this is done by GetCgiEnvironment().
    if parmCommandObject.actionRequestTDict is None:
      return
    wsPositionalParameters			= parmCommandObject.actionRequestTDict.positionalParameters
    wsPositionalParameterCt			= len(wsPositionalParameters)
    wsProcessedParameterCt			= 0
    self.cgiGetDataRaw.Clear()
    for wsPositionalArg in self.args.list:
      if wsProcessedParameterCt < wsPositionalParameterCt:
        ## INCOMPLETE !!
        ## Need to deal with upper case, values, boolean/keyword
        wsParameterName				= wsPositionalParameters[wsProcessedParameterCt]._name
        self.cgiGetDataRaw.AppendDatum(wsParameterName, wsPositionalArg)
      wsProcessedParameterCt			+= 1
    for (wsKeywordParameterName, wsKeywordValue) in list(self.args.parameters.items()):
      self.cgiGetDataRaw.AppendDatum(wsKeywordParameterName, wsKeywordValue)

  def GetCommandDataFromLexTokens(self, parmTokens, parmCommandObject):
    # parmTokens is an array of bzLex tokens
    if len(parmTokens) > 0 :
      wsCommandKeyword				= bzUtil.Upper(parmTokens[0].text)
    if parmCommandObject.actionRequestTDict is None:
      return
    wsPositionalParameters			= parmCommandObject.actionRequestTDict.positionalParameters
    wsPositionalParameterCt			= len(wsPositionalParameters)
    wsProcessedParameterCt			= 0
    self.cgiGetDataRaw.Clear()
    #
    # Parse
    #
    wsState					= CommandLineStateScan
    wsKeyword					= ""
    wsUpperCase					= True
    wsTokenCt					= len(parmTokens)
    wsTokenIx					= 1
    wsTableElement				= None
    wsParameterIx				= 0
    while wsTokenIx < wsTokenCt:
      wsToken					= parmTokens[wsTokenIx].text
      wsTokenIx					+= 1
      #print "analyze state %d token %s" % (wsState, wsToken)
      if wsState == CommandLineStateScan:
        if wsPositionalParameterCt > wsParameterIx:
          wsKeyword				= wsPositionalParameters[wsParameterIx]._name
          self.cgiGetDataRaw.AppendDatum(wsKeyword, wsToken)
          wsParameterIx				+= 1
          wsTableElement			= None
          wsState				= CommandLineStateScan
          continue
        elif parmActionObject.actionRequestTDict.HasElement(wsToken):				# is a valid keyword parameter
          wsTableElement				= parmActionObject.actionRequestTDict.GetElement(wsToken)
          if not wsTableElement.isValueParameter:
            self.cgiGetDataRaw.AppendDatum(wsToken, True)
            wsParameterIx			+= 1
            wsTableElement			= None
            wsState				= CommandLineStateScan
            continue
          wsState				= CommandLineStateEqSign
        else:
          self.errs.AddUserCriticalMessage("Invalid %s parameter '%s'" % (wsCommandKeyword, wsToken))
          return False
      elif wsState == CommandLineStateEqSign:
        if wsToken == '=':
          wsState				= CommandLineStateValue
        else:
          self.errs.AddUserCriticalMessage("Invalid %s parameter '%s' s/b '='" % (wsCommandKeyword, wsToken))
          return False
      elif wsState == CommandLineStateValue:
        if wsTableElement.isUpperCaseOnly:
          wsToken				= bzUtil.Upper(wsToken)
        self.cgiGetDataRaw.AppendDatum(wsTableElement._name, wsToken)
        wsParameterIx				+= 1
        if wsTableElement.combinedFieldSeparator != "":
          if wsTokenIx < wsTokenCt:
            wsPeek				= parmTokens[wsTokenIx].text
            if wsPeek == wsTableElement.combinedFieldSeparator:
              wsTokenIx				+= 1
              if wsTableElement.combinedFieldName in self.actionRequestTDict:
                wsTableElement			= parmActionObject.actionRequestTDict[wsTableElement.combinedFieldName]
                wsState				= CommandLineStateValue
                continue
              else:
                self.errs.AddUserCriticalMessage("Invalid %s combined field name '%s'" % (
							wsCommandKeyword, wsTableElement.combinedFieldName))
                return False
        wsTableElement				= None
        wsState					= CommandLineStateScan
        continue
      else:
        self.errs.AddUserCriticalMessage("Invalid %s state %d at '%s'" % (wsCommandKeyword, wsState, wsToken))
        return False
    return True

  def GetSystemClassObject(self, parmClassRefname):
    import sitelib.siteActions as siteActions
    wsClassVariableName				= parmClassRefname + bafErTypes.SiteClassesVariableSuffix
    wsClassDef					= getattr(siteActions, wsClassVariableName, None)
    if wsClassDef is None:
      return None
    wsClassPackage				= __import__(wsClassDef['PackageName'] + '.' + wsClassDef['ModuleName'])
    wsClassModule				= getattr(wsClassPackage, wsClassDef['ModuleName'])
    wsClassClass				= getattr(wsClassModule, wsClassDef['ClassName'])
    return wsClassClass

  def MakeSystemClassInstance(self, parmClassRefname):
    # It may be a good idea to have qualifiers as tow which classes we want access this way.
    if parmClassRefname == 'list':
      return []
    if parmClassRefname == 'dict':
      return {}
    wsClassClass				= self.GetSystemClassObject(parmClassRefname)
    try:
      wsClassObject				= wsClassClass()
    except:
      wsClassObject				= None
      self.errs.AddTraceback()
      self.errs.AddUserCriticalMessage("MakeSystemClassInstance(): Unable to create system class %s." % (
							parmClassRefname
							))
    return wsClassObject

  def RegisterSystemClassTDict(self, parmTDict):
    # Usually this will get called by GetTDictByClassRefname() below.
    # It is broken out so classes can be registered dynamically instead of
    # just during configuration and the generation of siteActions.py
    self.tDictsByClass[parmTDict.instanceClassName]	= parmTDict

  def GetTDictByObject(self, parmObject):
    """ Return a TDict for an object if it can be found. """
    wsTDict					= getattr(parmObject, '_tdict', None)
    if wsTDict is not None:
      if isinstance(wsTDict, bafTupeDictionary.bafTupleDictionary):
        return wsTDict
    wsClassName					= parmObject.__class__.__name__
    return self.GetTDictByClassRefname(wsClassName)

  def GetTDictByClassRefname(self, parmClassRefname):
    """ Return a TDict for a registered ClassRefname. """
    if parmClassRefname in self.tDictsByClass:
      return self.tDictsByClass[parmClassRefname]
    # Generating a generic object is a bad idea. This only returns registered TDicts now.
    # Saving this code for now to preserve subltleties of TDict definintion.
    #if parmClassRefname == 'list':
    #  wsTDict					= bafTupleDictionary.bafTupleDictionary(
	#						IsStaticCollection=False,
	#						Name='list',
	#						InstanceClassName='list',
	#						InstancePhysicalType=bafErTypes.Core_ListTypeCode,
	#						PrimaryDataPhysicalType=bafErTypes.Core_ListTypeCode)
      # self.RegisterSystemClassTDict(wsTDict)
      #return wsTDict
    # It may be a good idea to have qualifiers as to which classes we want access this way.
    import sitelib.siteActions as siteActions
    wsClassVariableName				= parmClassRefname + bafErTypes.SiteClassesVariableSuffix
    wsClassDef					= getattr(siteActions, wsClassVariableName, None)
    if wsClassDef is None:
      return None						# ClassRefname is not registered
    wsClassPackage				= __import__(wsClassDef['PackageName'] + '.' + wsClassDef['ModuleName'])
    wsClassModule				= getattr(wsClassPackage, wsClassDef['ModuleName'])
    wsTDict					= None
    wsTDictException				= False
    if 'MakeTDictFunctionName' in wsClassDef:
      wsMakeTDictFunctionName			= wsClassDef['MakeTDictFunctionName']
      wsMakeTDictFunction			= getattr(wsClassModule, wsMakeTDictFunctionName)
      try:
        wsTDict					= wsMakeTDictFunction(self, InstanceClassName=parmClassRefname)
      except:
        self.errs.AddTraceback()
        wsTDict					= None
        wsTDictException			= True
    else:
      wsMakeTDictFunctionName			= '**UNDEFINED**'
    if wsTDict is None:
      self.errs.AddDevCriticalMessage("Unable to create class TDict %s from %s.%s.%s" % (
							parmClassRefname,
							wsClassDef['PackageName'],
							wsClassDef['ModuleName'],
							wsMakeTDictFunctionName
							))
      return None
    wsTDict.instanceClassName			= parmClassRefname
    self.RegisterSystemClassTDict(wsTDict)
    return wsTDict

  def GetContainerType(self, parmObject):

    wsTDict				= self.GetTDictByObject(parmObject)
    if wsTDict is None:
      return None
    else:
      return wsTDict.primaryDataPhysicalType

  def AnyItems(self, parmObject, PhysicalType=None):
    """ Return list of key/value tuples, like dict.items(), for any object. """
    if PhysicalType is None:
      PhysicalType			= self.GetContainerType(parmObject)
    if wsPhysicalType == bafErTypes.Core_ObjectTypeCode:
      wsKeys				= bafTupleDictionary.GetAttributeNames(parmObject)
      wsResult				= []
      for wsThisKey in wsKeys:
        wsResult.append((wsThisKey, getattr(parmObject, wsThisKey)))
    elif wsPhysicalType in bafErTypes.Core_ContainerMapTypeCodes:
      return list(parmObject.items())
    raise TypeError("AnyItems() unable to clasify %s object" % (parmObject.__class__.__name__))

  def AnyKeys(self, parmObject, PhysicalType=None, TDict=None):
    """ Return list of keys, like dict.keys(), for any object. """
    if PhysicalType is None:
      # If PhysicalType is provided, use that. The caller wants that specific, low level operation.
      # Working from a TDict is probably the more natural BAF style.
      if TDict is None:
        TDict				= self.GetTDictByObject(parmObject)
    if PhysicalType == bafErTypes.Core_ObjectTypeCode:
      return bafTupleDictionary.GetAttributeNames(parmObject)
    elif PhysicalType in bafErTypes.Core_ContainerMapTypeCodes:
      return list(parmObject.keys())
    elif PhysicalType in bafErTypes.Core_ContainerIxVTypeCodes:
      return list(range(len(parmObject)))
    raise TypeError("AnyKeys() invalid physical type '%s' for %s object" % (PhysicalType, parmObject.__class__.__name__))


  def GetCommandUri(self, parmCommandRefname, IsGetForm=False):
    if parmCommandRefname is None:
      self.errs.AddUserCriticalMessage("GetCommandUri(): No path provided.")
      return ""
    import sitelib.siteActions as siteActions
    wsCommandVariableName			= parmCommandRefname + bafErTypes.SiteCommandsVariableSuffix
    wsCommandDef				= getattr(siteActions, wsCommandVariableName)
    wsCommandSelector				= wsCommandDef['Selector']
    wsUri					= wsCommandDef['Uri']
    if not IsGetForm:
      wsUri					+= '?%s=%s' % (
								CoreCommandSelectorCgiKeyword,
								wsCommandSelector)
    return wsUri

  def GetCommandLocatorByActionRefname(self, parmActionRefname):
    if parmActionRefname is None:
      self.errs.AddUserCriticalMessage("GetActionObject(): No name provided.")
      return ""
    import sitelib.siteActions as siteActions
    wsActionVariableName			= parmActionRefname + bafErTypes.SiteActionsVariableSuffix
    wsActionInfo				= getattr(siteActions, wsActionVariableName)
    wsCommandLocator				= bafCommandLocator(PackageName=wsActionInfo['PackageName'],
									ModuleName=wsActionInfo['ModuleName'],
									ActionClassName=wsActionInfo['ClassName'])
    return wsCommandLocator

  #
  # bafExeController Database Methods
  #
  #
  def OpenDb(self, parmDbRefname, Debug=0):
    if parmDbRefname in self.dbs:
      return self.dbs[parmDbRefname]
    if parmDbRefname not in self.pathInfo.DbNames:
      self.errs.AddDevCriticalMessage("Attempt to open undefined database '%s'." % (parmDbRefname))
      return None
    wsDbInfo					= self.pathInfo.DbNames[parmDbRefname]
    wsDbType					= wsDbInfo['DbType']
    if wsDbType == bafRdbms.DbTypeMySql:
      try:
        wsDb					= bafRdbms.bafRdbmsMySql(
								Host=wsDbInfo['ServerName'],
								Db=wsDbInfo['DbName'],
								User=wsDbInfo['UserName'],
								Password=wsDbInfo['Password'],
								ExeController=self,
								Debug=Debug)
      except:
        self.errs.AddTraceback()
        self.errs.AddDevCriticalMessage("Unable to create MySql connector for database '%s'." % (parmDbRefname))
        return None
    elif wsDbType == bafRdbms.DbTypeSqLite:
      try:
        wsDb					= bafRdbms.bafRdbmsSqLite(
								ExeController=self,
								Path=wsDbInfo['Path'],
								Debug=Debug)
      except:
        self.errs.AddTraceback()
        self.errs.AddDevCriticalMessage("Unable to create SqLite connector for database '%s'." % (parmDbRefname))
        return None
    elif wsDbType == bafRdbms.DbTypeFiles:
      wsDb					= bzFileDb.bzFileDbDb(ExeController=self)
    self.dbs[parmDbRefname]			= wsDb
    return wsDb

  def IsDbOpen(self, parmRefname):
    if parmRefname in self.dbs:
      return self.dbs[parmRefname].IsOpen()
    return False

  def GetDbTableInfo(self, parmDbTableReferenceName):
    if parmDbTableReferenceName not in self.pathInfo.TableNames:
      return None
    wsTableInfo					= self.pathInfo.TableNames[parmDbTableReferenceName]
    return wsTableInfo

  def GetDbTableModel(self, parmDbTableReferenceName=None, TableInfo=None):
    if parmDbTableReferenceName is not None:
      wsTableInfo				= self.GetDbTableInfo(parmDbTableReferenceName)
    else:
      wsTableInfo				= TableInfo
    if wsTableInfo is None:
      return None
    wsModelRefname				= wsTableInfo['ModelClassRefname']
    if wsModelRefname is None:
      return None
    return self.GetTDictByClassRefname(wsModelRefname)

  def OpenDbTable(self, parmDbTableReferenceName=None, Db=None, PhysicalTableName=None, Debug=0):
    # I'm not getting the model here because until BAF is strictly model driven, most model
    # TDict classes need the table open in order to get the RDBMS table structure as a starting
    # point. bafRdbms.Post() gets the model when needed. Getting it here results in infinite
    # recursion.
    #
    if parmDbTableReferenceName is None:
      # Requires Db and PhysicalTableName.
      # This is for development work where the database or table haven't been through the
      # config process. Don't use for normal application code.
      if (Db is None) or (PhysicalTableName is None):
        return None
      else:
        wsTable					= Db.OpenTable(PhysicalTableName, Debug=Debug)
        return wsTable
    #
    wsTableInfo					= self.GetDbTableInfo(parmDbTableReferenceName)
    if wsTableInfo is None:
      return None
    wsDb					= self.OpenDb(wsTableInfo['DbRefname'], Debug=Debug)
    if wsDb is None:
      return None
    #wsModelTDict				= self.GetDbTableModel(TableInfo=wsTableInfo)
    wsModelTDict				= None
    wsTable					= wsDb.OpenTable(wsTableInfo['TableName'], ModelTDict=wsModelTDict, Debug=Debug)
    return wsTable

  #
  # bafExeController: Content Index Methods
  #
  def ContentClear(self, parmSourceType, parmSourceKey):
    wsContentIndexTable				= self.OpenDbTable(ContentIndexTableName)
    wsContentIndexTable.Delete(parmWhere=[('SourceType', '=', parmSourceType),
						('SourceKey', '=', parmSourceKey)])


  def ContentRegister(self, parmSourceType, parmSourceKey, parmContentType, parmContentKey, parmUrl):
    wsContentIndexTable				= self.OpenDbTable(ContentIndexTableName)
    wsContentIndexTable.Insert(
				[parmSourceType, parmSourceKey,
				parmContentType, parmContentKey,
				parmUrl
				], [
				'SourceType', 'SourceKey',
				'ContentType', 'ContentKey',
				'Url'
				]);

  def ContentGetUrl(self, parmContentType, parmContentKey):
    wsContentIndexTable				= self.OpenDbTable(ContentIndexTableName)
    wsContentIndexTable.Lookup2(parmWhere=[('ContentType', '=', parmContentType),
						('ContentKey', '=', parmContentKey)])
    if len(wsContentIndexTable) == 1:
      return wsContentIndexTable[0]['Url']
    else:
      return None

  #
  # bafExeController Module Import Methods
  #
  def MakeDefinitionImportModuleName(self, parmFamily, parmType, parmName, IsDev=False, GetFilePath=False):
    wsTableImportModuleName			= 'Def' + '_' + parmFamily + '_' + parmType + '_' + parmName
    if GetFilePath:
      if IsDev:
        wsTableImportModulePath			= self.pathInfo.ProgmPath + 'new/' + wsTableImportModuleName + '.py'
      else:
        wsTableImportModulePath			= self.pathInfo.ProgmPath + wsTableImportModuleName + '.py'
    else:
      # Get import path
      wsTableImportModulePath			= self.pathInfo.ProgmPackageName + '.' + wsTableImportModuleName
    return (wsTableImportModuleName, wsTableImportModulePath)

  def MakeTableImportModuleName(self, parmName, IsDev=False, IsMddl=False, GetFilePath=False):
    if not IsMddl:
      wsTableImportModuleName			= 'dtdTable' + parmName
    else:
      wsTableImportModuleName			= 'ErdSchema' + parmName
    if GetFilePath:
      if IsDev:
        wsTableImportModulePath			= self.pathInfo.ProgmPath + 'new/' + wsTableImportModuleName + '.py'
      else:
        wsTableImportModulePath			= self.pathInfo.ProgmPath + wsTableImportModuleName + '.py'
    else:
      # Get import path
      wsTableImportModulePath			= self.pathInfo.ProgmPackageName + '.' + wsTableImportModuleName
    return (wsTableImportModuleName, wsTableImportModulePath)

  def GetTableImportModuleName(self, parmTableReferenceName, IsDev=False, IsMddl=False, GetFilePath=False):
    wsTableDefinition				= self.pathInfo.TableNames[parmTableReferenceName]
    if wsTableDefinition is None:
      self.errs.AddUserCriticalMessage("bafExeController.GetTableImportModuileName: Table '%s' not defined in pathInfo." % (parmTableReferenceName))
      return (None, None)
    if not IsMddl:
      wsTableImportModuleName			= 'dtdTable' + wsTableDefinition.referenceName
    else:
      wsTableImportModuleName			= 'ErdSchema' + wsTableDefinition.referenceName
    if GetFilePath:
      if IsDev:
        wsTableImportModulePath			= self.pathInfo.ProgmPath + 'new/' + wsTableImportModuleName + '.py'
      else:
        wsTableImportModulePath			= self.pathInfo.ProgmPath + wsTableImportModuleName + '.py'
    else:
      # Get import path
      wsTableImportModulePath			= self.pathInfo.ProgmPackageName + '.' + wsTableImportModuleName
    return (wsTableImportModuleName, wsTableImportModulePath)

  def GetTableImportModuleObject(self, parmTableReferenceName, IsMddl=False):
    (wsTableImportModuleName, wsTableImportModulePath)	= self.GetTableImportModuleName(parmTableReferenceName, IsMddl=IsMddl)
    if wsTableImportModulePath is None:
      return None
    wsPackage					= __import__(wsTableImportModulePath)
    wsModule					= getattr(wsPackage, wsTableImportModuleName)
    return wsModule

  def GetTableObject(self, parmTableReferenceName, IsMddl=False):
    # This caching is OK for now because reference names and tables map 1:1. Need to do a copy or something
    # as full model is implemented. The same DTD could be used for multiple tables
    if not IsMddl:
      wsCache					= self.tableSchemas
    else:
      wsCache					= self.mddlSchemas
    if parmTableReferenceName in wsCache:
      return wsCache[parmTableReferenceName]
    if parmTableReferenceName not in self.pathInfo.TableNames:
      return None
    wsTableInfo					= self.pathInfo.TableNames[parmTableReferenceName]
    wsTableModule				= self.GetTableImportModuleObject(parmTableReferenceName, IsMddl=IsMddl)
    wsTable					= wsTableModule.MakeTable(self)
    wsTable.DefinePhysicalTableName(wsTableInfo.dbTableName)
    wsCache[parmTableReferenceName]		= wsTable
    return wsTable

  def GetModuleObject(self, parmImportName):
    wsNameSplit					= parmImportName.split('.')
    if len(wsNameSplit) != 2:
      return None
    wsModuleName				= wsNameSplit[1]
    wsPackage					= __import__(parmImportName)
    wsModule					= getattr(wsPackage, wsModuleName)
    return wsModule

  def GetTableNameByHandle(self, parmHandle):
    wsSuffix					= 'TableName'
    wsSuffixLen					= len(wsSuffix)
    parmHandle					= bzUtil.Upper(parmHandle)
    wsModule					= self.GetModuleObject(__name__)
    for (wsKey, wsValue) in list(wsModule.__dict__.items()):
      if wsKey[-wsSuffixLen:] == wsSuffix:
        if bzUtil.Upper(wsKey[:-wsSuffixLen]) == parmHandle:
          return wsValue
    return ''

  def GetCodeObject(self, parmCodeReferenceName):
    return bafErTypes.Core_GetCodeObject(self, parmCodeReferenceName)

  def GetCookie(self, parmCookieName):
    if parmCookieName in self.cookieDataRaw:
      return self.cookieDataRaw[parmCookieName]
    else:
      return None

  def GetData(self, parmPath):
    wsPath					= parmPath.split('/')
    if len(wsPath) == 1:
      wsResult					= getattr(self, wsPath[0])
      return wsResult
    if wsPath[0] == 'specfiles':
      wsFilePath				= self.pathInfo.SpecfilesPath + wsPath[1] + '.snip'
      #wsDataFile				= bzTextFile.open(wsFilePath, "r")
      wsDataFile				= open(wsFilePath, "r")
      wsResult					= wsDataFile.read()
      wsDataFile.close()
      del wsDataFile
      return wsResult
    wsSource					= self
    for wsThisPathElement in wsPath[:-1]:
      wsSource					= getattr(wsSource, wsThisPathElement)
    wsResult					= getattr(wsSource, wsPath[-1])
    return wsResult

  def FormatText(self, parmText):
    wsCommandStringStart			= string.find(parmText, '$')
    if wsCommandStringStart < 0:
      # no substitutions -- just write it
      return parmText
    wsResultText				= ""
    wsResultText				+= parmText[:wsCommandStringStart]		# write up to first substitution
    while wsCommandStringStart < len(parmText):
      wsCommandStringEnd = string.find(parmText, '$', wsCommandStringStart+1)
      if wsCommandStringEnd < 0:
        # The last $ is just a $, no substitution, write it out
        wsResultText				+= parmText[wsCommandStringStart:]
        return wsResultText
      if (wsCommandStringEnd - wsCommandStringStart) == 1:
        wsSubstCmdi				= "$"
        wsSubstType				= "$"
        wsTarget				= ""
      else:
        wsSubstCmd				= parmText[wsCommandStringStart:wsCommandStringEnd]
        wsSubstType				= parmText[wsCommandStringStart+1]
        wsTarget				= parmText[wsCommandStringStart+2:wsCommandStringEnd]
      #
      # first gather modifiers and remove from target
      #
      wsParmStart				= string.find(wsTarget, ':')
      if wsParmStart >= 0:
        wsParm					= wsTarget[wsParmStart+1:]
        wsTarget				= wsTarget[:wsParmStart]
      else:
        wsParm					= ""
      # if (len(wsTarget) > 1) and (wsTarget[-1] == "U"):


      if True:
        if wsSubstType == 'S':		# Link to section
          wsInfo = bfsCatalogSupport.SectionInfoByCode(wsTarget)
          if not wsInfo:
            wsCommandStringStart		= wsCommandStringEnd
            DescError(wsSubstCmd, wsCommandStringStart, "Invalid section code")
            continue
          if TextOnly:
            wsCommandStringStart		= wsCommandStringEnd
            DescError(wsSubstCmd, wsCommandStringStart, "$S not allowed in TextOnly mode")
            continue
          Run.catHtml.WriteLinkToSection(wsInfo)
        else:
          wsCommandStringStart			= wsCommandStringEnd
          DescError(wsSubstCmd, wsCommandStringStart, "Invalid substitution command")
          continue
        wsCommandStringStart			= wsCommandStringEnd + 1
        wsCommandStringStart			= string.find(parmText, '$', wsCommandStringStart)
        if wsCommandStringStart < 0:
          # No more substitutions, write the reset
          wsResultText				+= parmText[wsCommandStringEnd+1:]
          break
        else:
          # write up to the next substitution.  wsCommandStringEnd points to end of prev substitution
          pass
          wsResltText				+= parmText[wsCommandStringEnd+1:wsCommandStringStart]

  #
  # bafExeController Security and Session Methods
  #
  def IsLocalNetwork(self):
    if self.cgiRemoteAddr == "99.181.30.62":	# Harbor Way
      return True
    return False

  def CheckLoginStatus(self, NonSSLok=None, CheckLocationOnly=None, login_not_required=False):
      self.lastLoginError			= 0
      if self.isSsl or NonSSLok:
          # http:// or https:// status is OK
          wsIsLocalNetwork			= self.IsLocalNetwork()
      if login_not_required:
          self.lastLoginError		= 208
          return True
      if CheckLocationOnly:
          self.lastLoginError		= 207
          return self.IsLocalNetwork()
      if self.db is None:
          self.lastLoginError		= 210
          return False
      session_cookie			= self.GetCookie(SESSION_COOKIE_NAME)
      if session_cookie is None:
          # not getting cookie back
          self.lastLoginError		= 205					
          return False
      sessions_db_table		= self.db.OpenTable(self.siteControls.SessionsTableName)
      if not sessions_db_table.Lookup('SessionId', session_cookie):
          # unknown session id: flushed after timeout or intrusion attempt
          self.lastLoginError		= 204
          return False
      # session id is known in database
      wsSessionIpAddr		= sessions_db_table[0]['IpAddr']
      wsSessionCloseTime		= sessions_db_table[0]['CloseTimestamp']
      if wsSessionCloseTime is not None:
          # session was logged out
          self.lastLoginError	= 201
          return False
      if self.cgiRemoteAddr != wsSessionIpAddr:
          self.lastLoginError	= 203
          return False
      # session verified, no problems found
      self.lastLoginError	= 202
      return True

    #
    # We get here with an http:// request when https:// is required
    #
    self.lastLoginError			= 206
    return False

  def AssignSessionCookie(self):
    # This should be somewhat paranoid since the cookies may have been
    # manipulated by an unfreindly client.
    # We don't want to slow things down too much, but don't make assumptions.
    #
    self.sessionCookie			= None
    self.sessionCookieStatus		= None
    wsIncomingFormSession		= self.cgiPostDataRaw.GetDatum(SessionFormKey)
    wsIncomingUrlSession		= self.cgiGetDataRaw[SessionUrlKey]
    wsIncomingCookieSessionStr		= self.cookieDataRaw[SessionCookieKey]
    self.activityId			= self.cookieDataRaw[ActivityIdCookieKey]
    if self.activityId == "":
      self.activityId			= None
    self.sessionId			= None
    if wsIncomingCookieSessionStr is not None:
      self.cookiesEnabled		= SessionCookiesEnabled			# The browser sent us a cookie
      wsCookieStatus			= wsIncomingCookieSessionStr[0]
      self.sessionCookie		= wsIncomingCookieSessionStr[1:]
      if self.sessionCookie.isdigit():
        if wsCookieStatus == CookieStatusNewNormal:
          self.sessionCookieStatus	= CookieStatusSetNormal
          return
        elif wsCookieStatus == CookieStatusNewOffline:
          self.sessionCookieStatus	= CookieStatusSetOffline
          return
        elif wsCookieStatus in [CookieStatusSetNormal, CookieStatusSetOffline]:
          self.sessionCookieStatus	= wsCookieStatus
          return
      self.errs.AddSecurityMessage("Invalid cookie '%s'." % (wsIncomingCookieSessionStr))
      self.sessionCookie		= None
      self.sessionCookieStatus		= None

    sessions_db_table			= self.OpenDbTable('sessions')
    if sessions_db_table is None:
      self.sessionCookie		= bzUtil.GetRandom(15)
      self.sessionCookieStatus		= CookieStatusNewOffline
      return
    wsRetryCt				= 0
    while (self.sessionId is None) and (wsRetryCt < 4):
      wsNewSessionCookie		= bzUtil.GetRandom(15)
      wsDbRecord				= {
						'Browser':		self.cgiUserAgent,
						'IpAddr':		self.cgiRemoteAddr,
						'SessionCookie':	wsNewSessionCookie,
						'SessionCreated':	bzUtil.NowYMDHM(),
						}

      if sessions_db_table.Insert(wsDbRecord):
        self.sessionId			= sessions_db_table.AutoId()
        self.sessionCookie		= wsNewSessionCookie
        self.sessionCookieStatus	= CookieStatusNewNormal
        return
      time.sleep(0.25)
      wsRetryCt				+= 1
    self.sessionCookie			= bzUtil.GetRandom(15)
    self.sessionCookieStatus		= CookieStatusNewOffline
    return

  def Login(self, parmUserId, parmPassword):
    wsResult				= False
    wsUsersTable			= self.db.OpenTable(self.siteControls.UsersTableName)
    if not bafRdbms.TableIsOpen(wsUsersTable):
      return False
    self.errs.AddUserCriticalMessage("XXX Checking %s %s" % (parmUserId, parmPassword))
    wsUsersTable.Select(parmWhere=('UserId', '=', parmUserId))
    if len(wsUsersTable) == 1:
      wsCheckPassword			= wsUsersTable[0]['password']
      wsRemoteLogin			= bzUtil.AsBool(wsUsersTable[0]['remotelogin'])
      wsIsLocalNetwork			= self.IsLocalNetwork()
      if (wsIsLocalNetwork or wsRemoteLogin) \
		and wsCheckPassword and (wsCheckPassword == parmPassword):
        wsResult			= self.CreateUserSession(parmUserId, wsIsLocalNetwork)
    return wsResult

  def LogOut(self):
    session_cookie				= self.GetCookie(SESSION_COOKIE_NAME)
    if not session_cookie:
      return
    sessions_db_table			= self.db.OpenTable(self.siteControls.SessionsTableName)
    wsConversationsTable		= self.db.OpenTable(self.siteControls.ConversationsTableName)
    if not sessions_db_table.Lookup('SessionId', session_cookie):
      return
    wsSessionIpAddr			= sessions_db_table[0]['IpAddr']
    wsSessionCloseTime			= sessions_db_table[0]['CloseTimestamp']
    if wsSessionCloseTime:
      return								# Already logged out
    wsLogoutTimestamp			= bzUtil.NowYMDHM()
    if self.cgiRemoteAddr != wsSessionIpAddr:
      return								# Don't logout someone else
    sessions_db_table.Update([wsLogoutTimestamp], ['CloseTimestamp'], parmWhere=[('SessionId', '=', session_cookie)])
    wsConversationsTable.Update([wsLogoutTimestamp], ['CloseTimestamp'], parmWhere=[('SessionId', '=', session_cookie)])

  def CheckWebSecurity(self, NonSSLok=None, CheckLocationOnly=None, login_not_required=False):
    if self.CheckLoginStatus(NonSSLok=NonSSLok, CheckLocationOnly=CheckLocationOnly, login_not_required=login_not_required):
      return True
    else:
      return False

  def SetFilePermissions(self, parmFilePath, parmPermissions, User=None, Group=None):
    if not User:
      if hasattr(self.pathInfo, 'INI_cms_WebUsrGrp'):
        User					= self.pathInfo.INI_cms_WebUsrGrp
      else:
        self.errs.AddDevCriticalMessage("SetFilePermissions() undefined user")
        return
    if not Group:
      Group					= self.pathInfo.INI_cms_WebUsrGrp
    #print "###", User, Group, parmFilePath
    wsUid					= pwd.getpwnam(User)
    wsUid					= wsUid[2]
    wsGid					= grp.getgrnam(Group)
    wsGid					= wsGid[2]
    os.chmod(parmFilePath, parmPermissions)
    os.chown(parmFilePath, wsUid, wsGid)

  def SetHtmlFilePermissions(self, parmFilePath):
    self.SetFilePermissions(parmFilePath, HTMLPERMISSIONS)

  def SetCgiFilePermissions(self, parmFilePath):
    self.SetFilePermissions(parmFilePath, CGIPERMISSIONS)

  def SetCgiDirPermissions(self, parmFilePath):
    self.SetFilePermissions(parmFilePath, DIRPERMISSIONS)

  def SessionInterrupt(self, ActionRefname=None):
    #
    # This is incomplete because there is no general session store yet.
    # It should save the current program path path and data so we can
    # pick up where we were. For now, we can't save anything for SessionRestore.
    #
    wsActionObject				= self.CreateActionObject(ActionRefname=ActionRefname)
    return wsActionObject

  def ExecuteFailMessage(self, parmId):
    # This is a vague message that is used to let users know something went wrong without
    # revealing any sensitive information.
    return "We cannot process your request at this time. Please try again later. (%s)" % (parmId)

  #
  # This is the "new" command dispatcher. This helps make sure that all
  # standard logging, security, etc. actions happen consistently.
  # Module capabiliites are declared within modules. Those declarations
  # are processed by bzConfigure and bafExeController. The goal is to have a
  # consistent framework while also allowing a reasonable amount of
  # flexibility and staying easy to use for both the programmer
  # and the user.
  #
  # One of the major goals is to keep simple things simple. Ideally
  # this franmework would allow "hello world" to remain a 3 line
  # program while not precluding the most advanced program conceivable.
  # This goal is unlikely to be literally acheved but it is worth some
  # investment to get as close to that as possible.
  #
  def StartMain(self, parmExecutableInfo):
    # import is here so it doesn't effect production during active development.
    # it probably replaces bzHtml and bfsHtml when the dust settles
    import pylib.bzHtml as bzHtml
    wsRunProgName			= self.args.progName
    wsRunCommandMap			= None
    wsRunCommandRefname			= None
    wsRunCommandSelector		= None
    syslog.openlog(parmExecutableInfo.executableFileName, syslog.LOG_PID, syslog.LOG_USER)
    #
    if self.mode == ModeCgi:
      #
      # This is CGI mode
      #
      if CoreCommandSelectorCgiKeyword in self.cgiGetDataRaw:
        wsRunCommandSelector		= bzUtil.Upper(bzUtil.Filter(
						self.cgiGetDataRaw[CoreCommandSelectorCgiKeyword],
						CGI_KEY_FILTER))
        wsRunCommandMap			= parmExecutableInfo.executableCommandsCgi
      else:
        wsRunCommandRefname		= parmExecutableInfo.defaultCommandRefname
      self.driverClass			= bzHtml.bzHtml
      self.printBodyOnly		= False
      self.errs.SetHtmlMode()
    else:
      #
      # This is shell / command line mode
      #
      for wsThisSwitch in self.args.switches:
        if wsThisSwitch in parmExecutableInfo.executableCommandSwitchesCli:
          wsRunCommandSelector		= wsThisSwitch
          wsRunCommandMap		= parmExecutableInfo.executableCommandSwitchesCli
          break
      if wsRunCommandSelector is None:
        # if the action isn't specified by a switch, check if the first list item identifiesa CGI action.
        if len(self.args.list) > 0:
          wsRunCommandSelector		= bzUtil.Upper(self.args.list[0])
          if wsRunCommandSelector in parmExecutableInfo.executableCommandsCgi:
            wsRunCommandMap		= parmExecutableInfo.executableCommandsCgi
            # remove the command from the list so the list has only positional parameters
            self.args.list		= self.args.list[1:]
          else:
            wsRunCommandSelector	= None				# undo the test assignment
      if wsRunCommandSelector is None:
        wsRunCommandRefname		= parmExecutableInfo.defaultCommandRefname
      #
      if GlobalCommands_ConsoleHtmlSwitch in self.args.switches:
        self.driverClass		= bzHtml.bzHtml
        self.printBodyOnly		= False
        self.errs.SetHtmlMode()
        self.printHtml			= True
      else:
        self.driverClass		= bzConsole.bzConsoleDriver
        self.printBodyOnly		= True
        self.errs.SetConsoleMode()
    #
    # Initialize Output Environment, now that we know enough about how we are running
    #
    # Long term, may not need driver here. Maybe it should just be inside aContext.
    self.driver				= self.driverClass(self.mode, self, Context=None)
    self.driver.domain			= getattr(self.webInfo, 'Domain', None)
    self.driver.cookiesPath		= getattr(self.webInfo, 'CookiesPath', '/')
    self.driver.cookiesSendExpireDays 	= getattr(self.webInfo, 'CookiesExpireDays', 7)
    # aContext grabs self.driver in normal cgi mode, so this has to follow driver initialization
    self.aContext			= bzContent.bzAuthoringContext(self, PageLayoutName='BasePage')
    self.driver.AssignContext(self.aContext)
    #
    # The output is now configured enough to display error messages, login screens, etc.
    #
    # First do some program level security.
    #
    # The login process executes as the bafExeController action. If already logged in, the actual
    # user action is executed as a child action.
    #
    #
    # Run the program
    #
    # Hmmm ... CreateActionObject() has been modified to always return a valid object.
    # If the actionCode is invalid it configures as a menu and sets CommandObject.runIsInvalidCommand.
    # This is an improvement because we keep going and get to Print(). Without that we never
    # see the error messages. The menu doesn't execute because Execute() stops if it finds
    # any critical messages. Fix later if it needs to be fixed at all. Defaulting to menu
    # could be considered a security leak. Maybe make that optional.
    #
    wsCommandObject			= self.CreateCommandObject(
						CommandRefname=wsRunCommandRefname,
						CommandMap=wsRunCommandMap,
						CommandSelector=wsRunCommandSelector,
						ExecutableInfo=parmExecutableInfo)
    if self.mode == ModeCgi:
      if bzUtil.AsBool(wsCommandObject.runExecutableInfo.programIsSslYN):
        if not self.isSsl:
          # This needs to be moved to Execute() so its owns all page setup.
          self.driver.WriteStandardPageHeading()
          self.driver.H1("Login Form")
          self.driver.Text("Not Authorized!")
          self.driver.WriteStandardPageBottom()
          sys.exit(0)
      self.AssignSessionCookie()
      self.driver.AddCookie(SessionCookieKey, self.sessionCookieStatus + self.sessionCookie)
      if bzUtil.AsBool(wsCommandObject.runExecutableInfo.programRequireAdminLoginYN):
        if (wsCommandObject is not None) and (wsCommandObject.isMeYN == 'Y') and (wsRunCommandSelector == ActionValidateLoginForm):
          pass
        else:
          if not self.CheckWebSecurity():
            wsActionObject		= self.SessionInterrupt(ActionRefname='AdminLoginAction')
    else:
      # for now, assume all CLI execution is allowed. This is the place to insert
      # CLI security checks.
      # For now, also assume the user is a developer.
      # --- this is incomplete, need to handle case of more than one trigger
      wsTriggers			= wsCommandObject.Triggers()
      if len(wsTriggers) == 1:
        self.cgiButtonName		= wsTriggers[0]._name
      self.GetCommandDataFromConsoleCli(wsCommandObject)
      wsCommandObject.exeController.errs.isUserMode		= False
    #
    # The bafExeController is what runs, using the bafActionDef definition.
    # As of now, exeController will always be self at this point but we use
    # wsActionObject.exeController below in case that ever changes. We will
    # always want to use wsActionObject's exeController.
    #
    wsCommandObject.exeController.errs.SetDebugLevel(0)					# need to control by user / request
    wsExecuteFailed			= False
    try:
      wsCommandObject.Execute()
    except:
      wsExecuteFailed				= True
      wsCommandObject.exeController.errs.AddTraceback()
    if wsExecuteFailed:
      # This catches syntax errors and other uncaught dev problems
      wsCommandObject.exeController.aContext.WriteText(self.ExecuteFailMessage(0))
    else:
      if wsCommandObject.isOldStyleCgi:
        # if old style, assume that the page has been displayed.
        # Ignore if Execute() failed to make sure something reaches
        # the screen.
        return
    if (wsCommandObject.exeController.errs.criticalMessageCount > 0) \
		and (wsCommandObject.exeController.errs.userMessageCount < 1):
      wsCommandObject.exeController.errs.AddUserCriticalMessage(self.ExecuteFailMessage(1))
    wsCommandObject.exeController.aContext.PrintLayout()
    if (self.mode == ModeConsole) and self.printHtml:
      # This is to make sure error messages get printed for debugging.
      # There are some cases where they get missed
      #
      print("********** EOJ **********")
      self.errs.PrintText()

    return

  def BecomeDeamon(self, KeepStandardFilesOpen=False):
    # Uses Double-Fork per Stevens and quoted by multiple examples
    try:
      wsPid = os.fork()
      if wsPid > 0:
        #print "OK - daemon forked"
        sys.exit(0)		# succesful termination of original shell script
      else:
        # The child process continues here -- little trick of fork
        pass
    # Need to specifically check for OSError because normal exit raises
    # exception SystemExit. Let that and everything else be handled by
    # default handlers for now.
    except OSError as wsErr:
      print("fork exceptioni 1: %s (%d)" % (wsErr.strerror, wsErr.errno))
      sys.exit(1)

    #
    # Only the first fork child process gets here.
    # Time to decouple from the terminal environment.
    #
    os.chdir("/")			# so deamon isn't using/blocking current directory
    os.setsid()				# detach from shell
    os.umask(0)
    # Second fork which makes process not a session leader so it can't accidentally
    # aquire a controlling terminal. That would happen if it opened a file/device that
    # happened to be a terminal. It doesn't seem likely that would happen by accident,
    # but this insurance doesn't cost much, so what the heck.
    try:
      wsPid = os.fork()
      if wsPid > 0:
        # print "OK - daemon forked 2"
        sys.exit(0)		# succesful termination of first forked process
      else:
        # The child process continues here -- little trick of fork
        pass
    # Need to specifically check for OSError because normal exit raises
    # exception SystemExit. Let that and everything else be handled by
    # default handlers for now.
    except OSError as wsErr:
      print("fork exceptioni 2: %s (%d)" % (wsErr.strerror, wsErr.errno))
      sys.exit(1)

    #
    # Only the second fork child process gets here.
    #
    # First scrub standard file descriptors. This may not be needed if
    # launched by inetd or other supervisors.
    #

    if not KeepStandardFilesOpen:
      os.close(0)
      os.close(1)
      os.close(2)
      os.open("/dev/null", os.O_RDWR)
      os.dup2(0, 1)
      os.dup2(0, 2)

    self.mode	= ModeDaemon
    return					# Now running as a deamon
