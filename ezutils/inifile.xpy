"""
Functions to read and write ini files.

This module is somewhat out of place in ezutils instead of
ezcore because it is need for ezstart, potentially before Python
importing is configured by the virtual environment.
"""

#
# INI File Support
#
# These should be the only methods that read/write INI files.
#
# In order to be fully supported, the data objects should include the following:
#   _exportFilePath
#   MakeChildTuple()
#   items()
#
# To the degree possible, these methods should also work with general Python types.
#

class EzIni():
    __slots__ = ('_data', $ezconst.SERIALIZED_FILE_PATH$)

    def __init__(self):
        self._data = {}
        self.$ezconst.SERIALIZED_FILE_PATH$ = None

    def get_dict(self, key):
        parts = key.split('.')
        data = self._data
        for this in parts[:-1]
            data = data[this]
        return data

    def __getitem__(self, key):
        data = self.get_dict(key)
        return data[key[-1]]

    def __setitem__(self, key, value):
        data = self.get_dict(key)
        data[key[-1]] = value

def AsIniText(parmData, Level=0, ParentName=''):
  wsIni				= ''
  wsChildRecordNames		= []
  for (wsChildName, wsChildData) in list(parmData.items()):
    if hasattr(parmData, 'items'):
      wsChildRecordNames.append(wsChildName)
    else:
      # This is an atomic data type
      wsIni			+= '%s = %s\n' % (wsChildName, wsChildData)
  for wsThisRecordName in wsChildRecordNames:
    if Level > 0:
      wsSectionName		= ParentName + '.' + wsThisRecordName
    else:
      wsSectionName		= wsThisRecordName
    wsIni			+= '[%s]\n' % (wsThisRecordName)
    wsIni			+= AsIniText(parmData[wsThisRecordName], Level=Level+1, ParentName=wsSectionName)
  return wsIni

INI_PARSE_STATE_INIT		= 0
INI_PARSE_STATE_NORMAL_LINE	= 1
INI_PARSE_STATE_START_MULTI	= 2
INI_PARSE_STATE_COLLECT_MULTI	= 3

def load(target, ini_path=None, hierarchy_separator=None, exe_controller=None, debug=0):
    """
    Load an ini text file into a hierarchy of map type objects.
    Load supports fundamental types such as Python dict and CommerceNode
    types such as
    """

    f = serializer.open_serialized_file(target, path=ini_path)
    if f is None:
        return False
    ini_lines = f.readlines()
    f.close()
    del f
    return ParseIniLines(wsIniLines, parmTarget, HierarchySeparator=HierarchySeparator, ExeController=ExeController, Debug=Debug)

def ParseIniLines(parmIniLines, parmTarget, HierarchySeparator=None, ExeController=None, Debug=0):
  wsTarget			= parmTarget
  wsState			= INI_PARSE_STATE_INIT			# parsing state
  for wsThisLine in parmIniLines:
    #print "^^^", wsThisLine, `parmTarget._tdict`
    if wsState == INI_PARSE_STATE_COLLECT_MULTI:
      # This is not required in file if the variable continues to EOF
      if wsThisLine == wsEndIdentifierString:
        wsState			= INI_PARSE_STATE_INIT
      else:
        wsTarget[wsKey].append(wsThisLine)
      continue
    if not wsThisLine:							# blank line
      continue
    if wsThisLine[0] == '#':						# comment line
      continue
    if wsThisLine[0] == '[':						# section start line
      wsPos			= wsThisLine.find(']')
      if wsPos < 1:
        if ExeController:
          ExeController.errs.AddUserCriticalMessage('Invalid Ini section line "%s"' % (wsThisLine))
        continue
      wsSectionFullName		= wsThisLine[1:wsPos]
      wsSectionNameParts	= wsSectionFullName.split('.')
      wsTarget			= parmTarget
      for wsThisSectionNamePart in wsSectionNameParts:
        if wsThisSectionNamePart in wsTarget:
          wsTarget		= wsTarget[wsThisSectionNamePart]
          if not isinstance(wsTarget, bafDataStore.bafTupleObject):
            if ExeController:
              ExeController.errs.AddUserCriticalMessage('Invalid section name part "%s" in Ini file line "%s"' % (
							wsThisSectionNamePart, wsThisLine))
            break
        else:
          wsSubTDictElement	= wsTarget._tdict.Element(wsThisSectionNamePart)
          if wsSubTDictElement is None:
            wsChildTDict	= None
          else:
            wsChildTDict	= wsSubTDictElement.collectionItemTDict
          wsTarget		= wsTarget.MakeChildTuple(Name=wsThisSectionNamePart,
							HierarchySeparator=HierarchySeparator,
							TDict=wsChildTDict)
      # print "XML adding ", wsSectionNameParts
      continue
    if wsThisLine[0] == '=':
      wsState			= INI_PARSE_STATE_START_MULTI		# declare multi-line value variable
      wsStartPos		= 1
    else:
      wsState			= INI_PARSE_STATE_NORMAL_LINE		# declare single-line value variable
      wsStartPos		= 0
    #
    wsEndPos			= wsThisLine.find('=', wsStartPos+1)
    if wsEndPos < 1:
      if ExeController:
        ExeController.errs.AddUserCriticalMessage('Invalid Ini file line "%s"' % (wsThisLine))
      continue
    wsKey			= wsThisLine[wsStartPos:wsEndPos].strip()
    wsValue			= wsThisLine[wsEndPos+1:].strip()
    if wsKey in wsTarget:
      if ExeController:
        ExeController.errs.AddUserCriticalMessage('Duplicate key in Ini file line "%s"' % (wsThisLine))
      continue
    if wsState == INI_PARSE_STATE_NORMAL_LINE:
      wsTarget[wsKey]		= wsValue
    elif wsState == INI_PARSE_STATE_START_MULTI:
      # Uses a Python array solves my immediate problem. I really need to have DTD and make
      # sure the data types are consistent with that. This is a kludge.
      wsEndIdentifierString	= "--%s--%s--" % (wsKey, wsValue)
      wsTarget[wsKey]		= []
      wsState			= INI_PARSE_STATE_COLLECT_MULTI		# collect multi-line value variable
    else:
      if ExeController:
        ExeController.errs.AddDevCriticalMessage('Invalid parse state %s for Ini file line "%s"' % (wsState, wsThisLine))
  return True

def WriteIniRecord(parmFile, parmRecord, Level=0, ParentName=''):
  if Level > 0:
    parmFile.write('[%s]\n' % (ParentName))
  wsChildRecords			= []
  for (wsKey, wsValue) in list(parmRecord.items()):
    print("III", wsKey, wsValue.__class__.__name__, wsValue)
    if isinstance(wsValue, bafDataStore.bafTupleObject):
      wsChildRecords.append((wsKey, wsValue))
    else:
      parmFile.write('%s = %s\n' % (wsKey, wsValue))
  # Child records need to be written after atomic fields or we wont know which record / child record each
  # field name belongs to.
  for (wsKey, wsValue) in wsChildRecords:
    if ParentName == '':
      wsParentName			= ''
    else:
      wsParentName			= ParentName + '.'
    wsParentName			+= wsKey
    WriteIniRecord(parmFile, wsValue, Level=Level+1, ParentName=wsParentName)

def WriteIniFile(parmTarget, Path=None, ExeController=None):
  wsFilePath				= Path
  if wsFilePath is None:
    try:
      wsFilePath			= parmTarget._exportFilePath
    except:
      pass
  if ExeController is None:
    ExeController			= parmTarget.exeController
  if wsFilePath is None:
    return False
  wsF					= bzTextFile.OpenBzTextFile(wsFilePath, "w", Temp=True)
  if not wsF:
    if ExeController is not None:
      ExeController.errs.AddUserCriticalMessage("Unable to open output INI file '%s'" % (wsFilePath))
    return False
  WriteIniRecord(wsF, parmTarget)
  wsF.TempClose()
  return True
