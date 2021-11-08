#!/usr/bin/python
#############################################
#
#  cncore/textfile (copy from baf/pylib/TextFile)
#
#
#  FEATURES
#
#  This class reads a text file.  Does read-ahead for neater
#  client "while EOF" loop.
#
#
#  WARNINGS
#
#
#  Copyright (C) 2001 by Albert B. Margolis - All Rights Reserved
#
#  2/16/2001:  Initial Release
#  2/28/2001:  Add module level open() which behaves similarly to
#		python built-in open.  Fix init() to set all variables.
#		Remove automatic open from init().  Add recCode.
#		Move comma parse code to utils.
#  4/21/2001:  Add basic write support.  Needs better security checking.
#  5/13/2001:  Don't use os.access(xxx, os.W_OK) because it returns
#		false if there is no exiting file, even if access
#		allows creation.  At some point, this needs to be
#		upgraded to security safe opening.
#  8/11/2001:  Add EOL and strip_eol option, add close().  Use EOL instead
#		of "\n" or other hard coded line termination string -- this
#		required re-writing readline() to do a block read
#		because the python readline() doesn't allow control over EOL.
#  9/08/2001: Add STDOUT as special file name indicating to use stdout file.a
#		Add writeSize accumulator of number of bytes written to file.
#		Fix open() to initialize self.recno.
# 11/28/2001: Add OpenAssign() for pre-opened files.  Add T_OpenAssign()
#		to open an
#		output file and make a copy while reading.  This is to
#		save I/O when you need to process and save stdin.  Added
#		for bzWebMailDA.py mail delivery agent.
# 12/19/2001: Fix bugs (typo) in calls to OpenAssign()
# 01/02/2002: Add self.readAheadMode for webmail smtp project.  Modify
#		readline() to omit read-ahead to avoid blocking at end
#		of transmission.  EOF is determined by SMTP dot ending.
# 01/19/2002: Satisfy Dan Bernstein's NFS-writing rules.  Required
#		creating class filedriver wrapper because built-in
#		file object doesn't return write size.  Delegate most
#		safety rules to that wrapper.
# 01/20/2002: Make this TextFile a descendent of filedriver instead
#		of a container.  Merge/move low level functions
#		to filedriver.  Makes package much neater!
# 12/07/2002: Add LoadCmaFileToDataStore()
# 12/18/2002: Add writecma()
# 02/09/2003: Add GetCounter()
# 04/05/2003: Add WriteDataStoreToCsvFile()
# 08/30/2003: Add FldSkipList to WriteDataStoreToCsvFile().
#		AddFldSkipMap to writecma()
# 08/20/2004: AddOpenBlob to read HTTP upload files
# 05/02/2004: Modify writecma() to support alternate delimiters
# 05/12/2004: Modify writecma() to prevent quoting in tab delimited files
# 04/03/2005: Add readblob() to read blobs after text
# 08/17/2006: Add ReadCounter()
# 09/19/2006: Modify OpenBlobTextFile() to support capture files
# 29 Aug 2009: Support tmp/bak for safe replacement of text files
#
#############################################

#
# This module is essential for site bootstraping so it should have
# the minimal number of dependencies and none outside the development
# directory.
#

import codecs
import os
import sys
import time
from contextlib import contextmanager

from . import commastr
from . import filedriver
from . import datastore
from . import tupledict
from . import virtfile
from . import utils

RANDOM_NAME_MAX_ATTEMPTS = 10

def open(path, mode, debug=0):
    """Simple text file open, like built-in function. """
    text_file = TextFile(debug=debug)
    if text_file.open(path, mode):
        return text_file
    else:
        return None

def open_read(file_name=None, dir=None, source=None, debug=0):
    text_file = TextFile(debug=debug)
    if text_file.open(file_name=file_name,
                                   mode=filedriver.MODE_R, dir=dir,
                                   source=source):
        return text_file
    return None

def open_write_with_swap_file(file_name=None, dir=None,
                         source=None, backup=False,
                         no_wait=False, debug=0):
    text_file = TextFile(debug=debug)
    if text_file.open(file_name=file_name, mode=filedriver.MODE_S, dir=dir,
                          source=source, backup=backup, no_wait=no_wait):
        return text_file
    return None

def open_read_and_replace(file_name=None, dir=None,
                          source=None, backup=False, no_wait=False, debug=0):
    """
    Safe open for a multi-tasking environment where there are potentially
    multiple readers and writers. Uses a lock file to prevent simultaneous
    writes and a swap file to provide a consistent file to readers.
    Optionally creates a backup of original file.
    """
    text_file = TextFile(debug=debug)
    return text_file.open(file_name=file_name, mode=filedriver.MODE_RR, dir=dir,
                          source=source, backup=backup, no_wait=no_wait)

def OpenBlobTextFile(parmBlob=None, mode="r", Encoding='ascii', debug=0):
  wsDriver			= filedriver.bzBlobFileDriver(Encoding=Encoding, debug=debug)
  if mode == "r":
    wsDriver.AddBlob(parmBlob)
  wsTextFile			= TextFile(driver=wsDriver, debug=debug)
  if wsTextFile.open("", mode):
    return wsTextFile
  else:
    return None

def create_randomly_named_file(dir='', ext='cart', name_lenght=12, prefix='', temp=True, debug=0):
    text_file = TextFile(debug=debug)
    attempt_ct = 0
    while attempt_ct < RANDOM_NAME_MAX_ATTEMPTS:
        attempt_ct += 1
        fn = prefix + utils.GetRandom(name_length) + "." + ext
        path = os.path.join(dir, fn)
        if text_file.open(path, "c"):
            return text_file
    return None


def ReleaseLock(parmLockFilePath):
    try:
      os.unlink(parmLockFilePath)
    except:
      pass					# No worries if non-existant
    return True

def SetLock(parmLockFilePath):
    wsLockFile = OpenTextFile(parmLockFilePath, "c")
    wsAttemptCt = 0
    while (not wsLockFile) and (wsAttemptCt < 20):
      time.sleep(0.5)
      wsLockFile = OpenTextFile(parmLockFilePath, "c")
      wsAttemptCt += 1
    if not wsLockFile: return False
    wsLockFile.close()
    return True

def ReadAndLockCounter(parmCounterName, dir="", default=1):
    # Need to follow with either SetCounter() or ReleaseLock()
    wsLockFileName = dir + parmCounterName + '.lock'
    wsDataFileName = dir + parmCounterName + '.data'

    if not SetLock(wsLockFileName): return None
    wsCtlFile = open(wsDataFileName, "r")
    if wsCtlFile:
      if wsCtlFile.EOF: wsCounter = default
      else:
        wsCounterStr = wsCtlFile.readline()
        wsCounter = utils.Int(utils.strip_eol(wsCounterStr))
      wsCtlFile.close()
    else:
      wsCounter = default
    return utils.Str(wsCounter)

def SetCounter(parmCounterName, parmValue, dir=""):
    # Assumes that lock is already set
    wsLockFileName = dir + parmCounterName + '.lock'
    wsDataFileName = dir + parmCounterName + '.data'
    try:
      wsStat = os.stat(wsLockFileName)
    except:
      wsStat = None
    if not wsStat: return None

    wsCtlFile = open(wsDataFileName, "w")
    if wsCtlFile:
      wsCtlFile.writeln(utils.Str(parmValue))
      wsCtlFile.close()
      wsResult = True
    else:
      wsResult = False
    ReleaseLock(wsLockFileName)
    if wsResult:
      return parmValue
    else:
      return None

def GetCounter(parmCounterName, dir="", seqInc=1):
    wsLockFileName = dir + parmCounterName + '.lock'
    wsDataFileName = dir + parmCounterName + '.data'

    if not SetLock(wsLockFileName): return None

    wsCtlFile = open(wsDataFileName, "r")
    if not wsCtlFile:
      wsCounter = "1"
    else:
      if wsCtlFile.EOF:
        wsCounter = "1"
      else:
        wsCounter = str(int(wsCtlFile.readline()) + seqInc)
      wsCtlFile.close()
      wsCtlFile = None
      del wsCtlFile

    wsCtlFile = open(wsDataFileName, "w")
    if wsCtlFile:
      wsCtlFile.writeln(wsCounter)
      wsCtlFile.close()
      wsResult = True
    else:
      wsResult = False
    wsCtlFile = None
    del wsCtlFile

    ReleaseLock(wsLockFileName)

    if wsResult:
      return wsCounter
    else:
      return None

def IncCtrFile(parmDataFileNamei, SeqInc=1):
  # This is used for session cookies and must be consisten/compatible
  # with the generated PHP function of the same name.
  wsCtlFile		= open(parmDataFileName, 'a+')
  wsCtlFile.lock()
  wsCtlFile.seek(0)					# prob not needed, just copied from PHP reference
  wsCounter		= str(int(wsCtlFile.readline()) + SeqInc)
  wsCtlFile.seek(0)
  wsCtlFile.truncate(0)
  wsCtlFile.writeln(wsCounter)
  wsCtlFile.flush()
  wsCtlFile.unlock()
  wsCtlFile.close()
  return wsCounter

#####################################################

STATEINTERFIELD = 0
STATEFIELDNAME = 1

def ParseTabHeadings(parmHeadings):
  wsIx = 0
  wsFields = []
  wsState = STATEINTERFIELD
  wsFieldName = ""
  wsFieldStart = 0
  wsLineLen = len(parmHeadings)
  while wsIx < wsLineLen:
    wsC = parmHeadings[wsIx]
    # print "%2d %d %s %s" % (wsIx, wsState, wsC, wsFieldName)
    wsIx += 1
    if wsState == STATEINTERFIELD:
      if wsC == " ":
        continue
      else:
        wsFieldName = wsC
        wsFieldStart = wsIx
        wsState = STATEFIELDNAME
    else:
      if wsC == " ":
        wsState = STATEINTERFIELD
        if len(wsFields) > 0:
          wsFields[-1][2] = wsFieldStart-1
        wsFields.append([wsFieldName, wsFieldStart-1, 0])
      else:
        wsFieldName += wsC
  if wsFieldName:
    if len(wsFields) > 0:
      wsFields[-1][2] = wsFieldStart-1
    wsFields.append([wsFieldName, wsFieldStart-1, None])
  wsFieldCt = len(wsFields)
  wsFields[wsFieldCt-1][2] = None		# so last field slices to End Of Line
  return wsFields

def LoadTabFileToDataStore(parmFn, DefaultValue="", debug=0):
  csv_file = open("tab.txt", "r", debug)
  if not csv_file: return None
  wsLine = csv_file.readline()
  wsLine = utils.StripAnyEOL(wsLine)
  wsLine = wsLine.expandtabs(8)
  wsTabDict = ParseTabHeadings(wsLine)
  if debug > 0:
    print("DICT: " + repr(wsTabDict))
  wsDataStore = datastore.datastoreObject(DefaultValue=DefaultValue, Dict=wsTabDict)
  while not csv_file.EOF:
    wsLine = csv_file.readline()
    wsLine = utils.StripAnyEOL(wsLine)
    wsLine = wsLine.expandtabs(8)
    wsFields = []
    for wsThisSpec in wsTabDict:
      wsFields.append(utils.Strip(wsLine[wsThisSpec[1]:wsThisSpec[2]]))
    wsDataStore.AppendTuple(wsFields)
  return wsDataStore

###################################################
#
# Load CSV file
#
# parmFn can be either a file path or an open file object.
# Optionally execute callback function for each line.
# Optionally return data datastore of records (otherwise callback can save)
#
# BOM indicates byte ordering. Not actually meaningful for UTF-8,
# but some applications insert it anyway. EBay is one of those.
# https://docs.python.org/3/howto/unicode.html
BOM = '\ufeff'

def load_csv_file(
						parmFn,
						DefaultValue=None,
						DefaultValueAssigned=None,
						Map=None,
						AdditionalTDictFields=None,
						AllowQuotedNewline=False,
						LineCleanUp=None,
						RecordLimit=None,
						ReturnDataStore=True,
						StripAll=False,
						Debug=0):
    if isinstance(parmFn, str):
        csv_file = open(parmFn, mode='r')
    else:
        csv_file = parmFn
    if csv_file is None:
        return None
    csv_file_header = None
    while csv_file_header is None:
        header_line = csv_file.readline()
        if (csv_file.source_line_ct == 1) and (header_line[0] == BOM):
            header_line = header_line[1:]
        csv_file_header = commastr.CommaStrToList(header_line, StripAll=StripAll)
        print("HDR", csv_file_header)
        if commastr.is_empty_list(csv_file_header):
            csv_file_header = None
    wsFieldNames = []
    for wsIx, wsColHdr in enumerate(csv_file_header):
      if (Map is None) or (wsIx >= len(Map)):
        wsMappedHdr			= wsColHdr
      else:
        wsModelHdr			= Map[wsIx][0]
        wsMappedHdr			= Map[wsIx][1]
        wsTestLen				= len(wsModelHdr)
        if wsColHdr[:wsTestLen] != wsModelHdr:
          raise TypeError("Invalid header '{ActualHdr}' s/b '{ModelHdr}'.".format(ActualHdr=wsColHdr, ModelHdr=wsModelHdr))
        if wsMappedHdr == '':
         wsMappedHdr			= wsModelHdr
      if wsMappedHdr == '':
        wsMappedHdr			= 'Col' + utils.Str(wsIx)
      wsFieldNames.append(wsMappedHdr)					# filter to symbol characters ??
    if AdditionalTDictFields is not None:
      # These are fields that we want in our non-dynamic TDict but may not be in this import file.
      for wsThisFieldName in AdditionalTDictFields:
        if wsThisFieldName in wsFieldNames:
          pass
        else:
          wsFieldNames.append(wsThisFieldName)
    wsTDict				= tupledict.MakeTDict(wsFieldNames)
    #
    if ReturnDataStore:
      wsDataStore				= datastore.DataStoreObject(
						DefaultValue=DefaultValue,
						DefaultValueAssigned=DefaultValueAssigned,
						TDict=wsTDict)
    wsRecCt				= 0
    if AllowQuotedNewline:
      wsGetNextLine			= csv_file.readline
    else:
      wsGetNextLine			= None
    for wsSourceLine in csv_file:
      if (wsSourceLine == '') or (wsSourceLine == '\n'):
        continue
      wsThis				= commastr.CommaStrToList(wsSourceLine, GetNextLine=wsGetNextLine, StripAll=StripAll)
      wsRecCt				+= 1
      if ReturnDataStore:
        wsTuple				= wsDataStore.AppendData(wsThis)
      else:
        wsTuple				= datastore.bafTupleObject(
						Data=wsThis,
						DefaultValue=DefaultValue,
						DefaultValueAssigned=DefaultValueAssigned,
						TDict=wsTDict)
      if LineCleanUp is not None:
        LineCleanUp(wsTuple)
      if RecordLimit is not None:					# limit records for testing
        if wsRecCt > RecordLimit:
          break
    if ReturnDataStore:
      return wsDataStore

def WriteDataStoreToCsvFile(FileName="", DataStore=None, FldSkipList=[], Delim=', ', debug=0):
  csv_file			= open(FileName, "w", debug)
  if not csv_file:
    return None
  #
  # Write Column Headings Line
  #
  wsFldSkipMap			= ""
  if len(FldSkipList) > 0:
    if DataStore._tdict:
      wsIx			= 0
      while wsIx < len(FldSkipList):
        FldSkipList[wsIx]	= FldSkipList[wsIx].upper()
        wsIx			+= 1
        wsDictSrc		= DataStore._tdict.ElementNamesByIx()
        wsDictDst		= []
        for wsThisDictItem in wsDictSrc:
          if wsThisDictItem.upper() in FldSkipList:
            wsFldSkipMap	+= "Y"
          else:
            wsDictDst.append(wsThisDictItem)
            wsFldSkipMap	+= "N"
        csv_file.writecma(wsDictDst, Delim=Delim)
  else:
    if DataStore._tdict:
      csv_file.writecma(DataStore._tdict.Captions(), Delim=Delim)
  #
  # Write Data Lines
  #
  for wsTuple in DataStore:
    csv_file.writecma(wsTuple._datums, FldSkipMap=wsFldSkipMap, Delim=Delim)
  return True

class TextFileIterator(object):
  def __init__(self, parmTextFile):
    self.textFile			= parmTextFile

  def __iter__(self):
    return self.TextFileIterator.__iter__()

  def __next__(self):
    if self.textFile.EOF:
      raise StopIteration
    return self.textFile.readline()

class TextFile(virtfile.VirtFile):
    __slots__ = (
                    'call_file_name', 'call_open_mode',
                    'printSrc', 'recCodeFlag', 'recCode'
                )
    def __init__(self, file_name=None, open_mode=None, driver=None, debug=0):
        if debug >= 3: print("TextFile.__init__(driver=%s, debug=%s)" % (
				repr(driver), repr(debug)))
        virtfile.VirtFile.__init__(self, driver=driver, debug=debug)
        self.call_file_name		= file_name
        self.call_open_mode		= open_mode
        self.recCodeFlag		= False
        self.recCode			= None
        self.printSrc			= False
        self.strip_eol = True

    def __enter__(self):
        # thee self.call_xxx attributes are to support with statement
        assert self.call_file_name is not None
        assert self.call_open_mode is not None
        self.open(self.call_file_name, self.call_open_mode)


    def __exit__(self, type, value, traceback):
        self.Close()

    def __iter__(self):
        return TextFileIterator(self)

    def readcma(self, AllowQuotedEol=False):
        if self.debug >= 3:
            print("TextFile.readcma(fd:%d)" % (self.fd))
        self.recCode		= None
        wsLine			= self.readline()
        if not wsLine:
            return None
        if AllowQuotedEol:
            wsReadNext		= self.readline
        else:
            wsReadNext		= None
        wsList			= commastr.CommaStrToList(wsLine, GetNextLine=wsReadNext)
        if self.recCodeFlag:
            self.recCode		= wsList[0].upper()
            wsList			= wsList[1:]
        return wsList

    def writecma(self, data, FldSkipMap="",
			Delim=", ", QuoteNever=False,
			AlsoQuote=""):
        if isinstance(data, type([])):
            self.writeln(commastr.ListToCommaStr(data, FldSkipMap=FldSkipMap,
					Delim=Delim, QuoteNever=QuoteNever,
					AlsoQuote=AlsoQuote))
        elif isinstance(data, type(())):
            self.writeln(commastr.ListToCommaStr(data, FldSkipMap=FldSkipMap,
					Delim=Delim, QuoteNever=QuoteNever,
					AlsoQuote=AlsoQuote))
        else: self.writeln(data)

if (__name__ == "__main__"):
    pass
