#!python
"""
Xpython is a preprocessor for python that adds data modeling and
structured programming features without interfering with normal
python fundamentals.

Xpython was developed for CommerceNode but does not use any of it's
modules because it needs to run regardless of its state. It's
simplest to keep this stand-alone.
"""

import os
import stat
import sys

import pdict
import sqlite_ez

SITE_CONF_DIR_NAME = 'conf'                 # relative to site_path
SITE_CONF_DB_DIR_NAME = 'conf/db'           # relative to site_path
PROJECT_DB_FN = 'project_db.sql'
PROJECT_CONF_FN = 'xpython.conf'

SOURCE_STATUS_READY = 0
SOURCE_STATUS_COMPLETE = 1
SOURCE_STATUS_ERROR = 2

db_dict = pdict.DbDict()

d = db_dict.add_table(pdict.DbTableDict('sources'))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('path'))
d.add_column(pdict.Number('status'))
d.add_column(pdict.Number('found'))
d.add_column(pdict.Number('modification_time'))
d.add_index('ix_sources', 'module_name')

d = db_dict.add_table(pdict.DbTableDict('module_uses'))
d.add_column(pdict.Text('source_module_name'))
d.add_column(pdict.Text('uses_module_name'))
d.add_index('ix_module_uses', 'source_module_name', 'uses_module_name')

d = db_dict.add_table(pdict.DbTableDict('defines'))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('define_name'))
d.add_column(pdict.Text('value'))
d.add_index('ix_defines', 'module_name', 'define_name')


def abend(msg):
    """Report critical error and exit xpython (abnormal end)."""
    print(msg)
    print("Unable to continue")
    sys.exit(-1)


def input_yn(prompt, default='y'):
    """CLI input with validation of y/n response."""
    if default is None:
        display_choices = ' (y/n)'
    elif default == 'y':
        display_choices = ' (Y/n)'
    else:
        display_choices = ' (y/N)'
    display_prompt = prompt + display_choices
    resp = 'x'
    while resp not in 'yn':
        resp = input(display_prompt)
        if resp == '':
            if default == 'y':
                resp = 'y'
            else:
                resp = 'n'
    return resp == 'y'


class FileInfo:  # pylint: disable=too-few-public-methods
    """
    FileInfo is a container for file metadata and
    processing state.
    """
    __slots__ = ('dir_name', 'file_name', 'file_ext',
                 'modification_time', 'module_name', 'path')

    def __init__(self, path):
        stats_obj = os.stat(path)
        self.path = path
        self.dir_name, self.file_name = os.path.split(path)
        self.module_name, self.file_ext = os.path.splitext(self.file_name)
        self.modification_time = stats_obj[stat.ST_MTIME]

    def new_path(self, ext):
        """
        Provide the path for a derivative file named by changing
        the extension.

        ext should include the leading period. e.g.: ".py"
        """
        return os.path.join(self.dir_name, self.module_name) + ext

class XSource:
    """ Class to process one XPython source file. """
    __slots__ = ('err_ct', 'file_info', 'py_out', 'src_line_ct', 'x_obj')

    def __init__(self, x_obj, file_info):
        self.x_obj = x_obj
        self.file_info = file_info
        print("Processing {}".format(file_info.module_name))
        self.py_out = []                # output python lines
        self.err_ct = 0
        self.src_line_ct = 0
        with open(file_info.path, 'r') as f:
            for this in f.read().splitlines():
                self.src_line_ct += 0
                if this[:2] == '#$':
                    self.xpython_x(this[2:])
                else:
                    self.xpython_p(this)
        if self.err_ct == 0:
            status = SOURCE_STATUS_COMPLETE
        else:
            status = SOURCE_STATUS_ERROR
        self.x_obj.db.update('sources',
                             {'status': status},
                             where={'module_name': file_info.module_name})
        with open(file_info.new_path('.py'), 'w') as f:
            print(self.py_out)
            f.write('\n'.join(self.py_out))

    def module_uses(self, module_uses_module_name):
        """Update the module uses table for one reference."""
        self.x_obj.db.update_insert('module_uses',
                        {
                            'source_module_name': self.file_info.module_name,
                            'module_uses_module_name': module_uses_module_name
                        },
                        where={
                            'source_module_name': self.file_info.module_name,
                            'module_uses_module_name': module_uses_module_name
                        })

    def xpython_p(self, src_line):
        """ Process one line of python source. """
        ix = src_line.find('$')
        if ix >= 0:
            ix2 = src_line.find('$', ix+1)  # NOQA E226
            if ix2 >= ix:
                xpy_string = src_line[ix+1:ix2]  # NOQA E226
                parts = xpy_string.split('.')
                if len(parts) == 1:
                    fld_values = {
                        'module_name': self.file_info.module_name,
                        'define_name': parts[0]
                    }
                else:
                    fld_values = {
                        'module_name': parts[0],
                        'define_name': parts[1]
                    }
                    self.module_uses(parts[0])
                sql_data = self.x_obj.db.select('defines', '*', where=fld_values)
                if len(sql_data) != 1:
                    self.syntax_error('Unknown substituion {}'.format(xpy_string))
                sub_string = sql_data[0]['value']
                src_line = src_line[:ix] + sub_string + src_line[ix2+1:]
        self.py_out.append(src_line)

    def syntax_error(self, msg):
        """Format and print an xpython syntax error."""
        self.err_ct += 1
        print("Line {}: {}".format(self.src_line_ct, msg))

    def xpython_x(self, src_line):
        """Parse and process an xpython directive line."""
        parts = [x.strip() for x in src_line.split()]
        print(parts)
        if len(parts) < 1:
            return
        if parts[0] == 'define':
            fld_values = {
                'module_name': self.file_info.module_name,
                'define_name': parts[1],
            }
            sql_data = self.x_obj.db.select('defines', '*', where=fld_values)
            if len(sql_data) > 0:
                self.syntax_error('Duplicate define {}'.format(parts[1]))
                return
            fld_values['value'] = parts[2]
            self.x_obj.db.insert('defines', fld_values)

class XPython:
    """ Main XPython implementation class."""
    __slots__ = ('base_dir', 'db', 'project_conf_dir_path', 'project_conf_file_path',
                    'project_db_path',
                    'source_dirs', 'xpy_files', 'xpy_files_changed')

    def __init__(self, option1):
        self.base_dir = os.getcwd()
        self.project_conf_dir_path = os.path.join(self.base_dir,
                                                  SITE_CONF_DIR_NAME)
        self.project_conf_file_path = os.path.join(self.project_conf_dir_path,
                                                   PROJECT_CONF_FN)
        self.project_db_path = os.path.join(self.project_conf_dir_path,
                                            PROJECT_DB_FN)
        if not os.path.isdir(self.project_conf_dir_path):
            if input_yn('Do you want to create a new Xpython project?'):
                os.mkdir(self.project_conf_dir_path)
        if option1 == 'reset':
            try:
                os.unlink(self.project_db_path)
            except FileNotFoundError:
                pass
        self.load_conf()
        self.db = sqlite_ez.SqliteEz(self.project_db_path,
                                     db_dict=db_dict, debug=1)
        self.process_xpy_files()

    def list_files(self, search_dir, ext, dir_files=None, recursive=False):
        """
        Build a list of files in a directory (or tree) that match
        the specified extension.
        """
        dir_all = os.listdir(search_dir)
        dir_dir = []
        if dir_files is None:
            dir_files = []
        for this in dir_all:
            this_path = os.path.join(search_dir, this)
            if os.path.isdir(this_path):
                dir_dir.append(this_path)
            else:
                parts = os.path.splitext(this_path)
                if parts[1] == ext:
                    dir_files.append(FileInfo(this_path))
        if recursive:
            for this_subdir in dir_dir:
                self.list_files(this_subdir, ext, dir_files=dir_files)
        return dir_files

    def process_xpy_files(self):
        """Build a list of *.xpy files and process them."""
        self.xpy_files = []
        xpy_files_changed = []
        for this in self.source_dirs:
            this_path = os.path.join(self.base_dir, this)
            self.xpy_files += self.list_files(this_path, '.xpy')
        self.db.update('sources', {'found': 0})
        for this in self.xpy_files:
            sql_data = self.db.select('sources', '*',
                                      where={'module_name':
                                             this.module_name})
            if len(sql_data) < 1:
                self.db.insert('sources', {
                            'module_name': this.module_name,
                            'path': this.path,
                            'found': 1,
                            'status': SOURCE_STATUS_READY,
                            'modification_time': this.modification_time
                            })
                xpy_files_changed.append(this)
            elif len(sql_data) == 1:
                flds = {'found': 1}
                if (this.modification_time != sql_data[0].modification_time) \
                        or (this.path != sql_data[0].path):
                    # the source has been changed or moved.
                    # mark it for processing
                    flds['path'] = this.path
                    flds['modification_time'] = this.modification_time
                    flds['status'] = SOURCE_STATUS_READY
                    xpy_files_changed.append(this)
                # mark source as found, possibly modified
                self.db.update('sources', flds,
                               where={'module_name': this.module_name})
            else:
                abend("Duplicate module name {}".format(this.module_name))
        for this in xpy_files_changed:
            #
            sql_data = self.db.select('module_uses',
                                      where={'uses_module_name':
                                             this.module_name})
            for this_uses in sql_data:
                self.db.update('sources', {'status': SOURCE_STATUS_READY},
                               where={'module_name':
                                      this_uses.source_module_name})
            XSource(self, this)

    def load_conf(self):
        """Load the xpython project configuration file."""
        self.source_dirs = []
        f = open(self.project_conf_file_path)
        for this_line in f.readlines():
            this_line = this_line.strip()
            if this_line == '':
                continue
            if this_line[0] == '#':
                continue
            pos = this_line.find('=')
            if pos > 0:
                key = this_line[:pos].strip()
                val = this_line[pos+1:].strip()
                if key == 'source':
                    self.source_dirs.append(val)
        f.close()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        ARG1 = sys.argv[1]
    else:
        ARG1 = None

    xp = XPython(ARG1)
