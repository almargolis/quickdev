#!/usr/bin/python
#############################################
#
#  VirtFile Module
#
#
#  FEATURES
#	A VirtFile is an abstract framework for file-type objects.
#	It is intended as a base class for drop in replacements for
#	python built-in file objects.  The descendant classes extend
#	the built-in objects with auto-magic safe programming practices
#	and/or to provide more generality of data sources.
#
#	File read access does a read-ahead to support "while not EOF"
#	loops without requiring a pre-read and related "first-time"
#	code.  NOTE: Except for special cases (like empty file and
#	intentional close(), VirtFile does not set EOF.  This is because
#	descendant classes, such as VirtFile, don't indicate EOF until
#	after specialized read functions have used the final buffer.
#
#	It also wraps misc. i/o calls so I only have to look at one
#	spot to lookup calls.
#
#  WARNINGS
#
#  Descendant Classes must implement the following methods.  These are
#	fairly basic wrappers.  Most error checking, tracing, etc.
#	should be done here.  The only exceptions are the open functions
#	which have to deal with the vagaries of different deveice types.
#
#	OsOpen()		return fd.  Must set parent fileName, fd, openMode
#	OsClose()		no return value
#	OsDup()			return (newDriver, newFd)
#	OsRead()		return data
#	OsWrite()		return # bytes actually written
#
#  The following methods are supported when needed:
#
#       OsLseek()		return new file read position
#       OsTell()		return file read position
#
#  Copyright (C) 2001 by Albert B. Margolis - All Rights Reserved
#
#  01/19/2002:  Initial Release
#  01/20/2002:	Add syslog functions from bzTcpip as merging
#  01/26/2002:  Add open() parmMode of "c" for create.
#  12/18/2002:  Add open() parmMode of "rwm" which opens file
#			for read/write, creating (making) file if
#			needed.
#
#  05/14/2006:  Add OpenBlobFile(), seek() and tell() to
#		support Python Image Library access to uploaded
#		images without creating a physical file.
#
#  05/13/2013:  Add lock(), unlock(), flush(), truncate() for "new style"
#		incremental counter VirtFile.IncCtrFile()
#
#############################################
#############################################

import os
import syslog

from . import filedriver
from . import utils

STDIN = "__stdin__"
STDOUT = "__stdout__"

BLOCKSIZE = 1024
BLOCKSIZE = 100000


def open(parmFn, parmMode, debug=0):
    wsFile = VirtFile(debug)
    if wsFile.open(parmFn, parmMode):
        return wsFile
    else: return None


def OpenBlobFile(parmBlob, debug=0):
    wsDriver = filedriver.bzBlobFileDriver(debug=debug)
    wsDriver.AddBlob(parmBlob)
    wsFile = VirtFile(driver=wsDriver, debug=debug)
    wsFile.readAheadMode = False
    if wsFile.open("", "r"):
        return wsFile
    else: return None


class VirtFileException:
    def __init__(self, code, message, sysfile):
        self.code = code
        self.message = message
        self.sysfile = sysfile


class VirtFile(object):
    __slots__ = (
                    'buf', 'bufIx', 'bufLen', 'bufSize',
                    'debug', 'dontClose', 'driver', 'EOF', 'EOL_bytes',
                    'funcResult',
                    'logForceDetail', 'logPriority', 'logSummary',
                    'openMode', 'readAheadMode', 'recno',
                    'srcLineCt', 'stripEOL',
                    'temp_output_file', 'tFile', 'writeResult', 'writeSize'
                )

    def __init__(self, driver=None, debug=0):
        if debug >= 3:
            print("VirtFile.__init__(driver=%s, debug=%s)" % (
                                    repr(driver), repr(debug)))
        # The file definition properties need to be copied by dup().
        # Client control properties need to be preserved by reset()
        # File Definition Properties
        if driver:
            self.driver = driver
            self.driver.parent = self
        else:
            self.driver = filedriver.FileDriver(self, debug=debug)
        self.debug = debug
        self.dontClose = False
        self.EOL_bytes = '\n'.encode('utf-8')
        self.logForceDetail = False
        self.logPriority = None
        self.logSummary = None
        self.openMode = filedriver.MODE_CLOSED
        self.readAheadMode = True
        self.stripEOL			= False
        self.tFile = None
        # I/O State Properties
        self.buf = ""
        self.bufIx = 0
        self.bufLen = 0
        self.bufSize = BLOCKSIZE
        self.EOF = True
        self.funcResult = 0
        self.recno = 0
        self.srcLineCt = 0
        self.temp_output_file = None
        self.writeResult = -1
        self.writeSize = 0

    def __del__(self):
        self.close()		# make sure self.tFile complete

    def close(self, ignore_temp=False):
        if self.debug >= 3:
            if self.tFile:
                try:
                    wsTFileFd = self.tFile.fd
                except: wsTFileFd = -1
                try:
                    wsTFileFileName = self.tFile.fileName
                except: wsTFileFileName = ""
                wsTFile = "t-file %d:%s" % (
                    wsTFileFd, wsTFileFileName)
            else:
                wsTFile = "no t-file"
            print("VirtFile.close(%d: %s) %s" % (
                self.driver.fd, self.driver.open_path, wsTFile))
        if self.driver.fd < 0:
            return
        if self.tFile:			# write rest of file copy
            while self.bufLen > 0:
                self.ReadBlock()
            self.tFile.close()
            self.tFile = None

        if not self.dontClose:
            self.driver.OsClose()
        self.EOF = True
        self.openMode = filedriver.MODE_CLOSED
        if not ignore_temp:
            # abandon associated temp file. We might get here due
            # to an exception or because we decided to abandon the
            # changes written to the temo file.
            if self.temp_output_file is not None:
                self.temp_output_file.close()
                self.temp_output_file = None
        # if self.funcResult != 0:
        #  raise VirtFileException, (1, "close() Error", self)

    def dup(self, parmSrcFile=None, driver=None, fd=None):
        # dup() copies the full definition of the file's open state
        # and access rules.  It initializes the i/o state of postion,
        # bytes written, etc.
        #
        if self.debug >= 3:
            print("VirtFile.dup(src=%s driver=%s fd=%s)"
                  % (repr(parmSrcFile), repr(driver), 'fd'))

        self.reset()

        # Note: driver.OsDup() does not necessarily return the same type.
        # Particularly, bzTcpipDriver.OsDup() returns a filedriver object.
        if (driver is not None) and (fd is not None):
            self.driver = driver
            self.driver.fd = fd
        else:
            self.driver = parmSrcFile.driver.OsDup(self, self.debug)
        if self.driver.fd == parmSrcFile.fd:
            self.dontClose = True
        else:
            self.dontClose = False
        self.debug = parmSrcFile.debug
        self.EOL_bytes = parmSrcFile.EOL_bytes
        self.logForceDetail = parmSrcFile.logForceDetail
        self.logPriority = parmSrcFile.logPriority
        self.logSummary = parmSrcFile.logSummary
        self.openMode = parmSrcFile.openMode
        self.readAheadMode = parmSrcFile.readAheadMode
        self.tFile = parmSrcFile.tFile

        self.OpenReadAhead()
        return self.driver.fd			# default is -1

    @property
    def EOL(self):
        return self.EOL_bytes.decode('utf-8')

    @EOL.setter
    def EOL(self, str):
        self.EOL_bytes = str.encode('utf-8')

    def fileno(self):
        return self.driver.fd

    def fsync(self):
        if self.debug >= 3:
            print("VirtFile.fsync(%d: %s)" % (
                                            self.driver.fd, self.driver.open_path))
        self.funcResult = self.driver.OsFsync()
        return self.funcResult
        # if self.funcResult != 0:
        #  raise VirtFileException, (1, "fsync() Error", self)

    def GetAndClearBlob(self):
        return self.driver.GetAndClearBlob()

    def open(self, parmFn, parmMode="r"):
        if self.debug >= 3:
            print("VirtFile.open(%s, %s)" % (parmFn, parmMode))

        try:
            wsFlags = filedriver.FLAGS[parmMode]
        except IndexError:
            raise VirtFileException(1, "open() INVALID MODE", self)

        if self.driver.OsOpen(parmFn, wsFlags) >= 0:
            self.openMode = parmMode
            self.OpenReadAhead()
            wsReturn = self
        else:
            self.EOF = True
            self.openMode = filedriver.MODE_CLOSED
            wsReturn = None
        return wsReturn

    def create_temp_output(self, debug=0):
        # This creates a file with an easily predictable name. This is suitable
        # command line tools, not CGI or other public facing processes.
        self.temp_output_file = None
        assert self.openMode == filedriver.MODE_R
        wsTempFileName = utils.ChangeFileNameExtension(self.driver.open_path, 'tmp')
        wsTempFile = VirtFile(debug=debug)
        if wsTempFile.open(wsTempFileName, filedriver.MODE_C) is None:
            return None
        self.temp_output_file = wsTempFile
        return self.temp_output_file

    def safe_close(self):
        # if the client program doesn't specifically call this the origin
        # text file is untouched.
        self.close(ignore_temp=True)
        if self.temp_output_file is None:
            # we didn't actually open a temp file. We are all done now.
            return
        self.temp_output_file.close()
        wsBackupFileName = utils.ChangeFileNameExtension(self.driver.open_path, 'bak')
        if os.path.exists(self.driver.open_path):
            if os.path.exists(wsBackupFileName):
                os.remove(wsBackupFileName)
            # os.link (make hard link) creates the backup without deleting the
            # original file directory entry.
            os.link(self.driver.open_path, wsBackupFileName)
        # os.rename replaces the original file directory entry.
        # It also gets rid of the temporary file directory entry, but not
        # the file contents.
        # This process means that some version of the original file is
        # always available. This is desireable when we are in the process of
        # updating web pages so nobody ever gets a 404 error.
        # It leaves open a possible race condition if the second opener is also an
        # editor. That can be mitigated with locks or other methods if deemed
        # a practical risk.
        os.replace(self.temp_output_file.driver.open_path, self.driver.open_path)
        self.temp_output_file = None

    def OpenReadAhead(self):
        # Called by open() and dup()
        if self.driver.fd < 0:
            self.EOF = True
            return
        if self.debug > 2:
            print('VirtFile.OpenReadAhead fd={} flags={} readable={}'.format(
				self.driver.fd, self.driver.open_flags, self.driver.is_readable()))
        if not self.driver.is_readable():
            # The file is not readable, so there is nothing to read
            self.EOF = True
            return
        if not self.readAheadMode:
            self.EOF = False
            return
        self.ReadBlock()
        if self.bufIx >= self.bufLen:
            self.EOF = True
        else:
            self.EOF = False

    def read(self, parmMaxBytes=BLOCKSIZE, LogPriority=None, LogSummary=None):
        if self.debug >= 3:
            print('VirtFile.read fd={} EOF={}'.format(self.driver.fd, self.EOF))
        if self.driver.fd < 0:
            raise VirtFileException(3, "read() for unopened file", self)
        wsData = self.driver.OsRead(parmMaxBytes)
        if not LogPriority:
            LogPriority = self.logPriority
        if not LogSummary: LogSummary = self.logSummary
        if LogPriority == -1:
            LogPriority = None
        if LogPriority or LogSummary:
            if not LogPriority:
                LogPriority = syslog.LOG_DEBUG
            if LogSummary and (not self.logForceDetail):
                syslog.syslog(LogPriority, "Read %d bytes" % len(wsData))
            else:
                syslog.syslog(LogPriority,
                              utils.DumpFormat("RD: " + wsData, Unfold=True,
                                         oStripEOL=True, oEOL=self.EOL))
        return wsData

    def ReadBlock(self):
        if self.debug >= 3:
            print("VirtFile.ReadBlock(fd:%d)" % (
                                            self.driver.fd))
        self.bufLen = 0
        self.bufIx = 0
        if not self.driver.is_readable():
            return
        self.buf = self.read(self.bufSize)
        self.bufLen = len(self.buf)
        if self.debug >= 3:
            print("VirtFile.ReadBlock(fd:%d) len = %d" % (
                                            self.driver.fd, self.bufLen))
        if self.tFile and (self.bufLen > 0):
            self.tFile.write(self.buf)

    def flush(self):
        if self.debug >= 3:
            print("VirtFile.flush(fd:%d)" % (
                                            self.driver.fd))
        if self.driver.fd < 0:
            raise VirtFileException(2, "flush() for unopened file", self)
        return self.driver.OsFlush()

    def lock(self):
        if self.debug >= 3:
            print("VirtFile.lock(fd:%d)" % (
                                            self.driver.fd))
        if self.driver.fd < 0:
            raise VirtFileException(2, "lock() for unopened file", self)
        return self.driver.OsLock()

    def readblob(self):
        if self.bufIx >= self.bufLen:
          return self.read()
        else:
          wsBlob = self.buf[self.bufIx:self.bufLen]
          self.bufIx = self.bufLen
          return wsBlob

    def readlines(self):
        wsResult			= []
        while not self.EOF:
            wsLine			= self.readline()
            wsResult.append(wsLine)
        return wsResult

    def readln(self):
        return self.readline()

    def readline(self):
        # This buffer check shouldn't do anything unless this is a
        # socket where the prior readline() emptied the buffer.  For
        # regular files we would have done a read-ahead at the end of
        # the prior readline()
        if self.debug >= 3:
            print('VirtFile.readline(fd={} EOF={} ix={} len={})'.format(self.driver.fd, self.EOF,
						self.bufIx, self.bufLen))
        if self.bufIx >= self.bufLen: self.ReadBlock()
        if self.bufIx >= self.bufLen: self.EOF = True

        if self.EOF:
            if self.debug >= 2:
                print("VirtFile.readline(fd:%d) past EOF." % (self.driver.fd))
            return None
        wsEolLen			= len(self.EOL_bytes)

        wsLine				= b""
        while True:
            wsEOL_ix			= self.buf.find(self.EOL_bytes, self.bufIx)
            wsStartIx			= self.bufIx
            if wsEOL_ix >= 0:
                wsEndIx			= wsEOL_ix
                if not self.stripEOL:
                    wsEndIx		+= wsEolLen
                self.bufIx		= wsEOL_ix + wsEolLen
                wsLine			+= self.buf[wsStartIx:wsEndIx]
                break
            wsEndIx			= self.bufLen
            wsLine			+= self.buf[wsStartIx:wsEndIx]
            if (self.buf[wsEndIx-1] == self.EOL_bytes[0]) and (wsEolLen > 1):
                # The last character in the previous block was the first
                # character of EOL.  Check if the first character of the
                # next block is the final character.  This logic assumes
                # that EOL is a maximum of 2 characters long.
                self.ReadBlock()				# read next block
                if self.bufIx >= self.bufLen:		# EOF
                    # At EOF we have found first char of EOL, strip it (this is
                    # a very marginal case, but anything can happen.
                    if self.stripEOL:
                        wsLine		= wsLine[:len(wsLine)-1]
                    break
                if self.buf[self.bufIx] == self.EOL_bytes[1]:
                    if self.stripEOL:
                        wsLine		= wsLine[:len(wsLine)-1]
                    else:
                        wsLine		+= self.wsEOL_bytes[1]
                    self.bufIx += 1				# advance pointer past EOL
                    break
                else:
                    self.ReadBlock()				# read next block
                    if self.bufIx >= self.bufLen:
                        break						# EOF

        # We get here after break from while loop at end of line.
        # wsLine is still a bytes class object.
        self.srcLineCt += 1
        if self.printSrc: print("%3d %s" % (self.srcLineCt, wsLine))
        if self.readAheadMode:
            # Can't read ahead if a socket because it blocks instead
            # of returning null buffer.  Sockets need other mechanism
            # to check EOF.
            if self.bufIx >= self.bufLen: self.ReadBlock()
            if self.bufIx >= self.bufLen: self.EOF = True
        if self.debug >= 4:
            print("VirtFile.readline(fd:%d) len = %d '%s'" % (
					self.driver.fd, len(wsLine), wsLine))
        if not self.stripEOL:
            # This is only needed for the last line of the filei which is often missing EOL.
            # Insert an EOL if its not there, so the last line isn't
            # a special case where EOL may be missing.
            wsEolLen			= len(self.EOL)
            if wsLine:
                if wsLine[-wsEolLen:] != self.EOLi_bytes:
                    wsLine		+= self.EOL_bytes
        return wsLine.decode('utf-8')					# return as string

    def reset(self):
        # reset() retains the definition of the file's access rules and
        # closes the file.  It initializes the i/o state of postion,
        # bytes written, etc.
        #
        if self.debug >= 3:
            print('VirtFile.reset(fd={})'.format(self.driver.fd))
        if self.driver.fd >= 0: self.close()
        wsEOL_bytes = self.EOL_bytes
        wsLogForceDetail = self.logForceDetail
        wsLogPriority = self.logPriority
        wsLogSummary = self.logSummary
        wsReadAheadMode = self.readAheadMode
        self.__init__(driver=self.driver, debug=self.debug)
        self.EOL_bytes = wsEOL_bytes
        self.logForceDetail = wsLogForceDetail
        self.logPriority = wsLogPriority
        self.logSummary = wsLogSummary
        self.readAheadMode = wsReadAheadMode

    def seek(self, parmOfs, whence=0):
        if self.debug >= 3:
            print("VirtFile.seek(fd:%d, %d, %d)" % (
                                            self.driver.fd, parmOfs, whence))
        if self.driver.fd < 0:
            raise VirtFileException(2, "seek() for unopened file", self)
        return self.driver.OsLseek(parmOfs, whence)

    def tee(self, parmSrcFile):
        if self.debug >= 3:
            print("VirtFile.tee(%s)" % (
                                            repr(parmSrcFile)))
        self.tFile = parmSrcFile
        # Write first block read during mail file open
        if self.tFile and (self.bufLen > 0):
            self.tFile.write(self.buf)

    def tell(self):
        if self.debug >= 3:
            print("VirtFile.tellfd:%d)" % (
                                            self.driver.fd))
        if self.driver.fd < 0:
            raise VirtFileException(2, "tell() for unopened file", self)
        return self.driver.OsTell()

    def truncate(self, parmOfs):
        if self.debug >= 3:
            print("VirtFile.truncate(fd:%d, %d)" % (
                                            self.driver.fd, parmOfs))
        if self.driver.fd < 0:
            raise VirtFileException(2, "truncate() for unopened file", self)
        return self.driver.OsLtruncate(parmOfs)

    def unlock(self):
        if self.debug >= 3:
            print("VirtFile.unlock(fd:%d)" % (
                                            self.driver.fd))
        if self.driver.fd < 0:
            raise VirtFileException(2, "unlock() for unopened file", self)
        return self.driver.OsUnlock()

    def write(self, parmData, LogPriority=None, LogSummary=None):
        if self.debug >= 3:
            print("VirtFile.write(fd:%d)" % (
                                            self.driver.fd))
        if self.driver.fd < 0:
            raise VirtFileException(2, "write() for unopened file", self)
        if not LogPriority:
            LogPriority = self.logPriority
        if LogPriority == -1: LogPriority = None
        if LogPriority or LogSummary:
            if not LogPriority:
                LogPriority = syslog.LOG_DEBUG
            if LogSummary and (not self.logForceDetail):
                syslog.syslog(LogPriority, "Write %d bytes" % len(wsData))
            else:
                syslog.syslog(LogPriority,
                              utils.DumpFormat("WR: " + parmData, Unfold=True,
                                         oStripEOL=True, oEOL=self.EOL))

        self.writeResult = self.driver.OsWrite(parmData)
        if self.writeResult != len(parmData):
            raise VirtFileException(1, "write() Error", self)
        self.writeSize += self.writeResult

    def writeln(self, str, LogPriority=None, LogSummary=None):
        if str is None:
            str = ''
        self.write(str.encode('utf-8') + self.EOL_bytes, LogPriority=None, LogSummary=None)


if __name__ == "__main__":
    pass
