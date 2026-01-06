#
# MakePythonExecutionStub
#
# The CommandMap created here is a structure used directly by bafExeController
# to launch command execution. Each entry in the map is a CommandRefname
# mapped by a CommandSelector. For cgi mode function codes, the selector is
# always all upper case letters. For cli mode switches, the selector folows
# unix tradition and is case sensitive.
#


def MakePythonExecutionStub(parmConfiguration, ExecutableResource=None, IsHelp=False):
    def WriteCommands(parmSection):
        if parmSection == 'cgi':
            wsCommands = list(ExecutableResource.commandsBySelector.values())
        else:
            wsCommands = list(ExecutableResource.commandsBySwitch.values())

        if parmSection == 'cgi':
            wsPropertyName = CoreRunCommandsCgi
        else:
            wsPropertyName = CoreRunCommandSwitchesCli
        wsCommandMap = {}
        for wsThisCommandResource in wsCommands:
            wsThisActionResource = wsThisCommandResource.actionResourceObject
            if parmSection == 'cgi':
                wsCommandSelector = bzUtil.Upper(
                    wsThisCommandResource.selector)
            else:
                wsCommandSelector = wsThisCommandResource.switch
            wsCommandMap[wsCommandSelector] = wsThisCommandResource.commandRefname
        wsF.write("    self.%s            = %s" % (wsPropertyName,
                                                   bafExpCodeWriter.MakePythonDictLiteral(wsCommandMap)))
    #
    #
    if ExecutableResource:
        wsPrefix = 'Program'
        wsModuleName = ExecutableResource.primaryModuleResourceObject.pythonModuleName
        if ExecutableResource.apacheSiteResource is not None:
            wsCgiDir = parmConfiguration.siteCgiDirectoryResource.resolvedPath
            wsOutputFileName = os.path.join(
                wsCgiDir, ExecutableResource.executableFileName)
        else:
            wsProgDir = parmConfiguration.siteProgDirectoryResource.resolvedPath
            wsOutputFileName = os.path.join(
                wsProgDir, ExecutableResource.executableFileName)
    else:
        # if no ExecutableResource, we are making one of the standard files.
        if IsHelp:
            wsOutputFileName = os.path.join(
                parmConfiguration.siteHelpPyFileResource.resolvedPath)
        else:
            wsOutputFileName = os.path.join(
                parmConfiguration.siteTestImportPyFileResource.resolvedPath)

    wsF = OpenTextFile(wsOutputFileName, "w")
    wsF.write("#!/usr/bin/python\n")
    wsF.write("#\n")
    wsF.write("import %s\n" %
              (parmConfiguration.sitePathInfoPyFileResource.resolvedNameBase))
    wsF.write("try:\n")
    wsF.write("  import %s\n" %
              (parmConfiguration.siteWebInfoPyFileResource.resolvedNameBase))
    wsF.write("except:\n")
    wsF.write("  pass\n")
    wsF.write("#\n")
    if ExecutableResource:
        wsObjectClassName = wsPrefix + 'Info'
        if ExecutableResource.apacheSiteResource is None:
            wsIsSsl = False
            wsIsCgi = False
        else:
            wsIsSsl = ExecutableResource.apacheSiteResource.isSsl
            wsIsCgi = True
        if len(ExecutableResource.commandsBySelector) >= 1:
            # For new style modules, import the application runtime module
            wsF.write("import %s.%s as %s\n" % (parmConfiguration.bafLibDirectoryResource.resolvedName,
                                                CoreExeControllerModuleName, CoreExeControllerModuleName))
        else:
            # For transitional style, import the program module
            wsF.write("import %s.%s as %s\n" % (
                ExecutableResource.primaryModuleResourceObject.pythonPackageName, wsModuleName, wsModuleName))
        wsF.write("\n")
        wsF.write("class %s:\n" % (wsObjectClassName))
        wsF.write("  def __init__(self):\n")
        wsF.write("    self.%s = '%s'\n" %
                  (CoreRunIsSslYN, bzUtil.BoolAsStr(wsIsSsl)))
        wsF.write("    self.%s = '%s'\n" % (CoreRunRequireAdminLoginYN,
                                            bzUtil.BoolAsStr(ExecutableResource.requireAdminLogin)))
        wsF.write("    self.%s = '%s'\n" %
                  (CoreRunIsCgiYN, bzUtil.BoolAsStr(wsIsCgi)))
        wsF.write("    self.%s = '%s'\n" %
                  (CoreRunProgramName, ExecutableResource.executableFileName))
        wsF.write("    self.%s = '%s'\n" % (
            CoreRunDefaultCommandRefname, ExecutableResource.defaultCommandRefname))

        if ExecutableResource.executableFileName == 'config':
            print(">>>>>>>>>>>>>>>>>>>")
            print(repr(ExecutableResource.commandsBySwitch))
            print(">>>>>>>>>>>>>>>>>>>")
        WriteCommands('cgi')
        WriteCommands('cli')

        #
        wsF.write("#\n")
        wsF.write("if __name__ == '__main__':\n")
        if len(ExecutableResource.commandsBySelector) >= 1:
            # New style
            wsF.write("  wsInfo = %s()\n" % (wsObjectClassName))
            wsF.write("  wsCtlr = %s.%s()\n" %
                      (CoreExeControllerModuleName, CoreExeControllerClassName))
            wsF.write("  wsCtlr.%s(wsInfo)\n" %
                      (CoreExeControllerRunMethodName))
        else:
            # Transitional style
            # This needs to be kept permanently, but in the long run it should only be
            # used for the bootstrap config program created during site initialization
            wsF.write("  %s.%s()\n" %
                      (wsModuleName, CoreTransitionalRunFunctionName))
    else:
        if IsHelp:
            # Create help
            wsF.write("if __name__ == '__main__':\n")
            for wsThisExecutableRefname in parmConfiguration.executableRefnames:
                wsThisExecutableResource = parmConfiguration.executables[wsThisExecutableRefname]
                if len(wsThisExecutableResource.commandsBySwitch) > 0:
                    wsF.write("  print '%s'\n" %
                              (wsThisExecutableResource.executableFileName))
                    for wsThisCommandResource in list(wsThisExecutableResource.commandsBySwitch.values()):
                        wsF.write("  print '  %s %s'\n" % (
                            wsThisCommandResource.switch, wsThisCommandResource.commandRefname))
        else:
            # Create testimport
            for wsThisModuleKeyName in parmConfiguration.pythonModuleList:
                wsModuleResourceObject = parmConfiguration.pythonModules[wsThisModuleKeyName]
                try:
                    wsSelfTest = getattr(
                        wsModuleResourceObject.pythonModule, SelfTestCommandFunc)
                except:
                    wsSelfTest = None
                wsF.write("import %s.%s as %s\n" % (wsModuleResourceObject.pythonPackageName,
                                                    wsModuleResourceObject.pythonModuleName, wsModuleResourceObject.pythonModuleName))
                if wsSelfTest is None:
                    pass
                else:
                    wsF.write("%s.%s()\n" % (
                        wsModuleResourceObject.pythonModuleName, SelfTestCommandFunc))
            wsF.write("#\n")
            wsF.write("if __name__ == '__main__':\n")
            wsF.write("  print 'All Modules Imported'\n")

    CloseTextFile(parmConfiguration, wsF, wsOutputFileName)
