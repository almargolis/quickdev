"""
Functions to read and write ini files.

This module is somewhat out of place in ezutils instead of
ezcore because it is need for ezstart, potentially before Python
importing is configured by the virtual environment.
"""

import ezconst
from ezcore import textfile

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
    __slots__ = ('_data', '_serialized_file_path')

    def __init__(self, path=None):
        self._data = {}
        self._serialized_file_path = path

    def get_dict(self, key):
        parts = key.split('.')
        data = self._data
        for this in parts[:-1]:
            data = data[this]
        return data

    def __getitem__(self, key):
        data = self.get_dict(key)
        return data[key[-1]]

    def __setitem__(self, key, value):
        data = self.get_dict(key)
        data[key[-1]] = value

    def write(self, path=None):
        if path is not None:
            pass

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

def read_ini_file(target, path=None, hierarchy_separator=None, exe_controller=None, debug=0):
    """
    Load an ini text file into a hierarchy of map type objects.
    Load supports fundamental types such as Python dict and CommerceNode
    types such as
    """

    with ezconst.serialized_file(target, path=path) as f:
        ini_lines = f.readlines()
    return ParseIniLines(wsIniLines, target, HierarchySeparator=HierarchySeparator, ExeController=ExeController, Debug=Debug)

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

def write_ini_level(f, data, section_name=''):
    children = []
    if section_name != '':
        f.write('[{}]\n'.format(section_name))
    for key, value in data.items():
        try:
            child_data = value.items()
            children.append((key, value))
        except AttributeError:
            # We get here if value doesn't have an items method.
            # It's a scalar.
            f.write('{} = {}\n'.format(key, value))
    for child_key, child_data in children:
        f.write('\n')
        child_section_name = child_key
        if section_name != '':
            child_section_name = section_name + '.'
        write_ini_level(f, child_data, section_name=child_section_name)

def write_ini_file(source, path=None, exe_controller=None):
    """ Write a hierarchy of dict-like data as an ini file. """
    if path is None:
        path = getattr(source, '_serialized_file_path', None)
    if path is None:
        raise ValueError("No path specified for output file.")
    if exe_controller is None:
        exe_controller = getattr(source, 'exe_controller', None)
    f = textfile.write_with_swap_file(path, backup=True)
    if f is None:
        if exe_controller is not None:
            exe_controller.errs.AddUserCriticalMessage("Unable to open output INI file '%s'" % (wsFilePath))
        return False
    write_ini_level(f, source)
    f.keep()
    return True
