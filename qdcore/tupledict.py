#
# TupleDictionary + bafTupleAssociation
#
# A TupleDictionary describes the contents of a container.
#

import copy
import inspect
import os
import types

from . import ertypes
from . import qddict

from . import commastr
from . import utils

#
# TupleDictionary should probably be descendant from bafDataStoreObject
# instead of QdDict because each entry is a complex element instead
# of a scalar. Making that happen requires more work to avoid circular
# definintions.
#
#
# bafTupleSchema is a lightweight schema used with TupleDictionary
#
# The goal is for it to be used very little.
#
# TupleDictionary is very tactical and should contain all the
# information needed to implement associations.
#
# TupleDictionary and the data it describes are parallel
# in structure and often generated at the same time and
# both deal with the same data.
#
# I find it very easy to get confused between data containers
# and diotionary containers. Be careful!
#
# BAF uses TDict to describe all sorts of data containers
# implemented in different ways. Associated data can be stored
# either relationally or hierarchically and the BAF system
# can automatically move data between different types of
# storage.
#
# Serialized data formats like XML, JSON, etc. are serialize
# a hierarchical structure.
#
# Association Terminology
#
# Primary Participant is the parent in a parent-child relationship.
#
# The data container should have a UDI to uniquely identify the
# particular data. This is most often an autoincrement primary key
# for database records or an address for memory objects.
# The TDict has an RoleType=ertypes.Core_PrimaryParticipantRoleCode
# element representing the association. When data is stored
# hierarchically, this is implemented in the data as a container.
# For data stored relationally, this is not impemented at all.
#
# The associated TDict is identified in element.collectionItemTDict
# in the Core_PrimaryParticipantRoleCode element. There is a
# potentially confusing difference between TDict and data here.
# For data, this is a one-to-many relationship so in a relational
# implementation the parent does not store anything about the
# children. In relational databases all the children have the same
# structure so the TDict relationship is one-to-one (one TDict
# to one TDict) so the parent TDict can hold a pointer to its child TDict.
#
# Secondary Particpant is the child in a parent-child relationship.
#
# When data is stored relationally, the child data must include a
# foreign key which is typically the UDI of the parent data.
# When data is stored hierarchically the foreign key is not needed.
# When serializing relational data, the foreign key of the container
# can be removed to save space and easily replaced when loading
# back into a relational structure.
#
# The TDict association is identifed in _superiorTDict. This is
# essentially the foreign key of the parent.
#
TaElementNamePrefix = "TaE_"
TaAssociationNamePrefix = "TaA_"
TaAssociationNameConnector = "_Of_"
FIELD_ARRAY_CT = "_IX"


def GetAttributeNames(parmObject):
    """Return a list of keys of data attributes of an object, similar to what dict.keys() does."""
    wsDir = []
    wsAttributeNames = dir(parmObject)
    try:
        (wsSource, wsLineNo) = inspect.getsourcelines(parmObject.__class__)
    except BaseException:
        # Get here because parmObject is a built-in
        wsSource = None
        wsLineNo = 0
    wsProperties = []
    if wsSource is not None:
        # This is very fragile. It works for my simple property
        # definitions but is not a broad solution
        for (wsThisLineNo, wsThisLine) in enumerate(wsSource):
            if wsThisLine.find("@property") >= 0:
                wsPropDefLine = wsSource[wsThisLineNo + 1]
                wsDefPos = wsPropDefLine.find("def")
                wsParmPos = wsPropDefLine.find("(")
                wsPropName = wsPropDefLine[wsDefPos + 4 : wsParmPos]
                wsProperties.append(wsPropName)
    for wsThisAttribName in wsAttributeNames:
        if wsThisAttribName[:2] == "__":
            continue
        wsThisAttrib = getattr(parmObject, wsThisAttribName)
        wsThisValue = repr(wsThisAttrib)
        if isinstance(wsThisAttrib, types.MethodType):
            continue
        if isinstance(wsThisAttrib, types.BuiltinMethodType):
            continue
        if wsThisAttribName in wsProperties:
            # this can happen due to @property (see above)
            continue
        wsDir.append(wsThisAttribName)
    return wsDir


def MakeClassTDict_For_bafTupleAssociation(ExeController=None, InstanceClassName=None):
    wsTDict = TupleDictionary(
        InstanceClassName=InstanceClassName,
        PrimaryDataPhysicalType=ertypes.Core_ObjectTypeCode,
        ExeController=ExeController,
    )

    wsTDict.AddScalarElementBoolean("isHierarchical")
    wsTDict.AddScalarElement("_name")
    wsTDict.AddScalarElementReference(
        "primaryParticipantTDict", AssociatedClassRefname="TupleDictionary"
    )
    wsTDict.AddScalarElementReference(
        "primaryParticipantElement", AssociatedClassRefname="TupleDictionaryElement"
    )
    wsTDict.AddScalarElementReference(
        "secondaryParticipantTDict", AssociatedClassRefname="TupleDictionary"
    )
    wsTDict.CompleteDictionary()
    return wsTDict


class bafTupleAssociation(object):
    __slots__ = (
        "isHierarchical",
        "_name",
        "primaryParticipantTDict",
        "primaryParticipantElement",
        "secondaryParticipantTDict",
    )

    def __init__(self, Name=None, PrimaryParticipant=None, SecondaryParticipant=None):
        self.isHierarchical = True  # This is implemntation detail
        self._name = Name
        self.primaryParticipantTDict = PrimaryParticipant
        self.primaryParticipantElement = None  # If hierarchical, the container
        self.secondaryParticipantTDict = SecondaryParticipant

    def __repr__(self):
        wsResult = "ASSOC: %s %s->%s" % (
            self._name,
            self.primaryParticipantTDict._name,
            self.secondaryParticipantTDict._name,
        )
        return wsResult


def MakeClassTDict_For_bafTupleSchema(ExeController=None, InstanceClassName=None):
    wsTDict = TupleDictionary(
        InstanceClassName=InstanceClassName,
        PrimaryDataPhysicalType=ertypes.Core_ObjectTypeCode,
        ExeController=ExeController,
    )

    wsAssociationTDict = MakeClassTDict_For_bafTupleAssociation(
        ExeController=ExeController
    )
    wsDictionaryTDict = MakeClassTDict_For_TupleDictionary(ExeController=ExeController)
    wsTDict.AddContainerElement(
        "associations",
        RoleType=ertypes.Core_PrimaryParticipantRoleCode,
        PhysicalType=ertypes.Core_MapBafTypeCode,
        CollectionItemTDict=wsAssociationTDict,
    )
    wsTDict.AddContainerElement(
        "dictionaries",
        RoleType=ertypes.Core_PrimaryParticipantRoleCode,
        PhysicalType=ertypes.Core_MapBafTypeCode,
        CollectionItemTDict=wsDictionaryTDict,
    )
    wsTDict.AddScalarElement("_name")
    wsTDict.CompleteDictionary()
    return wsTDict


def MakeTDictForObject(parmObject, ExeController=None, Name=None, Register=False):
    if Register:
        # if registering, only go thorugh this process once
        wsTDict = ExeController.GetTDictByObject(parmContainer)
        if wsTdict is not None:
            return wsTDict
    wsAttributeNames = GetAttributeNames(parmObject)
    wsTDict = TupleDictionary(ExeController=ExeController, Name=Name)
    for wsThisAttribName in wsAttributeNames:
        wsValue = getattr(parmObject, wsThisAttribName, None)
        wsElement = wsTDict._AddElement(wsThisAttribName, Sample=wsValue)
    return wsTDict


def MakeTDictFromCaptionCsvString(parmCsvStr):
    wsCaptionList = commastr.CommaStrToList(parmCsvStr)
    wsTDict = TupleDictionary()
    for wsThisCaption in wsCaptionList:
        wsThisName = utils.StrToInnercap(wsThisCaption)
        print(wsThisName, wsThisCaption)
        if wsTDict.HasElement(wsThisName):
            print("Duplicate element name %s" % wsThisName)
            return None
        wsElement = wsTDict.AddScalarElement(wsThisName)
        wsElement.caption = wsThisCaption
    return wsTDict


def MakeTDict(parmTDict, Name=None):
    if parmTDict is None:
        return None
    if isinstance(parmTDict, TupleDict):
        # Assume its a proper dictionary
        return parmTDict
    try:
        wsItems = list(parmTDict.items())
    except BaseException:
        wsItems = None
    if wsItems is not None:
        parmTDict = wsItems
    if isinstance(parmTDict, list) or isinstance(parmTDict, tuple):
        wsDict = TupleDict(Name=Name)
        for wsElement in parmTDict:
            if isinstance(wsElement, list) or isinstance(wsElement, tuple):
                wsFieldName = wsElement[0]
                wsValue = wsElement[1]
            else:
                wsFieldName = wsElement
                wsValue = None
            wsDict.AddScalarElement(wsFieldName, Sample=wsValue)
        return wsDict
    return None  # This is an unknown type


class bafTupleSchema(object):
    __slots__ = ("associations", "dictionaries", "_name")

    def __init__(self, Name=None):
        self._name = Name
        self.dictionaries = qddict.QdDict(Name="dictionaries")
        self.associations = qddict.QdDict(Name="associations")

    def __repr__(self):
        return "SCHEMA: %s %s" % (repr(self.associations), repr(self.dictionaries))

    def MakeAssociation(
        self, parmPrimaryParticipant, parmSecondaryParticipant, Name=None
    ):
        if Name is None:
            wsName = (
                parmSecondaryParticipant._name
                + TaAssociationNameConnector
                + parmPrimaryParticipant._name
            )
        else:
            wsName = Name
        wsAssociation = bafTupleAssociation(
            Name=wsName,
            PrimaryParticipant=parmPrimaryParticipant,
            SecondaryParticipant=parmSecondaryParticipant,
        )
        self.associations.AppendDatum(wsName, wsAssociation)
        return wsAssociation

    def CompareSchema(self, parmSubjectSchema, CompareNamesOnly=False):
        def ErrorMessage(parmMessage):
            if parmSubjectTDict is None:
                wsPhysicalTableName = ""
            else:
                wsPhysicalTableName = parmSubjectTDict._name
            self.exeController.errs.AddDevCriticalMessage(
                "TupleDictionary.CompareTDict() %s: %s" % (self._name, parmMessage)
            )


#
# Query Support Actions
#
# TupleDictionary / TupleDictionaryElement
#
# This is the dictionary for bafTupleObject objects.
#
# The dictionary includes internal validation and record set validation rules for the data.
#
# Internal validation rules are are validated by looking at that tuple
# 	and not any other information. One edge case is code validation.
# 	That is generally modeled as an external dependency (association / relation)
# 	but often implemented as a short code list. A code list can be included
# 	as part of the internal validation rules.
#
# Record set rules are validated by considering other tuples in the same record set.
# 	This primarily identifies unique _indices.
#
# There are at least 3 mode of dictionary usage:
#
# 1. Dictionary Mode: Only name and _ix are populated. This mode is basically the
# 	same as a native Python dictionary object, except for the capability to be
# 	case insensitive.
#
# 2. DTD Control Mode: Dictionary data format attibutes are populated and
# 	used to validate data before it is stored in the record. This might be used
# 	for conventional, structured data processing applications.
#
# 3. DTD Disovery Mode: Dictionary data format attibutes are populated as data
# 	is stored so we end up with both the data and a corresponding dictionary.
# 	This mode might be used when loading an interchange XML, JSON or CSV file.
# 	The dictionary can be used for ad-hoc processing or used to generate
# 	initial models for MVC development.
#


def MakeClassTDict_For_TupleDictionary(ExeController=None, InstanceClassName=None):
    wsTDict = TupleDictionary(
        InstanceClassName=InstanceClassName,
        PrimaryDataPhysicalType=ertypes.Core_ObjectTypeCode,
        ExeController=ExeController,
    )

    wsElementTDict = MakeClassTDict_For_TupleDictionaryElement(
        ExeController=ExeController
    )
    wsTDict.AddScalarElement("associations")
    wsTDict.AddScalarElementNumber("binderUdi")
    wsTDict.AddScalarElementReference(
        "exeController", PhysicalType=ertypes.Core_ProcessPtrTypeCode
    )
    wsTDict.AddScalarElement("choosingFields")
    wsTDict.AddScalarElementReference("createTimestamp")
    wsTDict.AddScalarElement("primaryDataPhysicalType")
    wsTDict.AddScalarElement("instanceClassName")
    wsTDict.AddScalarElement("instancePhysicalType")
    wsTDict.AddScalarElement("dbmsFieldNames")
    wsTDict.AddContainerElement(
        "dbmsTableIndices",
        RoleType=ertypes.Core_PrimaryParticipantRoleCode,
        PhysicalType=ertypes.Core_ListTypeCode,
        CollectionItemPhysicalType=ertypes.Core_StringTypeCode,
    )
    wsTDict.AddScalarElement("debug")
    wsTDict.AddScalarElementReference(
        "dictionaryElementClass",
        PhysicalType=ertypes.Core_ClassPtrTypeCode,
        InstanceOfClassRefname="TupleDictionaryElement",
    )
    wsTDict.AddContainerElement(
        "elements",
        RoleType=ertypes.Core_PrimaryParticipantRoleCode,
        PhysicalType=ertypes.Core_MapBafTypeCode,
        CollectionItemTDict=wsElementTDict,
    )
    wsTDict.AddScalarElement("filesDbExtension")
    wsTDict.AddScalarElement("filesDbPath")
    wsTDict.AddScalarElementNumber("formCt")
    wsTDict.AddScalarElementBoolean("isStaticCollection")
    wsTDict.AddScalarElementBoolean("hasSubmit")
    wsTDict.AddScalarElement("indexDefs")
    wsTDict.AddScalarElementBoolean("isMddl")
    wsTDict.AddScalarElementNumber("ixCtr")
    wsTDict.AddScalarElement("_name")
    wsTDict.AddScalarElement("_path")
    wsTDict.AddScalarElement("physicalTableName")
    wsTDict.AddScalarElementBoolean("recordLocatorFieldsDone")
    wsTDict.AddScalarElementNumber("recordLocatorFieldCt")
    wsTDict.AddScalarElementNumber("recordDisplayRowCt")
    wsTDict.AddScalarElementNumber("recordDisplayCurColCt")
    wsTDict.AddScalarElementNumber("recordDisplayMaxColCt")
    wsTDict.AddContainerElement(
        "recordHeadings",
        RoleType=ertypes.Core_PrimaryParticipantRoleCode,
        PhysicalType=ertypes.Core_ListTypeCode,
        CollectionItemPhysicalType=ertypes.Core_StringTypeCode,
    )
    wsTDict.AddScalarElement("recordHtmlTable")
    wsTDict.AddScalarElementReference("rsf")
    wsTDict.AddScalarElementReference("schema")
    wsTDict.AddScalarElement("singularName")
    wsTDict.AddScalarElementReference("_superiorTDict")
    wsTDict.AddScalarElement("tabSelectionFieldReferenceName")
    wsTDict.AddScalarElement("tabSelectionValue")
    wsTDict.AddScalarElement("tabBinderReferenceName")
    wsTDict.AddScalarElement("tabTabReferenceNameList")
    wsTDict.AddScalarElementReference("udi", BlankAllowed=True)
    wsTDict.AddScalarElementReference("uii")
    wsTDict.AddScalarElementReference("updateTimestamp")

    wsTDict.CompleteDictionary()
    return wsTDict


class bafTupleIndexDefinition(object):
    __slots__ = ("fieldNames", "isUnique", "_name")

    def __init__(self, parmName, parmFieldNames, IsUnique=True):
        self.fieldNames = parmFieldNames
        self.isUnique = IsUnique
        self._name = parmName


class TupleDictionaryIterator(object):
    __slots__ = ("dictionary", "elementNames", "ix")

    def __init__(self, parmDictionary):
        self.dictionary = parmDictionary
        self.elementNames = self.dictionary.ElementNames()
        self.ix = 0

    def __iter__(self):
        return self.bafTupleDicitonaryIterator.__iter__()

    def __next__(self):
        if self.ix >= len(self.elementNames):
            raise StopIteration
        wsThisIx = self.ix
        self.ix += 1
        return self.dictionary.Element(self.elementNames[wsThisIx])


class TupleDict(object):
    __slots__ = (
        "associations",
        "binderUdi",
        "createTimestamp",
        "exeController",
        "primaryDataPhysicalType",
        "choosingFields",
        "dbmsFieldNames",
        "dbmsTableIndices",
        "debug",
        "dictionaryElementClass",
        "elements",
        "filesDbExtension",
        "filesDbPath",
        "formCt",
        "isStaticCollection",
        "hasSubmit",
        "indexDefs",
        "instanceClassName",
        "instancePhysicalType",
        "isMddl",
        "ixCtr",
        "_name",
        "_path",
        "physicalTableName",
        "recordLocatorFieldsDone",
        "recordLocatorFieldCt",
        "recordDisplayRowCt",
        "recordDisplayCurColCt",
        "recordDisplayMaxColCt",
        "recordHeadings",
        "recordHtmlTable",
        "rsf",
        "schema",
        "singularName",
        "_superiorTDict",
        "tabSelectionFieldReferenceName",
        "tabSelectionValue",
        "tabBinderReferenceName",
        "tabTabReferenceNameList",
        "udi",
        "uii",
        "updateTimestamp",
    )

    def __init__(
        self,
        ExeController=None,
        Name=None,
        PrimaryDataPhysicalType=ertypes.Core_MapBafTypeCode,
        InstanceClassName=None,
        InstancePhysicalType=ertypes.Core_MapBafTypeCode,
        FormCt=None,
        IsStaticCollection=True,
        BinderUdi=0,
        Schema=None,
    ):
        self.associations = qddict.QdDict()
        self.binderUdi = BinderUdi  # Source definition (documentation only)
        self.exeController = ExeController
        # ordered list of record choosing fields
        self.choosingFields = qddict.QdDict()
        # identifies how to access values / container type
        self.primaryDataPhysicalType = PrimaryDataPhysicalType
        self.instanceClassName = InstanceClassName  # identifies class to create for new
        self.instancePhysicalType = (
            InstancePhysicalType  # identifies how to access data
        )
        self.dbmsFieldNames = qddict.QdDict()
        self.dbmsTableIndices = []  # list of bzDbmsTableIndex objects
        self.debug = 0
        self.dictionaryElementClass = TupleDictionaryElement
        self.elements = None  # initialized by Clear()
        self.filesDbExtension = ""
        self.filesDbPath = ""
        self.formCt = FormCt
        self.isStaticCollection = IsStaticCollection
        self.isMddl = False
        self._name = Name
        if self._name is None:
            self._name = InstanceClassName
        self.physicalTableName = ""
        self._path = ""
        self.rsf = None  # Record Status Field
        self.schema = Schema
        if self._name is None:
            self.singularName = None
        else:
            if (self._name[-2:] == "es") and (len(self._name) > 2):
                self.singularName = self._name[:-2]
            elif (self._name[-1:] == "s") and (len(self._name) > 1):
                self.singularName = self._name[:-1]
            else:
                self.singularName = self._name
        self._superiorTDict = None  # if a child dictionary
        self.tabSelectionFieldReferenceName = ""
        self.tabSelectionValue = ""
        self.tabBinderReferenceName = None
        self.tabTabReferenceNameList = None
        self.udi = None  # Unique Data Identifier
        self.uii = None  # Unique Information Identifier
        self.createTimestamp = None
        self.updateTimestamp = None
        #
        # display information -- mainly used in other modules
        #
        # recordLocatorFieldCt, recordDisplayRowCt and related fields are used when defining a DTD for display output and there are
        # more fields than will fit as separate columns. The locator fields are critical fields that help the reader locate
        # the record they are interested in. These must be the first columns defined and these output columns will not be
        # re-used. Subsequent columns will wrap with multiple data fieds (data columns) per display column.
        #
        self.hasSubmit = False
        self.recordLocatorFieldsDone = False
        self.recordLocatorFieldCt = 0
        self.recordDisplayRowCt = 1
        self.recordDisplayCurColCt = 0
        self.recordDisplayMaxColCt = 0
        self.recordHeadings = []
        self.recordHtmlTable = None
        self.Clear()

    def __iter__(self):
        return TupleDictionaryIterator(self)

    def __repr__(self):
        return "TDICT " + repr(self.elements)

    def MakeChildDictionary(
        self, Name=None, PhysicalType=ertypes.Core_MapBafTypeCode, FormCt=None
    ):
        # uses __class__ so it creates proper object for descendent classes
        #
        # This properly starts a TDict for data that will be stored hierarchically.
        # This both creates the TDict and the association.
        # For relational designs, you would just create a TDict and separately
        # define the association. That also allows more flexibility in naming
        # which is require when you have multiple associations between the same
        # binders (tables). This should work directly with any properly formatted
        # XML file (as well as JSON).
        #
        # Changes to construction of wsChildElement probably requires parallel
        # changes to GetChildTDict().
        #
        if self.schema is None:
            self.schema = bafTupleSchema()
            self.schema.dictionaries.AppendDatum(self._path, self)
        wsChildTDict = self.__class__(
            ExeController=self.exeController,
            Name=Name,
            Schema=self.schema,
            FormCt=FormCt,
        )
        wsChildTDict.ConfigureAsChildDictionary(self)
        wsAssociation = self.schema.MakeAssociation(self, wsChildTDict)
        self.schema.dictionaries.AppendDatum(wsChildTDict._path, wsChildTDict)
        wsChildElement = self.AddContainerElement(
            Name,
            RoleType=ertypes.Core_PrimaryParticipantRoleCode,
            PhysicalType=PhysicalType,
            CollectionItemTDict=wsChildTDict,
            FormCt=FormCt,
        )
        wsAssociation.isHierarchical = True
        wsAssociation.primaryParticipantElement = wsChildElement
        return wsChildTDict

    def StoreElement(self, parmElement):
        self.elements.AppendDatum(parmElement._name, parmElement)
        return parmElement

    def _AddElement(
        self,
        parmElementPath,
        Caption=None,
        StaticCollectionTDict=None,
        CollectionItemPhysicalType=None,
        CollectionItemTDict=None,
        DisplayOrder=None,
        Encoding=ertypes.Encoding_Ascii,
        FormCt=None,
        IsCaseSensitive=False,
        IsLocatorField=False,
        IsProcessElement=False,
        MinLength=None,
        MaxLength=None,
        BlankAllowed=True,
        PhysicalType=None,
        Prompt=None,
        RoleType=None,
        Sample=None,
        SchemaFieldUdi=0,
        SchemaFieldRoleSourceUdi=0,
    ):

        if isinstance(parmElementPath, type([])):
            if len(parmElementPath) == 1:
                wsElementName = parmElementPath[0]
            else:
                wsContainer = self[parmElementPath[0]]
                wsElement = wsContainer._AddElement(
                    parmElementPath[1:],
                    Caption=Caption,
                    StaticCollectionTDict=StaticCollectionTDict,
                    CollectionItemPhsicalType=CollectionItemPhysicalType,
                    CollectionItemTDict=CollectionItemTDict,
                    DisplayOrder=DisplayOrder,
                    Encoding=Encoding,
                    FormCt=FormCt,
                    IsCaseSensitive=IsCaseSensitive,
                    IsLocatorField=IsLocatorField,
                    IsProcessElement=IsProcessElement,
                    MinLength=MinLength,
                    MaxLength=MaxLength,
                    BlankAllowed=BlankAllowed,
                    PhysicalType=PhysicalType,
                    Prompt=Prompt,
                    RoleType=RoleType,
                    SchemaFieldUdi=SchemaFieldUdi,
                    SchemaFieldRoleSourceUdi=SchemaFieldRoleSourceUdi,
                )
                return wsElement
        else:
            if isinstance(parmElementPath, str):
                wsElementName = parmElementPath
            else:
                raise Exception(
                    "Element name ''%s' is not a string." % (repr(parmElementPath))
                )
        #
        # Figure out the type and creation parameters that may be overwritten
        #
        if Sample is not None:
            # if Sample is provided, this overrides PhysicalType because that is probably
            # the default. Providing both Sample and PhysicalType is ambiguous.
            wsSampleType = ertypes.ClassifyPhysicalType(Sample)
            if wsSampleType is not None:
                PhysicalType = wsSampleType
        if PhysicalType is None:
            PhysicalType = ertypes.Core_NoTypeCode
        if RoleType is None:
            RoleType = ertypes.Core_DataRoleCode
        wsAllowedValues = None
        wsMinLength = MinLength
        wsMaxLength = MaxLength
        if PhysicalType == ertypes.Core_BooleanTypeCode:
            wsAllowedValues = [True, False]
        elif PhysicalType == ertypes.Core_DateTypeCode:
            wsMinLength = 8
            wsMaxLength = 8
        elif PhysicalType == ertypes.Core_TimestampTypeCode:
            wsMinLength = 14
            wsMaxLength = 14

        #
        # Now create and configure the element
        #
        # ??? SetLength() ???
        #
        wsElement = self.dictionaryElementClass(
            Name=wsElementName,
            ParentTDict=self,
            Caption=Caption,
            StaticCollectionTDict=StaticCollectionTDict,
            BlankAllowed=BlankAllowed,
            CollectionItemPhysicalType=CollectionItemPhysicalType,
            CollectionItemTDict=CollectionItemTDict,
            DisplayOrder=DisplayOrder,
            Encoding=Encoding,
            FormCt=FormCt,
            IsCaseSensitive=IsCaseSensitive,
            IsProcessElement=IsProcessElement,
            Ix=self.ixCtr,
            MinLength=wsMinLength,
            MaxLength=wsMaxLength,
            PhysicalType=PhysicalType,
            RoleType=RoleType,
        )
        self.ixCtr += 1
        self.StoreElement(wsElement)
        #
        if wsAllowedValues is not None:
            wsElement.SetAllowedValues(wsAllowedValues, UpperCase=True)
        if IsLocatorField:
            # if self.recordLocatorFieldsDone:
            #  self.exeController.errs.AddDevCriticalMessage('Key Field added after regular field')
            self.recordLocatorFieldCt += 1
        else:
            self.recordLocatorFieldsDone = True
        self.recordDisplayCurColCt += 1
        if self.recordDisplayMaxColCt < self.recordDisplayCurColCt:
            self.recordDisplayMaxColCt = self.recordDisplayCurColCt
        if self.recordDisplayRowCt == 1:
            self.recordHeadings.append(wsElement._name)
        if Prompt:
            self.prompt = Prompt
        wsElement.isIdentifier = IsLocatorField
        wsElement.displayRow = self.recordDisplayRowCt
        wsElement.displayColumn = self.recordDisplayCurColCt
        wsElement.displayLength = wsElement.maxLength

        return wsElement

    def AsPlythonClass(self):
        wsClass = type(self._name, (), {"__slots__": self.ElementNames})

    def Captions(self):
        # This is the best source for a CSV heading line
        wsCaptions = []
        for wsThis in self.ElementsByIx():
            wsCaptions.append(wsThis.caption)
        return wsCaptions

    def Clear(self):
        self.elements = qddict.QdDict(Name=self._name)
        self.indexDefs = None
        self.ixCtr = 0

    def CompleteDictionary(self):
        # Look at CompleteTableDefinition() whihc may or may not be functinal now
        # this does any needed validation / clean-up after all elements are added but before the
        # dictionary is used.
        #
        def PostUniqueElement(parmAttr, parmElement):
            wsPtr = getattr(self, parmAttr)
            if wsPtr is not None:
                self.exeController.errs.AddDevCriticalMessage(
                    "Duplicate %s definition @ %s.%s"
                    % (parmAttr, self._name, wsThisElement._name)
                )
            setattr(self, parmAttr, parmElement)

        #
        self.udi = None
        self.uii = None
        self.createTimestamp = None
        self.updateTimestamp = None
        for wsThisElement in self.Elements():
            if wsThisElement.roleType == ertypes.Core_CreateTimestampRoleCode:
                PostUniqueElement("createTimestamp", wsThisElement)
            elif wsThisElement.roleType == ertypes.Core_UdiRoleCode:
                PostUniqueElement("udi", wsThisElement)
            elif wsThisElement.roleType == ertypes.Core_UiiRoleCode:
                PostUniqueElement("uii", wsThisElement)
            elif wsThisElement.roleType == ertypes.Core_UpdateTimestampRoleCode:
                PostUniqueElement("updateTimestamp", wsThisElement)

    def ConfigureAsChildDictionary(self, parmDictionary):
        self._superiorTDict = parmDictionary
        if self._superiorTDict._superiorTDict is None:
            self._path = self._name
        else:
            self._path = (
                self._superiorTDict._path
                + qddict.HierarchySeparatorCharacter
                + self._name
            )

    def DefineIndex(self, parmIndexFields, Name=None, IsUnique=True):
        # parmIndexFields is an array of field names. Each name must be defined for this
        # tuple. The combined values must be unique within the record set.
        if self.indexDefs is None:
            self.indexDefs = qddict.QdDict()
        if Name is None:
            # Default index name is field name(s) with dot separators
            wsIndexName = ""
            for wsThisFieldName in parmIndexFields:
                if wsIndexName != "":
                    wsIndexName += "."
                wsIndexName += wsThisFieldName
        else:
            wsIndexName = Name
        wsIndexDefinition = bafTupleIndexDefinition(
            wsIndexName, parmIndexFields, IsUnique=IsUnique
        )
        self.indexDefs[wsIndexName] = wsIndexDefinition

    def ElementNamesByIx(self):
        wsNames = []
        wsElements = self.ElementsByIx()
        for wsThisElement in wsElements:
            wsNames.append(wsThisElement._name)
        return wsNames

    def Elements(self):
        # values() gets all elements when filtering or sorting is not needed.
        # using Elements() makes it easier to search for all dictionary
        # iterations.
        return list(self.elements.values())

    def ElementNames(self):
        wsElementNames = sorted(list(self.elements.keys()))
        return wsElementNames

    def ElementsByDataEntryOrder(self):
        wsElements = []
        for wsThisElement in list(self.elements._data.values()):
            wsElements.append(wsThisElement[1])
        # This might need a sort, but I don't know yet
        return wsElements

    def ElementsByIx(self):
        wsElements = []
        for wsThisElement in list(self.elements._data.values()):
            # Filter for dictionary elements. The only expected exception
            # would be a child dictionary.
            if isinstance(wsThisElement[1], TupleDictionaryElement):
                if wsThisElement[1].isVirtual:
                    # virutal elements don't have an _ix
                    continue
                wsElements.append(wsThisElement[1])
        wsElements.sort(lambda a, b: cmp(a._ix, b._ix))
        return wsElements

    def ElementsByName(self):
        # This uses the "hidden" key so so sorting is case
        # sensitive or not depending on isCaseSensitive.
        # The returned list includes both virtual and physical elements and
        # child dictionaries.
        wsElementNames = sorted(list(self.elements._data.keys()))
        wsElements = []
        for wsThisElementName in wsElementNames:
            wsElements.append(self.elements._data[wsThisElementName][1])
        return wsElements

    def Element(self, parmElementName):
        if parmElementName in self.elements:
            return self.elements[parmElementName]
        return None

    def ElementByIx(self, parmIx):
        for wsThisElement in list(self.elements.values()):
            if wsThisElement._ix == parmIx:
                return wsThisElement
        return None

    def HasElement(self, parmElementName):
        wsElement = self.Element(parmElementName)
        if wsElement is None:
            return False
        else:
            return True

    def GetChildTDict(self, parmElementName):
        wsElement = self.Element(parmElementName)
        if wsElement is None:
            return None
        if wsElement.physicalType != ertypes.Core_TDictTypeCode:
            return None
        if wsElement.roleType != ertypes.Core_PrimaryParticipantRoleCode:
            return None
        return wsElement.collectionItemTDict

    def __len__(self):
        return len(self.elements)

    # TupleDictionary
    @property
    def positional_parameters(self):
        wsElements = []
        for wsThisElement in list(self.elements.values()):
            if wsThisElement.isPositionalParameter:
                wsElements.append(wsThisElement)
        wsElements.sort(key=lambda a: a._ix)
        return wsElements

    def cli_to_function_parms(self, parms):
        # parms is typically sys.argv[1:]
        # a list of tokenized parameters. sys.argv[0] is typically the program name
        # and not needed. If wanted, there is no reason that it can't be used by
        # defining a positional parameter for it.
        args = []
        kwargs = {}
        positional_parms = self.positional_parameters
        for ix, this in enumerate(parms):
            if ix < len(positional_parms):
                args.append(parms[ix])
        return (args, kwargs)

    def CompareObjects(
        self,
        parmData1,
        parmData2,
        ExeController=None,
        Instance1PhysicalType=None,
        Instance2PhysicalType=None,
    ):
        if ExeController is not None:
            # This is just a convenient way to set exeController in case it wasn't set before.
            # We need to accesss the environment in order to validate the data.
            self.exeController = ExeController
        try:
            wsRecord1Name = parmData1._name
        except BaseException:
            wsRecord1Name = None
        if wsRecord1Name is None:
            wsRecord1Name = "Record1"
        try:
            wsRecord2Name = parmData2._name
        except BaseException:
            wsRecord2Name = None
        if wsRecord2Name is None:
            wsRecord2Name = "Record2"

        for wsThisElement in list(self.elements.values()):
            (wsDatum1Specified, wsDatum1) = wsThisElement.GetDatumAndState(
                parmData1, InstancePhysicalType=Instance1PhysicalType
            )
            (wsDatum2Specified, wsDatum2) = wsThisElement.GetDatumAndState(
                parmData2, InstancePhysicalType=Instance2PhysicalType
            )
            if not wsDatum1Specified:
                if not wsDatum2Specified:
                    continue  # missing from both -- not a mis-match
                else:
                    self.exeController.errs.AddUserCriticalMessage(
                        "Field %s missing from %s. %s value is '%s'."
                        % (wsThisElement._name, wsRecord1Name, wsRecord2Name, wsDatum2)
                    )
            if not wsDatum2Specified:
                self.exeController.errs.AddUserCriticalMessage(
                    "Field %s missing from %s. %s value is '%s'."
                    % (wsThisElement._name, wsRecord2Name, wsRecord1Name, wsDatum1)
                )
            wsMatch = True
            if wsThisElement.physicalType in ertypes.Core_PointerTypeCodes:
                if wsDatum1 is not wsDatum2:
                    wsMatch = False
            else:
                if wsDatum1 != wsDatum2:
                    wsMatch = False
            if not wsMatch:
                self.exeController.errs.AddUserCriticalMessage(
                    "Field %s mismatch. %s value is '%s'. %s value is '%s'."
                    % (
                        wsThisElement._name,
                        wsRecord1Name,
                        wsDatum1,
                        wsRecord2Name,
                        wsDatum2,
                    )
                )

    def ValidateObject(self, parmData, ExeController=None, InstancePhysicalType=None):
        if ExeController is not None:
            # This is just a convenient way to st exeController in case it wasn't set before.
            # We need to accesss the environment in order to validate the data.
            self.exeController = ExeController
        # This may be reduntent with ValidateTuple -- replace later
        wsAssociatedRecords = qddict.QdDict()

        def GetAssociatedRecord(parmElement):
            # This can be accessees the record associated with parmElement.
            # It doesn't reference the value of the parmElement data field unless this is the Core_UdiMirrorRoleCode.
            # The record can be accessed as an RDBMS select or a pointer
            # reference.
            if parmElement.associationParticipantElement is None:
                self.exeController.errs.AddDevCriticalMessage(
                    "No association participant element for %s" % (parmElement._name)
                )
                return None
            wsAssociationName = parmElement.associationParticipantElement._name
            if wsAssociationName in wsAssociatedRecords:
                return wsAssociatedRecords[wsAssociationName]
            wsForeignKeyElement = (
                parmElement.associationParticipantElement.associationParticipationElement
            )
            print("DDD", wsForeignKeyElement._name, parmData)
            wsForeignKeyValue = wsForeignKeyElement.GetDatum(parmData)
            if wsForeignKeyElement.physicalType in ertypes.Core_PointerTypeCodes:
                # This is a pointer
                wsAssociatedRecords[wsAssociationName] = wsForeignKeyValue
                return wsForeignKeyValue
            # Otherwise do an RDBMS lookup
            wsAssociatedTableRefname = (
                parmElement.associationParticipantElement.associatedTableRefname
            )
            wsTable = self.exeController.OpenDbTable(wsAssociatedTableRefname)
            if wsTable is None:
                self.exeController.errs.AddDevCriticalMessage(
                    "Unable to open table '%s' for association %s (%s: %s) for element  %s"
                    % (
                        wsAssociatedTableRefname,
                        wsAssociationName,
                        wsForeignKeyElement.physicalType,
                        wsForeignKeyElement._name,
                        parmElement._name,
                    )
                )
            wsAssociatedFieldName = wsForeignKeyElement.associatedElementName
            print(
                "FFF",
                wsAssociatedTableRefname,
                wsAssociatedFieldName,
                wsForeignKeyValue,
            )
            wsRecord = wsTable.LookupDict(wsAssociatedFieldName, wsForeignKeyValue)
            wsAssociatedRecords[wsAssociationName] = wsRecord
            return wsRecord

        #

        def Print(**args):
            # This localizes changse if I need to log instead of print
            print(args)

        #
        wsResult = True
        for wsThisElement in list(self.elements.values()):
            if wsThisElement.roleType == ertypes.Core_PrimaryParticipantRoleCode:
                pass
            elif wsThisElement.roleType == ertypes.Core_SecondaryParticipantRoleCode:
                pass
            elif wsThisElement.roleType == ertypes.Core_UdiRoleCode:
                # maybe need to check for autoincrement and if insert or update
                pass
            elif wsThisElement.roleType == ertypes.Core_MirrorUdiRoleCode:
                # Check the value of the existing foreign key. This will identify type errors.
                # It will also generate an error if it is blank and tat isn't
                # allowed.
                (wsDatumSpecified, wsDatum) = wsThisElement.GetDatumAndState(
                    parmData, InstancePhysicalType=InstancePhysicalType
                )
                (wsResult, wsValidatedValue) = wsThisElement.ValidateDatum(
                    wsDatumSpecified, wsDatum
                )
                if wsResult:
                    wsThisElement.PutDatum(parmData, wsValidatedValue)
                else:
                    wsResult = False
                if wsResult and (wsValidatedValue is not None):
                    wsRecord = GetAssociatedRecord(wsThisElement)
                    if wsRecord is None:
                        wsForeignKeyValue = wsThisElement.GetDatum(
                            parmData, InstancePhysicalType=InstancePhysicalType
                        )
                        self.exeController.errs.AddUserCriticalMessage(
                            "Invalid Mirror UDI Role element %s value '%s'."
                            % (wsThisElement._name, wsForeignKeyValue)
                        )
            elif wsThisElement.roleType == ertypes.Core_MirrorRoleCode:
                wsRecord = GetAssociatedRecord(wsThisElement)
                if wsRecord is not None:
                    # ?? else default ??
                    wsMirrorValue = wsRecord[wsThisElement.associatedElementName]
                    wsThisElement.PutDatum(parmData, wsMirrorValue)
            else:
                (wsDatumSpecified, wsDatum) = wsThisElement.GetDatumAndState(
                    parmData, InstancePhysicalType=InstancePhysicalType
                )
                (wsResult, wsValidatedValue) = wsThisElement.ValidateDatum(
                    wsDatumSpecified, wsDatum
                )
                if wsResult:
                    wsThisElement.PutDatum(parmData, wsValidatedValue)
                else:
                    wsResult = False
        return wsResult

    #
    # This copies from a flat data source (originally the fields from an HTML form).
    # Source field naming has to be consistent with bzContent form generation.
    # The copy is controlled by the dictionary so the application doesn't see any unexpected
    # fields sent by a malevalent remote source.
    #
    # If the sender and receiver dictionaries are out of sync, this might result in
    # valid data being abandoned. If that is an issue, some other approach to data
    # safety is required.
    #
    # If moving to django, this is accomplished with the inline formset factory
    #
    def SafeCopy(
        self,
        parmDataStore,
        parmSource1,
        Source2=None,
        Prefix=None,
        Ix=None,
        ExeController=None,
    ):
        from . import bafDataStore

        for wsThisElement in list(self.elements.values()):
            if Prefix is None:
                wsSourceFieldName = wsThisElement._name
            else:
                wsSourceFieldName = "%s_%s_%s" % (
                    Prefix,
                    utils.Str(Ix),
                    wsThisElement._name,
                )
            if wsThisElement.physicalType == ertypes.Core_ListBafTypeCode:
                wsArray = bafDataStore.bafDataStoreObject(
                    Name=wsThisElement._name, TDict=wsThisElement.collectionItemTDict
                )
                parmDataStore[wsThisElement._name] = wsArray
                wsArrayLenFieldName = wsSourceFieldName + FIELD_ARRAY_CT
                if wsArrayLenFieldName in parmSource1:
                    wsArrayLen = utils.Int(parmSource1[wsArrayLenFieldName])
                else:
                    wsArrayLen = 0
                for wsIx in range(0, wsArrayLen):
                    wsTuple = wsArray.MakeChildTuple()
                    wsThisElement.collectionItemTDict.SafeCopy(
                        wsTuple, parmSource1, Prefix=wsThisElement._name, Ix=wsIx
                    )
            else:
                wsDatumSpecified = False
                if wsSourceFieldName in parmSource1:
                    wsValue = parmSource1[wsSourceFieldName]
                    wsDatumSpecified = True
                elif (Source2 is not None) and wsSourceFieldName in Source2:
                    wsValue = Source2[wsSourceFieldName]
                    wsDatumSpecified = True
                if wsDatumSpecified:
                    parmDataStore[wsThisElement._name] = wsValue

    def ValidateTuple(self, parmData, ExeController=None, RoundExtraDigits=False):
        if ExeController is not None:
            # This is just a convenient way to set exeController in case it wasn't set before.
            # We need to accesss the environment in order to validate the data.
            self.exeController = ExeController
        wsResult = True
        for wsThisElement in list(self.elements.values()):
            (wsDatumSpecified, wsDatum) = wsThisElement.GetDatumAndState(parmData)
            (wsResult, wsValidatedValue) = wsThisElement.ValidateDatum(
                wsDatumSpecified, wsDatum, RoundExtraDigits=RoundExtraDigits
            )
            if wsResult:
                wsThisElement.PutDatum(parmData, wsValidatedValue)
            else:
                wsResult = False
        return wsResult

    def GetTupleDatum(self, parmSource, parmElementName):
        wsElement = self.Element(parmElementName)
        return wsElement.GetDatum(parmSource)

    #
    # The following methods are the main way applications should add elements to a TDict
    #
    # The first group are for the most commomn data dictionaries. Following that are specific
    # methods for pararameter definintion dictionaries.
    #
    def AddUdiElement(
        self,
        parmElementPath="Udi",
        PhysicalType=ertypes.Core_IntegerTypeCode,
        IsAutoIncrement=True,
    ):
        wsUdiElement = self._AddElement(
            parmElementPath,
            PhysicalType=PhysicalType,
            RoleType=ertypes.Core_UdiRoleCode,
        )
        wsUdiElement.ConfigureAsUdiRole(IsAutoIncrement=IsAutoIncrement)
        return wsUdiElement

    def AddUiiElement(
        self,
        parmElementPath="Name",
        PhysicalType=ertypes.Core_StringTypeCode,
        MaxLength=32,
    ):
        wsUiiElement = self._AddElement(
            parmElementPath, PhysicalType=PhysicalType, MinLength=1, MaxLength=MaxLength
        )
        wsUiiElement.ConfigureAsUiiRole()
        return wsUiiElement

    def AddPrimaryParticipant(
        self,
        parmElementPath,
        ParticipationElementName=None,
        ParticipationElementPhysicalType=None,
        ParticipationElementiRoleType=None,
    ):
        wsParticipantElement = self._AddElement(
            parmElementPath,
            PhysicalType=ertypes.Core_NoTypeCode,
            RoleType=ertypes.Core_PrimaryParticipantRoleType,
        )
        if ParticipatiionElementName is not None:
            wsParticipationElement = self._AddElement(
                parmElementPath,
                PhysicalType=ParticipationElementPhysicalType,
                RoleType=ParticipationElementRoleType,
            )
            wsParticipationElement.associtaionParticipantElement = wsParticipantElement
            wsParticipantElement.associationParticipationElement = (
                wsParticipationElement
            )
        return wsParticipantElement

    def AddSecondaryParticipant(
        self,
        parmElementPath,
        AssociatedClassRefname=None,
        AssociatedElementName=None,
        AssociatedTableRefname=None,
        ForeignKeyElementName=None,
        ForeignKeyPhysicalType=None,
    ):
        wsParticipantElement = self._AddElement(
            parmElementPath,
            PhysicalType=ertypes.Core_NoTypeCode,
            RoleType=ertypes.Core_SecondaryParticipantRoleCode,
        )
        #
        # AssociatedTableRefname identifies the table where associated record is stored.
        # That leads us to an Associated Class. AssociatedClassRefname directly to the
        # class of the associated record but doesn't tell us where it is located.
        # Only one of these should be specified. If both are proveided, they should be
        # consistent.
        #
        # In the future I will add memory data stores to the DBMS info structure.
        # Then we will be able to use the same mechanism to identiffy both
        # where and what for both external data and memory data.
        #
        wsParticipantElement.associatedClassRefname = AssociatedClassRefname
        wsParticipantElement.associatedTableRefname = AssociatedTableRefname
        if ForeignKeyElementName is not None:
            wsForeignKeyElement = self._AddElement(
                ForeignKeyElementName,
                PhysicalType=ForeignKeyPhysicalType,
                RoleType=ertypes.Core_MirrorUdiRoleCode,
            )
            wsForeignKeyElement.associationParticipantElement = wsParticipantElement
            if AssociatedElementName is None:
                # Most of the time the mirror field name is the same as the
                # source field name
                wsForeignKeyElement.associatedElementName = wsForeignKeyElement._name
            else:
                wsForeignKeyElement.associatedElementName = AssociatedElementName
            wsParticipantElement.associationParticipationElement = wsForeignKeyElement
        return wsParticipantElement

    def AddScalarElement(
        self,
        parmElementPath,
        BlankAllowed=True,
        Encoding=ertypes.Encoding_Ascii,
        IsCaseSensitive=False,
        MinLength=None,
        MaxLength=None,
        PhysicalType=ertypes.Core_StringTypeCode,
        RoleType=None,
        Sample=None,
        SchemaFieldUdi=0,
        SchemaFieldRoleSourceUdi=0,
    ):
        if PhysicalType not in ertypes.Core_ScalarTypeCodes:
            self.exeController.errs.AddDevCriticalMessage(
                "AddScalarElement(): Invalid type '%s' for element %s"
                % (PhysicalType, parmElementPath)
            )
            return None
        wsDataElement = self._AddElement(
            parmElementPath,
            BlankAllowed=BlankAllowed,
            Encoding=Encoding,
            IsCaseSensitive=IsCaseSensitive,
            MinLength=MinLength,
            MaxLength=MaxLength,
            PhysicalType=PhysicalType,
            RoleType=RoleType,
            Sample=Sample,
            SchemaFieldUdi=SchemaFieldUdi,
            SchemaFieldRoleSourceUdi=SchemaFieldRoleSourceUdi,
        )
        if RoleType is None:
            wsDataElement.ConfigureAsDataRole()
        return wsDataElement

    def AddScalarElementsFromList(
        self,
        parmElementList,
        BlankAllowed=True,
        Encoding=ertypes.Encoding_Ascii,
        MinLength=None,
        MaxLength=None,
        PhysicalType=ertypes.Core_StringTypeCode,
    ):
        for wsThis in parmElementList:
            wsDataElement = self._AddElement(
                wsThis,
                BlankAllowed=BlankAllowed,
                Encoding=Encoding,
                MinLength=MinLength,
                MaxLength=MaxLength,
                PhysicalType=PhysicalType,
            )
            wsDataElement.ConfigureAsDataRole()
        return wsDataElement

    def AddScalarElementDate(self, parmElementPath):
        wsDataElement = self._AddElement(
            parmElementPath, PhysicalType=ertypes.Core_DateTypeCode
        )
        wsDataElement.ConfigureAsDataRole()
        return wsDataElement

    def AddScalarElementMirror(
        self,
        parmElementPath,
        AssociatedElementName=None,
        BlankAllowed=True,
        Encoding=ertypes.Encoding_Ascii,
        MinLength=None,
        MaxLength=None,
        ParticipantElement=None,
        PhysicalType=ertypes.Core_StringTypeCode,
        SchemaFieldUdi=0,
        SchemaFieldRoleSourceUdi=0,
    ):
        if PhysicalType not in ertypes.Core_ScalarTypeCodes:
            self.exeController.errs.AddDevCriticalMessage(
                "AddScalarElement(): Invalid type '%s' for element %s"
                % (PhysicalType, parmElementPath)
            )
            return None
        wsDataElement = self._AddElement(
            parmElementPath,
            BlankAllowed=BlankAllowed,
            Encoding=Encoding,
            MinLength=MinLength,
            MaxLength=MaxLength,
            PhysicalType=PhysicalType,
            RoleType=ertypes.Core_MirrorRoleCode,
            SchemaFieldUdi=SchemaFieldUdi,
            SchemaFieldRoleSourceUdi=SchemaFieldRoleSourceUdi,
        )
        wsDataElement.associationParticipantElement = ParticipantElement
        if AssociatedElementName is None:
            # Most of the time the mirror field name is the same as the source
            # field name
            wsDataElement.associatedElementName = wsDataElement._name
        else:
            wsDataElement.associatedElementName = AssociatedElementName
        return wsDataElement

    def AddScalarElementMoney(self, parmElementPath):
        wsDataElement = self._AddElement(
            parmElementPath, PhysicalType=ertypes.Core_IntegerTypeCode
        )
        wsDataElement.impliedDecimals = 2
        wsDataElement.unitsOfMeasure = "USD"
        wsDataElement.ConfigureAsDataRole()
        return wsDataElement

    def AddScalarElementNumber(self, parmElementPath, ImpliedDecimals=0):
        wsDataElement = self._AddElement(
            parmElementPath, PhysicalType=ertypes.Core_IntegerTypeCode
        )
        wsDataElement.impliedDecimals = ImpliedDecimals
        wsDataElement.ConfigureAsDataRole()
        return wsDataElement

    def AddScalarElementBoolean(
        self,
        parmElementPath,
        Caption=None,
        DisplayOrder=None,
        FormCt=None,
        RoleType=None,
    ):
        wsDataElement = self._AddElement(
            parmElementPath,
            PhysicalType=ertypes.Core_BooleanTypeCode,
            Caption=Caption,
            DisplayOrder=DisplayOrder,
            FormCt=FormCt,
            RoleType=RoleType,
        )
        wsDataElement.ConfigureAsDataRole(RoleType=RoleType)
        return wsDataElement

    def AddScalarElementReference(
        self,
        parmElementPath,
        AssociatedClassRefname=None,
        AssociatedTableRefname=None,
        BlankAllowed=True,
        InstanceOfClassRefname=None,
        IsProcessElement=False,
        PhysicalType=ertypes.Core_DataPtrTypeCode,
    ):
        # This implements an MDDL association secondary participation.
        # This is the child of a parent-child relationship.
        # This is a shortcut, creating a participation element without a participant element.
        # See AddSecondaryParticipant() for other notes
        wsDataElement = self._AddElement(
            parmElementPath,
            BlankAllowed=BlankAllowed,
            IsProcessElement=IsProcessElement,
            PhysicalType=PhysicalType,
            RoleType=ertypes.Core_MirrorUdiRoleCode,
        )
        wsDataElement.associationParticipantElement = wsDataElement
        wsDataElement.associationParticipationElement = wsDataElement
        wsDataElement.associatedClassRefname = AssociatedClassRefname
        wsDataElement.associatedTableRefname = AssociatedTableRefname
        wsDataElement.instanceOfClassRefname = InstanceOfClassRefname
        return wsDataElement

    def AddScalarElementVirtual(
        self, parmElementPath, parmRpn, PhysicalType=ertypes.Core_StringTypeCode
    ):
        wsThisElement = self._AddElement(parmElementPath, PhysicalType=PhysicalType)
        wsThisElement.ConfigureCalculator(parmRpn)
        return wsThisElement

    #
    # Containers are an ugly subject. My BAF Programming Philosophy paper attempts to define it.
    # This can be either one-dimensional, a map or a record, or two-dimensional, an array or table of records/tuples.
    #
    def AddContainerElement(
        self,
        parmElementPath,
        RoleType=ertypes.Core_PrimaryParticipantRoleCode,
        PhysicalType=ertypes.Core_MapBafTypeCode,
        StaticCollectionTDict=None,
        CollectionItemPhysicalType=None,
        CollectionItemTDict=None,
        FormCt=None,
        IsProcessElement=False,
        SchemaFieldUdi=0,
        SchemaFieldRoleSourceUdi=0,
    ):
        if PhysicalType not in ertypes.Core_ContainerTypeCodes:
            self.exeController.errs.AddDevCriticalMessage(
                "AddContainerElement(): Invalid type '%s' for element %s"
                % (PhysicalType, parmElementPath)
            )
            return None
        wsContainerElement = self._AddElement(
            parmElementPath,
            StaticCollectionTDict=StaticCollectionTDict,
            CollectionItemPhysicalType=CollectionItemPhysicalType,
            CollectionItemTDict=CollectionItemTDict,
            FormCt=FormCt,
            IsProcessElement=IsProcessElement,
            PhysicalType=PhysicalType,
            RoleType=RoleType,
            SchemaFieldUdi=SchemaFieldUdi,
            SchemaFieldRoleSourceUdi=SchemaFieldRoleSourceUdi,
        )
        # wsCollectionElement.ConfigureAsDataRole() should we call appropriate
        # ConfigureAsXxxx ????
        return wsContainerElement

    def AddContainerElementList(self, parmElementPath):
        wsContainerElement = self._AddElement(
            parmElementPath, ertypes.Core_ListTypeCode
        )
        return wsContainerElement

    def AddElementConfusion(self, parmElementPath, parmConfusedElementNameList):
        wsPhysicalType = None
        wsMinLen = 0
        wsMaxLen = 0
        wsIsVirtual = False
        for wsThisElementName in parmConfusedElementNameList:
            if wsThisElementName in self:
                wsElement = self[wsThisElementName]
                if wsElement.roleType in wsDataRoles.VirtualSet:
                    wsIsVirtual = True
                if wsPhysicalType is None:
                    wsPhysicalType = wsElement.physicalType
                    wsMinLen = wsElement.minLength
                    wsMaxLen = wsElement.maxLength
                else:
                    if wsElement.physicalType != wsPhysicalType:
                        # Coerce differing types to string. The query language will do the best it can.
                        # Maybe there should be a warning, but its hard to say.
                        wsPhysicalType = ertypes.Core_StringTypeCode
                    if wsElement.minLength < wsMinLen:
                        wsMinLen = wsElement.minLength
                    if wsElement.maxLength > wsMaxLen:
                        wsMaxLen = wsElement.maxLength
            else:
                self.exeController.errs.AddDevCriticalMessage(
                    "Invalid confused element name %s for confusion %s"
                    % (wsThisElementName, parmElementPath)
                )
                return None
        wsConfusion = self._AddElement(
            parmElementPath,
            PhysicalType=wsPhysicalType,
            MinLen=wsMinLen,
            MaxLen=wsMaxLen,
        )
        wsConfusion.ConfigureAsConfusion(parmConfusedElementNameList, wsIsVirtual)
        return wsConfusion

    #
    # Add elements for parameter dictionaries
    #

    def DefineKeywordParameter(self, parmKeyword, Prompt=None, Hint=None):
        wsElement = self._AddElement(parmKeyword, ertypes.Core_BooleanTypeCode)
        if Prompt:
            wsElement.prompt = Prompt
        if Hint:
            wsElement.hint = Hint
        return wsElement

    def define_positional_parameter(
        self,
        parmKeyword,
        PhysicalType=None,
        UpperCase=False,
        BlankAllowed=False,
        IsIdentifier=False,
        Hint=None,
    ):
        wsElement = self._AddElement(parmKeyword, PhysicalType=PhysicalType)
        wsElement.hint = Hint
        wsElement.isIdentifier = IsIdentifier
        wsElement.isBlankAllowed = BlankAllowed
        wsElement.isPositionalParameter = True
        wsElement.isUpperCaseOnly = UpperCase
        return wsElement

    def DefineValueParameter(
        self,
        parmKeyword,
        Hint=None,
        BlankAllowed=True,
        IsIdentifier=False,
        PhysicalType=None,
        Encoding=ertypes.Encoding_Ascii,
        FormCt=None,
        MinLength=None,
        MaxLength=None,
        Prompt=None,
        UpperCase=False,
    ):
        wsElement = self._AddElement(
            parmKeyword,
            PhysicalType=PhysicalType,
            Encoding=Encoding,
            FormCt=FormCt,
            MinLength=MinLength,
            MaxLength=MaxLength,
        )
        wsElement.isUpperCaseOnly = UpperCase
        wsElement.isValueParameter = True
        if Prompt:
            wsElement.prompt = Prompt
        if Hint:
            wsElement.hint = Hint
        wsElement.isBlankAllowed = BlankAllowed
        wsElement.isIdentifier = IsIdentifier
        return wsElement

    #
    #
    #

    def AddChoosingField(self, parmField):
        # Nice and simple. No need to check for duplicates, qddict maintains order.
        # Duplicates happen because we add uii, udi, unique identifiers and then all fields.
        # First insertions put important felds first.
        # This method exists to keep this service centralized in case it needs to be
        # made more complicatedc later.
        if parmField is None:
            return
        self.choosingFields[parmField._name] = parmField

    def AddTableIndex(self, parmElementPath, parmFields, parmIsUnique):
        wsTableIndex = bzDbmsTableIndex(parmElementPath, parmFields, parmIsUnique)
        self.dbmsTableIndices.append(wsTableIndex)
        return wsTableIndex

    def ScalarElements(self):
        wsItems = []
        for wsThisItem in list(self.elements.values()):
            if wsThisItem.physicalType not in ertypes.Core_ScalarTypeCodes:
                continue
            wsItems.append(wsThisItem)
        return wsItems

    def ConfigureAsMddl(self):
        self.isMddl = True

    def ConfigureAsTab(self, parmBinder, parmSelectionElementName, parmSelectionValue):
        if parmSelectionElementName not in parmBinder:
            self.exeController.errs.AddDevCriticalMessage(
                "TupleDictionary.ConfigureAsTab() %s: Element %s not in binder %s"
                % (self._name, parmSelectionElementName, parmBinder._name)
            )
        self.tabSelectionFieldReferenceName = parmSelectionElementName
        self.tabSelectionValue = parmSelectionValue
        self.tabBinderReferenceName = parmBinder._name
        self.physicalTableName = parmBinder.physicalTableName
        if parmBinder.tabTabReferenceNameList is None:
            parmBinder.tabTabReferenceNameList = []
        parmBinder.tabTabReferenceNameList.append(self._name)

    def CompareTDict(self, parmSubjectTDict, CompareNamesOnly=False):
        def ErrorMessage(parmMessage):
            if parmSubjectTDict is None:
                wsPhysicalTableName = ""
            else:
                wsPhysicalTableName = parmSubjectTDict._name
            self.exeController.errs.AddDevCriticalMessage(
                "TupleDictionary.CompareTDict() %s: %s" % (self._name, parmMessage)
            )

        def Compare(parmFieldName):
            wsMyFieldValue = getattr(wsMyElement, parmFieldName)
            wsPhysicalFieldValue = getattr(wsThisSubjectElement, parmFieldName)
            if wsMyFieldValue != wsPhysicalFieldValue:
                ErrorMessage(
                    "{Element}.{Field} '{SubjectVal}' s/b  '{MyVal}'.".format(
                        Element=wsMyElement._name,
                        Field=parmFieldName,
                        MyVal=wsMyFieldValue,
                        SubjectVal=wsPhysicalFieldValue,
                    )
                )

        #
        if parmSubjectTDict is None:
            ErrorMessage("Subject TDict not defined.")
            return None
        for wsThisSubjectElement in parmSubjectTDict.Elements():
            wsMyElement = self.Element(wsThisSubjectElement._name)
            if wsMyElement is None:
                ErrorMessage(
                    "Subject field %s not in this TDict" % (wsThisSubjectElement._name)
                )
            else:
                if CompareNamesOnly:
                    continue
                Compare("physicalType")
                Compare("maxLength")
        for wsMyElement in self.Elements():
            wsSubjectElement = parmSubjectTDict.Element(wsMyElement._name)
            if wsSubjectElement is None:
                ErrorMessage("My element %s not in Subject TDict" % (wsMyElement._name))

    def CopyElement(
        self,
        SourceElement=None,
        SourceTDict=None,
        ElementName=None,
        NewElementName=None,
        NewDbmsFieldName=None,
    ):
        if SourceElement is None:
            SourceElement = SourceTDict.Element(ElementName)
        if NewElementName:
            wsNewElementName = NewElementName
        else:
            wsNewElementName = SourceElement._name
        if NewDbmsFieldName:
            wsNewDbmsFieldName = NewDbmsFieldName
        else:
            wsNewDbmsFieldName = SourceElement.dbmsFieldName
        if wsNewElementName in self:
            if self.exeController is None:
                raise IndexError
            else:
                self.exeController.errs.AddDevCriticalMessage(
                    "TupleDictionary.CopyElement() adding duplicate '%s' to '%s'"
                    % (wsNewElementName, self._name)
                )
        # This had ancient code starting with copy.copy(SourceElement) for a shallow
        # copy followed by a bunch of fixups.
        # The following is better but maybe should copy more attributes.
        # The ultimate solution should be fairly automatic, conttrolled by a well
        # formed TupleDictionary.
        wsNewElement = self._AddElement(
            wsNewElementName, PhysicalType=SourceElement.physicalType
        )
        wsNewElement.dbmsFieldName = wsNewDbmsFieldName
        return wsNewElement

    def DefinePhysicalTableName(self, parmPhysicalTableName):
        # print "^^ ", self._name, parmPhysicalTableName
        self.physicalTableName = parmPhysicalTableName

    def CompleteTableDefinition(self, DevelopmentMode=False):
        # ** Look at CompleteDictionary() ** only one may be needed / working ??
        # This should be called before the set is used, but since its not enforced,
        # you can't completely count on this.
        if self.exeController is None:
            return
        wsAssociationTypeCodes = self.exeController.GetCodeObject(
            ertypes.TaAssociationTypesName
        )
        wsDataRoleCodes = self.exeController.GetCodeObject(ertypes.ErDataRolesName)
        wsDataTypeCodes = self.exeController.GetCodeObject(
            ertypes.ErPhysicalDataTypesName
        )
        if self.uii is None:
            for wsThisElement in self.Elements():
                if wsThisElement.roleType == ertypes.Core_DataRoleCode:
                    if wsThisElement.isUnique:
                        wsThisElement.ConfigureAsUiiRole()
                        break
        if self.tabBinderReferenceName is not None:
            if self.schema is None:
                # We can't validate if we don't have an order defining the overall schema.
                # This should probably be an error.
                pass
            else:
                wsBinder = self.schema.tabs[self.tabBinderReferenceName]
                self.physicalTableName = wsBinder.physicalTableName
                if not (self._name in wsBinder.tabTabReferenceNameList):
                    wsBinder.tabTabReferenceNameList.append(self._name)
        if not self.physicalTableName:
            self.physicalTableName = self._name
        #
        # Build Ordered List of Record Choosing Fields.
        #
        self.AddChoosingField(self.uii)
        self.AddChoosingField(self.udi)
        for wsThisElement in self.Elements():
            if wsThisElement.isUnique:
                # Get these at the top of the list
                self.AddChoosingField(wsThisElement)
        for wsThisElement in self.ScalarElements():
            self.AddChoosingField(wsThisElement)
        #
        # Build Ordered List of Associations.
        # These are only associations where this table is secondary.
        # The names key in self.associations is the secondary field name, not the association name.
        # self.associations is a qddict, so the sorted insertion order is accessed when
        # stepping though the dictionary.
        #
        wsIndirectAssociations = []
        for wsThisElement in list(self.elements.values()):
            if wsThisElement.roleType == wsDataRoleCodes.SecondaryParticipantCode:
                if wsThisElement.associationType == wsAssociationTypeCodes.PathCode:
                    wsIndirectAssociations.append(wsThisElement)
        wsIndirectAssociations.sort(key=lambda assoc: -assoc.associationPathStep)
        for wsThisAssociation in wsIndirectAssociations:
            self.associations[wsThisAssociation._name] = wsThisAssociation
        #
        # Go through all fields again, taking care of various clean-up triggers.
        #
        for wsThisElement in list(self.elements.values()):
            if wsThisElement.roleType == wsDataRoleCodes.SecondaryParticipantCode:
                # This will re-write the indirect entries placed above, but not
                # re-order them.
                self.associations[wsThisElement._name] = wsThisElement
            self.dbmsFieldNames[wsThisElement.dbmsFieldName] = wsThisElement
            #
            if not DevelopmentMode:
                continue
            #
            # The following code should already be reflected in production mode.
            # Skipping them saves a few CPU cycles including the need to fill put the schema.
            #
            wsThisElement.associationMirrorUdiElementName = self.FixElementName(
                wsThisElement.associationMirrorUdiElementName
            )
            if wsThisElement.associationMirrorUdiElementName != "":
                self.FixMirrorElement(
                    wsThisElement.associationMirrorUdiElementName,
                    ertypes.Core_MirrorUdiRoleCode,
                    wsThisElement,
                )
            wsThisElement.associationMirrorUiiElementName = self.FixElementName(
                wsThisElement.associationMirrorUiiElementName
            )
            if wsThisElement.associationMirrorUiiElementName != "":
                self.FixMirrorElement(
                    wsThisElement.associationMirrorUiiElementName,
                    ertypes.Core_MirrorUiiRoleCode,
                    wsThisElement,
                )

    def FixElementName(self, parmElementName):
        # Make sure name is a string and case senstive spelling is correct
        wsElementName = utils.Str(parmElementName)
        if wsElementName != "":
            if wsElementName in self:
                wsElementName = self[wsElementName]._name
        return wsElementName

    def FixMirrorElement(self, parmElementName, parmRole, parmParticipantElement):
        # This probably fails. I just changed to associatedTab from name, but I'm not sure what
        # to do with Binder reference. Need to finish definition of binders /
        # tabs / tabs
        wsAssociatedTab = self.schema.tabs[parmParticipantElement.associatedTab]
        wsAssociatedBinder = self.schema.GetBinderForTab(wsAssociatedTab)
        if parmRole == ertypes.Core_MirrorUdiRoleCode:
            if wsAssociatedBinder.udi is None:
                self.exeController.errs.AddUserCriticalMessage(
                    "No UDI assigned for tab %s @ %s.%s"
                    % (
                        parmParticipantElement.associatedTab._name,
                        self._name,
                        parmElementName,
                    )
                )
                return None
            else:
                wsMirroredElementName = wsAssociatedBinder.udi._name
        elif parmRole == ertypes.Core_MirrorUiiRoleCode:
            if wsAssociatedBinder.uii is None:
                self.exeController.errs.AddUserCriticalMessage(
                    "No UII assigned for tab %s @ %s.%s"
                    % (
                        parmParticipantElement.associatedTab._name,
                        self._name,
                        parmElementName,
                    )
                )
                return None
            else:
                wsMirroredElementName = wsAssociatedBinder.uii._name
        else:
            wsMirroredElementName = ""  # ERROR??
        wsElement = self[parmElementName]
        wsElement.ConfigureAsMirrorRole(
            parmRole, parmParticipantElement._name, wsMirroredElementName
        )

    def GetElementByDbmsFieldName(self, parmDbmsFieldName):
        if parmDbmsFieldName in self.dbmsFieldNames:
            return self.dbmsFieldNames[parmDbmsFieldName]
        else:
            return None


#
# TupleDictionaryElement
#


def MakeClassTDict_For_TupleDictionaryElement(
    ExeController=None, InstanceClassName=None
):
    wsTDict = TupleDictionary(
        InstanceClassName=InstanceClassName,
        PrimaryDataPhysicalType=ertypes.Core_ObjectTypeCode,
        ExeController=ExeController,
    )
    wsTDict.AddScalarElement("allowedValues")
    wsTDict.AddScalarElement("associatedClassRefname")
    wsTDict.AddScalarElement("associatedElementName")
    wsTDict.AddScalarElement("associatedTableRefname")
    wsTDict.AddScalarElementReference("associationParticipantElement")
    wsTDict.AddScalarElementReference("associationParticipationElement")
    wsTDict.AddContainerElementList("confusedElementNameList")
    wsTDict.AddScalarElementBoolean("confusedIsVirtual")
    wsTDict.AddScalarElement("calculator")
    wsTDict.AddScalarElement("_caption")
    wsTDict.AddScalarElement("codeObjectName")
    wsTDict.AddScalarElement("codeSetName")
    # collections contains only items defined in TDict
    wsTDict.AddScalarElementReference("staticCollectionTDict")
    # if element describes a collection, type of its content
    wsTDict.AddScalarElement("collectionItemPhysicalType")
    # if element describes a collection, TDict of its content
    wsTDict.AddScalarElementReference("collectionItemTDict")
    wsTDict.AddScalarElement("combinedFieldSeparator")
    wsTDict.AddScalarElement("combinedFieldName")
    wsTDict.AddScalarElement("dbmsFieldName")
    wsTDict.AddScalarElement("dbmsFieldType")
    wsTDict.AddScalarElement("dbmsNull")
    wsTDict.AddScalarElement("dbmsKey")
    wsTDict.AddScalarElement("dbmsDefaultValue")
    wsTDict.AddScalarElement("dbmsExtra")
    wsTDict.AddScalarElement("dbmsPrivileges")
    # TDict containing this element
    wsTDict.AddScalarElementReference("parentTDict")
    wsTDict.AddScalarElement("_defaultValue")
    wsTDict.AddScalarElementBoolean("_defaultValueAssigned")
    wsTDict.AddScalarElementNumber("displayColumn")
    wsTDict.AddScalarElementNumber("displayLength")
    wsTDict.AddScalarElementNumber("displayOrder")
    wsTDict.AddScalarElementNumber("displayRow")
    wsTDict.AddScalarElement("encoding")
    wsTDict.AddScalarElementNumber("formCt")
    wsTDict.AddScalarElement("formRole")
    wsTDict.AddScalarElement("hint")
    wsTDict.AddScalarElementNumber("impliedDecimals")
    wsTDict.AddScalarElement("instanceOfClassRefname")
    wsTDict.AddScalarElementBoolean("isAutoIncrement")
    wsTDict.AddScalarElementBoolean("isCaseSensitive")
    wsTDict.AddScalarElementBoolean("isDirectoryMustExist")
    wsTDict.AddScalarElementBoolean("isDirectoryPath")
    wsTDict.AddScalarElementBoolean("isIdentifier")
    wsTDict.AddScalarElementBoolean("isIndex")
    wsTDict.AddScalarElementBoolean("isBlankAllowed")
    wsTDict.AddScalarElementBoolean("isPassword")
    wsTDict.AddScalarElementBoolean("isPositionalParameter")
    wsTDict.AddScalarElementBoolean("isProcessElement")
    wsTDict.AddScalarElementBoolean("isReadOnly")
    wsTDict.AddScalarElementBoolean("isRsf")
    wsTDict.AddScalarElementBoolean("isUnique")
    wsTDict.AddScalarElementBoolean("isUpperCaseOnly")
    wsTDict.AddScalarElementBoolean("isValueParameter")
    wsTDict.AddScalarElementBoolean("isVirtual")
    wsTDict.AddScalarElement("_ix")
    wsTDict.AddScalarElementNumber("minLength")
    wsTDict.AddScalarElementNumber("maxLength")
    wsTDict.AddScalarElementNumber("textAreaRows")
    wsTDict.AddScalarElementNumber("textAreaCols")
    wsTDict.AddScalarElement("_name")
    wsTDict.AddScalarElement("_path")
    wsTDict.AddScalarElement("physicalType")
    wsTDict.AddScalarElement("processMethodName")
    wsTDict.AddScalarElement("prompt")
    wsTDict.AddScalarElement("roleType")
    wsTDict.AddScalarElement("schemaFieldUdi")
    wsTDict.AddScalarElement("schemaFieldRoleSourceUdi")
    wsTDict.AddScalarElement("unitsOfMeasure")
    wsTDict.CompleteDictionary()
    return wsTDict

    # This __init__() must be be compatible with TupleDictionaryElement.__init__()
    # because it will get called by TupleDictionary.AddElement()
    #


#
# TDict Elements support meta values which distinguish between various cases of missing data.
#
# Many people do not have middle names. In a system that attempts to collect middle names each
# of the following are META situations that explain lack of a middle name in the database:
#
# NONE:	I don't have a middle name
# IDN: I don't know about my middle name (I Don't Know)
# NYB: I don't want to answer this question (None of Your Business)
# BLANK: No answer. Nothing known. Could be one of the above. Could be the box was accidentally skipped.
#
# BLANK is encoded as NULL in RDBMSes that support that, as None in Python memory objects
# and the value zero or a zero length string everywhere else.
#
# Use of META values is specified in the element. Few elements need to distinguish among all these cases.
# BLANK is the only commonly used one. Most of the time we don't care why we don't have a value, just
# wheter we have one or not.
#
# A non-zero minimum lenght specification often works as an
# alternative of specifiying isBlankAllowed of False. BLANK is implemented to allow specifications with
# BLANK allowed and a non-zero minimum len if specified. For example, the Plus-4 part of a US Zip code is usually
# not required, but if it is supplied it has to be exactly four digits long.
#
# isProcessElement identifies ephemeral data that is inherently created and managed while populating
# 	a data structure and as a resuit should not be loaded and restored in data sserialization /
# 	persistant operations.
#


class TupleDictionaryElement(object):
    __slots__ = (
        "allowedValues",
        "associatedClassRefname",
        "associatedElementName",
        "associatedTableRefname",
        "associationParticipantElement",
        "associationParticipationElement",
        "calculator",
        "_caption",
        "codeObjectName",
        "codeSetName",
        "staticCollectionTDict",
        "collectionItemPhysicalType",
        "collectionItemTDict",
        "combinedFieldSeparator",
        "combinedFieldName",
        "confusedElementNameList",
        "confusedIsVirtual",
        "dbmsFieldName",
        "dbmsFieldType",
        "dbmsNull",
        "dbmsKey",
        "dbmsDefaultValue",
        "dbmsExtra",
        "dbmsPrivileges",
        "formCt",
        "parentTDict",
        "_defaultValue",
        "_defaultValueAssigned",
        "displayColumn",
        "displayLength",
        "displayOrder",
        "displayRow",
        "encoding",
        "formRole",
        "hint",
        "impliedDecimals",
        "instanceOfClassRefname",
        "isAutoIncrement",
        "isCaseSensitive",
        "isDirectoryMustExist",
        "isDirectoryPath",
        "isIdentifier",
        "isIndex",
        "isBlankAllowed",
        "isPassword",
        "isPositionalParameter",
        "isProcessElement",
        "isReadOnly",
        "isRsf",
        "isUnique",
        "isUpperCaseOnly",
        "isValueParameter",
        "isVirtual",
        "_ix",
        "minLength",
        "maxLength",
        "_name",
        "_path",
        "physicalType",
        "processMethodName",
        "prompt",
        "roleType",
        "schemaFieldUdi",
        "schemaFieldRoleSourceUdi",
        "textAreaRows",
        "textAreaCols",
        "unitsOfMeasure",
    )

    def __init__(
        self,
        Name=None,
        ParentTDict=None,
        Caption=None,
        StaticCollectionTDict=None,
        CollectionItemPhysicalType=None,
        CollectionItemTDict=None,
        DisplayOrder=None,
        Encoding=ertypes.Encoding_Ascii,
        FormCt=None,
        Ix=-1,
        IsCaseSensitive=False,
        IsProcessElement=False,
        MinLength=None,
        MaxLength=None,
        BlankAllowed=True,
        PhysicalType=ertypes.Core_StringTypeCode,
        RoleType=ertypes.Core_DataRoleCode,
        SchemaFieldUdi=0,
        SchemaFieldRoleSourceUdi=0,
    ):

        #
        # These are the minimum set of fields needed for the dictionary of a bafDataTreeBranch() object.
        # Actually, _short name is far from essential.
        #
        self.parentTDict = ParentTDict
        self._ix = Ix  # this is the position of field in data array (0 ...)
        self._name = Name  # this variable name's formal, case sensitive spelling
        if (self.parentTDict is None) or (self.parentTDict._superiorTDict) is None:
            self._path = self._name
        else:
            self._path = (
                self.parentTDict._path + qddict.HierarchySeparatorCharacter + self._name
            )
        self.roleType = RoleType
        if self.roleType == ertypes.Core_TriggerRoleCode:
            # Triggers don't get handled like data fields on forms -- they
            # become buttons
            self.formRole = ertypes.FormRole_Submit
        else:
            self.formRole = ertypes.FormRole_Data
        # if container, these are the only allowed keys
        self.staticCollectionTDict = StaticCollectionTDict
        # if container, this is its type of the items in the collection
        self.collectionItemPhysicalType = CollectionItemPhysicalType
        # if container, this is its dict of the items in the collection
        self.collectionItemTDict = CollectionItemTDict
        if (self.parentTDict is None) or (self.parentTDict.formCt is None):
            self.formCt = FormCt
        else:
            # This is a grid within a form (see bafExeController.bafAction and bzContent.
            # All the fields within the grid are implicitly on the same form, so it does
            # not have to be specified for each element and is ignored if it is
            # specified.
            self.formCt = self.parentTDict.formCt
        # Source definition (documentation only)
        self.schemaFieldUdi = SchemaFieldUdi
        # Source definition (documentation only)
        self.schemaFieldRoleSourceUdi = SchemaFieldRoleSourceUdi
        #
        self.associatedClassRefname = None  # if this is an object type
        # Field name being mirrored (in associated binder)
        self.associatedElementName = None
        self.associatedTableRefname = None
        self.associationParticipantElement = None
        self.associationParticipationElement = None
        #
        #
        # These "raw" definitions from the DBMS interface. They are here mainly for
        # use only by the DBMS module and for documentation.
        #
        # dbmsFieldName is not part of this set of dbms-internal fields -- it is a more general field.
        # When this is a dbms table dicitonary, the dbms field name is merely the name.
        # When this is an application dictionary, dbmsFieldName is used to map the
        # dictionaries where name is a reference name.
        #
        self.dbmsFieldName = Name
        self.dbmsFieldType = None
        self.dbmsNull = None
        self.dbmsKey = None
        self.dbmsDefaultValue = None
        self.dbmsExtra = None
        self.dbmsPrivileges = None
        #
        # These fields are translated to BAF standards and application code
        # should use only these to keep everything DBMS agnostic.
        #
        self.allowedValues = None
        self.combinedFieldSeparator = ""
        self.combinedFieldName = ""
        self.confusedElementNameList = []
        self.confusedIsVirtual = False
        self._defaultValue = None
        self._defaultValueAssigned = False  # allows defaultValue to be None
        self.displayColumn = 0
        self.displayLength = 0
        self.displayOrder = DisplayOrder
        self.displayRow = 0
        self.calculator = None
        self._caption = Caption  # column heading, including CSV
        self.codeObjectName = None
        self.codeSetName = None
        self.impliedDecimals = 0
        self.unitsOfMeasure = None
        self.encoding = Encoding
        self.hint = None
        # if a class reference, must descend from this
        self.instanceOfClassRefname = None
        self.isAutoIncrement = False
        # effects sorting/matching not how stored
        self.isCaseSensitive = IsCaseSensitive
        self.isBlankAllowed = BlankAllowed  # isRequired (see META notes above)
        self.isDirectoryMustExist = False
        self.isDirectoryPath = False
        self.isIdentifier = False
        self.isIndex = False  # ?? dbms specification / not for BAF
        self.isPassword = False
        self.isPositionalParameter = False
        self.isProcessElement = IsProcessElement
        self.isReadOnly = False
        self.isRsf = False
        self.isUnique = False
        self.isUpperCaseOnly = False  # effects how stored
        self.isValueParameter = False
        self.isVirtual = False  # _ix will be -1
        self.SetLength(MinLength=MinLength, MaxLength=MaxLength)
        self.processMethodName = None
        self.prompt = self._name  # always have a basic prompt
        self.physicalType = PhysicalType
        self.textAreaCols = 0
        self.textAreaRows = 0

    def __repr__(self):
        return "%s:%s:%s" % (self._name, self.roleType, self.physicalType)

    def ConfigureAsConfusion(self, parmConfusedElementNameList, parmIsVirtual):
        wsDataRoles = self.parentTDict.exeController.GetCodeObject(
            ertypes.ErDataRolesName
        )
        self.roleType = wsDataRoles.ConfusionCode
        self.confusedElementNameList = parmConfusedElementNameList
        self.confusedIsVirtual = parmIsVirtual

    def ConfigureAsUdiRole(self, IsAutoIncrement=None):
        self.roleType = ertypes.Core_UdiRoleCode
        self.isBlankAllowed = False
        if IsAutoIncrement is not None:
            self.isAutoIncrement = IsAutoIncrement
        self.parentTDict.udi = self
        self.ConfigureAsUnique()

    def ConfigureAsUiiRole(self):
        self.roleType = ertypes.Core_UiiRoleCode
        self.parentTDict.uii = self
        self.ConfigureAsUnique()

    def ConfigureAsRsfRole(self):
        self.roleType = ertypes.Core_RsfRoleCode
        self.isRsf = True
        self.parentTDict.rsf = self

    def ConfigureAsCalculatedRole(self, parmCalculator):
        wsDataRoles = self.parentTDict.exeController.GetCodeObject(
            ertypes.ErDataRolesName
        )
        self.roleType = wsDataRoles.CalculatedCode
        self.calculator = parmCalculator

    def ConfigureAsDataRole(
        self,
        MinLength=0,
        MaxLength=0,
        CodeObjectName=None,
        CodeSetName=None,
        RoleType=ertypes.Core_DataRoleCode,
    ):
        self.roleType = RoleType
        if MinLength > 0:
            self.minLength = MinLength
        elif MinLength < 0:
            self.minLength = 0
        if MaxLength > 0:
            self.maxLength = MaxLength
        elif MaxLength < 0:
            self.maxLength = 0
        self.codeObjectName = CodeObjectName
        self.codeSetName = CodeSetName

    #
    # Non-Role Configurators
    #

    def ConfigureAsHidden(self):
        self.formRole = ertypes.FormRole_Hidden

    def ConfigureAsUpload(self):
        self.formRole = ertypes.FormRole_File

    def ConfigureAsDirectoryPath(self, DirectoryMustExist=True):
        self.isDirectoryPath = True
        self.isDirectoryMustExist = DirectoryMustExist

    def ConfigureAsRsf(self):
        self.isRsf = True
        self.parentTDict.rsf = self

    def ConfigureAsNotBlank(self):
        self.isBlankAllowed = False

    def ConfigureCalculator(self, parmRpn):
        self.calculator = parmRpn
        self._ix = -1  # should already be -1

    def ConfigureAsCombinedField(self, parmFieldName, Separator="/"):
        # parmFieldName cannot be validated here because it might not be defined.
        # CompleteTableDefinition() should validate and check for potential
        # infinite recursion.
        self.combinedFieldSeparator = Separator
        self.combinedFieldName = parmFieldName

    def ConfigureAsDirectoryPath(self, DirectoryMustExist=True):
        self.isDirectoryPath = True
        self.isDirectoryMustExist = DirectoryMustExist

    def ConfigureAsReadOnly(self):
        self.isReadOnly = True

    def ConfigureAsUnique(self, IsUnique=True):
        self.isUnique = IsUnique

    def InitialValue(self):
        if self._defaultValueAssigned:
            return self._defaultValue
        if self.physicalType == ertypes.Core_BooleanTypeCode:
            return False
        if self.physicalType == ertypes.Core_IntegerTypeCode:
            return 0
        if self.physicalType == ertypes.Core_StringTypeCode:
            return ""
        return None

    @property
    def caption(self):
        if self._caption is None:
            return self.prompt
        else:
            return self._caption

    @caption.setter
    def caption(self, value):
        self._caption = value

    @property
    def defaultValue(self):
        return self._defaultValue

    def AssignDefaultValue(self, value):
        # In order to avoid ambigutiy regarding None,
        # this is the only way that the default value should be assigned.
        #
        self._defaultValue = value
        self._defaultValueAssigned = True

    def SaveDbmsSpecs(
        self, DbmsFieldType, Null, Key, DefaultValue, Extra, Privileges=None
    ):
        self.dbmsFieldType = DbmsFieldType
        self.dbmsNull = Null
        self.dbmsKey = Key
        self.dbmsDefaultValue = DefaultValue
        self.dbmsExtra = Extra
        self.dbmsPrivileges = Privileges

    def SetAllowedValues(self, parmValues, UpperCase=True):
        # should make sure its an array and maybe check value compatibility
        self.isUpperCaseOnly = UpperCase
        self.allowedValues = []
        for wsThisValue in parmValues:
            if self.isUpperCaseOnly:
                self.allowedValues.append(utils.Upper(wsThisValue))
            else:
                self.allowedValues.append(wsThisValue)

    def SetDbmsFieldName(self, parmValue):
        self.dbmsFieldName = parmValue

    def SetLength(self, MinLength=None, MaxLength=None, BlankAllowed=None):
        self.minLength = MinLength
        self.maxLength = MaxLength
        if BlankAllowed is not None:
            self.isBlankAllowed = BlankAllowed
        if self.displayLength == 0:
            self.displayLength = self.maxLength

    def SeparateValue(self, parmData):
        # This method exists to localize use of the combinedField properties
        if self.combinedFieldSeparator == "":
            return (parmData, None)
        wsData = utils.Str(parmData)
        wsSeparatorPosition = wsData.find(self.combinedFieldSeparator)
        if wsSeparatorPosition < 0:
            return (parmData, None)
        return (
            wsData[:wsSeparatorPosition],
            (self.combinedFieldName, wsData[wsSeparatorPosition + 1 :]),
        )

    #
    # ValidateDatum() should be the only place that performs atomic validation
    # of data fields. Relational validation is performed by bzDataStore.
    #
    # It also transforms data from external formats (generally strings from
    # users, databases, XML, etc.) to internal formats needed for program
    # execution. This mainly means turning numbers into integers and making sure
    # that strings are actually strings. Booleans values are intetgers
    # restricted to values True and False.
    #
    # GetDatumAndState() and GetDatum() access meta data.
    # InstancePhysicalType identifies how to access the data. Since Tuple Dictionaries
    # are essentially class descriptors, the most common access method is probably
    # Core_ObjectTypeCode. For various reasons the data may be dumped into another
    # container of convenience or to prevent class methods from being accessed
    # with untrusted data.
    #
    # Returns a tuple of (IsValid, ScrubbedValue).
    # IsValid is a boolean indicating whether or not the value conforms to the
    # element definition internal edits. For a foreign key it would check the
    # type, etc. but not whether or not the referenced record actully exists.
    # ScrubbedValue is the properly formatted value which may reflect certain
    # transformations such as converting a string number to an integer.
    #
    def GetDatumAndState(self, parmData, InstancePhysicalType=None):
        wsInstancePhysicalType = InstancePhysicalType
        if wsInstancePhysicalType is None:
            wsInstancePhysicalType = self.parentTDict.instancePhysicalType
        if wsInstancePhysicalType in ertypes.Core_ContainerMapTypeCodes:
            if self._name in parmData:
                return (True, parmData[self._name])
            else:
                return (False, None)
        # should check if parmData is really using same dict in case _ix is
        # different
        wsDatumSpecified = False
        wsDatum = None
        if wsInstancePhysicalType == ertypes.Core_ObjectTypeCode:
            try:
                wsDatum = getattr(parmData, self._name)
                wsDatumSpecified = True
            except BaseException:
                pass
            return (wsDatumSpecified, wsDatum)
        raise IndexError(
            "Unknown instance physical type '{PhysType}'for container '{Name'".form(
                PhysType=wsInstancePhysicalType, Name=self.parentTDict._name
            )
        )

    def GetDatum(self, parmData, InstancePhysicalType=None):
        (wsDatumSpecified, wsDatum) = self.GetDatumAndState(
            parmData, InstancePhysicalType=InstancePhysicalType
        )
        if wsDatumSpecified:
            return wsDatum
        if self._defaultValueAssigned:
            return self._defaultValue
        if self.isBlankAllowed:
            return self.InitialValue()
        raise TypeError("No value available for '%s'." % (self._name))

    def PutDatum(self, parmData, parmValue, InstancePhysicalType=None):
        wsInstancePhysicalType = InstancePhysicalType
        if wsInstancePhysicalType is None:
            wsInstancePhysicalType = self.parentTDict.instancePhysicalType
        if wsInstancePhysicalType in ertypes.Core_ContainerMapTypeCodes:
            parmData[self._name] = parmValue
            return
        # should check if parmData is really using same dict in case _ix is
        # different
        if wsInstancePhysicalType == ertypes.Core_ObjectTypeCode:
            setattr(parmData, self._name, parmValue)
            return
        raise IndexError(
            "Unknown instance physical type '{PhysType}'for container '{Name'".form(
                PhysType=wsInstancePhysicalType, Name=self.parentTDict._name
            )
        )

    def ValidateDatum(self, parmDatumSpecified, parmDatum, RoundExtraDigits=False):
        # Some of the messages below are AddDevXxxMessage and other AddUserXxxMessages.
        # Invalid values are most likely a problem for users to fix.
        # Invalid dictionaries are likely a problem for developers.
        wsDatum = parmDatum
        if (not parmDatumSpecified) or (parmDatum is None):
            if not self.isBlankAllowed:
                self.parentTDict.exeController.errs.AddUserCriticalMessage(
                    "%s value required." % (self._name)
                )
                return (False, wsDatum)
            wsDatum = self.InitialValue()
        #
        if isinstance(wsDatum, str):
            if self.encoding == ertypes.Encoding_Utf8:
                pass
            elif self.encoding == ertypes.Encoding_AsciiX:
                wsDatum = utils.UnicodeToAscii(wsDatum)
            else:
                try:
                    wsDatum = wsDatum.encode("ascii")
                except UnicodeEncodeError:
                    self.parentTDict.exeController.errs.AddUserCriticalMessage(
                        "Invalid value '%s' for ascii field %s"
                        % (repr(wsDatum), self._name)
                    )
        if self.physicalType == ertypes.Core_IntegerTypeCode:
            wsResult = utils.NumericToInt(
                wsDatum,
                ImpliedDecimals=self.impliedDecimals,
                UnitsOfMeasure=self.unitsOfMeasure,
                RoundExtraDigits=RoundExtraDigits,
                Errs=self.parentTDict.exeController.errs,
            )
            if wsResult is None:
                self.parentTDict.exeController.errs.AddUserCriticalMessage(
                    "Invalid value '%s' for integer field %s"
                    % (repr(wsDatum), self._name)
                )
            else:
                wsDatum = wsResult
            wsDatum = utils.Int(wsDatum)
        elif self.physicalType == ertypes.Core_BooleanTypeCode:
            wsDatum = utils.Bool(wsDatum)
        elif self.physicalType == ertypes.Core_DateTypeCode:
            wsResult = utils.TestYMD(wsDatum)
            if wsResult is None:
                self.parentTDict.exeController.errs.AddUserCriticalMessage(
                    "Invalid value '%s' for date field %s" % (repr(wsDatum), self._name)
                )
            else:
                wsDatum = wsResult
        elif self.physicalType in ertypes.Core_PointerTypeCodes:
            pass  # leave as pointer. ?? check class ??
        else:
            wsDatum = utils.Str(wsDatum)
        #
        if self.isUpperCaseOnly:
            wsDatum = utils.Upper(wsDatum)
        #
        if self.codeObjectName is not None:
            wsCodeObject = self.parentTDict.exeController.GetCodeObject(
                self.codeObjectName
            )
            if (wsCodeObject is None) or (
                not wsCodeObject.ValidateSet(self.codeSetName, wsDatum())
            ):
                self.parentTDict.exeController.errs.AddUserCriticalMessage(
                    "Field value '%s' not in code set %s.%s for field %s"
                    % (wsDatum, self.codeObjectName, self.codeSetName, self._name)
                )
                return (False, wsDatum)
        #
        if self.isDirectoryMustExist:
            if not os.path.isdir(wsDatum):
                self.parentTDict.exeController.errs.AddUserCriticalMessage(
                    "Field value '%s' for field %s is not a valid directory"
                    % (wsDatum, self._name)
                )
                return (False, wsDatum)

        if self.allowedValues is not None:
            if not (wsDatum in self.allowedValues):
                self.parentTDict.exeController.errs.AddUserCriticalMessage(
                    "%s value '%s' not in list %s."
                    % (self._name, repr(wsDatum), repr(self.allowedValues))
                )
                return (False, wsDatum)
        return (True, wsDatum)
