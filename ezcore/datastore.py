#!/usr/bin/python
#############################################
#
#  TupleObject class
#
#
#  FEATURES
#
#	TupleObject is a dictionary object that uses an external dictionary
#	so multiple records can have a common structure. It also
#	participates in a conntainer hierarchy.
#
#	DataStoreObject is a container of objects that behaves like an array
#	in that it can be indexed by number and itterated over. It also
#	managers a common dictionary for its content and participates
#	in a hierarchy of containers. It also includes database-like
#	access actions.
#
#  WARNINGS
#
#  Warning 1:  When accessing items, key types of integer are always
#	treated as array _indices and all other key types are treated
#	as dictionary keys.  In general, when there is a potential
#	conflict between array and dictiionary behavior, preference
#	is given array behavior.
#
#  Warning 2:  It is extremely bad form to directly access self._data[]
#	or self.dict{}.  The class methods take minimal care to verify
#	that the data structures are in proper form, so any direct
#	access that upsets integrity may have unpredictable results.
#
#  Warning 2B:  This class is intended to be a drop-in replacement for the
#	built-in dictionary and array types.  Any exceptions to this goal
#	should be corrected by
#	fixing the class, not accessing self._data[] and/or self.dict{}.
#
#  Copyright (C) 2001 by Albert B. Margolis - All Rights Reserved
#
#  4/29/2001:  Initial Release.  Clone from ezdict.
#  5/12/2001:  Add DataStoreObject.  Finally getting back to using this.
#		DataStoreObject becomes the ancestor class for Rdbms.
#  5/12/2001:  Move iterator process and FldAsType actions here
#		because they are good general record features.
# 11/21/2001:  Move boolean translation actions to utils.AsBool()
# 12/07/2002:  Add dict parameter to bzreordSet.__init__().
#		Add DataStoreObject.append().  Fix TupleObject.__getitem__()
#		out of range index if data has fewer fields than
#		dictionary.
# 12/18/2002:  Add First()
# 12/23/2002:  Fix bug in __setitem__.  Exception if field IX beyond
#		current end of data.  Add loop to expand self._data
#  3/08/2003:  Fix bug in TupleObject.__getitem__() causing exception
#		if numeric index out of range.  Check for data length
#		and return default value if needed.  Fix bug in
#		TupleObject.__repr__() missing "}" at end of value string.
#		Fix bug in First() returning Next instead of Next()
#  4/05/2003:  Add Dict()
#  6/27/2003:  Add index to DataStoreObject to access records by key value
#		rather than sequence.
#  9/01/2003:  Add Sort() to DataStoreObject
#  6/20/2004:  Modify handling of dictionary to allow richer dictionaries.
#		We only need the name here, but allow the definition to
#		be an array or tuple and take [0] as the name.  Eliminates
#		the need to create a separate dictionary for ezdict.
#		Added for bzCommaDb.py.
#  5/17/2006:  Add support for python iterator protocol and slices
# 10/02/2005:  Add Dup() to TupleObject and DataStoreObject
#  5/04/2014:  Change dict to tdict and its type to tupledict
#			from ezdict where there value was simply the ix.
#			(This has been very stable but there have definately
#			been changes in the last 9 years!)
#
#############################################


#
# This module is essential for site bootstraping so it should have
# the minimal number of dependencies and none outside the development
# directory.
#

from ezcore import ertypes
from ezcore import tupledict
from ezcore import vcomputer
from ezcore import ezdict

from ezcore import utils


def FullyQualifiedName(parmSelf):
    wsFqn = parmSelf._name
    wsObject = parmSelf.parent
    while wsObject:
        wsFqn = wsObject._name + '.' + wsFqn
        wsObject = wsObject.parent
    return wsFqn


def Compare(a, b, parmKeys):
    for wsThisKey in parmKeys:
        wsResult = cmp(a[wsThisKey], b[wsThisKey])
        if wsResult != 0:
            return wsResult
    return 0

#
# Query Support Actions
#


def MakeRpnExpressionForWhereClause(parmWhere):
    # Does not support all operators or deal with errors yet
    # Only supports one level of parens
    wsExpression = []
    wsParensOperator = None
    wsParensClosed = False
    wsClauseCt = 0
    if not (type(parmWhere[0]) in [type([]), type(())]):
        # If there is just one clause, don't require a container.
        # We just make one here.
        parmWhere = [parmWhere]
    for wsThisWhereClause in parmWhere:
        wsClauseCt += 1
        wsThisField1Name = wsThisWhereClause[0]
        wsThisOperator = wsThisWhereClause[1]
        wsThisOperand2 = wsThisWhereClause[2]
        if len(wsThisWhereClause) > 3:
            wsThisConjunction = utils.Upper(wsThisWhereClause[3])
        else:
            wsThisConjunction = 'AND'
        wsExpression.append(
            (vcomputer.OpPushTupleElement, 'R1', wsThisField1Name))
        wsExpression.append((vcomputer.OpPushString, wsThisOperand2))
        if wsThisOperator == '=':
            wsExpression.append(vcomputer.OpCompareEqual)
        if wsClauseCt > 1:
            if wsThisConjunction[0] == "(":
                # This operator will get pushed later
                wsParensOperator = wsThisConjunction[1:]
            else:
                if wsThisConjunction[0] == ")":
                    wsParensClosed = True
                    wsThisConjunction = wsThisConjunction[1:]
                if wsThisConjunction == 'AND':
                    wsExpression.append(vcomputer.OpAnd)
                elif wsThisConjunction == 'OR':
                    wsExpression.append(vcomputer.OpOr)
                if wsParensClosed:
                    if wsParensOperator == 'AND':
                        wsExpression.append(vcomputer.OpAnd)
                    elif wsParensOperator == 'OR':
                        wsExpression.append(vcomputer.OpOr)
                    wsParensOperator = None
                    wsParensClosed = False
    return wsExpression


def MakeLookupQuery(
        parmExeController,
        parmTableReferenceName,
        parmLookupFieldName,
        parmLookupValue,
        MatchEqual=False,
        Debug=0):
    wsDataRoles = parmExeController.GetCodeObject(ertypes.ErDataRolesName)
    wsEncodingTypes = parmExeController.GetCodeObject(
        ertypes.ErEncodingTypesName)
    wsTDict = parmExeController.GetTableObject(
        parmTableReferenceName, IsMddl=False)
    if Debug > 0:
        print('Table: ', parmTableReferenceName)
        print('Key: ', parmLookupFieldName)
    wsTDictElement = wsTDict.GetElement(parmLookupFieldName)
    if wsTDictElement is None:
        return None
    wsLookupTable = parmExeController.db.OpenTable(wsTDict.physicalTableName)
    wsLookupValueCdx = utils.Codex(parmLookupValue)

    if not MatchEqual:
        wsMatchOperator = 'like'
        wsMatchValueSuffix = '%'
    else:
        wsMatchOperator = '='
        wsMatchValueSuffix = ''
    if (wsTDictElement.role in wsDataRoles.PhysicalSet) or (
            wsTDictElement.role == wsDataRoles.UndefinedCode):
        # The test for Undefined is needed for query actions (ops WHERE). Not
        # sure if this is a good or bad solution.
        wsWhere = (wsTDictElement.dbmsFieldName, '=', parmLookupValue)
    elif wsTDictElement.role == wsDataRoles.ConfusionCode:
        if wsTDictElement.confusedIsVirtual:
            pass
            #self.errs.AddUserInfoMessage('Virtual Confusion.')
        wsWhere = []
        for wsThisConfusedElementName in wsTDictElement.confusedElementNameList:
            wsThisConfusedElement = wsTDict[wsThisConfusedElementName]
            if wsThisConfusedElement.role == wsDataRoles.CalculatedCode:
                pass
            else:
                if wsThisConfusedElement.encoding == wsEncodingTypes.CodexCode:
                    wsThisLookupValue = wsLookupValueCdx
                else:
                    wsThisLookupValue = parmLookupValue
                wsWhere.append(
                    (wsThisConfusedElement.dbmsFieldName,
                     wsMatchOperator,
                     wsThisLookupValue +
                     wsMatchValueSuffix,
                     'OR'))
    else:
        parmExeController.errs.AddUserInfoMessage(
            'MakeLookupQuery() unexpected role "%s" for element "%s".' %
            (wsTDictElement.role, parmLookupFieldName))
        return None
    wsLookupTable.Select(parmWhere=wsWhere)
    if Debug > 0:
        print(wsLookupTable.lastQuery)
    return wsLookupTable


def Select(DataStore, ExeController=None, Fields=None, Where=None, Debug=0):
    # DataStore is usually DataStore but can be any iterable that returns
    # a recognizable name-vvalue pair object
    wsResult = DataStoreObject()
    if Where is not None:
        wsExpression = MakeRpnExpressionForWhereClause(Where)
        if Debug > 0:
            print('Select Where Expression: ', repr(wsExpression))
        if ExeController is None:
            try:
                ExeController = DataStore.exeController
            except BaseException:
                ExeController = None
        wsVM = vcomputer.vcomputer(ExeController=ExeController)
    for wsThisTuple in DataStore:
        if Where is not None:
            if not wsVM.RunRPN(wsExpression, {'R1': wsThisTuple}, Debug=Debug):
                continue
        wsResult.AppendData(
            wsThisTuple,
            CopyFieldList=Fields,
            Name=wsThisTuple._name)
    return wsResult

#
# DataTreeBranch
#
# This will probably be a fairly pure virtual class.
#
# It provides standard attributes for a hierarchy of BAF data
# and standardizes the inheritance of those properties when
# creating a sub-branch (child).
#
# self._tdict is a dictionary where the key is the field name
#	and the value is a tupledictElement where _ix
#	if the index (0...) of self._data for that field's value
#
# Part of the reason DataTreeBranch exists is that the root
# of a hierarchy can be either DataStoreObject or TupleObject.
# This common base takes care of inheriting in any pattern without
# duplicate code that might be fragile. Among the downside is that
# some of this data my be irrelevant or redundant in particular
# instances.
#


class DataTreeBranch(object):
    __slots__ = ('exeController', '_debug',
                                  '_defaultValue',
                                  '_defaultValueAssigned',
                                  '_hierarchySeparator',
                                  '_isBequeathTDict',
                                  '_isCaseSensitive',
                                  '_isTDictDynamic',
                                  '_name',
                                  '_owner',
                                  '_parent',
                                  '_path',
                                  '_tdict'
                 )

    def __init__(self,
                 ExeController=None,
                 Data=None,
                 Debug=None,
                 DefaultValue=None,
                 DefaultValueAssigned=None,
                 IsBequeathTDict=False,
                 IsCaseSensitive=None,
                 Name="",
                 HierarchySeparator=None,
                 IsHierarchy=None,
                 Owner=None,
                 Parent=None,
                 IsTDictDynamic=None,
                 TDict=None):
        if Parent is not None:
            # Inherit parent characteristics
            if ExeController is None:
                ExeController = Parent.exeController
            if Debug is None:
                Debug = Parent._debug
            if (DefaultValue is None) and (DefaultValueAssigned is None):
                DefaultValue = Parent._defaultValue
                DefaultValueAssigned = Parent._defaultValueAssigned
            elif DefaultValueAssigned is None:
                # The caller provided a default value but didn't bother to set DefaultValueAssigned.
                # This is common. DefaultValueAssigned is only needed in the ambiguous case
                # case of the default value being None.
                DefaultValueAssigned = True
            if TDict is None:
                if Parent._isBequeathTDict:
                    # Tuples/Records within a data store are almost always identical in structure,
                    # so they inherit. Sub-Tuples within tuples almost always
                    # have unique structures compared to their parent, so they do not
                    # inherit.
                    TDict = Parent._tdict
                else:
                    TDict = Parent._tdict.GetChildTDict(Name)
            if IsCaseSensitive is None:
                IsCaseSensitive = Parent._isCaseSensitive
            if Owner is None:
                Owner = Parent._owner
            if IsTDictDynamic is None:
                IsTDictDynamic = Parent._isTDictDynamic
        #
        # In order for the above inheritance to work, the action parameters must have a default value of None.
        # The following assignments turn them into the real default values in
        # case they haven't been assigned.
        if Debug is None:
            Debug = 0
        if DefaultValueAssigned is None:
            DefaultValueAssigned = False
        if HierarchySeparator is None:
            # If a separator is provided, hierarchy mode is enabled using that separator.
            # Otherwise we consider IsHierarchy and the parent mode.
            if IsHierarchy is None:
                # Nothing was said about hierarchy, so do whatever the parent
                # does
                if Parent is not None:
                    HierarchySeparator = Parent._hierarchySeparator
            elif IsHierarchy:
                # Hierarchy is turned on but no character is specified. If the parent
                # specified a character, use that. Otherwise use the default.
                if Parent is not None:
                    HierarchySeparator = Parent._hierarchySeparator
                if HierarchySeparator is None:
                    # We didn't get a separator from the parent so use the
                    # default.
                    HierarchySeparator = ezdict.HierarchySeparatorCharacter
            else:
                # If IsHierarch is specifically set to no, clear the character.
                # This doesn't really need to be done because we wouldn't get here
                # unless HierarchySeparator was already None. If the calling
                # parameters are inconsistent, a specified HierarchySeparator
                # overrides IsHierarchy.
                HierarchySeparator = None
        if IsTDictDynamic is None:
            # This sets the actual default for top level objects
            if TDict is None:
                IsTDictDynamic = True
            else:
                IsTDictDynamic = False
        if IsCaseSensitive is None:
            # This sets the actual default for top level objects
            IsCaseSensitive = False

        # Most things intialized here need to be copied in Dup() below
        self.exeController = ExeController
        if Debug is None:
            self._debug = 0
        else:
            self._debug = Debug
        self._isBequeathTDict = IsBequeathTDict
        self._isCaseSensitive = IsCaseSensitive
        self._defaultValue = DefaultValue
        self._defaultValueAssigned = DefaultValueAssigned
        self._name = Name
        self._hierarchySeparator = HierarchySeparator
        self._owner = Owner
        self._parent = Parent
        self._AssignPathString()
        self._tdict = tupledict.MakeTDict(TDict, Name=Name)
        if self._tdict is None:
            if self._parent is None:
                self._tdict = tupledict.TupleDict(Name=Name)
            else:
                wsElement = self._parent._tdict.Element(Name)
                if wsElement is None:
                    self._tdict = self._parent._tdict.MakeChildDictionary(
                        Name=Name)
                elif wsElement.physicalType == ertypes.Core_TDictTypeCode:
                    # This seems to be an array item, all use the same
                    # dictionary
                    self._tdict = wsElement.collectionItemTDict
                else:
                    self.exeController.errs.AddDevCriticalMessage(
                        "Inconsistent array element type %s.%s" %
                        (self._name, Name))
        self.SetIsTDictDynamic(IsTDictDynamic)

    def AssignExeController(self, parmExeController):
        self.exeController = parmExeController

    def _AssignPathString(self):
        # This really wants to be multiple inheritance, providing consistent tree implementation
        # to a few different classes whos instances will be peers in the same
        # tree.
        if self._parent is None:
            self._path = self._name
        else:
            if self._parent._parent is None:
                # We probably need a path syntax like UNIX directories with a leading slash if
                # descending from the top of the tree. For now, this cheat solves the problem of
                # having the top node in the path when using path as the index.
                self._path = self._name
            else:
                wsName = self._name
                if wsName is None:
                    wsName = '---'
                self._path = self._parent._path + ezdict.HierarchySeparatorCharacter + wsName

    def MakeInheritedDataStore(
            self,
            Name=None,
            HierarchySeparator=None,
            Parent=None,
            TDict=None):
        if Parent is None:
            # This is the normal case. Parent is a parameter so we can create a semi-disconected
            # object that will later be connected. This is used by the XML loader. It can't just
            # use MakeChildDataStore() because the structure already has a tuple that is to be
            # replaced.
            Parent = self
        if HierarchySeparator is None:
            HierarchySeparator = Parent._hierarchySeparator
        wsInheritedDataStore = DataStoreObject(
            HierarchySeparator=HierarchySeparator,
            IsCaseSensitive=Parent._isCaseSensitive,
            Name=Name,
            Parent=Parent,
            IsTDictDynamic=Parent._isTDictDynamic,
            TDict=TDict
        )
        return wsInheritedDataStore

    def MakeInheritedTuple(
            self,
            Name=None,
            HierarchySeparator=None,
            TDict=None):
        if HierarchySeparator is None:
            HierarchySeparator = self._hierarchySeparator
        wsInheritedTuple = TupleObject(
            HierarchySeparator=HierarchySeparator,
            IsCaseSensitive=self._isCaseSensitive,
            Name=Name,
            Parent=self,
            IsTDictDynamic=self._isTDictDynamic,
            TDict=TDict
        )
        return wsInheritedTuple

    def SetIsTDictDynamic(self, parmIsTDictDynamic=True):
        self._isTDictDynamic = parmIsTDictDynamic

    def SetIsTDictStatic(self, parmTDictDynamic=False):
        self._isTDictDynamic = parmIsTDictDynamic

#
#
#


class DataStoreDuplicateKey(Exception):
    pass


class DataStoreIndex(object):
    __slots__ = ('fieldName', 'IX')

    def __init__(self, parmFieldName, IsCaseSensitive=False):
        self.fieldName = parmFieldName
        self.IX = ezdict.ezdictTuple(IsCaseSensitive=IsCaseSensitive)


class DataStoreIterator(object):
    __slots__ = ('dataStore', 'ix')

    def __init__(self, parmDataStore):
        self.dataStore = parmDataStore
        self.ix = 0

    def __iter__(self):
        return self.DataStoreObject.__iter__()

    def __next__(self):
        if self.ix >= self.dataStore.__len__():
            raise StopIteration
        wsThisIx = self.ix
        self.ix += 1
        return self.dataStore._tuples[wsThisIx]

#
# DataStoreObject is an array of TupleObject objects. It is a container class that is the
# foundation for database classes.
#
# It differs from a standard array in the the following ways
#	- name, owner and parent attributes to support hierarchies
#	- reference properties of TupleObject that are used to support
#		provide consistency among the TupleObjects it contains
#
# DataStoreObject contains many TupleObject fields which are not directly
# used by DataStoreObject but are used to support automatic inheritance
# of properties that are almost always consistent through a data
# structure (like case sensitivity, strict definition of fields, etc.
#
# DataStoreObject does not automatically inherit dict, because in almost
# all cases it has different fields from the parent. TupleObject does
# inherit dict from parent DataStoreObject because this usually is used
# for a collection of identically structured records. TupleObject does
# not inherit from other TupleObject because in almost all cases that
# is for a collection of fields that is different than the parent,
# a single instance of a sub-record, DataStoreObject is used when there
# are multiple instances.
#
# For the first few years of Hobby Engineering, this was the database.
# It included an single key indexing mechanism that was used to access
# part numbers, etc. That went out ouf use with the move to MySql but
# the code remained for a long time. It was finally removed 3/10/13
# with the creation of bzArrayOfCompositions which provided more
# DBMS like features and which was more complicated than desireable
# by attempting to stay consistent with the old index mechanism here.
#
# I just deleted __setitem__() and __getitem__() which were left
# over from the original bzRecord/bzRecordSet implementation. I
# don't think data stores are accessed like an array anywhere
# in the system. If I feel the need to re-eimplment them, they
# should probably be through an explicit call rather than the
# array syntax methods.
#


class DataStoreObject(DataTreeBranch):
    __slots__ = ('_tuples', '_s', 'rdbmsTDict',
                 '_indices',
                 '_lastAppendUdi', '_lastTuple',
                 '_lastErrorMsg', '_lastQuery')

    def __init__(self,
                 ExeController=None,
                 DefaultValue=None,
                 DefaultValueAssigned=None,
                 TDict=None,
                 Debug=None,
                 IsBequeathTDict=True,
                 IsCaseSensitive=None,
                 Name="",
                 HierarchySeparator=None,
                 IsHierarchy=None,
                 Owner=None,
                 Parent=None,
                 IsTDictDynamic=None):

        super(DataStoreObject, self).__init__(
            ExeController=ExeController,
            Debug=Debug,
            DefaultValue=DefaultValue,
            DefaultValueAssigned=DefaultValueAssigned,
            TDict=TDict,
            HierarchySeparator=HierarchySeparator,
            IsHierarchy=IsHierarchy,
            IsBequeathTDict=IsBequeathTDict,
            IsCaseSensitive=IsCaseSensitive,
            Name=Name,
            Owner=Owner,
            Parent=Parent,
            IsTDictDynamic=IsTDictDynamic)

        self.rdbmsTDict = None
        self._tuples = []
        self._indices = None
        self._lastAppendUdi = 0
        self._lastTuple = None
        self._lastErrorMsg = ''
        self._lastQuery = None				# needed so it can look like a DB set

    def __getitem__(self, parmIx):
        return self._tuples[parmIx]

    def DefineIndex(self, parmIndexField):
        if self._indices is None:
            self._indices = ezdict.ezdictTuple(
                IsCaseSensitive=self._isCaseSensitive)
        wsIndex = DataStoreIndex(
            parmIndexField,
            IsCaseSensitive=self._isCaseSensitive)
        self._indices[parmIndexField] = wsIndex

    def __iter__(self):
        return DataStoreIterator(self)

    def __len__(self):
        if self._debug > 0:
            print("DataStoreObjectLen=%d" % (len(self._tuples)))
        return len(self._tuples)

    def __repr__(self):
        return "D Dict: %s :: Data: %s" % (
            repr(self._tdict), repr(self._tuples))

    def GetIndex(self, parmRecordTypeName, parmIndexName):
        wsIndexFqnName = parmRecordTypeName + '.' + parmIndexName
        if self._indices is None:
            self._indices = ezdict.ezdictTuple()
        if wsIndexFqnName not in self._indices:
            self._indices[wsIndexFqnName] = ezdict.ezdictTuple()
        return self._indices[wsIndexFqnName]

    def GetIndexKey(self, parmIndexDef, parmDataSource):
        wsIndexKey = None
        for wsThisFieldName in parmIndexDef.fieldNames:
            wsFieldValue = vcomputer.GetFieldValue(
                parmDataSource, wsThisFieldName, DefaultTDict=self._tdict)
            if wsIndexKey is None:
                wsIndexKey = utils.Str(wsFieldValue)
            else:
                wsIndexKey += '.' + utils.Str(wsFieldValue)
        return wsIndexKey

    def _PostTuple(self, parmTuple):
        # Assume parmTuple is conformant (not sure what that means. same
        # tdict?)
        wsTupleIx = len(self._tuples)
        self._tuples.append(parmTuple)
        self._lastTuple = parmTuple
        try:
            wsTDict = parmTuple._tdict
        except BaseException:
            wsTDict = self._tdict
        if wsTDict is not None:
            if wsTDict.indexDefs is not None:
                if self._indices is None:
                    self._indices = ezdict.ezdictTuple()
                for wsThisIndexDef in list(wsTDict.indexDefs.values()):
                    wsThisIndex = self.GetIndex(
                        wsTDict.__class__.__name__, wsThisIndexDef._name)
                    wsIndexKey = self.GetIndexKey(wsThisIndexDef, parmTuple)
                    if wsThisIndexDef.isUnique:
                        if wsIndexKey in wsThisIndex:
                            raise DataStoreDuplicateKey(
                                "Index: %s, Key: %s" %
                                (wsThisIndexDef._name, repr(wsIndexKey)))
                    wsThisIndex[wsIndexKey] = wsTupleIx
        return parmTuple

    def AppendData(self, Data, Name=None, CopyFieldList=None):
        wsTuple = self.MakeInheritedTuple(Name=Name)
        wsTuple.AppendData(Data, CopyFieldList=CopyFieldList)
        self._PostTuple(wsTuple)
        return wsTuple

    @property
    def lastQuery(self):
        return self._lastQuery

    @lastQuery.setter
    def lastQuery(self, parmValue):
        self._lastQuery = parmValue

    def Lookup(self, parmFieldName, parmFieldValue):
        for wsThisTuple in self._tuples:
            wsFieldValue = vcomputer.GetFieldValue(wsThisTuple, parmFieldName,
                                                   DefaultTDict=self._tdict)
            if wsFieldValue == parmFieldValue:
                return wsThisTuple
        return None

    def LookupWhere(self, parmWhere):
        pass

    def LookupByIndex(self, parmTDict, parmIndexName, parmDataSource):
        wsIndexDef = parmTDict.indexDefs[parmIndexName]
        wsThisIndex = self.GetIndex(
            parmTDict.__class__.__name__, parmIndexName)
        wsIndexKey = self.GetIndexKey(wsIndexDef, parmDataSource)
        if wsIndexKey in wsThisIndex:
            return self._tuples[wsThisIndex[wsIndexKey]]
        else:
            return None

    def Select(self, Fields=None, Where=None, Debug=0):
        Select(self, ExeController=self.exeController,
               Fields=Fields, Where=Where, Debug=Debug)

    # DataStoreObject
    def MakeChildArrayItem(self):
        wsChild = self.MakeInheritedTuple(
            HierarchySeparator=self._hierarchySeparator,
            Name=self._name,
            TDict=self._tdict)
        self._PostTuple(wsChild)
        return wsChild

    def MakeChildTuple(self, Name=None, HierarchySeparator=None, TDict=None):
        wsChild = self.MakeInheritedTuple(
            HierarchySeparator=HierarchySeparator, Name=Name, TDict=TDict)
        self._PostTuple(wsChild)
        return wsChild

    # DataStoreObject
    def ClearAll(self):
        self._tuples = []
        self._tdict = None

    def ClearData(self, Query=''):
        self._tuples = []
        self._lastQuery = Query

    def Dup(self):
        # Dup() creates a new object as a fairly shallow copy
        # Parent is used during __init__ to do most of the copying, then reset.
        wsDup = DataStoreObject(Parent=self)
        wsDup._tdict = self._tdict
        wsDup._tuples = self._tuples
        wsDup.parent = self.parent
        return wsDup

    def items(self):
        # Unlike a python dict, data is stored in the order inserted.
        # This is an intentional behavior and must be preserved.
        wsList = []
        wsCt = 0
        for wsThisItem in self._tuples:
            wsList.append(("IX%d" % wsCt, wsThisItem))
            wsCt += 1
        return wsList

    def values(self):
        # Unlike a python dict, data is stored in the order inserted.
        # This is an intentional behavior and must be preserved.
        wsList = []
        for wsThisItem in self._tuples:
            wsList.append(list(wsThisItem.values()))
        return wsList

    def Sort(self, parmSortField):
        #
        # Assumes all records have same fields
        #
        if isinstance(parmSortField, type([])):
            self._tuples.sort(lambda a, b: Compare(a, b, parmSortField))
        else:
            self._tuples.sort(
                lambda a,
                b: cmp(
                    a[parmSortField],
                    b[parmSortField]))

    # ColumnHeadings()
    # This used to be called Dict()
    # As the dictionary becomes more fully defined, this may change to
    # use a better formatted field than name.
    #
    def ColumnHeadings(self):
        wsDictionary = self._tdict.ElementsByIx()
        wsHeadings = []
        for wsThisElement in wsDictionary:
            wsHeadings.append(wsThisElement._name)
        return wsHeadings

#
# FastTupleObject
#
# This is a variant of TupleObject that always stores data as
# object attributes. This is faster and allows normal looking application
# methods.
#
# This has most of the characteristics of TupleObject except:
#   - Always case senstive
#   - Never strict
#   - This keeps it fast by not getting in the way of normal attribute storage
#   - Some dictionary-like methods missing / misnamed to avoid potential
#	conflics with data: items(), values(), has_key()
#
# Like TupleObject it can be
#   - itterated over values
#   - access properties like a dict obj['name']
#   - supported for import/export via XML, JSON, etc.
#


class FastTupleObject(DataTreeBranch):
    def __init__(self,
                 ExeController=None,
                 Data=None,
                 Debug=None,
                 DefaultValue=None,
                 DefaultValueAssigned=None,
                 TDict=None,
                 IsCaseSensitive=None,
                 Name="",
                 HierarchySeparator=None,
                 IsHierarchy=None,
                 Owner=None,
                 Parent=None,
                 IsTDictDynamic=None):
        DataTreeBranch.__init__(self,
                                   ExeController=ExeController,
                                   Debug=Debug,
                                   DefaultValue=DefaultValue,
                                   DefaultValueAssigned=DefaultValueAssigned,
                                   TDict=TDict,
                                   IsCaseSensitive=IsCaseSensitive,
                                   Name=Name,
                                   HierarchySeparator=HierarchySeparator,
                                   IsHierarchy=IsHierarchy,
                                   Owner=Owner,
                                   Parent=Parent,
                                   IsTDictDynamic=IsTDictDynamic)

    # FastTupleObject
    def __getitem__(self, parmKey):
        object.__getattr__(self, parmKey)

    def _InitDataFields(self):
        for wsThisElement in self._tdict.Elements():
            setattr(self, wsThisElement._name, None)


class DatumWithAttribs(object):
    __slots__ = ('attribs', 'datum')

    def __init__(self, parmDatum, parmAttribs):
        self.attribs = parmAttribs
        self.datum = parmDatum


class TupleObject(DataTreeBranch):
    __slots__ = (
        '_datums',
        '_modifiedDatums',
        '_isTupleModified',
        '_lastElementModified')

    #
    # If provided, Data must be an array or tuple of data content in TDict._ix order.
    # If a tuple, the record is effectively read-only.
    #
    def __init__(self,
                 CopyFieldList=None,
                 Data=None,
                 Debug=None,
                 DefaultValue=None,
                 DefaultValueAssigned=None,
                 ExeController=None,
                 HierarchySeparator=None,
                 Initialize=False,
                 IsCaseSensitive=None,
                 IsHierarchy=None,
                 IsTDictDynamic=None,
                 Name="",
                 Owner=None,
                 Parent=None,
                 TDict=None
                 ):
        DataTreeBranch.__init__(self,
                                   Debug=Debug,
                                   DefaultValue=DefaultValue,
                                   DefaultValueAssigned=DefaultValueAssigned,
                                   ExeController=ExeController,
                                   HierarchySeparator=HierarchySeparator,
                                   IsCaseSensitive=IsCaseSensitive,
                                   IsHierarchy=IsHierarchy,
                                   IsTDictDynamic=IsTDictDynamic,
                                   Name=Name,
                                   Owner=Owner,
                                   Parent=Parent,
                                   TDict=TDict
                                   )
        self._modifiedDatums = []
        self._isTupleModified = False
        self._datums = []
        self._lastElementModified = None
        if Data is not None:
            self.AppendData(Data, CopyFieldList=CopyFieldList)
        if Initialize and (self._tdict is not None):
            self._tdict.InitializeTargetDatums(self)

    # TupleObject
    def AppendData(self, Data, CopyFieldList=None):
        if CopyFieldList is None:
            if type(Data) in [type(()), type([])]:
                # if ordered data without names, assume that it is in correct
                # order for TDict. This happens when processing RDBMS queries
                wsIx = 0
                for wsThisValue in Data:
                    self._StoreByIx(wsIx, wsThisValue)
                    wsIx += 1
            else:
                for wsKey, wsValue in list(Data.items()):
                    self.__setitem__(wsKey, wsValue)
            return self
        for wsKey in CopyFieldList:
            wsValue = Data[wsKey]
            self.__setitem__(wsKey, wsValue)
        return self
        # raise TypeError

    def AppendDatum(self, parmKey, parmValue):
        if parmKey in self:
            raise IndexError("Duplicate datum '%s' with value '%s' in '%s'" % (
                parmKey, parmValue, self._name))
        self.__setitem__(parmKey, parmValue)
        return parmValue

    def GetDatum(self, parmKey, SubstituteValue=None):
        if parmKey not in self:
            return SubstituteValue
        return self.__getitem__(parmKey)

    # TupleObject
    def ClearAll(self):
        self._datums = []
        self._isTupleModified = False
        self._modifiedDatums = []
        if self._tdict is None:
            self._tdict = tupledict.TupleDict(
                IsCaseSensitive=self._isCaseSensitive, Name=self._name)
        else:
            self._tdict.Clear()

    def _ClearData(self):
        self._datums = []
        self._isTupleModified = False
        self._modifiedDatums = []

    def __eq__(self, other):
        ## *** THIS IS HALF CONVERTED FROM __cmp__
        if isinstance(other, type([])):
            return self._datums.__eq__(other)
        elif isinstance(other, type(self)):
            return self._datums.__eq__(other._datums)
        elif (isinstance(parmOther, type({}))) \
                or (isinstance(parmOther, ezdict.EzDict)):
            if len(self._datums) != len(other):
                return False
            for (wsKey, wsDictElement) in list(self._tdict.items()):
                # parmOther can be a TupleObject or a normal {}
                if wsKey not in parmOther:
                    return -1
                wsValue = self._datums[wsDictElement._ix]
                if parmOther[wsKey] != wsValue:
                    return -1
            return 0
        return -1

    def __delitem__(self, parmKey):
        wsElement = self._tdict.Elements(parmKey)
        wsIx = wsElement._ix
        del self._datums[wsIx]
        self._modifiedDatums[wsIx] = False

    def _Dup(self):
        # Dup() creates a new object as a fairly shallow copy
        # Parent is used during __init__ to do most of the copying, then reset.
        wsDup = TupleObject(Parent=self, TDict=self._tdict)
        wsDup._datums = self._datums
        wsDup._parent = self._parent
        return wsDup

    # TupleObject
    # This may be used by other modules for array style access
    def _GetByIx(self, parmIx, Element=None, Name=None, WithAttribs=False):
        if (parmIx < 0) and (Element is not None):
            parmIx = Element._ix
        if parmIx >= 0:
            if parmIx < len(self._modifiedDatums):
                if self._modifiedDatums[parmIx]:
                    if WithAttribs:
                        # If attributes are wanted, just return the stored
                        # object
                        return self._datums[parmIx]
                    else:
                        # if attributes aren't wanted, filter out
                        # DatumWithAttribs layer
                        wsScalar = self._datums[parmIx]
                        if isinstance(wsScalar, DatumWithAttribs):
                            return wsScalar.datum
                        else:
                            return wsScalar
        if Element is None:
            Element = self._tdict.ElementByIx(parmIx)
        if Element is not None:
            if Element._defaultValueAssigned:
                return Element.InitialValue()
        if self._defaultValueAssigned:
            return self._defaultValue
        wsKey = Name
        if (wsKey is None) and (Element is not None):
            wsKey = Element._name
        raise IndexError("Datum '%s' (%d) undefined" % (wsKey, parmIx))

    def __contains__(self, parmKey):
        # True means parmKey is defined AND a value has been assigned for this tuple.
        # This makes it equivalent to dict.has_key() so this is a good
        # substitute.
        if (self._tdict is not None) and parmKey in self._tdict.elements:
            wsIx = self._tdict.elements[parmKey]._ix
            if wsIx < len(self._modifiedDatums):
                if self._modifiedDatums[wsIx]:
                    return True
        return False

    # TupleObject
    def __getitem__(self, parmKey, WithAttribs=False):
        if self._hierarchySeparator is not None:
            wsKeySegments = parmKey.split(self._hierarchySeparator)
            if len(wsKeySegments) > 1:
                wsChild = self
                for wsThisKey in wsKeySegments:
                    wsChildElement = wsChild._tdict.Element(wsThisKey)
                    if wsChildElement is None:
                        raise IndexError(
                            "Datum path `%s` undefined at `%s`." %
                            (parmKey, wsThisKey))
                    wsChild = wsChild._GetByIx(-1,
                                               Element=wsChildElement,
                                               Name=wsThisKey)
                return wsChild

        wsElement = self._tdict.Element(parmKey)
        return self._GetByIx(-1,
                             Element=wsElement,
                             Name=parmKey,
                             WithAttribs=WithAttribs)

    def __len__(self):
        return len(self._datums)

    def __repr__(self):
        wsDictLen = len(self._tdict)
        wsDataLen = len(self._datums)
        wsString = ""
        for (wsKey, wsDictElement) in list(self._tdict.elements.items()):
            if wsDictElement._ix < len(self._datums):
                wsValue = self._datums[wsDictElement._ix]
            else:
                wsValue = self._defaultValue
            if wsString != "":
                wsString += ", "
            wsString += "{" + repr(wsKey) + ": " + repr(wsValue) + "}"
        for wsValue in self._datums[wsDictLen:]:
            if wsString != "":
                wsString += ", "
            wsString += "{?: " + repr(wsValue) + "}"
        return wsString

    # TupleObject
    # This may be used by other modules for array style access
    def _StoreByIx(self, parmIx, parmValue):
        while parmIx >= len(self._datums):
            self._datums.append(None)
            self._modifiedDatums.append(False)
        self._datums[parmIx] = parmValue
        self._lastElementModified = parmValue
        self._modifiedDatums[parmIx] = True

    # TupleObject
    def __setitem__(self, parmKey, parmValue):
        if (self._tdict is not None) and parmKey in self._tdict.elements:
            wsDictionaryElement = self._tdict.elements[parmKey]
        elif not self._isTDictDynamic:
            raise IndexError(
                "Attempt to store dynamic datum %s = %s" %
                (parmKey, repr(parmValue)))
        else:
            if self._tdict is None:
                self._tdict = tupledict.TupleDict(Name=self._name)
            wsDictionaryElement = self._tdict._AddElement(
                parmKey, Sample=parmValue)
        self._StoreByIx(wsDictionaryElement._ix, parmValue)

    def change_key(self, parmOldKey, parmNewKey):
        return self._tdict.change_key(parmOldKey, parmNewKey)

    def IsModified(self, parmKey):
        if (self._tdict is not None) and parmKey in self._tdict.elements:
            wsIx = self._tdict.elements[parmKey]._ix
            if wsIx < len(self._modifiedDatums):
                if self._modifiedDatums[wsIx]:
                    return True
        return False

    # TupleObject
    def keys(self):			# sort keys into data order
        # This behaves like a dict, only stored values are returned
        wsDict = self._tdict.ElementsByIx()
        wsList = []
        for wsElement in wsDict:
            if wsElement._ix >= len(self._datums):
                continue
            if not self._modifiedDatums[wsElement._ix]:
                continue
            wsList.append(wsElement._name)
        return wsList

    def items(self):			# sort dictionary into data order
        # This behaves like a dict, only stored values are returned
        wsDict = self._tdict.ElementsByIx()
        wsList = []
        for wsElement in wsDict:
            if wsElement._ix >= len(self._datums):
                continue
            if not self._modifiedDatums[wsElement._ix]:
                continue
            wsValue = self._datums[wsElement._ix]
            wsList.append((wsElement._name, wsValue))
        return wsList

    def replace(self, parmEntry):
        self._datums = {}
        return self.append(parmEntry)

    def values(self):
        # This behaves like a dict, only stored values are returned
        wsDict = self._tdict.ElementsByIx()
        wsList = []
        for wsElement in wsDict:
            if wsElement._ix >= len(self._datums):
                continue
            if not self._modifiedDatums[wsElement._ix]:
                continue
            wsValue = self._datums[wsElement._ix]
            wsList.append(wsValue)
        return wsList

    # TupleObject
    def MakeChildDataStore(
            self,
            Name=None,
            HierarchySeparator=None,
            TDict=None):
        if Name is None:
            raise IndexError("Name required for DataStoreObject datum.")
        wsChild = self.MakeInheritedDataStore(
            HierarchySeparator=HierarchySeparator, Name=Name, TDict=TDict)
        self.AppendDatum(Name, wsChild)
        return wsChild

    def MakeChildTuple(self, Name=None, HierarchySeparator=None, TDict=None):
        if Name is None:
            raise IndexError("Name required for TupleObject datum.")
        wsChild = self.MakeInheritedTuple(
            HierarchySeparator=HierarchySeparator, Name=Name, TDict=TDict)
        self.AppendDatum(Name, wsChild)
        return wsChild

    def ValuesForKeyList(self, parmKeyList):
        wsList = []
        for wsThisKey in parmKeyList:
            wsList.append(self[wsThisKey])
        return wsList

    def CopyItems(self, parmSource, parmCopyList):
        wsSourceTDict = self.exeController.GetTDictByObject(parmSource)
        for (wsThisTarget, wsThisSourceElementName) in parmCopyList:
            if wsThisSourceElementName[0] == '*':
                if wsThisSourceElementName == '*NowYMDHM':
                    wsValue = utils.NowYMDHM()
                else:
                    raise TypeError(
                        "Invalid special value '%s'" %
                        (wsThisSourceElementName))
            else:
                wsValue = wsSourceTDict.GetTupleDatum(
                    parmSource, wsThisSourceElementName)
            self[wsThisTarget] = wsValue

    def FldAsBool(self, parmKey):
        wsData = self.__getitem__(parmKey)
        wsResult = utils.AsBool(wsData)
        return wsResult

    def FldAsStr(self, parmKey):
        wsData = self.__getitem__(parmKey)
        if isinstance(wsData, type("")):
            return wsData
        else:
            return repr(wsData)


def ModuleTest():

    wsTestTupleDict = tupledict.TupleDict()
    wsElement = wsTestTupleDict.AddScalarElement('IndexFieldInt1')
    wsElement = wsTestTupleDict.AddScalarElement('IndexFieldStr2')
    wsElement.ConfigureAsNotBlank()
    wsElement = wsTestTupleDict.AddScalarElement('dbmsFieldName')
    wsTestTupleDict.DefineIndex(
        ['IndexFieldInt1', 'IndexFieldStr2'], Name='TwoFieldsIx')

    wsTestDataStore = DataStoreObject(TDict=wsTestTupleDict)
    wsTestRecord = TupleObject(TDict=wsTestTupleDict)
    wsTestRecord['IndexFieldInt1'] = 1
    wsTestRecord['IndexFieldStr2'] = "ABC"
    wsTestDataStore.AppendDatum(wsTestRecord)
    wsTestRecord = TupleObject(TDict=wsTestTupleDict)
    wsTestRecord['IndexFieldInt1'] = 3
    wsTestRecord['IndexFieldStr2'] = "GHI"
    wsTestDataStore.AppendDatum(wsTestRecord)
    wsTestRecord = TupleObject(TDict=wsTestTupleDict)
    wsTestRecord['IndexFieldInt1'] = 2
    wsTestRecord['IndexFieldStr2'] = "DEF"
    wsTestDataStore.AppendDatum(wsTestRecord)

    print("*** Test Lookup() ***")
    for wsInt1 in [1, 2, 3]:
        print(repr(wsTestDataStore.Lookup('IndexFieldInt1', wsInt1)))

    print("*** Test LookupByIndex() ***")
    wsKeys = {'IndexFieldInt1': 3, 'IndexFieldStr2': "GHI"}
    print(
        repr(
            wsTestDataStore.LookupByIndex(
                wsTestTupleDict,
                'TwoFieldsIx',
                wsKeys)))

    print("*** Test Select() ***")
    print(repr(Select(wsTestDataStore)))

    print("*** Test Select(Where) ***")
    print(
        repr(
            Select(
                wsTestDataStore, Where=(
                    ('IndexFieldStr2', '=', "ABC"), ('IndexFieldStr2', '=', "GHI", 'OR')))))
