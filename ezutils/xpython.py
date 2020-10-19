#!python
"""
Xpython is a preprocessor for python that adds data modeling and
structured programming features without interfering with normal
python fundamentals.

Xpython was developed for EzDev but has both a stand-alone and
EzDev mode. In stand-alone mode it has minimal EzDev dependencies,
it just processes the files in a directory. This means that almost all
EzDev modules but XPython can use XPython features.

"""

import argparse
import os
import stat
import sys

import pdict
import sqlite_ez

# the following are place holders for EzDev modules which
# are imported below if this is not a stand-alone run.
ezconst = None

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
    """Report critical error and exit xpython (abnormal end). """
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

def list_files(search_dir, ext, dir_files=None, recursive=False):
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
            list_files(this_subdir, ext, dir_files=dir_files)
    return dir_files

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
                if xpy_string[0] in ['"', "'"]:
                    quote = xpy_string[0]
                    xpy_string = xpy_string[1:]
                else:
                    quote = ''
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
                sub_string = '{}{}{}'.format(quote, sql_data[0]['value'], quote)
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
                    'project_db_path', 'quiet',
                    'source_dirs', 'stand_alone',
                    'xpy_files', 'xpy_files_changed')

    def __init__(self, args):
        self.quiet = args.quiet
        self.stand_alone = args.stand_alone
        if args.site_path is None:
            self.base_dir = os.getcwd()
        else:
            self.base_dir = args.site_path
        if self.stand_alone:
            self.project_conf_dir_path = None
            self.project_conf_file_path = None
            self.source_dirs = [self.base_dir]
            self.project_db_path = sqlite_ez.SQLITE_IN_MEMORY_FN
        else:
            if not self.init_ezdev(args):
                return
        self.db = sqlite_ez.SqliteEz(self.project_db_path,
                                     db_dict=db_dict, debug=1)
        self.process_xpy_files()

    def init_ezdev(self, args):
        global ezconst
        try:
            import ezconst
        except ImportError:
            print('EzDev not inintialied. Run EzStart. (E1)')
            return False

        self.project_conf_dir_path = os.path.join(self.base_dir,
                                                  ezconst.SITE_CONF_DIR_NAME)
        self.project_conf_file_path = os.path.join(self.project_conf_dir_path,
                                                   ezconst.PROJECT_CONF_FN)
        self.project_db_path = os.path.join(self.project_conf_dir_path,
                                            ezconst.PROJECT_DB_FN)
        if not os.path.isdir(self.project_conf_dir_path):
            print('EzDev not inintialied. Run EzStart. (E2)')
            return False
        if args.reset:
            try:
                os.unlink(self.project_db_path)
            except FileNotFoundError:
                pass
        if not self.load_conf():
            print('XPython source files not processed.')
            return False
        return True

    def process_xpy_files(self):
        """Build a list of *.xpy files and process them."""
        self.xpy_files = []
        xpy_files_changed = []
        for this_path in self.source_dirs:
            self.xpy_files += list_files(this_path, '.xpy')
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

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('site_path',
                            action='store',
                            nargs='?',
                            default=None,
                            help='Path of site root directory.')
    arg_parser.add_argument('-q',
                            action='store_true',
                            dest='quiet',
                            help='Display as few messages as possible.')
    arg_parser.add_argument('-r',
                            action='store_true',
                            dest='reset',
                            help='Reset (clear) EzDev process.')
    arg_parser.add_argument('-s',
                            action='store_true',
                            dest='stand_alone',
                            help='Stand-alone operation. No conf file.')
    run_args = arg_parser.parse_args()
    xp = XPython(run_args)
