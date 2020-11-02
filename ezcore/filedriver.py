#!/usr/bin/python
#############################################
#
#  FileDriver Module
#
#
#  FEATURES
#	A FileDriver is a driver for bzVirtFile for os file descriptors.
#	It is intended as a drop in replacement for python #built-in file
#	objects, but with some system safety rules built-in.
#
#  WARNINGS
#
#
#  Copyright (C) 2001 by Albert B. Margolis - All Rights Reserved
#
#  01/19/2002:  Initial Release
#  01/27/2002:  Add OsLseek() for bzBdamFile class
#  02/20/2004:  Add bzBlobFileDriver class so file-like operation
#		can be applied to a blob.  Initial need is for
#		reading files delivered by HTTP.
#  05/14/2006:  Add OsLseek() and OsTell() to blob driver to
#		support Python Image Library access to uploaded
#		images without creating a physical file.
#  09/19/2006:  Allow write to blob driver to allow capture of
#		file output. OsWrite()
#  05/12/2013:  Add OsLock, OsUnlock, OsTruncate, OsFlush to support
#		incremental counter in a file. Need to make sure
#		that these are compatible with PHP. Python docs mentions
#		POSIX locks and ioctl locks without clarity if different.
#		Also seems to have a set that specifies parts of a file.
#		Also need to research difference between flush and fsync.
#
#############################################

import fcntl
import os
import tempfile

STDIN = "__stdin__"
STDIN_FD = 0
STDOUT = "__stdout__"
STDOUT_FD = 1
INVALID_FD = -1

# Modes are used with POSIX fopen() - extended a bit here

MODE_CLOSED = 'xx'
MODE_R = 'r'			# read an existing file
MODE_RR = 'rr'          # read an existing file and neatly replace it
MODE_W = 'w'			# write - making new file or erasing existing
MODE_A = 'a'			# write - making new file or appending to existing
MODE_C = 'c'			# create - write a new file, fail if it exists - not a POSIX mode
MODE_RW = 'r+'			# read/write an existing file
MODE_RWA = 'a+'			# read/write an existing file
MODE_RWM = 'w+'			# read/write - making new file or erasing existing
MODE_T = 't'			# safely create a temporary file - not a POSIX mode

# Flags are used by POSIX file descriptor open()
# MODE_T is not in FLAGS because it isn't handled by OsOpen()

FLAGS = {}
FLAGS[MODE_R] = os.O_RDONLY
FLAGS[MODE_W] = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
FLAGS[MODE_A] = os.O_WRONLY | os.O_CREAT | os.O_APPEND
FLAGS[MODE_C] = os.O_WRONLY | os.O_CREAT | os.O_EXCL
FLAGS[MODE_RW] = os.O_RDWR
FLAGS[MODE_RWA] = os.O_RDWR | os.O_CREAT | os.O_APPEND
FLAGS[MODE_RWM] = os.O_RDWR | os.O_CREAT | os.O_TRUNC

def is_writeable(flags):
    FLAGS_WRITEABLE = os.O_WRONLY | os.O_RDWR
    return (flags & FLAGS_WRITEABLE) > 0

def is_readable(flags):
    FLAGS_READABLE = os.O_RDONLY | os.O_RDWR
    if flags == os.O_RDONLY:
        # O_RDONLY is zero, so bit mask does't identify it
        return True
    return (flags & FLAGS_READABLE) > 0


class FileDriverException:
    def __init__(self, code, message, sysfile):
        self.code = code
        self.message = message
        self.sysfile = sysfile


class FileDriver(object):
    __slots__ = ('debug', 'encoding', 'fd', 'open_flags', 'parent', 'path')

    def __init__(self, Encoding='ascii', parent=None, debug=0):
        self.encoding = Encoding
        self.debug = debug
        self.fd = INVALID_FD
        self.open_flags = None
        self.path = None           # FQN of opened file
        self.parent = parent

    @property
    def is_open(self):
        if self.fd >= STDIN_FD:
            return True
        else:
            return False

    @property
    def is_readable(self):
        return is_readable(self.open_flags)

    @property
    def is_writeable(self):
        return is_writeable(self.open_flags)

    def OsClose(self):
        self.OsFsync()
        result = os.close(self.fd)
        self.fd = INVALID_FD            # leave open_flags and path
        return result

    def OsDup(self, parent, debug=0):
        wsDup = FileDriver(
            Encoding=self.encoding,
            parent=self.parent,
            debug=self.debug)
        if self.fd >= 0:
            wsDup.fd = os.dup(self.fd)
        else:
            wsDup.fd = INVALID_FD
        wsDup.open_flags = self.open_flags
        wsDup.path = self.open_flags
        return wsDup

    def OsFsync(self):
        if self.fd < 0:
            return 0
        if not self.is_writeable:
            return 0				# not a writeable file
        if self.fd == STDOUT_FD:
            return 0				# maybe we should flush() prob prob not
        return os.fsync(self.fd)

    def OsLock(self):
        fcntl.flock(self.fd, os.LOCK_EX)

    def OsLseek(self, parmOfs, whence=0):
        # whence: 0=relative beginning of file, 1=relative current, 2=from EOF
        os.lseek(self.fd, parmOfs, whence)

    def OsOpen(self, parmFn, parmFlags, parmPermissions=None):
        """
        Calls OS file open() with a wrapper to provide consistency
        for special files and automatically remember file state.

        Returns the file descriptor which is >= 0 for success or a
        negative number for failure.

        Symetry must be maintained between OsOpen() and OsTemp()
        """
        if self.debug >= 3:
            print("FileDriver.OsOpen(%s, %d, %s)" % (
                parmFn, parmFlags, parmPermissions))

        self.fd = INVALID_FD
        self.open_flags = parmFlags
        self.path = parmFn
        #
        # stdin, stdout and stderr are always open, don't call os.open()
        #
        if self.path == STDIN:
            if self.open_flags != FLAGS[MODE_R]:
                if self.debug >= 1:
                    print(
                        "FileDriver.open(%s, %d, %s) ** invalid flags for stdin" %
                        (parmFn, parmFlags, parmPermissions))
                return self.fd
            self.fd = STDIN_FD
            return self.fd
        if self.path == STDOUT:
            if self.open_flags != FLAGS[MODE_W]:
                if self.debug >= 1:
                    print(
                        "FileDriver.open(%s, %d, %s) ** invalid flags for stdout" %
                        (parmFn, parmFlags, parmPermissions))
                return self.fd
            self.fd = STDOUT_FD
            return self.fd

        #try:
        self.path = os.path.abspath(self.path)
        try:
            if parmPermissions is None:
                self.fd = os.open(self.path, self.open_flags)
            else:
                self.fd = os.open(self.path, self.open_flags, parmPermissions)
        except FileNotFoundError:
            return INVALID_FD
        if self.fd >= 0:
            #self.path = os.readlink('/proc/self/fd/{}'.format(self.fd))
            if self.debug >= 1:
                print('FileDriver.open() fd={} flags={} permissions={} path={} ** sucessful'.format(
                    self.fd, self.open_flags, parmPermissions, self.path))
        else:
            self.path = None
            if self.debug >= 1:
                print("FileDriver.open(%s, %d, %s) ** failed" % (
                    parmFn, parmFlags, parmPermissions))

        return self.fd

    def OsOpenMode(self, path, mode, permissions=None):
        try:
            flags = FLAGS[mode]
        except IndexError:
            raise Exception("open() INVALID MODE")
        return self.OsOpen(path, flags, parmPermissions=permissions)

    def OsOpenTemp(self):
        # Symetry must be maintained between OsOpen() and OsTemp()
        # !!!! NOT TESTED ***********
        # This should be used for process temp files
        (self.fd, self.path) = tempfile.mkstemp(suffix='.tmp', prefix='tmp_', dir=None, text=False)
        self.open_flags = os.O_WRONLY
        return self.fd

    def OsRead(self, parmMaxBytes):
        return os.read(self.fd, parmMaxBytes)

    def OsTruncate(self, parmOfs):
        os.ftruncate(self.fd, parmOfs)

    def OsUnlock(self):
        fcntl.flock(self.fd, os.LOCK_UN)

    def OsWrite(self, data):
        """ Write a byte array or string to a file descriptor. """
        if isinstance(data, str):
            data = data.encode()
        return os.write(self.fd, data)


class bzBlobFileDriver(object):
    __slots__ = (
        'blob',
        'blobIx',
        'blobLen',
        'debug',
        'encoding',
        'fd',
        'open_flags',
        'parent')

    def __init__(self, Encoding='ascii', parent=None, debug=0):
        self.blob = None
        self.blobLen = 0
        self.blobIx = 0
        self.encoding = Encoding
        self.fd = INVALID_FD
        self.debug = debug
        self.open_flags = None
        self.parent = parent
        self.ClearBlob()					# encoding must be set

    def AddBlob(self, parmBlob):
        self.blob += parmBlob
        self.blobLen = len(self.blob)

    def ClearBlob(self):
        if self.encoding == 'ascii':
            self.blob = ""
        else:
            self.blob = ""
        self.blobLen = 0
        self.blobIx = 0

    def GetAndClearBlob(self):
        wsBlob = self.blob
        self.ClearBlob()
        return wsBlob

    def OsClose(self):
        return 0

    def OsOpen(self, parmFn, parmFlags, parmPermissions=None):
        if self.debug >= 3:
            print("bzBlobFileDriver.OsOpen(%s, %d, %s)" % (
                parmFn, parmFlags, parmPermissions))

        self.open_flags = parmFlags
        self.fd = STDOUT_FD
        return 0

    def OsRead(self, parmMaxBytes):
        if self.blobIx >= self.blobLen:
            return ""
        wsStart = self.blobIx
        self.blobIx += parmMaxBytes
        return self.blob[wsStart:self.blobIx]

    def OsWrite(self, parmData):
        self.blob += parmData
        self.blobLen = len(self.blob)
        self.blobIx = self.blobLen
        return len(parmData)

    def OsLseek(self, parmOfs, whence=0):
        if whence == 1:
            self.blobIx += parmOfs
        elif whence == 2:
            self.blobIx = self.blobLen - parmOfs
        else:						# default 0, absolute
            self.blobIx = parmOfs
        if self.blobIx < 0:
            self.blobIx = 0
        if self.blobIx > self.blobLen:
            self.blobIx = self.blobLen
        return self.blobIx

    def OsTell(self):
        return self.blobIx


if __name__ == "__main__":
    pass
