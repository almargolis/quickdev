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
import time

from ezcore import filedriver
from ezcore import utils

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


class VirtFileException(Exception):
    def __init__(self, code, message, virtual_file):
        self.code = code
        self.message = message
        self.virtual_file = virtual_file
        if virtual_file.driver is None:
            self.path = ''
        else:
            self.path = virtual_file.driver.path


class VirtFile(object):
    __slots__ = (
                    'buf', 'bufIx', 'bufLen', 'bufSize',
                    'debug', 'dont_close', 'driver', 'EOF', 'eol_bytes',
                    'funcResult',
                    'lock_file', 'lock_retries', 'lock_wait_secs',
                    'logForceDetail', 'logPriority', 'logSummary',
                    'make_backup', 'open_mode', 'print_source',
                    'readAheadMode', 'recno',
                    'source_line_ct', 'strip_eol',
                    'swap_output_file', 'tFile', 'writeResult', 'writeSize'
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
        self.dont_close = False
        self.eol_bytes = '\n'.encode('utf-8')
        self.lock_file = None
        self.lock_retries = 10
        self.lock_wait_secs=0.01
        self.logForceDetail = False
        self.logPriority = None
        self.logSummary = None
        self.make_backup = False
        self.open_mode = None
        self.print_source = False
        self.readAheadMode = True
        self.strip_eol = False
        self.tFile = None
        # I/O State Properties
        self.buf = ""
        self.bufIx = 0
        self.bufLen = 0
        self.bufSize = BLOCKSIZE
        self.EOF = True
        self.funcResult = 0
        self.recno = 0
        self.source_line_ct = 0
        self.swap_output_file = None
        self.writeResult = -1
        self.writeSize = 0

    def __del__(self):
        self.close()		# make sure self.tFile complete

    def __repr__(self):
         return '[VirtFile {}:{}]'.format(self.fd, self.path)

    def drop(self):
        self.safe_close(abandon=True)

    def keep(self):
        self.safe_close(abandon=False)

    def safe_close(self, abandon=True):
        if self.debug >= 3:
            if self.tFile:
                try:
                    tfile_fd = self.tFile.fd
                except: tfile_fd = filedriver.INVALID_FD
                try:
                    tfile_path = self.tFile.path
                except: tfile_path = ""
                tfile_desc = "t-file {}:%{}".format(tfile_fd, tfile_path)
            else:
                tfile_desc = "no t-file"
            print("VirtFile.safe_close({}: {}) {}".format(
                self.driver.fd, self.driver.path, tfile_desc))
        if self.tFile:			# write rest of file copy
            while self.bufLen > 0:
                self.ReadBlock()
            self.tFile.close()
            self.tFile = None

        if self.driver.is_open and not self.dont_close:
            # It may be that there is no open primary file but
            # a swap file or lock file needs to be handled.
            self.driver.OsClose()
        self.EOF = True
        self.close_swap_file(abandon=abandon)
        if self.is_locked:
            self.lock_clear()

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
            self.dont_close = True
        else:
            self.dont_close = False
        self.debug = parmSrcFile.debug
        self.eol_bytes = parmSrcFile.eol_bytes
        self.logForceDetail = parmSrcFile.logForceDetail
        self.logPriority = parmSrcFile.logPriority
        self.logSummary = parmSrcFile.logSummary
        self.readAheadMode = parmSrcFile.readAheadMode
        self.tFile = parmSrcFile.tFile

        self.initialize_readahead()
        return self.driver.fd			# default is -1

    @property
    def EOL(self):
        return self.eol_bytes.decode('utf-8')

    @EOL.setter
    def EOL(self, str):
        self.eol_bytes = str.encode('utf-8')

    @property
    def fd(self):
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

    @property
    def is_locked(self):
        if self.lock_file is None:
            return False
        return self.lock_file.is_open

    @property
    def path(self):
        if self.driver is None:
            return ''
        return self.driver.path

    def lock_clear(self):
        """ Clear file lock. Makes sure to only clear locks set by this process. """
        if not self.is_locked:
            raise VirtFileException(1, "Attempt to clear non-existant lock.", self)
        self.lock_file.OsClose()
        os.unlink(self.lock_file.path)
        self.lock_file = None

    def lock_set(self, path, no_wait=False):
        """Create lock file. Return True or False indicating success. """
        try_ct = 0
        if no_wait:
            retries = 0
            wait_secs = 0
        else:
            retries = self.lock_retries
            wait_secs = self.lock_wait_secs
        if self.lock_file is None:
            self.lock_file = self.driver.__class__(parent=self)
        while try_ct <= retries:
            if self.lock_file.OsOpenMode(path+'.lock', filedriver.MODE_C) > 0:
                return True
            try_ct += 1
            time.sleep(wait_secs)
        return False

    def open(self, file_name=None, mode=None, dir=None, source=None,
             backup=False, lock=False, no_wait=False, swap=False):
        """ Open file. Return True or False to indicate result. """
        self.make_backup = backup
        self.open_mode = mode
        path = None
        if file_name is None:
            if source is not None:
                if hasattr(source, '_source_file_path'):
                    path = getattr(source, '_source_file_path', None)

        elif dir is None:
            path = file_name
        else:
            path = os.path.join(dir, file_name)
        if path is None:
            raise VirtFileException(1, "No path specified for open.", self)
        if self.debug >= 3:
            print("VirtFile.open(%s, %s)" % (path, self.open_mode))

        # MODE_RR open a file for input and a swap file for output.
        # MODE_S is output only using a swap file.
        # In both cases, if successful the swap file replaces the
        # original file and the original is optionally saved as
        # a *.bak backup file.
        # When writing to a swap file, close() abandons the
        # swap files and leave any original as it was.
        # Call keep() if everything was succesful and the output
        # is to be kept.
        if self.open_mode == filedriver.MODE_RR:
            os_mode = filedriver.MODE_R
            swap = True
            lock = True
        elif self.open_mode == filedriver.MODE_S:
            os_mode = filedriver.MODE_N
            swap = True
            lock = True
        else:
            os_mode = self.open_mode
        if lock:
            if not self.lock_set(path, no_wait=no_wait):
                return False
        if swap:
            if not self.create_swap_output(path):
                if lock:
                    self.lock_clear()
                return False
        if self.driver.OsOpenMode(path, os_mode) >= 0:
            self.initialize_readahead()
            if source is not None:
                if hasattr(source, '_source_file_path'):
                    setattr(source, '_source_file_path', path)
            return True
        self.EOF = True
        if mode == filedriver.MODE_N:
            # driver is only used to hold path.
            # we are probably writing to a swap file.
            if source is not None:
                if hasattr(source, '_source_file_path'):
                    setattr(source, '_source_file_path', path)
            return True
        # We get here if the open was unsuccesful in order to
        # clean up the temporary files we created.
        if swap:
            self.close_swap_file(abandon=True)
        if lock:
            self.lock_clear()
        return False

    def create_swap_output(self, path, debug=0):
        """
        Open a temporary output file with the expectation that
        this file will replace the "real" file if the process
        is succesful.

        This has two purposes:
        *In the event of a program failure, the original target
         file is left untouched.
        *In a multi-tasking environment, it avoids a race condition
         where readers get mangled data by reading a file that
         is being rewritten in place.

         open_swap_file() should only be called after the primary file
         is succesfully opened for input and locked.
        """
        # This creates a file with an easily predictable name. This is suitable
        # command line tools, not CGI or other public facing processes.
        if not self.is_locked:
            raise VirtFileException(1, "Attempt to create swap file for unlocked file.", self)
        if self.swap_output_file is not None:
            raise VirtFileException(1, "Attempt to create redundant swap file.", self)
        swap_file_path = path + '.swap'
        swap_output_file = VirtFile(debug=debug, driver=self.driver.__class__(parent=self))
        if swap_output_file.open(swap_file_path, filedriver.MODE_C) is None:
            return None
        self.swap_output_file = swap_output_file
        return self.swap_output_file

    def close_swap_file(self, abandon=False):
        if self.debug >= 3:
            print("close_swap_file {} {}".format(abandon, self.swap_output_file))
        if self.swap_output_file is None:
            # we didn't actually open a temp file. We are all done now.
            return
        self.swap_output_file.close()
        if abandon:
            os.unlink(self.swap_output_file.path)
            self.swap_output_file = None
            return
        if self.make_backup:
            backup_file_path = utils.ChangeFileNameExtension(self.driver.path, 'bak')
            if os.path.exists(self.driver.path):
                if os.path.exists(backup_file_path):
                    os.remove(backup_file_path)
                # os.link (make hard link) creates the backup without deleting the
                # original file directory entry, so the original file is still readable.
                os.link(self.driver.path, backup_file_path)
        # os.rename replaces the original file directory entry.
        # It also gets rid of the temporary file directory entry, but not
        # the file contents.
        # This process means that some version of the original file is
        # always available. This is desireable when we are in the process of
        # updating web pages so nobody ever gets a 404 error.
        # It leaves open a possible race condition if the second opener is also an
        # editor. That can be mitigated with locks or other methods if deemed
        # a practical risk.
        os.replace(self.swap_output_file.driver.path, self.driver.path)
        self.swap_output_file = None

    def initialize_readahead(self):
        # Called by open() and dup()
        if self.driver.fd < 0:
            self.EOF = True
            return
        if self.debug > 2:
            print('VirtFile.initialize_readahead fd={} flags={} readable={}'.format(
				self.driver.fd, self.driver.open_flags, self.driver.is_readable()))
        if not self.driver.is_readable:
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
                                         ostrip_eol=True, oEOL=self.EOL))
        return wsData

    def ReadBlock(self):
        if self.debug >= 3:
            print("VirtFile.ReadBlock(fd:%d)" % (
                                            self.driver.fd))
        self.bufLen = 0
        self.bufIx = 0
        if not self.driver.is_readable:
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
        """
        Request OS flock() with exclusive flag.

        This functionality is not well supported by EzDev.
        Implementation is mainly up to the application.
        Use the lock_file feature of open() for an easier to understand
        lock at the cost of a performance hit and some crudeness.
        """
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
        wsEolLen			= len(self.eol_bytes)

        wsLine				= b""
        while True:
            wsEOL_ix			= self.buf.find(self.eol_bytes, self.bufIx)
            wsStartIx			= self.bufIx
            if wsEOL_ix >= 0:
                wsEndIx			= wsEOL_ix
                if not self.strip_eol:
                    wsEndIx		+= wsEolLen
                self.bufIx		= wsEOL_ix + wsEolLen
                wsLine			+= self.buf[wsStartIx:wsEndIx]
                break
            wsEndIx			= self.bufLen
            wsLine			+= self.buf[wsStartIx:wsEndIx]
            if (self.buf[wsEndIx-1] == self.eol_bytes[0]) and (wsEolLen > 1):
                # The last character in the previous block was the first
                # character of EOL.  Check if the first character of the
                # next block is the final character.  This logic assumes
                # that EOL is a maximum of 2 characters long.
                self.ReadBlock()				# read next block
                if self.bufIx >= self.bufLen:		# EOF
                    # At EOF we have found first char of EOL, strip it (this is
                    # a very marginal case, but anything can happen.
                    if self.strip_eol:
                        wsLine		= wsLine[:len(wsLine)-1]
                    break
                if self.buf[self.bufIx] == self.eol_bytes[1]:
                    if self.strip_eol:
                        wsLine		= wsLine[:len(wsLine)-1]
                    else:
                        wsLine		+= self.wseol_bytes[1]
                    self.bufIx += 1				# advance pointer past EOL
                    break
                else:
                    self.ReadBlock()				# read next block
                    if self.bufIx >= self.bufLen:
                        break						# EOF

        # We get here after break from while loop at end of line.
        # wsLine is still a bytes class object.
        self.source_line_ct += 1
        if self.print_source: print("%3d %s" % (self.source_line_ct, wsLine))
        if self.readAheadMode:
            # Can't read ahead if a socket because it blocks instead
            # of returning null buffer.  Sockets need other mechanism
            # to check EOF.
            if self.bufIx >= self.bufLen: self.ReadBlock()
            if self.bufIx >= self.bufLen: self.EOF = True
        if self.debug >= 4:
            print("VirtFile.readline(fd:%d) len = %d '%s'" % (
					self.driver.fd, len(wsLine), wsLine))
        if not self.strip_eol:
            # This is only needed for the last line of the filei which is often missing EOL.
            # Insert an EOL if its not there, so the last line isn't
            # a special case where EOL may be missing.
            wsEolLen			= len(self.EOL)
            if wsLine:
                if wsLine[-wsEolLen:] != self.EOLi_bytes:
                    wsLine		+= self.eol_bytes
        return wsLine.decode('utf-8')					# return as string

    def reset(self):
        # reset() retains the definition of the file's access rules and
        # closes the file.  It initializes the i/o state of postion,
        # bytes written, etc.
        #
        if self.debug >= 3:
            print('VirtFile.reset(fd={})'.format(self.driver.fd))
        if self.driver.fd >= 0: self.close()
        wseol_bytes = self.eol_bytes
        wsLogForceDetail = self.logForceDetail
        wsLogPriority = self.logPriority
        wsLogSummary = self.logSummary
        wsReadAheadMode = self.readAheadMode
        self.__init__(driver=self.driver, debug=self.debug)
        self.eol_bytes = wseol_bytes
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

    def write(self, data, LogPriority=None, LogSummary=None):
        if self.swap_output_file is not None:
            self.swap_output_file.write(data=data, LogPriority=LogPriority,
                                        LogSummary=LogSummary)
            return
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
                syslog.syslog(LogPriority, "Write %d bytes" % len(data))
            else:
                syslog.syslog(LogPriority,
                              utils.DumpFormat("WR: " + data, Unfold=True,
                                         ostrip_eol=True, oEOL=self.EOL))

        self.writeResult = self.driver.OsWrite(data)
        if self.writeResult != len(data):
            raise VirtFileException(1, "write() Error", self)
        self.writeSize += self.writeResult

    def writeln(self, str, LogPriority=None, LogSummary=None):
        if str is None:
            str = ''
        self.write(str.encode('utf-8') + self.eol_bytes, LogPriority=None, LogSummary=None)
