#!/usr/bin/python
#############################################
#
#  bzCommaStr Module
#
#
#  FEATURES
#
#
#
#  WARNINGS
#
#
#  Copyright (C) 2001,2002,2003,2004,2005
#		by Albert B. Margolis - All Rights Reserved
#
#  4/20/2005:  move from utils to avoid cross-import problems.

import string
import sys

from . import qddict
from . import utils


def AsList(parmData):
    if parmData is None:
        return []
    if isinstance(parmData, str):
        if len(parmData) == 0:			# this works for Unicode and not
            return []
        if (parmData[:1] == '[') and (parmData[-1:] == "]"):
            parmData = parmData[1:-1]
            return CommaStrToList(parmData, RecognizeArrays=True)
        else:
            return CommaStrToList(parmData)
    return [parmData]

# This method converts a list into string.  It is nearly redundant with
# __expr__() except that it gives me more direct control over formatting
# of components.  It is very similar to ListToCommaStr() but doesn't
# quote sub-arrays -- essentially it considers [] a form of quoting.
# It also uses "'" as the default string quote character in order
# to minimize double-quoting when inserted into a ListToCommaStr()
#


def ListToStr(parmList, quote="'", Escape=None, Delim=", ", AlsoQuote=""):
    if not parmList:
        return "[]"
    wsStr = ""
    wsFldDstCt = 0
    for wsThisField in parmList:
        if wsFldDstCt > 0:
            wsStr += Delim
        if isinstance(wsThisField, type([])):
            wsThisField = ListToStr(wsThisField, quote=quote,
                                    Escape=Escape, Delim=Delim,
                                    AlsoQuote=AlsoQuote)
        else:
            wsThisField = utils.FilterText(wsThisField)
            wsThisField = utils.QuoteStr(wsThisField,
                                         Escape=Escape, Delim=Delim,
                                         AlsoQuote=AlsoQuote)
        wsStr += wsThisField
        wsFldDstCt += 1
    return "[%s]" % (wsStr)

#
#  ListToCommaStr() Converts an array into a comma delimited line of text for data export
#
#  If an array element is an array, it is converted to a comma separated list quoted with brackets.
#
#  Non-Text characters are filtered out by FilterText()
#
#  QuoteAlways=TRUE quotes all elements, even if they don't contain quotes, delimters, etc.
#		Needed to conform to Excel comma delimited format.
#		Also used to generate a list of strings when generating code.
#
#  AlsoQuote="," needed to conform to Excel tab delimited format
#


def ListToCommaStr(parmList, Quote='"', QuoteAlways=False, Escape=None,
                   fldCt=-1, FldSkipMap="", Delim=", ",
                   QuoteNever=False, AlsoQuote=""):
    wsStr = ""
    if not parmList:
        return wsStr
    wsFldSrcCt = 0
    wsFldDstCt = 0
    for wsThisField in parmList:
        wsFldSrcCt += 1
        if (len(FldSkipMap) >= wsFldSrcCt) and (
                FldSkipMap[wsFldSrcCt - 1] == "Y"):
            continue
        if wsFldDstCt > 0:
            wsStr += Delim
        if isinstance(wsThisField, type([])):
            wsThisField = '[' + ListToCommaStr(wsThisField,
                                               Quote=Quote,
                                               QuoteAlways=QuoteAlways,
                                               Escape=Escape,
                                               Delim=Delim,
                                               QuoteNever=QuoteNever,
                                               AlsoQuote=AlsoQuote) + ']'
        else:
            wsThisField = utils.FilterText(wsThisField)
            if not QuoteNever:
                wsThisField = utils.QuoteStr(
                    wsThisField,
                    QuoteAlways=QuoteAlways,
                    Escape=Escape,
                    Delim=Delim,
                    AlsoQuote=AlsoQuote)
        wsStr += wsThisField
        wsFldDstCt += 1
        if (fldCt >= 0) and (wsFldDstCt >= fldCt):
            # Stop here if a maximum field is specified and we have gotten that
            # far
            return wsStr
    if fldCt >= 0:
        # Create empty fields up to fldCt
        while wsFldCt < fldCt:
            if wsStr != "":
                wsStr += Delim
            if QuoteAlways:
                wsStr += Quote + Quote
            wsFldCt += 1
    return wsStr

#
# This is has limited reentrancy to support an array of arrays.
# Parsing is fairly simpleminded.  Most of CommaStrToList()
# Should be a method in this class and that standaline function
# shouild become a wrapper.
#


class bzLineParse:
    def __init__(
            self,
            Escape=None,
            getKeywords=None,
            RecognizeArrays=None,
            StripAll=False):
        self.ascii = True
        self.ClearCurField()
        self.Escape = Escape
        self.getKeywords = getKeywords
        self.RecognizeArrays = RecognizeArrays
        self.fields = []
        self.keyName = ""
        self.quoteChar = ""
        self.stripAll = StripAll
        if getKeywords:
            self.keywords = qddict.EzDict()

    def ClearCurField(self):
        if self.ascii:
            self.curField = ""
        else:
            self.curField = ""

    def AppendField(self):
        if self.stripAll or (self.quoteChar == ""):
            # Defalt mode is is not strip leading/trailing white space
            # from quoted fields. That space could be why the field is
            # quoted. Some interchange files quote random fields and
            # include innaproriate leading/trailing white space
            # within the quotes. StripAll is a broad solution.
            self.curField = self.curField.strip()
        if self.curField and self.RecognizeArrays:
            # recognize arrays in the string
            if (self.curField[0] == "[") and (self.curField[-1] == "]"):
                wsCurField = utils.Strip(self.curField[1:-1])
                if wsCurField == "":
                    self.curField = []
                else:
                    self.curField = CommaStrToList(
                        wsCurField, Escape=self.Escape, RecognizeArrays=True)
        if self.keyName:
            self.keywords[self.keyName] = self.curField
        else:
            self.fields.append(self.curField)
        self.ClearCurField()
        self.keyName = ""
        self.quoteChar = ""


def ParseColonArray(wsLine, ColonArrayLen=0):
    wsArray = string.split(wsLine, ":")
    if ColonArrayLen > 0:
        while len(wsArray) < ColonArrayLen:
            wsArray.append("")
    return wsArray


def FastCommaStrToList(parmStr, Delim=",", UpperCase=True):
    # This is faster than bzCommaStr.CommaStrToList() if simple parsing OK
    # and all upper case
    if parmStr:
        if UpperCase:
            parmStr = utils.Upper(parmStr)
        wsArray = string.split(parmStr, Delim)
        wsCleanArray = []
        for wsThis in wsArray:
            wsCleanArray.append(string.strip(wsThis))
        return wsCleanArray
    return []

#
# Parse a comma delimited string into a array of items.  If RecognizeArrays
# is true, a value delimited with [] is itself interpreted as a list.
# The [list] will generally contain comma separators so it must be
# string quoted like "[a, b, c]".  In order for this to be reentrant
# with simple parsing, the outer brackets must be stripped before calling
# this function.  In addition, any inner arrays with more than one item
# (and therefore with commas) are not string quoted. "[[a, b], [c, d]]"
# but an Escape character must be specified to allow use of brackets
# in field values.
#
# If GetNextLine is supplied, wsLine and wsLineLen can be changed
# within loop.
#


def CommaStrToList(wsLine,
                   Escape=None, Delim=",",
                   getKeywords=None, RecognizeArrays=None,
                   ColonArray=None, ColonArrayLen=0,
                   GetNextLine=None, StripAll=False):
    if not wsLine:
        return []
    if ColonArrayLen > 0:
        ColonArray = True
    wsParse = bzLineParse(Escape=Escape,
                          getKeywords=getKeywords,
                          RecognizeArrays=RecognizeArrays,
                          StripAll=StripAll)
    if isinstance(wsLine, str):
        wsParse.ascii = False
    wsLineLen = utils.GetLineLen(wsLine)
    wsIx = 0
    wsState = 0
    while wsIx < wsLineLen:
        #print "%d %3d %s" % (wsState, wsIx, wsLine)
        wsC = wsLine[wsIx]
        if wsState == 0:			# collect field chars
            if wsC == Delim:
                wsParse.AppendField()
            elif (wsC in "'\"") and (wsParse.curField == ""):
                # Only 1st char triggers quoting.  In any other
                # position it is just a character.
                wsParse.quoteChar = wsC
                wsState = 1
            elif (wsC == "[") and (wsParse.curField == ""):
                wsEndPos = 0
                wsNextIx = wsIx + 1
                wsLevel = 0
                while (wsNextIx < wsLineLen) and (wsEndPos == 0):
                    wsB = wsLine[wsNextIx]
                    if wsB == "[":
                        wsLevel += 1
                    if wsB == "]":
                        if wsLevel == 0:
                            wsEndPos = wsNextIx
                        else:
                            wsLevel -= 1
                    wsNextIx += 1
                #print "line " + wsLine
                #print "array %d %d" % (wsIx, wsEndPos)
                if wsEndPos > 0:
                    wsParse.curField = wsLine[wsIx:wsEndPos + 1]
                    wsState = 0
                    wsIx = wsEndPos
            elif (wsC == "=") and getKeywords \
                    and (wsParse.curField != "") \
                    and (wsParse.keyName == ""):
                wsParse.keyName = wsParse.curField
                wsParse.curField = ""
            elif (wsC in " \t") and (wsParse.curField == ""):
                pass		# skip leading spaces
            else:
                wsParse.curField += wsC
        elif wsState == 1:			# collect quoted field
            if wsC == wsParse.quoteChar:  # check if next character is also quote
                if ((wsIx + 1) < wsLineLen) \
                        and (wsLine[wsIx + 1] == wsParse.quoteChar):
                    # treat double quote as literal quote
                    wsIx += 1
                    wsParse.curField += wsParse.quoteChar
                else:
                    wsState = 0			# single quote, this is end of string
            elif (wsC == Escape) and ((wsIx + 1) < wsLineLen):  # handle escape characters
                wsIx += 1
                wsC = wsLine[wsIx]
                wsParse.curField += wsC
            else:
                wsParse.curField += wsC			# just a normal character within quote
            if (wsIx + 1) >= wsLineLen:			# check if this is last character
                if GetNextLine is not None:
                    wsNextLine = GetNextLine()		# EOL is allowed within string, get continuation
                    if wsNextLine is not None:
                        # there is another line, treat as continuation
                        wsParse.curField += '\n'
                        wsLine = wsNextLine
                        wsLineLen = utils.GetLineLen(wsLine)
                        wsIx = -1
        wsIx += 1
    #
    # Line Processed
    #
    wsParse.AppendField()			# save last field
    if getKeywords:
        return (wsParse.fields, wsParse.keywords)
    else:
        if ColonArray:
            for wsIx in range(0, len(wsParse.fields)):
                wsParse.fields[wsIx] = ParseColonArray(
                    wsParse.fields[wsIx], ColonArrayLen=ColonArrayLen)
        return wsParse.fields


def MultiLineCommaColonStrToList(parmString):
    if not parmString:
        return []
    if not isinstance(parmString, type("")):
        return []
    wsResult = []
    wsLines = parmString.split(chr(13) + chr(10))
    for wsThisLine in wsLines:
        wsElements = wsThisLine.split(',')
        wsFinishedLine = []
        for wsThisElement in wsElements:
            wsParameters = wsThisElement.split(':')
            wsFinishedElement = []
            for wsThisParameter in wsParameters:
                wsFinishedElement.append(utils.Strip(wsThisParameter))
            wsFinishedLine.append(wsFinishedElement)
        wsResult.append(wsFinishedLine)
    return wsResult


def CommaColonStrToList(parmLine):
    if not parmLine:
        return []
    wsPos = parmLine.find(",")
    if wsPos < 0:
        # Newline delimited
        wsArray = CommaStrToList(parmLine, Delim=chr(13))
    else:
        # Comma delimited
        wsArray = CommaStrToList(parmLine)
    wsIx = 0
    for wsThisLine in wsArray:
        # Filter text mainly to elimilate formattin CR/LF
        wsThisLine = utils.FilterText(wsThisLine)
        wsThisArray = CommaStrToList(wsThisLine, Delim=":")
        wsArray[wsIx] = wsThisArray
        wsIx += 1
    return wsArray


if __name__ == "__main__":
    wsStrA = 'A, [], b'
    wsStrA = 'A, "[[1215, 1], [1413, 2]]", b'
    wsLstA = CommaStrToList(wsStrA, RecognizeArrays=True)
    wsStrB = ListToCommaStr(wsLstA)
    wsLstB = CommaStrToList(wsStrB, RecognizeArrays=True)
    print("StrA    ==> " + repr(wsStrA) + " <==")
    print("LstA    ==> " + repr(wsLstA) + " <==")
    print("StrB    ==> " + repr(wsStrB) + " <==")
    print("LstB    ==> " + repr(wsLstB) + " <==")
    sys.exit(0)

    wsList1 = ["simple", "com,ma", '"leading quote', 'internal"quote',
               'double,""Escape', "Escape,\Escape"]
    wsCma = ListToCommaStr(wsList1)
    wsList2 = CommaStrToList(wsCma)
    print("List1 ==> " + repr(wsList1) + " <==")
    print("Str   ==> " + repr(wsCma) + " <==")
    print("List2 ==> " + repr(wsList2) + " <==")
    print()
    wsListList1 = [['a', 1], ['b', 2]]
    wsListCma = ListToCommaStr(wsListList1)
    wsListList2 = CommaStrToList(wsListCma, RecognizeArrays=True)
    print("ListList1 ==> " + repr(wsListList1) + " <==")
    print("Str       ==> " + repr(wsListCma) + " <==")
    print("ListList2 ==> " + repr(wsListList2) + " <==")
