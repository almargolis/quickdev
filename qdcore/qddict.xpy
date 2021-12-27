#!/usr/bin/python
#############################################
#
#  QdDict class
#
#
#  FEATURES
#
#
#  WARNINGS
#
#  Warning 1:  It is extremely bad form to directly access self._data{}.
#	The class methods take minimal care to verify that the dictionary
#	is properly structured.
#  Warning 1B:  This class is intended to be a drop-in replacement for the
#	build-in dictionay type.  Any exceptions should be corrected by
#	fixing the class, not accessing self._data{}.
#
#  Copyright (C) 2001 by Albert B. Margolis - All Rights Reserved
#
#  2/11/2001:  Initial Release
#  3/ 3/2001:  __getitem__ failed on string.upper(key) when an integer
#		was used as the index.  Since the idea is to index easily,
#		modified get and set to reasonably convert all keys to
#		strings.  Create FixKey() to localize logic.
#  4/29/2001:  __repr__ failed if key was not a string.  Use back-quote
#		to stringize original key
# 12/20/2002:  Add AppendFromFile(), WriteToFile()
# 11/09/2003:  Add SrcFile parameter to AppendFromFile() to use open file
# 01/22/2012:  Make case insensitivity optional, but still the default
#
#############################################

#
# This module is essential for site bootstraping so it should have
# the minimal number of dependencies and none outside the development
# directory.
#
from . import utils

def MakeClassTDict_For_QdDict(exe_controller=None, InstanceClassname=None):
    from . import bafErTypes
    from . import bafTupleDictionary
    wsTDict = bafTupleDictionary.bafTupleDictionary(
        InstanceClassname=InstanceClassname,
        PrimaryDataPhysicalType=bafErTypes.Core_MapBafTypeCode,
        exe_controller=exe_controller)

    wsTDict.AddScalarElementReference('exe_action')
    wsTDict.AddScalarElementReference('exe_controller')
    wsTDict.AddContainerElement(
        '_data',
        RoleType=bafErTypes.Core_PrimaryParticipantRoleCode,
        PhysicalType=bafErTypes.Core_MapDictTypeCode,
        IsProcessElement=True)
    wsTDict.AddScalarElement('_defaultValue')
    wsTDict.AddScalarElementBoolean('_defaultValueAssigned')
    wsTDict.AddScalarElement('_exportFilePath')
    wsTDict.AddScalarElement('$qdconst.HIERARCHY_SEPARATOR_ATTR$')
    wsTDict.AddScalarElementBoolean('_isCaseSensitive')
    wsTDict.AddScalarElementReference(
        '_lastElementModified',
        IsProcessElement=True)
    wsTDict.AddScalarElement('_name')

    wsTDict.CompleteDictionary()
    return wsTDict


def GetDatum(
        parmSource,
        parmFieldname,
        Default=None,
        EmptyStringAsDefault=True,
        NoneAsDefault=True):
    # Defaults return None for not specified, empty string or actually None
    if parmFieldname in parmSource:
        wsDatum = parmSource[parmFieldname]
        if wsDatum is None:
            return Default
        if EmptyStringAsDefault and isinstance(
                wsDatum, str) and (
                wsDatum == ""):
            return Default
        return wsDatum
    else:
        return Default


def CopyFields(parmSource, parmTarget, FieldList=None):
    if FieldList is None:
        FieldList = list(parmSource.keys())
    for wsThis in FieldList:
        wsKeyParts = wsThis.split(':')
        wsTargetKey = wsKeyParts[0]
        if len(wsKeyParts) > 1:
            wsSourceKey = wsKeyParts[1]
        else:
            wsSourceKey = wsTargetKey
        wsValue = parmSource[wsSourceKey]
        parmTarget[wsTargetKey] = wsValue
    return parmTarget

class QdDict():
    """
    This is a replacement for the built-in dictionary class which
        (1) ignores the case of alphabetic key characters, and
     	(2) preserves the case of the first use of the key.
    	(3) provides a default value instead of exception for invalid key access.
        (4) maintains the insertion order for serial access.
    	(5) append() and replace() to copy and merge dictionaries.
    		Accepts QdDict, {} and ().
        (6) supports CommerceNode standards and idioms.

    Feature one is handy for any case-insensitive application, saving
    the client actions from muddying the code with string.upper()
    calls.

    Feature two is handy for symbol table usage which respects the
    user's definition as the proper spelling of the key (i.e. case
    is not significant to the application but is meaningful to the
    user).

    Feature three is that it returns a default value when you attempt to
    access an undefined key (rather than raising an exception).
    The default value is user defined via __init__() and
    self._defaultValue.  In many cases this allows for clearer
    client action code.

    Features three and four are now supported by built-in Dictionaries.
    I had them working here much sooner and this class provides many otherwise
    convenience features.
    """
    __slots__ = ('exe_action', 'exe_controller',
                 '_data', 'debug', '_defaultValue', '_defaultValueAssigned',
                          $'qdconst.SOURCE_FILE_PATH_ATTR$,
                          $'qdconst.HIERARCHY_SEPARATOR_ATTR$,
                          $'qdconst.IS_DIRECTORY_ATTR$,
                          '_isCaseSensitive',
                          '_lastElementModified', '_name',
                          '_upper_keys'
                 )

    def __init__(
            self,
            exe_action=None,
            exe_controller=None,
            is_case_sensitive=False,
            is_directory=False,
            is_hierarchy=True,
            hierarchy_separator=None,
            name=None,
            debug=0):
        self.exe_controller = exe_controller
        self.Assignexe_action(exe_action)
        self.debug = debug
        self._defaultValue = None
        self._defaultValueAssigned = False
        self.$qdconst.SOURCE_FILE_PATH_ATTR$ = None
        self.$qdconst.HIERARCHY_SEPARATOR_ATTR$ = hierarchy_separator
        self._isCaseSensitive = is_case_sensitive
        self.$qdconst.IS_DIRECTORY_ATTR$ = is_directory
        self._name = name
        if is_hierarchy:
            if self.$qdconst.HIERARCHY_SEPARATOR_ATTR$ is None:
                self.$qdconst.HIERARCHY_SEPARATOR_ATTR$ = $'qdconst.HIERARCHY_SEPARATOR_CHARACTER$
        self.Clear()

#  __lt__, __gt__, __le__, __ge__, __eq__, and __ne__
    def __eq__(self, other):
        if isinstance(other, QdDict):
            return self._data.__eq__(other._data)
        elif isinstance(other, dict):
            return self._data.__eq__(other)
        return super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __contains__(self, parmKey):				# this implement in operator
        try:
            wsThis = self.__getitem__(parmKey, allow_default=False)
            return True
        except IndexError:
            return False

    def __delitem__(self, parmKey):
        wsKey = self.FixKey(parmKey)
        del self._data[wsKey]

    def _translate_key(self, key):
        """ Returns the actual key in _data. """
        if self._isCaseSensitive:
            return key
        upper_key = key.upper()
        if upper_key in self._upper_keys:
            return self._upper_keys[upper_key]
        return key

    def __getitem__(self, key, allow_default=True):
        if self.$qdconst.HIERARCHY_SEPARATOR_ATTR$ is not None:
            pos = key.find(self.$qdconst.HIERARCHY_SEPARATOR_ATTR$)
            if pos > 0:
                local_key = self._translate_key(key[:pos])
                child_key = key[pos + 1:]
                if local_key in self._data:
                    child = self._data[local_key]
                    if isinstance(child, QdDict):
                        return child[child_key]
        local_key = self._translate_key(key)
        if local_key in self._data:
            return self._data[local_key]
        if allow_default and self._defaultValueAssigned:
            return self._defaultValue
        if self._name is None:
            wsname = ""
        else:
            wsname = self._name + " "
        raise IndexError(
            "%sNV value has not been assigned for name %s" %
            (wsname, repr(local_key)))

    def __len__(self):
        return len(self._data)

    def get(self, key, default_value=None):
        if key in self:
            return self[key]
        else:
            return default_value

    @property
    def name(self):
        return self._name

    def __repr__(self):
        return repr(self._data)

    def __setitem__(self, key, value, hierarchy_separator=None):
        if self.$qdconst.HIERARCHY_SEPARATOR_ATTR$ is not None:
            pos = key.find(self.$qdconst.HIERARCHY_SEPARATOR_ATTR$)
            if pos > 0:
                # Set value further down the tree.
                local_key = self._translate_key(key[:pos])
                child_key = key[pos + 1:]
                if local_key in self._data:
                    child = self._data[local_key]
                    if isinstance(child, QdDict):
                        child[child_key] = value
                        return
            if isinstance(value, QdDict):
                # Since a hierarchy is enabled, treat this as part of the
                # hierarchy, not as a value that happens to be an QdDict.
                if hierarchy_separator is not None:
                    value.$qdconst.HIERARCHY_SEPARATOR_ATTR$ = hierarchy_separator
                if value.$qdconst.HIERARCHY_SEPARATOR_ATTR$ is None:
                    value.$qdconst.HIERARCHY_SEPARATOR_ATTR$ = self.$qdconst.HIERARCHY_SEPARATOR_ATTR$
                if value.exe_action is None:
                    value.exe_action = self.exe_action
                if value.exe_controller is None:
                    value.exe_controller = self.exe_controller
        # Set value at this level of tree.
        local_key = self._translate_key(key)
        if local_key not in self._data:
            # this is a new key
            if local_key != local_key.upper():
                self._upper_keys[local_key.upper()] = local_key
        self._data[local_key] = value
        self._lastElementModified = local_key

    def _baf_MakeModel(self):
        import pylib.bafErModel.py as bafErModel
        wsModel = bafErModel.BafErTable()
        for (wsThisKey, wsThisValue) in list(self._data.items()):
            wsModel.AddElement(wsThisKey, Sample=wsThisValue)
        wsModel.CompleteTableDefinition()
        return wsModel

    def append(self, key, value):
        if self.__contains__(key):
            raise IndexError
        self.__setitem__(key, value)

    def AppendDatum(self, parmKey, parmValue, hierarchy_separator=None):
        if parmKey in self:
            raise IndexError(
                "%s value has already been assigned for name %s" %
                (self._name, repr(parmKey)))
        self.__setitem__(
            parmKey,
            parmValue,
            hierarchy_separator=hierarchy_separator)
        return parmValue

    def GetDatum(self, parmKey, SubstituteValue=None):
        if parmKey not in self:
            return SubstituteValue
        return self.__getitem__(parmKey)

    # bafTupleObject
    def _AppendDict(self, parmDict):
        for (wsKey, wsValue) in list(parmDict.items()):
            self.AppendDatum(wsKey, wsValue)

    def _MergeDict(self, parmDict):
        if parmDict is None:
            return
        for (wsKey, wsValue) in list(parmDict.items()):
            self.__setitem__(wsKey, wsValue)

    def Assignexe_action(self, parmexe_action):
        self.exe_action = parmexe_action
        if parmexe_action is not None:
            if self.exe_controller is None:
                self.exe_controller = parmexe_action.exe_controller

    def AssignDefaultValue(self, parmDefaultValue):
        self._defaultValue = parmDefaultValue
        self._defaultValueAssigned = True

    def ConfigureAsHierarchy(
            self,
            hierarchy_separator=$'qdconst.HIERARCHY_SEPARATOR_CHARACTER$):
        if self.$qdconst.HIERARCHY_SEPARATOR_ATTR$ is None:
            self.$qdconst.HIERARCHY_SEPARATOR_ATTR$ = hierarchy_separator

    def MakeChildTuple(self, parmKey, hierarchy_separator=None):
        wsValue = self.__class__(name=parmKey)
        self.AppendDatum(
            parmKey,
            wsValue,
            hierarchy_separator=hierarchy_separator)
        return wsValue

    @property
    def defaultValue(self):
        return self._defaultValue

    @defaultValue.setter
    def defaultValue(self, value):
        self._defaultValue = value
        self._defaultValueAssigned = True

    def Clear(self):
        self._data = {}
        self._upper_keys = {}
        self._lastElementModified = None

    def ConfigureAsCaseSensitive(parmis_case_sensitive=True):
        # probably should convert existing entries if this is a change
        self._isCaseSensitive = parmis_case_sensitive

    def Dup(self):
        wsDup = QdDict()
        wsDup._defaultValue = self._defaultValue
        wsDup._defaultValueAssigned = self._defaultValueAssigned
        for (wsKey, wsData) in list(self._data.items()):
            wsDup.__setitem__(wsData[0], wsData[1])
        return wsDup

    def AsStr(self, key, Default=""):
        value = self.__getitem__(key, allow_default=False)
        return utils.Str(value)

    def AsStrUpper(self, parmKey, Default=""):
        wsKey = self.FixKey(parmKey)
        if wsKey in self._data:
            wsValue = self._data[wsKey][1]
        else:
            wsValue = Default
        wsValue = utils.Upper(wsValue)
        self.__setitem__(parmKey, wsValue)
        return wsValue

    def AsInt(self, parmKey, Default=0):
        wsKey = self.FixKey(parmKey)
        if wsKey in self._data:
            wsValue = self._data[wsKey][1]
        else:
            wsValue = Default
        wsValue = utils.Int(wsValue)
        self.__setitem__(parmKey, wsValue)
        return wsValue

    def change_key(self, parmOldKey, parmNewKey):
        wsOldKey = self.FixKey(parmOldKey)
        if wsOldKey in self._data:
            wsValue = self._data[wsOldKey][1]
            del self._data[wsOldKey]
            self.__setitem__(parmNewKey, wsValue)
            return parmNewKey
        return None

#  def append(self, parmEntry):
#    try:
#      for (wsKey, wsValue) in parmEntry.items():
#        self.__setitem__(wsValue[0], wsValue[1])
#      return self
#    except:
#      if (type(parmEntry) == type(())) and (len(parmEntry) >= 2):
#        if len(parmEntry) == 2:
##          self.__setitem__(parmEntry[0], parmEntry[1])
#        else:
#          self.__setitem__(parmEntry[0], parmEntry[1:])
#        return self
#      else:
#        return None

    def keys(self):
        return self._data.keys()

    def sorted_keys(self):
        return sorted(self._data.keys())

    def keyeditems(self):
        wsList = []
        for (wsKey, wsValue) in list(self._data.items()):
            wsList.append(wsValue)
        return wsList

    def items(self):
        return self._data.items()

    def replace(self, parmEntry):
        self._data = {}
        return self.append(parmEntry)

    def values(self):
        return self._data.values()

    def SetLenient(self, DefaultValue=None):
        self.defaultValue = DefaultValue

    def sorted_values(self):
        sorted_keys = self.sorted_keys()
        result = []
        for this_key in sorted_keys:
            result.append(self._data[this_key])
        return result

    def ValuesForKeyList(self, parmKeyList):
        wsList = []
        for wsThisKey in parmKeyList:
            wsList.append(self[wsThisKey])
        return wsList

    def Accumulate(self, parmKey, parmValue):
        if parmKey in self:
            pass
        else:
            self.__setitem__(parmKey, 0)
        self[parmKey] += parmValue

    def AppendFromFile(self, parmFilename, SrcFile=None):
        from . import bzTextFile
        wsOpenedHere = False
        if not SrcFile:
            SrcFile = bzTextFile.open(parmFilename, "r")
            wsOpenedHere = True
        if not SrcFile:
            return False
        while not SrcFile.EOF:
            wsLine = SrcFile.readline()
            wsEqPos = wsLine.find("=")
            if wsEqPos < 1:
                continue
            wsKey = wsLine[:wsEqPos].strip()
            wsValue = wsLine[wsEqPos + 1:].strip()
            self[wsKey] = wsValue
        if wsOpenedHere:
            SrcFile.close()
            del(SrcFile)
        return True


def testAssign(parmDict, parmKey, parmValue):
    print("Assign " + parmDict._name
          + "[" + parmKey + "] = " + repr(parmValue))
    parmDict[parmKey] = parmValue


def testChangeKey(parmDict, parmOldKey, parmNewKey):
    print("Change " + parmDict._name
          + "[" + parmOldKey + "]  TO "
                + parmDict._name
                + "[" + parmNewKey + "]")
    parmDict.change_key(parmOldKey, parmNewKey)


def testCompare(parmDict1, parmDict2):
    print("Compare " + parmDict1._name + " TO " + parmDict2._name
          + utils.iif(parmDict1 == parmDict2, " are equal", " are NOT equal"))


def testReference(parmDict, parmKey):
    wsValue = parmDict[parmKey]
    print("Reference " + parmDict._name
          + "[" + parmKey + "] = " + repr(wsValue))


if (__name__ == "__main__"):
    wsDict = QdDict()
    wsDict._name = "wsDict"
    wsDict2 = QdDict()
    wsDict2._name = "wsDict2"
    testAssign(wsDict, "fred", "string 1")
    testAssign(wsDict, "joe", "string 2")
    testReference(wsDict, "FRED")
    testReference(wsDict, "JoE")
    testAssign(wsDict, "FRED", "string 1A")
    testAssign(wsDict, "JOE", "string 2A")
    print("*************** wsDict._data **")
    print(repr(wsDict._data))
    print("*************** wsDict **")
    print(repr(wsDict))
    print("*************** wsDict.keys() **")
    print(repr(list(wsDict.keys())))
    print("*************** wsDict.values() **")
    print(repr(list(wsDict.values())))
    testChangeKey(wsDict, "JOE", "JoE")
    print("*************** wsDict **")
    print(repr(wsDict))
    wsDict2.replace(wsDict)
    testCompare(wsDict, wsDict2)
    print("*************** wsDict2 **")
    print(repr(wsDict2))
    testAssign(wsDict2, "fReD", "string B")
    print("*************** wsDict2 **")
    print(repr(wsDict2))
    testCompare(wsDict, wsDict2)
