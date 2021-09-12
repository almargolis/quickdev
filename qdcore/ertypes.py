#!/usr/bin/python
#############################################
#
#  bafErTypes
#

#
# This module shold import as few other pylib modules as possible in order to avoid circular references.
#
# Its also critical because bzConfigure needs it to bootstrap site initialization
#
from . import utils

ErCodeDefElementCode = 'Code'
ErCodeDefElementSet = 'Set'

SiteActionsVariableSuffix = '_Action'
SiteClassesVariableSuffix = '_Class'
SiteCommandsVariableSuffix = '_Command'
SiteTriggersVariableSuffix = '_Trigger'

#
# These constants are used when calling exeAction.GetCodeObject() to minimize uncaught typos
#
ErLogicalDataTypesName = 'ErLogicalDataTypes'
ErLogicalDataClassesName = 'ErLogicalDataClasses'
ErEncodingTypesName = 'ErEncodingTypes'
ErDataRolesName = 'ErDataRoles'
ErRecordStatusName = 'ErRecordStatus'
TaAssociationTypesName = 'TaAssociationTypes'


class ErCodeDef:
    def __init__(self, parmExeAction):
        self.exeAction = parmExeAction
        self.codeValues = {}
        # dup of setattr, to validate sets w/o confusion of otehr attributes
        self.codeSymbols = {}
        self.codeNames = {}
        self.setValues = {}
        self.setSymbols = {}
        self.name = self.__class__.__name__

    def AddElement(self, parmElementType, parmValue, parmSymbol):
        wsSymbolName = parmSymbol + parmElementType
        if parmElementType == ErCodeDefElementSet:
            wsValueContainer = self.setValues
            wsSymbolContainer = self.setSymbols
            wsNameContainer = None
            wsValueArray = []
            for wsThisSymbol in parmValue:
                wsThisCodeSymbolName = wsThisSymbol + ErCodeDefElementCode
                if wsThisCodeSymbolName in self.codeSymbols:
                    wsValueArray.append(self.codeSymbols[wsThisCodeSymbolName])
                else:
                    if self.exeAction:
                        self.exeAction.errs.AddDevCriticalMessage(
                            "Attempt to add invalid code symbol '%s' to Set %s of Code Def %s" %
                            (wsThisCodeSymbolName, wsSymbolName, self.name))
                    return
            wsValueArray.sort()
            wsValue = ''
            for wsThisValue in wsValueArray:
                wsValue += wsThisValue
        else:
            wsValueContainer = self.codeValues
            wsSymbolContainer = self.codeSymbols
            wsNameContainer = self.codeNames
            wsValue = parmValue
        if wsValue in wsValueContainer:
            if self.exeAction:
                self.exeAction.errs.AddDevCriticalMessage(
                    "Attempt to add duplicate %s value '%s' (%s) to Code Def %s" %
                    (parmElementType, wsValue, wsSymbolName, self.name))
            return
        if wsSymbolName in self.__dict__:
            if self.exeAction:
                self.exeAction.errs.AddDevCriticalMessage(
                    "Attempt to add duplicate %s symbol '%s' (%s) to Code Def %s" %
                    (parmElementType, wsSymbolName, wsValue, self.name))
            return
        #
        wsSymbolContainer[wsSymbolName] = wsValue
        wsValueContainer[wsValue] = wsSymbolName
        if wsNameContainer is not None:
            wsNameContainer[wsValue] = parmSymbol
        setattr(self, wsSymbolName, wsValue)

    def AddCode(self, parmCode, parmSymbol):
        wsCode = utils.Upper(parmCode)
        self.AddElement(ErCodeDefElementCode, parmCode, parmSymbol)

    def AddSet(self, parmSetSymbol, parmSetMembers):
        # I called this a Set instead of Class to avoid confusion with object classes.
        # I'm not sure if that's effective or necessary.
        self.AddElement(ErCodeDefElementSet, parmSetMembers, parmSetSymbol)

    def DefineFullSet(self):
        self.AddSet('Full', list(self.codeNames.values()))

    def LookupCodeName(self, parmCode):
        if parmCode in self.codeNames:
            return self.codeNames[parmCode]
        return None

    def LookupCodeSymbol(self, parmCode):
        if parmCode in self.codeValues:
            return self.codeValues[parmCode]
        return None

    def ValidateCode(self, parmCode):
        wsCode = utils.Upper(parmCode)
        if wsCode in self.codeValues:
            return wsCode							# codes must be upper case
        else:
            return None

    def ValidateSet(self, parmSetName, parmCode):
        wsSetValues = self.setSymbols[parmSetName]
        if parmCode in wsSetValues:
            return True
        else:
            return False


#
#
#
Encoding_Ascii = 'A'
Encoding_AsciiX = 'X'		# using utils.UnicodeToAscii()
Encoding_Codex = 'C'
Encoding_Soundex = 'S'
Encoding_Utf8 = 'U'


#
# Type Codes identify the storage format of data. Storage includes
# process memory variable storage and persistant storage in
# databases and serialized files (XML, JSON, XPDI). The goal
# is for the type to properly define the data in all these
# environments with one type code.
#
# Role Codes identify why data exists and how it is used.
#
# Sometimes the distiction is a bit hazy. the XxxPtrTypeCodes are
# all the same memory storage format in Python. They often
# have different roles, but those don't map cleanly by type.
# While their memory format is identical, their XPDI serialized
# storage is fairly different.
#
# Letter Codes Used: A B C D E F I M N O R S T X Y Z
#
Core_ListTypeCode = 'A'		# A collection of unnamed items -- system []
Core_ListBafTypeCode = 'C'		# A collection of unnamed items -- bafDataStoreObject
Core_BooleanTypeCode = 'B'		# A scalar
Core_DateTypeCode = 'D'
Core_FunctionTypeCode = 'F'		# for bafExpCodeWriter, not ErLogicalDataTypes
Core_IntegerTypeCode = 'I'
Core_MapDictTypeCode = 'M'		# A container that supports __get/set item__ {}
Core_MapNvTypeCode = 'N'		# A container that supports __get/set item__ bafNvTuple
Core_MapBafTypeCode = 'R'		# A container that supports __get/set item__ bafTupleObject
Core_NoTypeCode = 'Z'		# Non implemented element
Core_ObjectTypeCode = 'O'		# A container that supports __get/set attr__
Core_ClassPtrTypeCode = 'X'
Core_DataPtrTypeCode = 'Y'
Core_ProcessPtrTypeCode = 'Z'
Core_StringTypeCode = 'S'
Core_TDictTypeCode = 'E'
Core_TimestampTypeCode = 'T'

Core_ContainerMapTypeCodes = [		# Types accessed by [name] or __get/set item__
    Core_MapDictTypeCode,
    Core_MapNvTypeCode,
    Core_MapBafTypeCode
]

Core_ContainerNVTypeCodes = Core_ContainerMapTypeCodes + [Core_ObjectTypeCode]

Core_ContainerIxVTypeCodes = [
    Core_ListBafTypeCode,
    Core_ListTypeCode
]

Core_ContainerTypeCodes = Core_ContainerNVTypeCodes + Core_ContainerIxVTypeCodes


Core_ContainerIxVTypeCodes = [
    Core_ListBafTypeCode,
    Core_ListTypeCode
]

Core_PointerTypeCodes = [
    Core_ClassPtrTypeCode,
    Core_DataPtrTypeCode,
    Core_ProcessPtrTypeCode
]

Core_ScalarTypeCodes = [
    Core_BooleanTypeCode,
    Core_DateTypeCode,
    Core_IntegerTypeCode,
    Core_StringTypeCode,
    Core_TimestampTypeCode
]

Core_StringTypeCodes = [
    Core_StringTypeCode,
    Core_DateTypeCode,
    Core_TimestampTypeCode]


def ClassifyPhysicalType(Sample):
    from . import bafDataStore
    from . import bafNv
    if isinstance(Sample, bafDataStore.bafDataStoreObject):
        return Core_ListBafTypeCode
    if isinstance(Sample, bafDataStore.bafTupleObject):
        return Core_MapBafTypeCode
    if isinstance(Sample, bafNv.bafNvTuple):
        return Core_MapNvTypeCode
    if isinstance(Sample, str):
        return Core_StringTypeCode
    if isinstance(Sample, bool):
        return Core_BooleanTypeCode
    if isinstance(Sample, dict):
        return Core_MapDictTypeCode
    if isinstance(Sample, int):
        return Core_IntegerTypeCode
    if isinstance(Sample, list):
        return Core_ListTypeCode
    return None


# RoleCodes: A B C D E F G H M P R S U X
Core_CreateTimestampRoleCode = 'B'
Core_CalculatedRoleCode = 'A'
Core_ConfusionRoleCode = 'C'
Core_DataRoleCode = 'D'
Core_PrimaryParticipantRoleCode = 'P'
Core_SecondaryParticipantRoleCode = 'S'
Core_MirrorRoleCode = 'M'
Core_MirrorUdiRoleCode = 'F'
Core_MirrorUiiRoleCode = 'G'
Core_RsfRoleCode = 'R'
Core_UdiRoleCode = 'X'
Core_UiiRoleCode = 'U'
Core_UpdateTimestampRoleCode = 'E'
Core_TriggerRoleCode = 'H'

Core_VirtualRoleCodes = [Core_ConfusionRoleCode]

FormRole_Data = 'D'
FormRole_Hidden = 'H'
FormRole_File = 'F'
FormRole_Submit = 'S'


class ErLogicalDataTypes(ErCodeDef):
    def __init__(self, parmExeAction):
        ErCodeDef.__init__(self, parmExeAction)
        self.AddCode(Core_StringTypeCode, 'String')
        self.AddCode(Core_IntegerTypeCode, 'Integer')
        self.AddCode(Core_BooleanTypeCode, 'Boolean')
        self.AddCode(Core_TimestampTypeCode, 'Timestamp')
        self.AddCode(Core_DateTypeCode, 'Date')
        self.AddCode(Core_MapDictTypeCode, 'Dict')
        #
        self.DefineFullSet()
        self.AddSet('Datastore', ('String', 'Integer'))


class ErDataRoles(ErCodeDef):
    def __init__(self, parmExeAction):
        ErCodeDef.__init__(self, parmExeAction)
        self.AddCode(Core_CalculatedRoleCode, 'Calculated')
        self.AddCode(Core_ConfusionRoleCode, 'Confusion')
        self.AddCode(Core_DataRoleCode, 'Data')
        self.AddCode(Core_PrimaryParticipantRoleCode, 'PrimaryParticipant')
        self.AddCode(Core_SecondaryParticipantRoleCode, 'SecondaryParticipant')
        self.AddCode(Core_MirrorRoleCode, 'Mirror')
        self.AddCode(Core_UdiRoleCode, 'Udi')
        self.AddCode(Core_UiiRoleCode, 'Uii')
        self.AddCode(Core_RsfRoleCode, 'Rsf')
        self.AddCode(Core_MirrorUdiRoleCode, 'MirrorUdi')
        self.AddCode(Core_MirrorUiiRoleCode, 'MirrorUii')
        #
        self.DefineFullSet()
        self.AddSet(
            'Virtual',
            ('Calculated',
             'Confusion',
             'PrimaryParticipant',
             'SecondaryParticipant'))
        self.AddSet('Mirrored', ('Mirror', 'MirrorUdi', 'MirrorUii'))
        self.AddSet(
            'Physical',
            ('Data',
             'Mirror',
             'Udi',
             'Uii',
             'Rsf',
             'MirrorUdi',
             'MirrorUii'))
        self.AddSet('Source', ('Data', 'Udi', 'Uii', 'Rsf'))
        self.AddSet(
            'Participant',
            ('PrimaryParticipant',
             'SecondaryParticipant'))


class ErRecordStatus(ErCodeDef):
    def __init__(self, parmExeAction):
        ErCodeDef.__init__(self, parmExeAction)
        self.AddCode('U', 'Undefined')
        self.AddCode('A', 'Active')
        self.AddCode('D', 'Deleted')
        #
        self.DefineFullSet()


Core_DirectAssociationTypeCode = 'D'
Core_LookupAssociationTypeCode = 'L'
Core_PathAssociationTypeCode = 'P'


class TaAssociationTypes(ErCodeDef):
    def __init__(self, parmExeAction):
        ErCodeDef.__init__(self, parmExeAction)
        self.AddCode(Core_PathAssociationTypeCode, 'Path')
        self.AddCode(Core_LookupAssociationTypeCode, 'Lookup')
        self.AddCode(Core_DirectAssociationTypeCode, 'Direct')
        #
        self.DefineFullSet()
        self.AddSet('Direct', ('Lookup', 'Direct'))
        self.AddSet('Path', ('Path', 'Direct'))


def GetPythonClassAsStr(parmObject):
    try:
        return parmObject.__class__.__name__
    except BaseException:
        pass
    return repr(type(parmObject))


def Core_GetCodeObject(parmExeController, parmCodeReferenceName):
    # hardwire for now
    if parmExeController is not None:
        if parmCodeReferenceName in parmExeController.codes:
            return parmExeController.codes[parmCodeReferenceName]
    if parmCodeReferenceName == ErLogicalDataTypesName:
        wsCodeObject = ErLogicalDataTypes(parmExeController)
        if parmExeController is not None:
            parmExeController.codes[parmCodeReferenceName] = wsCodeObject
        return wsCodeObject
    if parmCodeReferenceName == ErLogicalDataClassesName:
        wsCodeObject = ErLogicalDataClasses(parmExeController)
        if parmExeController is not None:
            parmExeController.codes[parmCodeReferenceName] = wsCodeObject
        return wsCodeObject
    if parmCodeReferenceName == ErDataRolesName:
        wsCodeObject = ErDataRoles(parmExeController)
        if parmExeController is not None:
            parmExeController.codes[parmCodeReferenceName] = wsCodeObject
        return wsCodeObject
    if parmCodeReferenceName == ErRecordStatusName:
        wsCodeObject = ErRecordStatus(parmExeController)
        if parmExeController is not None:
            parmExeController.codes[parmCodeReferenceName] = wsCodeObject
        return wsCodeObject
    if parmCodeReferenceName == TaAssociationTypesName:
        wsCodeObject = TaAssociationTypes(parmExeController)
        if parmExeController is not None:
            parmExeController.codes[parmCodeReferenceName] = wsCodeObject
        return wsCodeObject
    if parmCodeReferenceName == ErEncodingTypesName:
        wsCodeObject = ErEncodingTypes(parmExeController)
        if parmExeController is not None:
            parmExeController.codes[parmCodeReferenceName] = wsCodeObject
        return wsCodeObject
    return None
