#############################################
#
#  bzUtil Module
#
#
#  FEATURES
#
#  iif(parmExpr, parmTrueValue, parmFalseValue):
#
#
#  WARNINGS
#
#
#  Copyright (C) 2001 by Albert B. Margolis - All Rights Reserved
#
#  2/11/2001:  Initial Release function iif()
#  2/12/2001:  Add True, False, IsDigit(), IsLetter(), IsWhiteSpace()
#  2/15/2001:  Add GetLineLen()
#  2/28/2001:  Add CommaStrToList(), bzLineParse, ListToCommaStr()
# 		broken out from bzTextFile.readcma() and bzMySql
#  3/ 2/2001:  Add DateYmdToDisp(), DispToDateYmd(), Fill(), Repl()
#  3/ 3/2001:  Add GetEnv()
#  4/22/2001:  Fix GetLineLen() to handle empty line
#  5/05/2001:  Add ChangeFileNameExtension(), BinToString(),
# 		NibbleToHex() and ByteToHex()
#  5/13/2001:  Add GetFileNameExtension()
#  8/11/2001:  Add EOL and StripEOL(), change GetLineLen() to use EOL
#  8/18/2001:  Add FilterText()
#  8/08/2001:  Add GetFileName()
#  9/16/2001:  Add HexToByte() and HexToNibble()
# 11/21/2001:  Add AsBool()
# 11/28/2001:  Add StripQuotes()
# 01/02/2002:  Add DumpFormat()
# 01/26/2002:  Add GetFilePath()
# 01/27/2002:  Add CalcCRC() and DumpRaw()
# 12/20/2002:  Add Filter(), NUMBERS, LETTERS, UPPCASELETTERS,
# 		LOWERCASELETTERS, Strip()
# 12/22/2002:  Add Int() and IsDigits()
#  1/ 8/2003:  Add getKewords to CommaStrToList()
#  2/ 9/2003:  Add GetRandom()
#  2/14/2003:  Add TodayYMD()
#  2/15/2003:  Add DaysFromYMD(), CheckDigit()
#  2/16/2003:  Add DateToYMD(), DateToYMDHMS()
#  2/22/2003:  Add ParseFileName()
#  3/22/2003:  Add ListStripTrailingBlanks()
#  4/05/2003:  Modify ListToCommaStr() to strip trailing "L" from long ints
# 			and substitute "" for None
#  4/15/2003:  Add BoolAsStr(), AsInt(), AsArray()
#  4/18/2003:  Add QuoteStr() and AsStr() by pulling from ListToCommaStr()
#  8/18/2003:  Add HexToInt()
#  8/26/2003:  Add WrapText()
#  8/30/2003:  Modify ListToCommaStr() to filter non-text characters.
# 		<CR> in string would cause file reading to fail.
# 		Modify FilterText() to handle null and non-string input.
# 		Add fldSkipMap to ListToCommaStr().
#  9/09/2003:  Add GetArrayFieldAsInt(), GetArrayFieldAsStr()
#  9/26/2003:  Fix GetArrayFieldAsStr() to return "" for errors instead
# 		of 0.  Fix AsInt() to use Int() for consistency.
# 		Add DictLookup() and DictLookupAsStr().
# 		Add PutArrayField()
# 10/24/2003:  Add GetArrayFieldAsBool(), modify AsBool() to recognize
# 		"1" as true in case a boolean gets written as an integer
# 11/17/2003:  Add Upper() to be null and type safe.
# 12/15/2003:  Add PRINTABLE
# 12/20/2003:  Add NowYMDHM()
# 03/21/2004:  Add DIGITNAMES and NumberToText()
# 03/23/2004:  Modify CommaStrToList() to support lists of lists
# 05/02/2004:  Modify CommaStrToList() to support other delimiters
# 05/12/2004:  Modify CommaStrToList() to support prevent quoting
# 		of tab delimited data.
# 09/25/2004:  Add CommaColonStrToList()
# 03/18/2006:  Add FilterMultiLineText(), CheckBankNumber()
# 09/09/2009:  Add AppendDirectoryPath(), AppendDirectorySlash()
# 05/25/2014:  Add Codex()
# 06/07/2014:  Add IsSubclass()
#
#############################################

import os
import random
import sys
import time

#
# DON'T IMPORT ANY BZ MODULES, they all import bzUtil.py
#

#
# Use True & False for assignment only.  Neither is a safe value for
# comparison.
#
TrueSTRINGS = "TtYy1"
FalseSTRINGS = "FfNn0"
EOL = "\n"
SINGLEQUOTE = "'"
DOUBLEQUOTE = '"'
WHITESPACE = " \t"
NUMBERS = "0123456789"
LOWERCASELETTERS = "abcdefghijklmnopqrstuvwxyz"
UPPERCASELETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LETTERS = LOWERCASELETTERS + UPPERCASELETTERS
LETTERSANDNUMBERS = LETTERS + NUMBERS
PRINTABLE = LETTERS + NUMBERS + r" `~!@#$%^&*()_+[{]}\|;:,<.>/?" + '"' + "'"
PRINTABLE_HTML = LETTERS + NUMBERS + r" `~!@#$%^*()_+[{]}\|;:,./?" + '"' + "'"
DIGITNAMES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
MONTHNAMES3 = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]


def MakeBankCheckDigit(parmAcctNum):
    if type(parmAcctNum) in [type(0), type(0)]:
        wsAcctNum = Str(parmAcctNum)
    else:
        wsAcctNum = parmAcctNum
    wsLookup = [0, 2, 4, 6, 8, 1, 3, 5, 7, 9]
    if (len(wsAcctNum) % 2) == 1:
        wsOdd = True
    else:
        wsOdd = False
    wsSum = 0
    for wsDigitChar in wsAcctNum:
        wsDigitNum = ord(wsDigitChar) - ord("0")
        if (wsDigitNum < 0) or (wsDigitNum > 9):
            return False
        if wsOdd:
            wsSum += wsLookup[wsDigitNum]
            wsOdd = False
        else:
            wsSum += wsDigitNum
            wsOdd = True
    wsTest = 10 - (wsSum % 10)
    if wsTest == 10:
        wsTest = 0
    wsTest = repr(wsTest)
    return wsTest


def CheckBankNumber(parmAcct):
    wsAcctNum = parmAcct[0:-1]
    wsAcctChk = parmAcct[-1:]
    wsTest = MakeBankCheckDigit(wsAcctNum)
    # print "%15s %s %s" % (wsAcctNum, wsAcctChk, wsTest)
    if wsTest != wsAcctChk:
        return False
    return True


def iif(parmExpr, parmTrueValue, parmFalseValue):
    if parmExpr:
        return parmTrueValue
    else:
        return parmFalseValue


def IsBool(parmData):
    if isinstance(parmData, type("")):
        parmData = Strip(parmData)
        if len(parmData) > 0:
            wsC = parmData[:1]
            if wsC in TrueSTRINGS:
                return True
            if wsC in FalseSTRINGS:
                return True
    return False


def IsDigit(parmC):
    if (parmC >= "0") and (parmC <= "9"):
        return True
    return False


def IsDigits(parmC):
    if isinstance(parmC, type(0)):
        return True
    if isinstance(parmC, type(0)):
        return True
    if not isinstance(parmC, str):
        return False
    for wsC in parmC:
        if not ((wsC >= "0") and (wsC <= "9")):
            return False
    return True


def IsNumber(parmStr):
    if isinstance(parmStr, int):
        return True
    if not isinstance(parmStr, str):
        return False
    if parmStr[0] in "+-":
        parmStr = parmStr[1:]
    wsPos = parmStr.find(".")
    if wsPos < 0:
        return IsDigits(parmStr)
    if not IsDigits(parmStr[:wsPos]):
        return False
    return IsDigits(parmStr[wsPos + 1 :])


def IsLetter(parmC):
    if (parmC >= "A") and (parmC <= "Z"):
        return True
    if (parmC >= "a") and (parmC <= "z"):
        return True
    return False


def IsLetters(parmStr):
    for wsC in parmStr:
        if wsC not in LETTERS:
            return False
    return True


def IsWhiteSpace(parmC):
    if (parmC == " ") or (parmC == "\t"):
        return True
    return False


def FindFirstWhiteSpace(parmStr, Whitespace=WHITESPACE, StartPos=0):
    for wsIx, wsC in enumerate(parmStr[StartPos:]):
        if wsC in Whitespace:
            return wsIx + StartPos  # return index within original string
    return -1


def FindFirstNonWhiteSpace(parmStr, Whitespace=WHITESPACE, StartPos=0):
    for wsIx, wsC in enumerate(parmStr[StartPos:]):
        if wsC not in Whitespace:
            return wsIx + StartPos
    return -1


def FindFirstUpperCaseLetter(parmStr, StartPos=0):
    return FindFirstWhiteSpace(parmStr, Whitespace=UPPERCASELETTERS, StartPos=0)


def FindFirstNonLetter(parmStr, StartPos=0):
    wsStr = parmStr.upper()
    return FindFirstNonWhiteSpace(wsStr, Whitespace=UPPERCASELETTERS, StartPos=0)


def FindFirstNumber(parmStr, StartPos=0):
    wsStr = parmStr.upper()
    return FindFirstWhiteSpace(wsStr, Whitespace=NUMBERS, StartPos=0)


def FindRemainder(parmStr, parmStart):
    if not isinstance(parmStr, str):
        return None
    wsLen = len(parmStart)
    if parmStr[:wsLen] != parmStart:
        return None
    wsRemainder = parmStr[wsLen:]
    return wsRemainder


def FindBetween(parmStr, parmStart, parmEnd):
    # Get the part of a string between two substrings.
    # Excluding the start / end strings
    if not isinstance(parmStr, str):
        return None
    wsPos = parmStr.find(parmStart)
    if wsPos < 0:
        return ""
    wsRemainder = parmStr[wsPos + len(parmStart) :]
    wsPos = wsRemainder.find(parmEnd)
    if wsPos < 0:
        return ""
    wsRemainder = wsRemainder[:wsPos]
    return wsRemainder.strip()


def Match(str, target, start=0):
    target_len = len(target)
    if str[start : start + target_len] == target:
        return target_len
    else:
        return -1


def UnQuote(parmStr):
    wsClean = Strip(parmStr)
    if wsClean[0] in ['"', "'"]:
        if wsClean[-1] == wsClean[0]:
            return wsClean[1:-1]
    return wsClean


def NumberToText(parmNumber):
    parmNumber = Int(parmNumber)
    wsSign = ""
    if parmNumber < 0:
        parmNumber = -parmNumber
        wsSign = "negative "
    if parmNumber < 20:
        return wsSign + DIGITNAMES[parmNumber]
    return "****"


def ReportTypeError(parmMessage, parmErrs, SilentErrors=False):
    if SilentErrors:
        return
    if parmErrs is None:
        raise TypeError(parmMessage)
    else:
        parmErrs.AddUserCriticalMessage(parmMessage)


def NumericToInt(
    parmN,
    ImpliedDecimals=0,
    UnitsOfMeasure=None,
    RoundExtraDigits=False,
    Errs=None,
    SilentErrors=False,
):
    if isinstance(parmN, int):
        return parmN
    if isinstance(parmN, int):
        return parmN
    if (parmN == "") or (parmN is None):
        return 0
    wsStr = parmN
    if UnitsOfMeasure is None:
        pass
    elif UnitsOfMeasure == "USD":
        if parmN[0] == "$":
            wsStr = wsStr[1:]
        elif parmN[:4] == "USD$":
            wsStr = wsStr[4:]
    else:
        ReportTypeError(
            "Unknown Units of Measure '{UOM} for value '{Parm}'.".format(
                UOM=UnitsOfMeasure, Parm=parmN
            ),
            Errs,
            SilentErros=SilentErrors,
        )
        return None
    wsStr = wsStr.strip()
    wsParts = wsStr.split(".")
    if ((ImpliedDecimals == 0) and (len(wsParts) > 1)) or (len(wsParts) > 2):
        ReportTypeError(
            "Extra decimal point for value '{Parm}'.".format(Parm=parmN),
            Errs,
            SilentErrors=SilentErrors,
        )
        return None
    #
    wsDecimalStr = ""
    wsRoundValue = 0
    if ImpliedDecimals > 0:
        if len(wsParts) > 1:
            wsDecimalStr = wsParts[1]
            if not wsDecimalStr.isdigit():
                ReportTypeError(
                    "Invalid decimal character for value '{Parm}'.".format(Parm=parmN),
                    Errs,
                    SilentErrors=SilentErrors,
                )
                return None
            if len(wsDecimalStr) > ImpliedDecimals:
                wsExtraDecimals = wsDecimalStr[ImpliedDecimals:]
                if int(wsExtraDecimals) > 0:
                    # we only care about extra decimals if non-zero
                    if RoundExtraDigits:
                        wsRoundValue = int(wsExtraDecimals[0])
                    else:
                        ReportTypeError(
                            "Extra decimal digits for value '{Parm}, only {DigitCt} allowed'.".format(
                                Parm=parmN, DigitCt=ImpliedDecimals
                            ),
                            Errs,
                            SilentErrors=SilentErrors,
                        )
                        return None
        wsDecimalStr = Pad(wsDecimalStr, ImpliedDecimals, "0")
    #
    wsIntegerStr = ""
    if wsParts is not None:
        wsIntegerStr = wsParts[0]
    if wsIntegerStr == "":
        # this happens for values like ".00"
        wsIntegerStr = "0"
    wsNegativeValue = False
    if wsIntegerStr[0] in "-+":
        if wsIntegerStr[0] == "-":
            wsNegativeValue = True
        wsIntegerStr = wsIntegerStr[1:]
    if len(wsIntegerStr) > 8:
        if wsIntegerStr[-8] == ",":
            wsIntegerStr = wsIntegerStr[:-8] + wsIntegerStr[-7:]
    if len(wsIntegerStr) > 4:
        if wsIntegerStr[-4] == ",":
            wsIntegerStr = wsIntegerStr[:-4] + wsIntegerStr[-3:]

    if not wsIntegerStr.isdigit():
        ReportTypeError(
            "Invalid integer character for value '{Parm}'.".format(Parm=parmN),
            Errs,
            SilentErrors=SilentErrors,
        )
        return None
    wsValue = int(wsIntegerStr + wsDecimalStr)
    if wsRoundValue > 5:
        wsValue += 1
    elif wsRoundValue == 5:
        # Banker's Rounding and IEEE 754 default rounding.
        # Round to nearest even number.
        if (wsValue % 2) == 1:
            wsValue += 1
    if wsNegativeValue:
        return -wsValue
    else:
        return wsValue


def Int(parmI):
    if parmI is None:
        return 0
    if isinstance(parmI, type(0)):
        return parmI
    if isinstance(parmI, type(0)):
        return parmI
    if not isinstance(parmI, str):
        return 0
    if parmI == "":
        return 0
    if not IsDigits(parmI):
        return 0
    return int(parmI)


def Str(parmData):
    if isinstance(parmData, int):
        parmData = repr(parmData)
        if parmData[-1:] == "L":
            parmData = parmData[:-1]
        if parmData == "":
            parmData = "0"
    elif not parmData:
        parmData = ""
    elif not isinstance(parmData, str):
        parmData = repr(parmData)
    return parmData


def Bool(parmData):
    if isinstance(parmData, str):
        # If a string, the first character determines true / false
        parmData = Strip(parmData)
        if len(parmData) > 0:
            wsC = parmData[:1]
            if wsC in TrueSTRINGS:
                return True
    else:
        # not a string, use Python truthe logic
        if parmData:
            return True
    return False


def Codex(parmOriginalCode):
    wsNewCode = ""
    wsIsDigits = False
    parmOriginalCode = Upper(parmOriginalCode)
    wsPrevC = ""
    wsPrevCCt = 0
    for wsC in parmOriginalCode:
        if wsC == " ":
            continue  # ignore all spaces
        if wsC == "O":
            wsC = "0"
        elif wsC == "I":
            wsC = "1"
        elif wsC == "L":
            wsC = "1"
        if (wsC == "0") and (not wsIsDigits):
            continue  # ignore leading zero of any number sequence
        if wsC in NUMBERS:
            wsIsDigits = True
        else:
            wsIsDigits = False  # stop, even for decimal point
        if wsC == wsPrevC:
            wsPrevCCt += 1
            if wsPrevCCt >= 2:
                continue  # allow only two consecutive of same character
            else:
                wsNewCode += wsC
        else:
            wsNewCode += wsC
            wsPrevC = wsC
            wsPrevCCt = 0
    wsNewCode = Filter(wsNewCode, LETTERSANDNUMBERS)
    return wsNewCode


def IsSubclass(parmClass, parmTestClass):
    wsTestElements = parmTestClass.__module__.split(".")
    try:
        wsBaseClasses = parmClass.__bases__
    except BaseException:
        return False
    for wsThisBaseClass in wsBaseClasses:
        if wsThisBaseClass.__name__ != parmTestClass.__name__:
            continue
        wsModuleNameElements = wsThisBaseClass.__module__.split(".")
        if wsModuleNameElements[-1] != wsTestElements[-1]:
            continue
        if wsModuleNameElements[-2] == wsTestElements[-2]:
            return True
    return False


def DumpRaw(parmData):
    wsText = ""
    wsHex = ""
    wsHasHex = False
    for wsC in parmData:
        if (wsC < " ") or (wsC >= chr(127)):
            wsText += " "
            wsHasHex = True
        else:
            wsText += wsC
        wsHex += ByteToHex(wsC)
    return (wsText, wsHex, wsHasHex)


def Cmp(parm1, parm2):
    if IsDigits(parm1):
        ws1IsDigits = True
    else:
        ws1IsDigits = False
    if IsDigits(parm2):
        ws2IsDigits = True
    else:
        ws2IsDigits = False
    if ws1IsDigits and ws2IsDigits:
        parm1 = Int(parm1)
        parm2 = Int(parm2)
        return cmp(parm1, parm2)
    if not isinstance(parm1, type("")):
        parm1 = Str(parm1)
    if not isinstance(parm2, type("")):
        parm2 = Str(parm2)
    return cmp(parm1, parm2)


def DumpFormat(parmData, Unfold=None, oStripEOL=None, oEOL=EOL):
    if oStripEOL:
        parmData = StripEOL(parmData, oEOL)
    (wsText, wsHex, wsHasHex) = DumpRaw(parmData)
    if not Unfold:
        wsHasHex = True
    if wsHasHex:
        wsText += "  " + wsHex
    return wsText


def AsInt(parmData):
    return Int(parmData)


def AsBool(parmData):
    return Bool(parmData)


def BoolAsStr(parmData):
    if Bool(parmData):
        return "Y"
    return "N"


UomStandardUnits = {"mm": "m", "in": "m"}

UomConversion = {"mm:m": 0.001, "m:in": 39.3701, "in:m": 0.0254}


def ConvertStep(parmValue, parmSourceUom, parmTargetUom):
    wsKey = parmSourceUom + ":" + parmTargetUom
    wsScale = UomConversion[wsKey]
    return parmValue * wsScale


def ConvertUnitsStr(parmStr, parmNewUnits, Decimals=2, IncludeUnits=True):
    wsDigitsFound = False
    for wsIx, wsC in enumerate(reversed(parmStr)):
        if wsC.isdigit():
            wsDigitsFound = True
            break
    if not wsDigitsFound:
        return None
    wsValue = parmStr[:-wsIx].strip()
    wsUnits = parmStr[-wsIx:].strip()
    if wsUnits not in UomStandardUnits:
        return None
    if wsValue == "":
        return None
    wsValue = float(wsValue)
    wsStandardUnits = UomStandardUnits[wsUnits]
    wsStandardValue = ConvertStep(wsValue, wsUnits, wsStandardUnits)
    wsConvertedValue = ConvertStep(wsStandardValue, wsStandardUnits, parmNewUnits)
    wsFormattingStr = "{{Val:.{Digits}f}}".format(Digits=Decimals)
    wsConvertedStr = wsFormattingStr.format(Val=wsConvertedValue)
    if IncludeUnits:
        wsConvertedStr += parmNewUnits
    return wsConvertedStr


def WeightStrAsTInt(parmStr, Grams=False):
    wsP = parmStr.find("#")
    if wsP >= 0:
        wsPounds = parmStr[:wsP]
        wsOunces = parmStr[wsP + 1 :]
    else:
        wsPounds = 0
        wsOunces = parmStr
    if wsOunces[-2:] == "oz":
        wsOunces = wsOunces[:-2]
    if wsPounds == "":
        wsPounds = 0.0
    if wsOunces == "":
        wsOunces = 0.0
    if Grams:
        return PoundsAndOuncesAsTGrams(wsPounds, wsOunces)
    else:
        return PoundsAndOuncesAsTOunces(wsPounds, wsOunces)


def PoundsAndOuncesAsTGrams(parmPounds, parmOunces):
    wsOunces = (float(parmPounds) * 16.0) + float(parmOunces)
    wsGrams = wsOunces * 28.3495
    return int(wsGrams * 10.0)


def PoundsAndOuncesAsTOunces(parmPounds, parmOunces):
    wsOunces = (float(parmPounds) * 16.0) + float(parmOunces)
    return int(wsOunces * 10.0)


def AsStr(parmData):
    return Str(parmData)


def DictLookup(parmDict, parmKey):
    if not isinstance(parmDict, type({})):
        return None
    if parmKey in parmDict:
        return parmDict[parmKey]
    else:
        return None


def DictLookupAsStr(parmDict, parmKey):
    return AsStr(DictLookup(parmDict, parmKey))


def PutArrayField(parmArray, parmIx, parmValue):
    if not isinstance(parmArray, type([])):
        return None
    while len(parmArray) <= parmIx:
        parmArray.append(None)
    parmArray[parmIx] = parmValue
    return True


def GetArrayFieldAsInt(parmArray, parmIx):
    if (not isinstance(parmArray, type([]))) and (not isinstance(parmArray, type(()))):
        return 0
    if parmIx >= len(parmArray):
        return 0
    return AsInt(parmArray[parmIx])


def GetArrayFieldAsStr(parmArray, parmIx):
    if (not isinstance(parmArray, type([]))) and (not isinstance(parmArray, type(()))):
        return ""
    if parmIx >= len(parmArray):
        return ""
    return Strip(AsStr(parmArray[parmIx]))


def GetArrayFieldAsBool(parmArray, parmIx):
    if (not isinstance(parmArray, type([]))) and (not isinstance(parmArray, type(()))):
        return False
    if parmIx >= len(parmArray):
        return False
    return AsBool(parmArray[parmIx])


def Repl(parmChar, parmSize):
    wsText = ""
    if parmSize > 0:
        for x in range(parmSize):
            wsText += parmChar
    return wsText


def SubstChars(parmText, parmTarget, parmReplacement):
    parmText = Str(parmText)
    wsText = ""
    for wsC in parmText:
        wsIx = parmTarget.find(wsC)
        if wsIx >= 0:
            if wsIx <= len(parmReplacement):
                wsText += parmReplacement[wsIx]
            else:
                wsText += parmReplacement[-1]
        else:
            wsText += wsC
    return wsText


def NibbleToHex(parmNibble):
    wsDigits = "0123456789abcdef"
    try:
        wsNibble = wsDigits[parmNibble]
    except BaseException:
        wsNibble = "0"
    # print `parmNibble` + "--" + wsNibble
    return wsNibble


def ByteToHex(parmByte):
    if isinstance(parmByte, type("")):
        parmByte = ord(parmByte)
    parmByte = parmByte & 0xFF
    wsHex = NibbleToHex(parmByte >> 4) + NibbleToHex(parmByte & 0xF)
    # print `parmByte` + "--" + wsHex
    return wsHex


def BinToString(parmBin):
    wsString = ""
    for wsC in parmBin:
        if wsC == "\\":
            wsC += "\\\\"
        elif (wsC >= " ") and (wsC <= chr(126)):
            wsString += wsC
        else:
            wsString += "\\x" + ByteToHex(wsC)
    return wsString


def HexToNibble(parmString):
    wsC = parmString[0]
    if (wsC >= "0") and (wsC <= "9"):
        return ord(wsC) - ord("0")
    else:
        wsC = wsC.upper()
        if (wsC >= "A") and (wsC <= "F"):
            return ord(wsC) - ord("A") + 10
        else:
            return 0


def HexToUnicode(parmString):
    wsInt = HexToInt(parmString, MaxLen=2)
    return chr(wsInt)


def HexToChr(parmString):
    wsInt = HexToInt(parmString, MaxLen=2)
    return chr(wsInt)


def HexToInt(parmString, MaxLen=None):
    wsInt = 0
    wsLen = len(parmString)
    if MaxLen is not None:
        if wsLen > MaxLen:
            wsLen = MaxLen
    wsIx = 0
    while wsIx < wsLen:
        wsN = HexToNibble(parmString[wsIx])
        wsInt = (wsInt << 4) + wsN
        wsIx += 1
    return wsInt


def Len(parmObject):
    try:
        return len(parmObject)
    except BaseException:
        return 0


def Strip(parmText):
    parmText = Str(parmText)
    return parmText.strip()


#
# Lower() and Upper()
#
# Perform lower() and upper() with variation attemp to do so
# on an object that doesn't have the function just leaves the
# object alone. The lower case of an integer is just an integer.
#


def Lower(parmStr):
    try:
        return parmStr.lower()
    except BaseException:
        return parmStr


def Upper(parmStr):
    try:
        return parmStr.upper()
    except BaseException:
        return parmStr


#
# FilterText() - delete non printable ASCII characters from string
# 		with options to eliminate specific printable characters or
# 		keep spcific non-printable characters.
#
# FilterMultiLineText() is FilterText() configured to all CR and LF
#


def FilterText(parmText, parmExcept="", Allow=""):
    if parmText is None:
        return ""
    if isinstance(parmText, str):
        wsResult = ""
    elif isinstance(parmText, str):
        wsResult = ""
    else:
        parmText = str(parmText)
        wsResult = ""
    for wsC in parmText:
        if ((wsC >= " ") and (wsC <= chr(127))) or (wsC in Allow):
            if wsC in parmExcept:
                continue
            wsResult += wsC
    return wsResult


def FilterMultiLineText(parmText, parmExcept=""):
    return FilterText(parmText, parmExcept, Allow=chr(10) + chr(13))


#
# Filter() - delete all but specified characters from string
#


def Filter(parmText, parmAllow):
    if parmText is None:
        return ""
    if isinstance(parmText, str):
        wsResult = ""
    elif isinstance(parmText, str):
        wsResult = ""
    else:
        parmText = str(parmText)
        wsResult = ""
    for wsC in parmText:
        if wsC in parmAllow:
            wsResult += wsC
    return wsResult


def Innercap(parmStr):
    wsStr = Filter(parmStr, LETTERSANDNUMBERS)
    if wsStr == "":
        return ""
    if wsStr[0] not in LETTERS:
        wsStr = "Z" + wsStr
    wsResult = Upper(wsStr[0]) + Lower(wsStr[1:])
    return wsResult


def StrToInnercap(parmStr):
    wsWords = parmStr.split(" ")
    wsResult = ""
    for wsThis in wsWords:
        wsResult += Innercap(wsThis)
    return wsResult


#
# InnercapSplit() Split a string into component words/numbers
#


def InnercapSplit(parmText):
    wsResult = []
    if isinstance(parmText, str):
        wsBlankStr = ""
    else:
        wsBlankStr = ""
    wsThisSymbol = wsBlankStr
    wsLastWasLetter = False
    wsLastWasUpper = False
    wsLastWasNumber = False
    for wsThis in parmText:
        wsIsDelim = False
        wsKeep = True
        if wsThis in LOWERCASELETTERS:
            if not wsLastWasLetter:
                if (wsThis == "d") and (wsThisSymbol in ["2", "3"]):
                    pass  # keep 2d / 3d as idiom
                else:
                    wsIsDelim = True
            wsKeep = True
            wsLastWasLetter = True
            wsLastWasUpper = False
            wsLastWasNumber = False
        elif wsThis in UPPERCASELETTERS:
            if not wsLastWasUpper:  # This is an innercap
                if (wsThis == "D") and (wsThisSymbol in ["2", "3"]):
                    pass  # keep 2D / 3D as idiom
                else:
                    wsIsDelim = True
            wsKeep = True
            wsLastWasLetter = True
            wsLastWasUpper = True
            wsLastWasNumber = False
        elif wsThis in NUMBERS:
            if not wsLastWasNumber:
                wsIsDelim = True
            wsKeep = True
            wsLastWasLetter = False
            wsLastWasUpper = False
            wsLastWasNumber = True
        else:
            # This will be underscore, dash, white space or lots of other
            # things
            wsIsDelim = True
            wsKeep = False
            wsLastWasLetter = False
            wsLastWasUpper = False
            wsLastWasNumber = False
        if wsIsDelim:
            if wsThisSymbol != wsBlankStr:
                wsResult.append(wsThisSymbol)
                wsThisSymbol = wsBlankStr
        if wsKeep:
            wsThisSymbol += wsThis
    #
    if wsThisSymbol != wsBlankStr:
        wsResult.append(wsThisSymbol)
    return wsResult


def SplitLine(parmText, parmMaxLineLen, WhiteSpace=WHITESPACE):
    wsText = Strip(parmText)
    if len(wsText) <= parmMaxLineLen:
        return (wsText, "")
    wsIx = 0
    wsPossibleBreakIx = 0
    while wsIx < len(parmText):
        wsC = parmText[wsIx]
        if wsC in WhiteSpace:
            wsPossibleBreakIx = wsIx
        else:  # this is a content character
            if wsIx > parmMaxLineLen:
                break
        wsIx += 1
    if wsPossibleBreakIx == 0:
        wsPossibleBreakIx = wsIx
    return (parmText[:wsPossibleBreakIx], parmText[wsPossibleBreakIx + 1 :])


def WrapText(parmText, parmColWidth):
    if not isinstance(parmText, type("")):
        parmText = repr(parmText)
    if len(parmText) <= parmColWidth:
        return [parmText]
    wsLines = []
    wsPrevSpacePos = -1
    wsNextSegmentPos = parmColWidth
    while wsPrevSpacePos < len(parmText):
        if wsNextSegmentPos >= len(parmText):
            # This is the last line
            wsNewLine = parmText[wsPrevSpacePos + 1 :]
            wsPrevSpacePos = len(parmText)
        else:
            # need to search for wrap point
            wsSpacePos = parmText.rfind(" ", wsPrevSpacePos + 1, wsNextSegmentPos)
            if wsSpacePos < 0:  # no space, truncate line
                wsNewLine = parmText[wsPrevSpacePos + 1 : wsNextSegmentPos]
                wsPrevSpacePos = wsNextSegmentPos - 1
            else:
                wsNewLine = parmText[wsPrevSpacePos + 1 : wsSpacePos]
                wsPrevSpacePos = wsSpacePos
        wsLines.append(wsNewLine.strip())
        wsNextSegmentPos = wsPrevSpacePos + parmColWidth + 1
    return wsLines


def CheckDigit(parmSrc):
    wsSum = 0
    wsOdd = True
    for wsC in parmSrc:
        wsD = ord(wsC) - ord("0")
        if (wsD < 0) or (wsD > 9):
            return None
        if wsOdd:
            wsSum += 9 - wsD
            wsOdd = False
        else:
            wsSum += wsD
            wsODD = True
    while wsSum > 9:
        wsSumStr = repr(wsSum)
        wsSum = 0
        for wsC in wsSumStr:
            wsD = ord(wsC) - ord("0")
            if (wsD < 0) or (wsD > 9):
                return None
            wsSum += wsD
    return repr(wsSum)


def GetRandom(rlen=15):
    # 15 is the maximum useful rlen due to the matissa of floats
    wsRandom = random.Random()
    wsRandomNo = wsRandom.random() * ((10**rlen) - 1)
    wsStrFormat = "%%0%d.0f" % (rlen)
    return wsStrFormat % (wsRandomNo)


def IsSafeFileName(parmFileName):
    if not parmFileName:
        return False
    if not isinstance(parmFileName, type("")):
        return False
    if parmFileName.find("/") >= 0:
        return False
    if parmFileName.find("\\") >= 0:
        return False
    if parmFileName.find("..") >= 0:
        return False
    return True


def SafeDelete(parmDirectory, parmFileName):
    if not IsSafeFileName(parmFileName):
        return False
    if not parmDirectory:
        return False
    try:
        os.unlink(parmDirectory + parmFileName)
    except BaseException:
        return False
    return True


def MoveFile(parmSrcFileName, parmDstFileName):
    try:
        wsSrcStat = os.stat(parmSrcFileName)
    except BaseException:
        return False
    try:
        wsDstStat = os.stat(parmDstFileName)
        return False
    except BaseException:
        pass
    wsSrc = open(parmSrcFileName, "r")
    if not wsSrc:
        return None
    wsContent = wsSrc.read()
    try:
        wsDst = open(parmDstFileName, "w")
    except BaseException:
        return False
    if not wsDst:
        return False
    wsLen = wsDst.write(wsContent)
    wsDst.close()
    wsSrc.close()
    wsDstStat = os.stat(parmDstFileName)
    if wsSrcStat.st_size != wsDstStat.st_size:
        return False
    os.unlink(parmSrcFileName)
    return True


def ChangeFileNameExtension(parmFileName, parmNewExtension):
    if not parmFileName:
        return None
    if parmNewExtension:
        if parmNewExtension[0] != ".":
            parmNewExtension = "." + parmNewExtension
    else:
        parmNewExtension = ""

    # This assembles the new file name+ext for any combination
    # existing and new extensions, incuding either being blank.
    parmFilename = os.path.splitext(parmFileName)[0]
    return parmFileName + parmNewExtension


FNPROTOCOL = 0
FNSERVER = 1
FNROOT = 2
FNPATH = 3
FNFILENAME = 4
FNLOCNAME = 5
FNPARMS = 6


def ParseFileName(parmPath):  # also works for URLs
    # returns (type, server, root, path, file, parms)
    # protocol like http: or blank
    # server like //www.hobbyengineering.com
    # root like /		(leading slash if any -- either a blank or a slash)
    # path like html	(no leading or trailing slash)
    # file name like index.html	(no leading or trailing slash)
    # parms like x=3434&y=56768
    if not parmPath:
        parmPath = ""
    wsQuestion = parmPath.find("?")
    if wsQuestion < 0:
        wsParms = ""
    else:
        wsParms = parmPath[wsQuestion + 1 :]
        parmPath = parmPath[:wsQuestion]
    #
    wsPound = parmPath.find("#")
    if wsPound < 0:
        wsLocName = ""
    else:
        wsLocName = parmPath[wsPound + 1 :]
        parmPath = parmPath[:wsPound]
    #
    wsColon = parmPath.find(":")
    if wsColon < 0:
        wsProtocol = ""
    else:
        wsProtocol = parmPath[: wsColon + 1]
        parmPath = parmPath[wsColon + 1 :]
    if parmPath[0:2] == "//":
        wsSlash = parmPath.find("/", 2)
        if wsSlash < 0:
            wsSlash = len(parmPath)
        wsServer = parmPath[:wsSlash]
        parmPath = parmPath[wsSlash:]
    else:
        wsServer = ""
    if parmPath and (parmPath[0] == "/"):
        wsRoot = "/"
        parmPath = parmPath[1:]
    else:
        wsRoot = ""
    wsPath = ""
    wsFileName = ""
    if parmPath:
        if parmPath[-1:] == "/":
            wsPath = parmPath[:-1]
        else:
            # if no trailing slash, have to guess if last part file or
            # directory
            wsSlash = parmPath.rfind("/")
            if wsSlash >= 0:
                wsPath = parmPath[:wsSlash]
                wsFileName = parmPath[wsSlash + 1 :]
            else:
                # assume last part is a file
                wsFileName = parmPath
    return [wsProtocol, wsServer, wsRoot, wsPath, wsFileName, wsLocName, wsParms]


def MergeFileNameParse(parmParse, parmDefault):
    wsProtocol = parmParse[FNPROTOCOL]
    wsServer = parmParse[FNSERVER]
    wsRoot = parmParse[FNROOT]
    wsPath = parmParse[FNPATH]
    wsFileName = parmParse[FNFILENAME]
    wsLocName = parmParse[FNLOCNAME]
    wsParms = parmParse[FNPARMS]

    if wsProtocol == "":
        wsProtocol = parmDefault[FNPROTOCOL]
    if wsServer == "":
        wsServer = parmDefault[FNSERVER]
    if wsRoot == "":
        wsRoot = parmDefault[FNROOT]
    if wsPath == "":
        wsPath = parmDefault[FNPATH]
    # This function fills in the default path, not the reference
    # wsFileName, wsParms and wsLocName aren't filled in
    return [wsProtocol, wsServer, wsRoot, wsPath, wsFileName, wsLocName, wsParms]


def ComposeUrl(parmParse, parmDefault=None):
    if isinstance(parmParse, str):
        wsParsedTarget = ParseFileName(parmParse)
    else:
        wsParsedTarget = parmParse
    if parmDefault is not None:
        if isinstance(parmDefault, str):
            wsDefaults = ParseFileName(parmDefault)
        else:
            wsDefaults = parmDefault
        wsParsedTarget = MergeFileNameParse(wsParsedTarget, wsDefaults)
    wsComposedName = (
        wsParsedTarget[FNPROTOCOL] + wsParsedTarget[FNSERVER] + wsParsedTarget[FNROOT]
    )
    if wsParsedTarget[FNPATH] is not None:
        wsComposedName += wsParsedTarget[FNPATH] + "/"
    wsComposedName += wsParsedTarget[FNFILENAME]
    return wsComposedName


def ComposeFileName(wsParsedTarget, parmDefault=None):
    if parmDefault:
        parmParse = MergeFileNameParse(parmParse, parmDefault)
    wsComposedName = parmParse[FNPROTOCOL] + parmParse[FNSERVER] + parmParse[FNROOT]
    if parmParse[FNPATH]:
        wsComposedName += parmParse[FNPATH] + "/"
    wsComposedName += parmParse[FNFILENAME]
    if parmParse[FNLOCNAME]:
        wsComposeName += "#" + parmParse[FNLOCNAME]
    if parmParse[FNPARMS]:
        wsComposeName += "?" + parmParse[FNPARMS]
    return wsComposedName


def GetFileName(parmFilePath):
    wsSlash = parmFilePath.rfind("/")
    if wsSlash < 0:
        return parmFilePath
    return parmFilePath[wsSlash + 1 :]


def BreakFileName(parmFilePath):
    wsNameExt = GetFileName(parmFilePath)
    wsDot = wsNameExt.rfind(".")
    if wsDot < 0:
        return (wsNameExt, "")
    else:
        return (wsNameExt[:wsDot], wsNameExt[wsDot + 1 :])


def GetFileNameExtension(parmFileName):
    wsDot = parmFileName.rfind(".")
    if wsDot < 0:
        return ""
    return parmFileName[wsDot + 1 :]


def GetFilePath(parmFilePath):
    wsSlash = parmFilePath.rfind("/")
    if wsSlash < 0:
        return ""
    return parmFilePath[: wsSlash + 1]


def GetFileDirectory(parmFilePath):
    return GetFilePath(parmFilePath)


def CleanSlashes(parmPath):
    if not isinstance(parmPath, type("")):
        parmPath = ""
    wsNewPath = ""
    if len(parmPath) > 0:
        if parmPath[0] == os.sep:
            wsNewPath = os.sep
    wsSegments = parmPath.split(os.sep)
    for wsThisSegment in wsSegments:
        if wsThisSegment:
            wsNewPath += wsThisSegment + os.sep
    return wsNewPath


def AppendDirectorySlash(parmDirectoryPath):
    if not parmDirectoryPath:
        return "/"
    if parmDirectoryPath[-1] != "/":
        parmDirectoryPath += "/"
    return parmDirectoryPath


def AddAppendDirectoryPath(parmBasePath, parmAppendPath):
    wsPath = AppendDirectorySlash(parmBasepath)
    wsAppendPath = AppendDirectorySlash(parmAppendPath)
    if wsAppendPath[0] == "/":
        wsAppendPath = wsAppendPath[1:]
    return wsPath + wsAppendPath


#
# Fill() - Make string of length parmSize.
# 		Fill leading positions with specified character to achieve length.
# 		Truncate long fields, keeping trailing part.


def Fill(parmText, parmSize, parmFill="0"):
    if parmSize < 1:
        return ""
    if (isinstance(parmText, type(0))) or (isinstance(parmText, type(0))):
        parmText = str(parmText)
    if not isinstance(parmText, str):
        parmText = repr(parmText)
    wsLen = len(parmText)
    if wsLen >= parmSize:
        wsText = parmText[wsLen - parmSize :]
    else:
        wsText = Repl(parmFill, parmSize - len(parmText)) + parmText
    return wsText


#
# Pad() - Make string of length parmSize.
# 		Fill trailing positions with specified character to achieve length.
# 		Truncate long fields, keeping leading part.


def Pad(parmText, parmSize, Fill=" "):
    if parmSize < 1:
        return ""
    if (isinstance(parmText, type(0))) or (isinstance(parmText, type(0))):
        parmText = str(parmText)
    if not isinstance(parmText, str):
        parmText = repr(parmText)
    wsLen = len(parmText)
    if wsLen >= parmSize:
        wsText = parmText[:parmSize]
    else:
        wsText = parmText + Repl(Fill, parmSize - len(parmText))
    return wsText


def DateYmdToDisp(parmDate):
    wsDate = parmDate[4:6] + "/" + parmDate[6:8] + "/" + parmDate[0:4]
    return wsDate


def DateYMDToEpochSeconds(parmDate=None):
    wsDate = None
    if parmDate:
        if isinstance(parmDate, type(0.0)):
            wsDate = parmDate
        elif isinstance(parmDate, type("")):
            wsDateTup = (
                int(parmDate[:4]),
                int(parmDate[4:6]),
                int(parmDate[6:8]),
                0,
                0,
                0,
                0,
                0,
                -1,
            )
            wsDate = time.mktime(wsDateTup)
    if not wsDate:
        wsDate = time.time()
    return wsDate


def DaysFromYMD(parmDayCt, parmDate=None):
    wsDate = DateYMDToEpochSeconds(parmDate)
    wsDate += parmDayCt * 86400.0  # seconds / day
    return time.strftime("%Y%m%d", time.localtime(wsDate))


def DaysBetweenYMD(parmDate1, parmDate2):
    # This returns the wrong result in the transition between stanard time
    # time and daylight time because that day is either 23 or 25 hours long.
    # The fall day works out because it truncates down to the expect reult.
    # The spring day returns one day less than expected.
    # Quick fix is to round instead of tuncate the integer conversion.
    # It would be better use a differnt algorith, perhaps Jlian dates.
    # A failure occurs betwee March  9 and 10, 2008.
    wsDate1 = DateYMDToEpochSeconds(parmDate1)
    wsDate2 = DateYMDToEpochSeconds(parmDate2)
    return int((wsDate2 - wsDate1) / 86400.0)


def IsDate(parmDate):
    wsPos = parmDate.find("-")
    if wsPos > 0:
        wsParts = parmDate.split("-")
    else:
        wsParts = parmDate.split("/")
    if len(wsParts) != 3:
        return False
    wsMo = Int(wsParts[0])
    wsDa = Int(wsParts[1])
    wsYr = Int(wsParts[2])
    if (wsMo < 1) or (wsMo > 12):
        return False
    if (wsDa < 1) or (wsDa > 31):
        return False
    if wsYr == 0:
        return False
    return True


def TestYMD(parmDate, AllowMDZero=False):
    # Test date for validity and return in YYYYMMDD format.
    # Return None if invalid.
    # Converts RFC date to this format.
    # Optionally allow YYYY0000.
    if not parmDate:
        return None
    if not isinstance(parmDate, str):
        return None
    if len(parmDate) < 8:
        return None
    if (parmDate[4] == "-") and (parmDate[7] == "-"):
        # RFC Date
        parmDate = parmDate[:4] + parmDate[5:7] + parmDate[8:10]
    elif (parmDate[2] == "/") and (parmDate[5] == "/"):
        # mo/da/yyyy
        parmDate = parmDate[6:10] + parmDate[0:2] + parmDate[3:5]
    elif (parmDate[2] == " ") and (parmDate[6] == " "):
        # DD MMM YYYY
        wsMonthStr = parmDate[3:6].upper()
        try:
            wsMonth = MONTHNAMES3.index(wsMonthStr) + 1
        except BaseException:
            wsMonth = -1
        if wsMonth < 0:
            return None
        parmDate = parmDate[7:11] + "%02d" % (wsMonth) + parmDate[0:2]
    if not parmDate.isdigit():
        return None
    wsMo = Int(parmDate[4:6])
    wsDa = Int(parmDate[6:])
    if AllowMDZero:
        wsLowMD = 0
    else:
        wsLowMD = 1
    if (wsMo < wsLowMD) or (wsMo > 12):
        return None
    if (wsDa < wsLowMD) or (wsDa > 31):
        return None
    return parmDate


def DateToYMD(parmDate=None):
    wsDate = None
    if parmDate:
        if (isinstance(parmDate, type(0.0))) or (isinstance(parmDate, type(0))):
            wsDate = parmDate
        elif isinstance(parmDate, type("")):
            wsDateTup = (
                int(parmDate[:4]),
                int(parmDate[4:6]),
                int(parmDate[6, 8]),
                0,
                0,
                0,
                0,
                0,
                -1,
            )
            wsDate = time.mktime(wsDateTup)
    if not wsDate:
        wsDate = time.time()
    return time.strftime("%Y%m%d", time.localtime(wsDate))


def DateToYMDHMS(parmDate=None):
    wsDate = None
    if parmDate:
        if (isinstance(parmDate, type(0.0))) or (isinstance(parmDate, type(0))):
            wsDate = parmDate
        elif isinstance(parmDate, type("")):
            wsDateTup = (
                int(parmDate[:4]),
                int(parmDate[4:6]),
                int(parmDate[6, 8]),
                0,
                0,
                0,
                0,
                0,
                -1,
            )
            wsDate = time.mktime(wsDateTup)
    if not wsDate:
        wsDate = time.time()
    return time.strftime("%Y%m%d%H%M%S", time.localtime(wsDate))


def DispToDateYmd(parmDate):
    wsSlash1 = parmDate.find("/")
    wsSlash2 = parmDate.find("/", wsSlash1 + 1)
    wsDate = (
        Fill(parmDate[wsSlash2 + 1 :], 4)
        + Fill(parmDate[0:wsSlash1], 2)
        + Fill(parmDate[wsSlash1 + 1 : wsSlash2], 2)
    )
    return wsDate


def GetEnv(parmKey, parmDefault=""):
    if parmKey in os.environ:
        return os.environ[parmKey]
    else:
        return parmDefault


def GetLineLen(parmSrcLine, parmEOL=EOL):
    if not parmSrcLine:
        return 0
    wsSrcLineLen = len(parmSrcLine)
    wsEolLen = len(parmEOL)
    if parmSrcLine[wsSrcLineLen - wsEolLen :] == parmEOL:
        wsSrcLineLen -= wsEolLen
    return wsSrcLineLen


def StripAnyEOL(parmSrcLine):
    if not isinstance(parmSrcLine, type("")):
        return parmSrcLine
    while parmSrcLine and (parmSrcLine[-1:] in [chr(13), chr(10)]):
        parmSrcLine = parmSrcLine[:-1]
    return parmSrcLine


def StripEOL(parmSrcLine, parmEOL=EOL):
    if not isinstance(parmSrcLine, str):
        return parmSrcLine
    wsLen = GetLineLen(parmSrcLine, parmEOL)
    return parmSrcLine[:wsLen]


def StripQuotes(parmSrcLine):
    if len(parmSrcLine) < 2:
        return parmSrcLine
    if (parmSrcLine[0] == '"') and (parmSrcLine[-1:] == '"'):
        return parmSrcLine[1:-1]
    return parmSrcLine


def Find(parmSrcLine, parmTarget):
    parmSrcLine = Str(parmSrcLine)
    parmTarget = Str(parmTarget)
    return parmSrcLine.find(parmTarget)


def TodayYMD():
    return time.strftime("%Y%m%d")


def NowYMDHM():
    return time.strftime("%Y%m%d%H%M")


def CalcCRC(data, maxCRC=9999):
    if not data:
        return 1
    wsCRC = 0
    wsShift = 0
    for wsC in data:
        wsVal = ord(wsC) + 1
        if wsShift > 0:
            wsVal = wsVal << wsShift
        if wsShift >= 20:
            wsShift = 0
        else:
            wsShift += 1
        wsCRC += wsVal
    if wsCRC > maxCRC:
        wsFoldBits = 1
        wsFoldMask = 1
        while wsFoldMask < maxCRC:
            wsFoldBits += 1
            wsFoldMask = (wsFoldMask << 1) | 1
        wsFoldBits -= 1
        wsFoldMask = wsFoldMask >> 1
        while wsCRC > maxCRC:
            wsHold = wsCRC & wsFoldMask
            wsCRC = (wsCRC >> wsFoldBits) + wsHold
    return wsCRC


def ListStripTrailingBlanks(parmList, parmMinLen=0):
    if not isinstance(parmList, type([])):
        return None
    while len(parmList) < parmMinLen:
        parmList.append(None)
    while len(parmList) > parmMinLen:
        if parmList[-1]:
            return parmList
        parmList = parmList[:-1]
    return parmList


UnicodeTranslator = {
    127: "",  # control character (u'\x79' / 127)
    128: "",  # control character (u'\x80' / 128)
    129: "",  # control character (u'\x81' / 129)
    130: "",  # control character (u'\x82' / 130)
    131: "",  # control character (u'\x83' / 131)
    132: "",  # control character (u'\x84' / 132)
    133: "",  # control character (u'\x85' / 133)
    136: "",  # control character (u'\x88' / 136)
    137: "",  # control character (u'\x89' / 137)
    142: "",  # control character (u'\x8e' / 142)
    143: "",  # control character (u'\x8f' / 143)
    144: "",  # control character (u'\x90' / 144)
    145: "",  # control character (u'\x91' / 145)
    146: "",  # control character (u'\x92' / 146)
    147: "",  # control character (u'\x93' / 147)
    148: "",  # control character (u'\x94' / 148)
    149: "*",  # GP some sort of alert (u'\x95' / 149)
    150: "",  # control character (u'\x96' / 150)
    151: "",  # control character (u'\x97' / 151)
    152: "",  # control character (u'\x98' / 152)
    153: "",  # control character (u'\x99' / 153)
    154: "",  # control character (u'\x9a' / 154)
    155: "",  # control character (u'\x9b' / 155)
    156: "",  # control character (u'\x9c' / 156)
    157: "",  # control character (u'\x9d' / 157)
    160: " ",  # no-break space (u'\xa0' / 160)
    161: "!",  # inverted exclamation (u'\xa1' / 161)
    162: " cents",  # cents sign  (u'\xa2' / 162)
    163: "BP",  # pounds currency (u'\xa3' / 163)
    164: " currency",  # currency sign   (u'\xa4' / 164) looks like a box
    165: "YEN",  # Yen currency   (u'\xa5' / 165)
    166: "|",  # broken bar   (u'\xa6' / 166)
    167: "S",  # section symbol (u'\xa7' / 167)
    168: "",  # DIAERESIS  (u'\xa8' / 168) the two dots over oomlout, etc.
    169: "(C)",  # copyright symbol (u'\xa9' / 169)
    170: "",  # feminine ordinal (u'\xaa' / 170)
    171: "<<",  # lf point double arrow (u'\xab' / 171)
    172: ".NOT.",  # NOT logical operator (u'\xac' / 172)
    173: "",  # soft hyphen  (u'\xad' / 173)
    174: "(R)",  # registered trademark (u'/xae' / 174)
    176: " degree",  # degree symbol  (u'/xb0' / 176)
    177: "+/-",  # degree symbol  (u'/xb1' / 177)
    178: "^2",  # superscript 2  (u'/xb2' / 178)
    179: "^3",  # superscript 3  (u'/xb3' / 179)
    181: "u",  # micro symbol  (u'/xb5' / 181)
    182: "P",  # pilcro / paragraph (u'/xb6' / 182)
    186: "",  # masculine ordinal (u'/xba' / 186) looks like degree
    187: ">>",  # rt point double arrow (u'/xbb' / 187)
    188: "1/4",  # vulgar fraction (u'/xbc' / 188)
    189: "1/2",  # vulgar fraction (u'/xbd' / 189)
    190: "3/4",  # vulgar fraction (u'/xbe' / 190)
    191: "?",  # inverted question (u'\xbf' / 193)
    192: "A",  # (u'\xc0' / 192)
    193: "A",  # (u'\xc1' / 193)
    194: "A",  # (u'\xc2' / 194)
    195: "A",  # (u'\xc3' / 195)
    196: "A",  # (u'\xc4' / 196)
    197: "A",  # (u'\xc5' / 197)
    198: "A",  # (u'\xc6' / 198)
    202: " degree",  # degree symbol? GP (u'\xca' / 202)
    209: "a",  # GP a-oomlout  (u'\xd1' / 209)
    # 211 is probably wrong. Came from AKA8045 for tire bead size. Neither
    # GP nor AKA had reasonable representation and I couldn't find reference
    # in a hurry.
    211: " ...",  # ??? GP  (u'\xd3' / 211)
    215: "x",  # raised mult GP (u'\xd7' / 215)
    216: " diameter",  # theta GP  (u'\xd8' / 216)
    220: "U",  # GP U-Oomlout Uberlite (u'\xdc' / 220)
    225: "a",  # GP a' (or o')  (u'\xe1' / 225)
    226: '"',  # ELENCO " (inch) (u'\xe2' / 226)
    # The same line kicked out 209 and 228 but only one special character visible
    # Search for Navy U-201 in technote.txt
    228: "a",  # GP ???  (u'\xe4' / 228)
    231: "c",  # GP c' Fac'ade  (u'\xe7' / 231)
    233: "e",  # GP e' Applique' (u'\xe9' / 233)
    243: "o",  # GP o'   (u'\xf3' / 243)
    246: "u",  # GP u-oomlout  (u'\xf6' / 246)
    248: "--",  # GP long dash  (u'\xf8' / 248)
    249: "u",  # (u'\xf9' / 249)
    250: "u",  # (u'\xfa' / 250)
    251: "u",  # (u'\xfb' / 251)
    252: "u",  # (u'\xfc' / 252)
    253: "y",  # (u'\xfd' / 253)
    # characters >= 128 and <= 255 may be extended ascii / maybe Latin-1
    937: " ohms",  # capital omega  (u'\x03a9' / 937)
    956: "u",  # small mu (micro) (u'\x03bc' / 956)
    8211: "--",  # EN (long) dash (u'\x2013' / 8211)
    8212: "-",  # EM dash  (u'\x2014' / 8212)
    8216: "'",  # left single quote (u'\x2018' / 8216)
    8217: "'",  # right single quote (u'\x2019' / 8217)
    8220: "'",  # left single quote (u'\x201c' / 8220)
    8221: '"',  # right double quote (u'\x201d' / 8221)
    8226: "*",  # chinese han character (u'\x2022' / 8226)
    8230: "...",  # horizontal elipse (u'\x2026' / 8230)
    8243: '"',  # double prime (accent) (u'\x2033' / 8243)
}


def UnicodeToAscii(parmStr, Errs=None):
    if parmStr is None:
        return ""
    try:
        wsResult = parmStr.encode("ascii")
        return wsResult
    except BaseException:
        pass
    #
    wsResult = ""
    for wsC in parmStr:
        wsOrd = ord(wsC)
        if wsOrd < 32:
            if wsOrd in [10]:
                continue
            ReportTypeError(
                "Invalid control character {COrd}".format(COrd=ord(wsC)), Errs
            )
        if wsOrd >= 127:
            if wsOrd in UnicodeTranslator:
                wsN = UnicodeTranslator[wsOrd]
            else:
                print("***", parmStr, "***")
                ReportTypeError(
                    "Unknown unicode char {COrd}".format(COrd=ord(wsC)), Errs
                )
        else:
            wsN = wsC.encode("ascii")
        wsResult += wsN
    return wsResult


#
# QuoteStr() Conditionally quotes a string if it contains a quote character or delimiter
# 		It is intended primaryily when creating comma separated files for export
#
# There are lots of options:
# 	- The opening quote character, closing quote character and delimiter character
# 		can be specified
# 	- A list of additional characters can be specified whihc force quoting if found in the data.
# 	- An escape character can be specified to mark internal quote characters, otherwise
# 		the double quote convention is used.
#


def QuoteStr(
    parmData,
    Quote='"',
    QuoteAlways=False,
    Escape=None,
    QuoteEnd='"',
    Delim=",",
    AlsoQuote="",
):
    #
    # When deciding to quote, only look at first character of
    # delimiter -- assume that any extra characters are padding like ", "
    #
    parmData = AsStr(parmData)
    wsNeedQuotes = False
    if (
        QuoteAlways
        or (parmData.find(Delim[0]) >= 0)
        or (parmData.find(QuoteEnd) >= 0)
        or (parmData[:1] == Quote)
    ):
        wsNeedQuotes = True
    if not wsNeedQuotes:
        for wsC in AlsoQuote:
            if parmData.find(wsC) >= 0:
                wsNeedQuotes = True

    if not wsNeedQuotes:
        return parmData

    wsPos = 0
    wsLen = len(parmData)
    while wsPos < wsLen:
        wsC = parmData[wsPos]
        if (wsC == Quote) or (wsC == QuoteEnd) or (wsC == Escape):
            if Escape:
                parmData = parmData[:wsPos] + Escape + parmData[wsPos:]
            else:
                parmData = parmData[:wsPos] + Quote + parmData[wsPos:]
            wsPos += 1
            wsLen += 1
        wsPos += 1
    parmData = Quote + parmData + QuoteEnd
    return parmData


#
# Sort(_ sort an array based on the value of the elements as discovered by cmp()
#


def Sort(parmArray):
    parmArray.sort(lambda a, b: cmp(a, b))


#
# SortIx() sort an array of arrays or tuypples based on the value of any column
#


def SortIx(parmArray, parmIx=0):
    parmArray.sort(lambda a, b: cmp(a[parmIx], b[parmIx]))
    return parmArray


if __name__ == "__main__":
    pass
