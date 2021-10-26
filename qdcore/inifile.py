"""
Functions to read and write ini files.

This module is somewhat out of place in ezutils instead of
ezcore because it is need for ezstart, potentially before Python
importing is configured by the virtual environment.
"""

import os

from . import qdconst
from . import qddict
from . import textfile

#
# INI File Support
#
# These should be the only methods that read/write INI files.
#
# In order to be fully supported, the data objects should include the following:
#   _exportFilePath
#   MakeChildTuple()
#   items()
#
# To the degree possible, these methods should also work with general Python types.
#


def AsIniText(parmData, Level=0, ParentName=''):
    wsIni = ''
    wsChildRecordNames = []
    for (wsChildName, wsChildData) in list(parmData.items()):
        if hasattr(parmData, 'items'):
            wsChildRecordNames.append(wsChildName)
        else:
            # This is an atomic data type
            wsIni += '%s = %s\n' % (wsChildName, wsChildData)
    for wsThisRecordName in wsChildRecordNames:
        if Level > 0:
            wsSectionName = ParentName + '.' + wsThisRecordName
        else:
            wsSectionName = wsThisRecordName
        wsIni += '[%s]\n' % (wsThisRecordName)
        wsIni += AsIniText(parmData[wsThisRecordName], Level=Level+1,
                           ParentName=wsSectionName)
    return wsIni

INI_PARSE_STATE_INIT		= 0
INI_PARSE_STATE_NORMAL_LINE	= 1
INI_PARSE_STATE_COLLECT_MULTI	= 3

def read_ini_directory(dir, ext='conf', target=None, debug=0):
    """
    Read a hierarchy of conf files into a hierarchy of dict-like objects.

    This is convenient for code where we want to see the full configuration.
    In order to be able to write back, we will need a trail of breadcrumbs
    in order to tell if a sub-dict represents a different file or directory or
    just a section within an ini file.
    """
    if target is None:
        target = qddict.EzDict()
    if debug >= 1:
        print(read_ini_directory, ext, target)
    dir = os.path.abspath(dir)
    set_target_path(target, True, dir)
    ini_ext = '.' + ext
    for this_item in os.listdir(dir):
        this_path = os.path.join(dir, this_item)
        if this_item.endswith(ini_ext):
            if debug >= 1:
                print('read_ini_directory', 'FILE', this_item, target)
            ext_pos = this_item.rfind(ini_ext)
            this_container = this_item[:ext_pos]
            child_target = target.__class__()
            target[this_container] = child_target
            read_ini_file(file_name=this_item, dir=dir, target=child_target, debug=debug)
        elif os.path.isdir(this_path):
            if debug >= 1:
                print('read_ini_directory', 'DIR', this_item, target)
            child_target = target.__class__()
            target[this_item ] = child_target
            read_ini_directory(dir=this_path, ext=ext, target=child_target, debug=debug)
    return target

def read_ini_file(file_name=None, dir=None, target=None,
                  hierarchy_separator='.',
                  exe_controller=None, debug=0):
    """ Load an ini text file into a hierarchy of map type objects. """
    if target is None:
        target = qddict.EzDict()
    ini_reader = IniReader(file_name=file_name, dir=dir, target=target,
                           hierarchy_separator=hierarchy_separator,
                           exe_controller=exe_controller, debug=debug)
    if ini_reader.load():
        return ini_reader.target
    else:
        return None

def set_target_path(target, is_dir, path):
    if hasattr(target, '_is_directory'):
        setattr(target, '_is_directory', is_dir)
    if hasattr(target, '_source_file_path'):
        setattr(target, '_source_file_path', path)

class IniReader:
    __slots__ = ('active_target', 'active_key', 'current_line',
                 'debug', 'dir', 'exe_controller', 'file_name',
                 'hierarchy_separator', 'multi_line_signature',
                 'state', 'target')

    def __init__(self, file_name=None, dir=None, target=None,
                 hierarchy_separator='.',
                 exe_controller=None, debug=0):
        self.active_target = target
        self.active_key = None
        self.current_line = None
        self.debug = debug
        self.dir = dir
        self.exe_controller = exe_controller
        self.file_name = file_name
        self.hierarchy_separator = hierarchy_separator
        self.multi_line_signature = None
        self.state = INI_PARSE_STATE_INIT
        self.target = target

    def load(self, file_name=None, dir=None, target=None):
        if file_name is not None:
            self.file_name = file_name
        if dir is not None:
            self.dir = dir
        if target is not None:
            self.target = target
        if self.target is None:
            self.target = qddict.EzDict()
        if self.debug >= 1:
            print('IniReader', 'load', self.file_name, self.dir)
        f = textfile.open_read(file_name=self.file_name, dir=self.dir, source=self.target)
        if f is not None:
            ini_lines = f.readlines()
            f.close()
            for self.current_line in ini_lines:
                self.parse_line()
            set_target_path(self.target, False, f.path)
            return True
        else:
            return False

    def err_message(self, msg):
        """ Record an error message. """
        if self.exe_controller is None:
            print(msg)
        else:
            self.exe_controller.errs.AddUserCriticalMessage(msg)

    def locate_active_target_section(self, section_name):
        """ Set self.active_target in a hierarchical data store. """
        parts = section_name.split(self.hierarchy_separator)
        self.active_target = self.target
        for this_part in parts:
            if not this_part in self.active_target:
                new_child = self.active_target.__class__()
                self.active_target[this_part] = new_child
                set_target_path(new_child, False, '')
            self.active_target = self.active_target[this_part]

    def start_section(self):
        pos2 = self.current_line.find(']', 1)
        if pos2 < 1:
            self.err_message('Invalid Ini section line "%s"'.format(self.current_line))
            return
        section_name = self.current_line[1:pos2].strip()
        self.locate_active_target_section(section_name)

    def add_key(self, key, value, is_list_value):
        if key in self.active_target:
            if is_list_value and isinstance(self.active_target[key], list):
                self.active_target[key].append(value)
                return
            self.err_message('Duplicate key in Ini file line "{}"'.format(self.current_line))
            return
        if is_list_value:
            self.active_target[key] = []
            if value is not None:
                self.active_target[key].append(value)
            return
        self.active_target[key] = value

    def start_multi_line(self):
        pos2 = self.current_line.find('=', 1)
        if pos2 < 1:
            self.err_messsage('Invalid Ini file line "%s"' % (self.current_line))
            return
        key = self.current_line[1:pos2].strip()
        if key == '':
            self.err_messsage('Invalid Ini file line "%s"' % (self.current_line))
            return
        self.add_key(key, None, True)
        self.multi_line_signature = "--%s--%s--".format(key, [])
        self.state = INI_PARSE_STATE_COLLECT_MULTI

    def normal_value(self):
        pos2 = self.current_line.find('=')
        if pos2 < 1:
            self.err_messsage('Invalid Ini file line "%s"' % (self.current_line))
            return
        key = self.current_line[:pos2].strip()
        if key[-2:] == '[]':
            key = key[:-2]
            is_list_value = True
        else:
            is_list_value = False
        value = self.current_line[pos2+1:].strip()
        try:
            value = int(value)
        except ValueError:
            value = value
        self.add_key(key, value, is_list_value)

    def parse_line(self):
        """ Parse self.current_line of the ini file. """
        if self.debug >= 1:
            print("^^^", self.current_line)
        if self.state == INI_PARSE_STATE_COLLECT_MULTI:
            # This is not required in file if the variable continues to EOF
            if this_line == self.multi_line_signature:
                self.state = INI_PARSE_STATE_INIT
            else:
                self.active_target[self.active_key].append(this_line)
            return
        if self.current_line == '':
            return
        elif self.current_line[0] == '#':
            return
        elif self.current_line[0] == '[':						# section start line
            self.start_section()
        elif self.current_line[0] == '=':
            self.start_multi_line()
        else:
            self.normal_value()

def write_ini_level(f, data, section_name=''):
    children = []
    if section_name != '':
        f.write('[{}]\n'.format(section_name))
    for key, value in data.items():
        try:
            child_data = value.items()
            children.append((key, value))
        except AttributeError:
            # We get here if value doesn't have an items method.
            # It's a scalar.
            if isinstance(value, list):
                for this_list_value in value:
                    f.write('{}[] = {}\n'.format(key, this_list_value))
            else:
                f.write('{} = {}\n'.format(key, value))
    for child_key, child_data in children:
        f.write('\n')
        child_section_name = child_key
        if section_name != '':
            child_section_name = section_name + '.'
        write_ini_level(f, child_data, section_name=child_section_name)

def write_ini_file(source, path=None, exe_controller=None):
      """ Write a hierarchy of dict-like data as an ini file. """
      if path is None:
          path = getattr(source, '_source_file_path', None)
      if path is None:
          raise ValueError("No path specified for output file.")
      if exe_controller is None:
          exe_controller = getattr(source, 'exe_controller', None)
      f = textfile.open_write_with_swap_file(path, backup=True)
      if f is None:
          err_msg = "Unable to open output INI file '{}'.".format(path)
          if exe_controller is None:
              raise Exception(err_msg)
          else:
              exe_controller.errs.AddUserCriticalMessage(err_msg)
              return False
      write_ini_level(f, source)
      f.keep()
      return True
