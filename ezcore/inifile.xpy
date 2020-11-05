"""
Functions to read and write ini files.

This module is somewhat out of place in ezutils instead of
ezcore because it is need for ezstart, potentially before Python
importing is configured by the virtual environment.
"""

import ezconst
import textfile

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

class EzIni():
    __slots__ = ('_data', $'ezconst.SERIALIZED_FILE_PATH$)

    def __init__(self, path=None):
        self._data = {}
        self.$ezconst.SERIALIZED_FILE_PATH$ = path

    def get_dict(self, key):
        parts = key.split('.')
        data = self._data
        for this in parts[:-1]:
            data = data[this]
        return data

    def __getitem__(self, key):
        data = self.get_dict(key)
        return data[key[-1]]

    def __setitem__(self, key, value):
        data = self.get_dict(key)
        data[key[-1]] = value

    def write(self, path=None):
        if path is not None:
            pass

def AsIniText(parmData, Level=0, ParentName=''):
  wsIni				= ''
  wsChildRecordNames		= []
  for (wsChildName, wsChildData) in list(parmData.items()):
    if hasattr(parmData, 'items'):
      wsChildRecordNames.append(wsChildName)
    else:
      # This is an atomic data type
      wsIni			+= '%s = %s\n' % (wsChildName, wsChildData)
  for wsThisRecordName in wsChildRecordNames:
    if Level > 0:
      wsSectionName		= ParentName + '.' + wsThisRecordName
    else:
      wsSectionName		= wsThisRecordName
    wsIni			+= '[%s]\n' % (wsThisRecordName)
    wsIni			+= AsIniText(parmData[wsThisRecordName], Level=Level+1, ParentName=wsSectionName)
  return wsIni

INI_PARSE_STATE_INIT		= 0
INI_PARSE_STATE_NORMAL_LINE	= 1
INI_PARSE_STATE_COLLECT_MULTI	= 3

def read_ini_file(file_name=None, dir=None, target={},
                  hierarchy_separator=$'ezconst.HIERARCHY_SEPARATOR_CHARACTER$,
                  exe_controller=None, debug=0):
    """ Load an ini text file into a hierarchy of map type objects. """
    ini_reader = IniReader(file_name=file_name, dir=dir,
                           hierarchy_separator=hierarchy_separator,
                           exe_controller=exe_controller, debug=debug)
    if ini_reader.load(file_name=file_name, dir=dir):
        return ini_reader.target
    else:
        return None

class IniReader:
    def __init__(self, file_name=None, dir=None, target={},
                 hierarchy_separator=$'ezconst.HIERARCHY_SEPARATOR_CHARACTER$,
                 exe_controller=None, debug=0):
        self.target = target
        self.active_target = target
        self.active_key = None
        self.current_line = None
        self.exe_controller = exe_controller
        self.hierarchy_separator = hierarchy_separator
        self.multi_line_signature = None
        self.state = INI_PARSE_STATE_INIT
        if file_name is not None:
            self.load(file_name=file_name, dir=dir)

    def load(self, file_name, dir=None):
        f = textfile.open_read(file_name=file_name, dir=dir, source=self.target)
        if f is not None:
            ini_lines = f.readlines()
            f.close()
            for self.current_line in ini_lines:
                self.parse_line()
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
                self.active_target[this_part] = {}
            self.active_target = self.active_target[this_part]

    def start_section(self):
        pos2 = self.current_line.find(']', 1)
        if pos2 < 1:
            self.err_message('Invalid Ini section line "%s"'.format(self.current_line))
            return
        section_name = self.current_line[1:pos2].strip()
        self.locate_active_target_section(section_name)

    def add_key(self, key, value):
        if key in self.active_target:
            self.err_message('Duplicate key in Ini file line "{}"'.format(self.current_line))
        self.active_target[key] = value

    def start_multi_line(self):
        pos2 = self.current_line.find('=', 1)
        if pos2 < 1:
            self.err_messsage('Invalid Ini file line "%s"' % (self.current_line))
            return
        key = self.current_line[1:pos2].strip()
        self.add_key(key, [])
        self.multi_line_signature = "--%s--%s--".format(key, [])
        self.state = INI_PARSE_STATE_COLLECT_MULTI

    def normal_value(self):
        pos2 = self.current_line.find('=')
        if pos2 < 1:
            self.err_messsage('Invalid Ini file line "%s"' % (self.current_line))
            return
        key = self.current_line[:pos2].strip()
        value = self.current_line[pos2+1:].strip()
        try:
            value = int(value)
        except ValueError:
            value = value
        self.add_key(key, value)

    def parse_line(self):
        """ Parse self.current_line of the ini file. """
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
            f.write('{} = {}\n'.format(key, value))
    for child_key, child_data in children:
        f.write('\n')
        child_section_name = child_key
        if section_name != '':
            child_section_name = section_name + '.'
        write_ini_level(f, child_data, section_name=child_section_name)

def write_ini_file(source, path=None, $ezconst.EXE_CONTROLLER$=None):
      """ Write a hierarchy of dict-like data as an ini file. """
      if path is None:
          path = getattr(source, $'ezconst.SERIALIZED_FILE_PATH$, None)
      if path is None:
          raise ValueError("No path specified for output file.")
      if $ezconst.EXE_CONTROLLER$ is None:
          $ezconst.EXE_CONTROLLER$ = getattr(source, $'ezconst.EXE_CONTROLLER$, None)
      f = textfile.open_write_with_swap_file(path, backup=True)
      if f is None:
          if $ezconst.EXE_CONTROLLER$ is not None:
              $ezconst.EXE_CONTROLLER$.errs.AddUserCriticalMessage("Unable to open output INI file '%s'" % (wsFilePath))
          return False
      write_ini_level(f, source)
      f.keep()
      return True
