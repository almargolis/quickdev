#!/usr/bin/python
#############################################
#
#  TupleData class
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
from ezcore import utils

def MakeClassTDict_For_TupleData(ExeController=None, InstanceClassName=None):
    from . import bafErTypes
    from . import bafTupleDictionary
    wsTDict = bafTupleDictionary.bafTupleDictionary(
        InstanceClassName=InstanceClassName,
        PrimaryDataPhysicalType=bafErTypes.Core_MapBafTypeCode,
        ExeController=ExeController)

    wsTDict.AddScalarElementReference('exeAction')
    wsTDict.AddScalarElementReference('exeController')
    wsTDict.AddContainerElement(
        '_data',
        RoleType=bafErTypes.Core_PrimaryParticipantRoleCode,
        PhysicalType=bafErTypes.Core_MapDictTypeCode,
        IsProcessElement=True)
    wsTDict.AddScalarElement('_defaultValue')
    wsTDict.AddScalarElementBoolean('_defaultValueAssigned')
    wsTDict.AddScalarElement('_exportFilePath')
    wsTDict.AddScalarElement('_hierarchySeparator')
    wsTDict.AddScalarElementBoolean('_isCaseSensitive')
    wsTDict.AddScalarElementReference(
        '_lastElementModified',
        IsProcessElement=True)
    wsTDict.AddScalarElement('_name')

    wsTDict.CompleteDictionary()
    return wsTDict


def GetDatum(
        parmSource,
        parmFieldName,
        Default=None,
        EmptyStringAsDefault=True,
        NoneAsDefault=True):
    # Defaults return None for not specified, empty string or actually None
    if parmFieldName in parmSource:
        wsDatum = parmSource[parmFieldName]
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

class TupleData(object):
    """
    This is a replacement for the built-in dictionary class which
        (1) ignores the case of alphabetic key characters, and
     	(2) preserves the case of the first use of the key.
    	(3) provides a default value instead of exception for invalid key access.
        (4) maintains the insertion order for serial access.
    	(5) append() and replace() to copy and merge dictionaries.
    		Accepts TupleData, {} and ().
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
    __slots__ = ('exeAction', 'exeController',
                 '_data', '_defaultValue', '_defaultValueAssigned',
                          '_serialized_file_path',
                          '_hierarchySeparator',
                          '_isCaseSensitive',
                          '_lastElementModified', '_name'
                 )

    def __init__(
            self,
            ExeAction=None,
            ExeController=None,
            IsCaseSensitive=False,
            IsHierarchy=False,
            HierarchySeparator=None,
            Name=None):
        self.exeController = ExeController
        self.AssignExeAction(ExeAction)
        self._defaultValue = None
        self._defaultValueAssigned = False
        self._serialized_file_path = None
        self._hierarchySeparator = HierarchySeparator
        self._isCaseSensitive = IsCaseSensitive
        self._name = Name
        if IsHierarchy:
            if self._hierarchySeparator is None:
                self._hierarchySeparator = '.'
        self.Clear()

    def __cmp__(self, parmOther):
        if parmOther:
            if len(self._data) != len(parmOther):
                return -1
            for (wsKey, wsValue) in list(self._data.items()):
                # parmOther can be a TupleData or a normal {}
                if wsKey not in parmOther:
                    return -1
                if parmOther[wsKey] != wsValue[1]:
                    return -1
            return 0
        else:
            if len(self._data) == 0:
                return 0
            else:
                return -1

    def __contains__(self, parmKey):				# this implement in operator
        try:
            wsThis = self.__getitem__(parmKey, AllowDefault=False)
            return True
        except IndexError:
            return False

    def __delitem__(self, parmKey):
        wsKey = self.FixKey(parmKey)
        del self._data[wsKey]

    def __getitem__(self, parmKey, AllowDefault=True):
        wsKey = self.FixKey(parmKey)
        if self._hierarchySeparator is not None:
            wsPos = wsKey.find(self._hierarchySeparator)
            if wsPos > 0:
                wsThis = wsKey[:wsPos]
                wsRest = wsKey[wsPos + 1:]
                if wsThis in self._data:
                    wsChild = self._data[wsThis]
                    if isinstance(wsChild, TupleData):
                        return wsChild[wsRest]
        if wsKey in self._data:
            return self._data[wsKey][1]
        if AllowDefault and self._defaultValueAssigned:
            return self._defaultValue
        if self._name is None:
            wsName = ""
        else:
            wsName = self._name + " "
        raise IndexError(
            "%sNV value has not been assigned for name %s" %
            (wsName, repr(parmKey)))

    def __len__(self):
        return len(self._data)

    @property
    def name(self):
        return self._name

    def __repr__(self):
        wsString = "{"
        for (wsKey, wsValue) in list(self._data.items()):
            if wsString != "{":
                wsString += ","
            wsString += repr(wsValue[0]) + ": " + repr(wsValue[1])
        wsString += "}"
        return wsString

    def __setitem__(self, parmKey, parmValue, HierarchySeparator=None):
        wsKey = self.FixKey(parmKey)
        if self._hierarchySeparator is not None:
            if isinstance(parmValue, TupleData):
                if HierarchySeparator is not None:
                    parmValue._hierarchySeparator = HierarchySeparator
                if parmValue._hierarchySeparator is None:
                    parmValue._hierarchySeparator = self.hierarchySeparator
                if parmValue.exeAction is None:
                    parmValue.exeAction = self.exeAction
                if parmValue.exeController is None:
                    parmValue.exeController = self.exeController
        if wsKey in self._data:
            parmKey = self._data[wsKey][0]
        self._data[wsKey] = (parmKey, parmValue)
        self._lastElementModified = parmValue

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

    def AppendDatum(self, parmKey, parmValue, HierarchySeparator=None):
        if parmKey in self:
            raise IndexError(
                "%s value has already been assigned for name %s" %
                (self._name, repr(parmKey)))
        self.__setitem__(
            parmKey,
            parmValue,
            HierarchySeparator=HierarchySeparator)
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

    def AssignExeAction(self, parmExeAction):
        self.exeAction = parmExeAction
        if parmExeAction is not None:
            if self.exeController is None:
                self.exeController = parmExeAction.exeController

    def AssignDefaultValue(self, parmDefaultValue):
        self._defaultValue = parmDefaultValue
        self._defaultValueAssigned = True

    def ConfigureAsHierarchy(
            self,
            HierarchySeperator='.'):
        if self._hierarchySeparator is None:
            self._hierarchySeparator = HierarchySeparator

    def MakeChildTuple(self, parmKey, HierarchySeparator=None):
        wsValue = self.__class__(Name=parmKey)
        self.AppendDatum(
            parmKey,
            wsValue,
            HierarchySeparator=HierarchySeparator)
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
        self._lastElementModified = None

    def ConfigureAsCaseSensitive(parmIsCaseSensitive=True):
        # probably should convert existing entries if this is a change
        self._isCaseSensitive = parmIsCaseSensitive

    def Dup(self):
        wsDup = TupleData()
        wsDup._defaultValue = self._defaultValue
        wsDup._defaultValueAssigned = self._defaultValueAssigned
        for (wsKey, wsData) in list(self._data.items()):
            wsDup.__setitem__(wsData[0], wsData[1])
        return wsDup

    def FixKey(self, parmKey):
        if parmKey is None:
            return None
        if isinstance(parmKey, str):
            if self._isCaseSensitive:
                return parmKey
            else:
                return parmKey.upper()
        if isinstance(parmKey, type(0)):
            return str(parmKey)
        return repr(parmKey)

    def AsStr(self, parmKey, Default=""):
        wsKey = self.FixKey(parmKey)
        if wsKey in self._data:
            wsValue = self._data[wsKey][1]
        else:
            wsValue = Default
        wsValue = utils.Str(wsValue)
        self.__setitem__(parmKey, wsValue)
        return wsValue

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
        wsList = []
        for (wsKey, wsValue) in list(self._data.items()):
            wsList.append(wsValue[0])
        return wsList

    def sortedkeys(self):
        wsList = list(self.keys())
        return sorted(wsList)

    def keyeditems(self):
        wsList = []
        for (wsKey, wsValue) in list(self._data.items()):
            wsList.append(wsValue)
        return wsList

    def items(self):
        wsList = []
        for (wsKey, wsValue) in list(self._data.items()):
            wsList.append((wsValue[0], wsValue[1]))
        return wsList

    def replace(self, parmEntry):
        self._data = {}
        return self.append(parmEntry)

    def values(self):
        wsList = []
        for (wsKey, wsValue) in list(self._data.items()):
            wsList.append(wsValue[1])
        return wsList

    def SetLenient(self, DefaultValue=None):
        self.defaultValue = DefaultValue

    def sortedvalues(self):
        wsSortedKeys = self.sortedkeys()
        wsList = []
        for wsThisKey in wsSortedKeys:
            wsList.append(self[wsThisKey])
        return wsList

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

    def AppendFromFile(self, parmFileName, SrcFile=None):
        from . import bzTextFile
        wsOpenedHere = False
        if not SrcFile:
            SrcFile = bzTextFile.open(parmFileName, "r")
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

    def WriteToFile(self, parmFileName, SelectStartsWith="", DstFile=None):
        from . import bzTextFile
        if not self._isCaseSensitive:
            SelectStartsWith = SelectStartsWith.upper()
        wsSelectLen = len(SelectStartsWith)
        if not DstFile:
            DstFile = bzTextFile.open(parmFileName, "w")
        if not DstFile:
            return None
        for (wsKey, wsValue) in list(self.items()):
            if wsSelectLen > 0:
                if wsKey[:wsSelectLen] != SelectStartsWith:
                    continue
            DstFile.writeln(wsKey + '=' + utils.Str(wsValue))


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
    wsDict = TupleData()
    wsDict._name = "wsDict"
    wsDict2 = TupleData()
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
