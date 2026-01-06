
# bafSiteExecutableResource identifies a site executable program.
#
# A site executable is an operating system file that can be "run" by users. Each
# executable performs one or more commands that are selected by command line
# switches or URI FUNC parameters.
#
# The actual "work" is done by bafActionDef objects. Multiple executables and
# commands may initiate the same action. This allows files system security
# to be applied along the path to action execution.
#
# For now, all executables are generated python programs, They are just little
# stubs of programs. Long term there is no reason why they have to be python programs.
# They should probably always be generated so the configuration system always has
# full control over action execution paths.
#


class bafSiteExecutableResource:
    def __init__(self, parmPythonModuleResourceObject, ExecutableName, Refname=None,
                 DefaultCommandRefname=''):
        self.configuration = parmPythonModuleResourceObject.configuration
        self.executableFileName = ExecutableName
        if Refname is None:
            wsRefname = ExecutableName
            if wsRefname[-4:] == '.cgi':
                wsRefname = wsRefname[:-4]
            wsRefname = bzUtil.Lower(bzUtil.Filter(
                wsRefname, bzUtil.LETTERSANDNUMBERS))
            wsRefname = bzUtil.Upper(wsRefname[0]) + wsRefname[1:]
            self.executableRefname = wsRefname
        else:
            self.executableRefname = Refname
        self.primaryModuleResourceObject = parmPythonModuleResourceObject
        self.apacheSiteResource = None
        self.requireAdminLogin = True			# only matters for CGI
        self.commandsBySelector = {}			# bafSiteCommandResource by function code
        self.commandsBySwitch = {}			# bafSiteCommandResource by switch
        # allows URI without func parameter
        self.defaultCommandRefname = DefaultCommandRefname
        self.executablesCommands = []
        self.resolvedImportPath = None
        self.resolvedUri = None

    def AddCommand(self, parmActionClassName, ModuleResourceObject=None, CommandSwitch=None, CommandSelector=None):
        if ModuleResourceObject is None:
            wsModuleResourceObject = self.primaryModuleResourceObject
        else:
            wsModuleResourceObject = ModuleResourceObject
        if parmActionClassName not in wsModuleResourceObject.actionResourceObjects:
            PrintError('Undefined Action Class Name "%s" for AddCommand() for %s %s' % (
                parmActionClassName, self.executableRefname, wsModuleResourceObject.actionResourceObjects))
            return None
        wsActionResourceObject = wsModuleResourceObject.actionResourceObjects[
            parmActionClassName]
        wsCommandResourceObject = bafSiteCommandResource(ActionResourceObject=wsActionResourceObject,
                                                         SiteExecutableResourceObject=self,
                                                         CommandSwitch=CommandSwitch, CommandSelector=CommandSelector)
        self.executablesCommands.append(wsCommandResourceObject)

    def ConfigureAsCgi(self, SiteResource=None, SiteRefname=None, AdminLogin=None):
        if SiteResource is None:
            if SiteRefname in self.configuration.apacheSites:
                self.apacheSiteResource = self.configuration.apacheSites[SiteRefname]
        else:
            self.apacheSiteResource = SiteResource
        if AdminLogin is None:
            # default login rules
            if (self.apacheSiteResource is not None) and (not self.apacheSiteResource.isSsl):
                self.requireAdminLogin = False
            else:
                # This is the default if there is no site resource. Default to strict to avoid
                # accidental disclosures early in site configuration.
                self.requireAdminLogin = True
        else:
            self.requireAdminLogin = AdminLogin
        if self.executableFileName[-4:] != '.cgi':
            self.executableFileName += '.cgi'

    # class bafSiteExecutableResource
    def ResolveOneCommand(self, parmSiteCommandResourceObject):
        #
        # This maps actions to functions and switches of this program
        #
        wsActionResourceObject = parmSiteCommandResourceObject.actionResourceObject
        wsActionExeObject = wsActionResourceObject.actionExeObject
        if len(wsActionExeObject.inPrograms) > 0:			# this command is only for certain programs
            if not (self.executableRefname in wsActionExeObject.inPrograms):
                return							# command not allowed for this program
        #
        wsThisCommandSelector = parmSiteCommandResourceObject.selector
        if wsThisCommandSelector is not None:
            if wsThisCommandSelector in self.commandsBySelector:
                wsFirstCommandObject = self.commandsBySelector[wsThisCommandSelector]
                PrintError('Duplicate program command func "%s" for actions "%s.%s" and %s.%s" in program "%s"' % (
                    wsThisCommandSelector,
                    wsActionResourceObject.moduleResourceObject.pythonModuleName, wsActionExeObject.__class__.__name__,
                    wsFirstCommandObject.actionResourceObject.moduleResourceObject.pythonModuleName, wsFirstActionObject.__class__.__name__,
                    self.executableRefname))
            self.commandsBySelector[wsThisCommandSelector] = parmSiteCommandResourceObject
        #
        wsThisCommandSwitch = parmSiteCommandResourceObject.switch
        if wsThisCommandSwitch is not None:
            if wsThisCommandSwitch in self.commandsBySwitch:
                wsFirstCommandObject = self.commandsBySwitch[wsThisCommandSwitch]
                PrintError('Duplicate program command switch "%s" for actions "%s.%s" and "%s.%s" in program "%s"' % (
                    wsThisCommandSwitch,
                    wsActionResourceObject.moduleResourceObject.pythonModuleName,
                    wsActionExeObject.__class__.__name__,
                    wsFirstCommandObject.actionResourceObject.moduleResourceObject.pythonModuleName,
                    wsFirstCommandObject.actionResourceObject.actionExeObject.__class__.__name__,
                    self.executableRefname))
            self.commandsBySwitch[wsThisCommandSwitch] = parmSiteCommandResourceObject

    # class bafSiteExecutableResource
    def ResolveResource(self):
        if self.configuration.verbose:
            PrintStatus("Resolving Python Program Resource %s with %d actions in module %s." % (
                self.executableFileName,
                len(self.primaryModuleResourceObject.actionResourceObjects),
                self.primaryModuleResourceObject.pythonModuleName))
        if len(self.executablesCommands) == 0:
            # If no commands have been explicitly defined, add all actions of the primary module
            for wsThisActionResourceObject in list(self.primaryModuleResourceObject.actionResourceObjects.values()):
                if wsThisActionResourceObject.actionExeObject.isAutoGenerateCommand:
                    self.AddCommand(wsThisActionResourceObject.actionClassName)
        for wsThisSiteCommandResourceObject in self.executablesCommands:
            wsThisSiteCommandResourceObject.ResolveResource()
            self.ResolveOneCommand(wsThisSiteCommandResourceObject)
        #
        self.resolvedImportPath = "%s.%s" % (self.primaryModuleResourceObject.pythonModuleName,
                                             self.primaryModuleResourceObject.pythonPackageName)
        if self.apacheSiteResource is not None:
            self.resolvedUri = self.apacheSiteResource.resolvedUri \
                + '/' + self.configuration.siteCgiDirectoryResource.definitionUriName \
                + '/' + self.executableFileName
