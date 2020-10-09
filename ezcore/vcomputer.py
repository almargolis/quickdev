# bzVmachine
#
# This is a simple virtual machine who's only claim to fame is that it is intimately aware of the BFS
# runtime and its related data structure.
#
# 6 Aug 2011 - Start Development
#		A lot of leraning for this comes from bzBizgen and its predecessors and the explression
#		analyzer in bzParse but I'm not particularly looking at that code.
#

from . import ertypes

from . import utils


class bzPcodes(ertypes.ErCodeDef):
    def __init__(self, parmExeAction):
        ertypes.ErCodeDef.__init__(self, parmExeAction)
        self.AddCode('P', 'PushData')
        self.AddCode('A', 'Add')
        #
        self.DefineFullSet()
        #self.AddSet('Virtual', ('Confusion', 'AssociationPrimary', 'AssociationSecondaryDirect', 'AssociationSecondaryPath'))


StackUnderflowIx = -1

#
# As of this moment opcodes are never stored outside of runtime memory
# so they can be changed at any time. Eventually this will change.
# For now, insert as needed with minimal typing and peridodically
# resequence.
#
# These should be "proper literals" so we can translate back to symbols
#
OpPushTupleElement = 0o1
OpPushNumber = 0o5
OpPushString = 0o7
OpPushVariable = 12

OpAdd = 29
OpAnd = 30
OpCompareEqual = 40
OpConcat = 50
OpOr = 60
OpSubtract = 70


class bafVStack(object):
    def __init__(self):
        self.stack = []
        self.top = StackUnderflowIx

    def Push(self, parmStackObject):
        self.top += 1
        if self.top >= len(self.stack):
            self.stack.append(parmStackObject)
        else:
            self.stack[self.top] = parmStackObject

    def Pop(self):
        if self.top <= StackUnderflowIx:
            raise Exception
        self.top -= 1
        return self.stack[self.top + 1]


def GetFieldValue(parmRecord, parmFieldName, DefaultTDict=None):
    #print ">>>", `parmRecord`
    #print "---", `parmFieldName`
    try:
        return parmRecord[parmFieldName]
    except BaseException:
        pass
    #
    # The above takes care of the most common case of the value being
    # accessable via index with no wories about spelling case.
    # Now it gets more complicated. We need a TDict entry to get the
    # case sensitive name.
    #
    try:
        wsDictionaryElement = parmRecord._tdict[parmFieldName]
    except BaseException:
        wsDictionaryElement = None
    if wsDictionaryElement is None:
        if DefaultTDict is not None:
            try:
                wsDictionaryElement = DefaultTDict[parmFieldName]
            except BaseException:
                wsDictionaryElement = None
    if wsDictionaryElement is None:
        wsFormalName = parmFieldName
    else:
        wsFormalName = wsDictionaryElement.name
    try:
        return getattr(parmRecord, wsFormalName)
    except BaseException:
        pass
    if wsDictionaryElement is not None:
        if wsDictionaryElement.defaultValueSet:
            return wsDictionaryElement.defaultValue
    raise IndexError


class bafVMachine(object):
    def __init__(self, ExeController=None):
        self.exeController = ExeController		# bafExeController
        self.stack = bafVStack()

    def RunRPN(self, parmCode, parmDataStore, Debug=0):
        if Debug > 0:
            print("Code: ", repr(parmCode))
        #print `parmDataStore`
        for wsThisOperation in parmCode:
            if isinstance(wsThisOperation, type(())):
                wsThisOpcode = wsThisOperation[0]
                wsThisOperand = wsThisOperation[1:]
            else:
                wsThisOpcode = wsThisOperation
                wsThisOperand = ()
            if wsThisOpcode == OpPushTupleElement:
                # The "tuple" can be any kind of object. This works best
                # if we can identify a bafTupleDictionary or if it is a
                # bafTupleObject
                wsTupleObject = parmDataStore[wsThisOperand[0]]
                wsElementValue = GetFieldValue(wsTupleObject, wsThisOperand[1])
                self.stack.Push(wsElementValue)
            elif wsThisOpcode == OpPushNumber:
                self.stack.Push(utils.Int(wsThisOperand[0]))
            elif wsThisOpcode == OpPushString:
                self.stack.Push(utils.Str(wsThisOperand[0]))
            if wsThisOpcode == OpPushVariable:
                wsVariableValue = parmDataStore[wsThisOperand[0]]
                self.stack.Push(wsVariableValue)
            #
            elif wsThisOpcode == OpAdd:
                wsOperand2 = utils.Int(self.stack.Pop())
                wsOperand1 = utils.Int(self.stack.Pop())
                self.stack.Push(wsOperand1 + wsOperand2)
            elif wsThisOpcode == OpAnd:
                wsOperand2 = utils.AsBool(self.stack.Pop())
                wsOperand1 = utils.AsBool(self.stack.Pop())
                if wsOperand1 and wsOperand2:
                    self.stack.Push(True)
                else:
                    self.stack.Push(False)
            elif wsThisOpcode == OpCompareEqual:
                wsOperand2 = utils.Upper(self.stack.Pop())
                wsOperand1 = utils.Upper(self.stack.Pop())
                if wsOperand1 == wsOperand2:
                    self.stack.Push(True)
                else:
                    self.stack.Push(False)
            elif wsThisOpcode == OpConcat:
                wsOperand2 = utils.Str(self.stack.Pop())
                wsOperand1 = utils.Str(self.stack.Pop())
                self.stack.Push(wsOperand1 + wsOperand2)
            elif wsThisOpcode == OpOr:
                wsOperand2 = utils.AsBool(self.stack.Pop())
                wsOperand1 = utils.AsBool(self.stack.Pop())
                if wsOperand1 or wsOperand2:
                    self.stack.Push(True)
                else:
                    self.stack.Push(False)
            elif wsThisOpcode == OpSubtract:
                wsOperand2 = utils.Int(self.stack.Pop())
                wsOperand1 = utils.Int(self.stack.Pop())
                self.stack.Push(wsOperand1 - wsOperand2)
            if Debug > 0:
                print(repr(self.stack.stack))
        #
        wsResult = self.stack.Pop()
        return wsResult


def ModuleTest(ExeAction=None):
    R1 = {'Species': "Cat", 'Name': "Chloe"}
    R2 = {'Species': "Cat", 'Name': "Tippie"}
    DS = {'R1': R1, 'R2': R2}

    VM = bafVMachine(ExeAction=ExeAction)
    #
    wsProg = (
        (OpPushTupleElement, 'R1', 'Species'),
        (OpPushTupleElement, 'R2', 'Species'),
        OpCompareEqual
    )
    if VM.RunRPN(wsProg, DS):
        print("Species Match -- OK")
    else:
        print("Species Mis-Match -- WRONG!!!")
    #
    wsProg = (
        (OpPushTupleElement, 'R1', 'Name'),
        (OpPushTupleElement, 'R2', 'Name'),
        OpCompareEqual
    )
    if VM.RunRPN(wsProg, DS):
        print("Name Match -- WRONG!!!")
    else:
        print("Name Mis-Match -- OK")
    #
    wsProg = (
        (OpPushNumber, 6),
        (OpPushNumber, 2),
        OpSubtract
    )
    wsResult = VM.RunRPN(wsProg, DS)
    if wsResult == 4:
        print("6 - 2 = 4 -- OK")
    else:
        print("6 - 2 = %d -- WRONG!!!" % (wsResult))
