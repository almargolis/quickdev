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

# These paths and the ezcore import exception logic below are
# required for when xpython is run before ezstart has
# has configured the python virtual environment.

THIS_MODULE_PATH = os.path.abspath(__file__)
EZUTILS_PATH = os.path.dirname(THIS_MODULE_PATH)
EZDEV_PATH = os.path.dirname(EZUTILS_PATH)
EZCORE_PATH = os.path.join(EZDEV_PATH, 'ezcore')

try:
    from ezcore import pdict
except ModuleNotFoundError:
    pdict = None

if pdict is None:
    sys.path.append(EZCORE_PATH)
    import pdict

try:
    from ezcore import sqlite_ez
except ModuleNotFoundError:
    import sqlite_ez

# the following are place holders for EzDev modules which
# are imported below if this is not a stand-alone run.
ezconst = None

SOURCE_STATUS_READY = 0
SOURCE_STATUS_PROCESSING = 1
SOURCE_STATUS_COMPLETE = 2
SOURCE_STATUS_ERROR = 3

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

class FileInfo:  # pylint: disable=too-few-public-methods
    """
    FileInfo is a container for file metadata and
    processing state.
    """
    __slots__ = ('dir_name', 'file_name', 'file_ext',
                 'modification_time', 'module_name', 'path')

    def __init__(self, path):
        stats_obj = os.stat(path)
        self.path = os.path.abspath(path)
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
    __slots__ = ('err_ct', 'py_out', 'sources_row', 'src_line_ct', 'x_obj')

    def __init__(self, x_obj, sources_row):
        self.x_obj = x_obj
        self.sources_row = sources_row  # row of sources table
        print("Processing {}".format(sources_row['module_name']))
        self.x_obj.db.update('sources',
                     {'status': SOURCE_STATUS_PROCESSING},
                     where={'module_name': sources_row['module_name']})
        self.py_out = []                # output python lines
        self.err_ct = 0
        self.src_line_ct = 0
        x_source_file_path = sources_row['path']
        p_output_file_path = x_source_file_path[:-3] + 'py'
        with open(x_source_file_path, 'r') as f:
            for this_line in f.read().splitlines():
                self.src_line_ct += 1
                if this_line[:2] == '#$':
                    self.xpython_x(this_line[2:])
                else:
                    self.xpython_p(this_line)
        if self.err_ct == 0:
            status = SOURCE_STATUS_COMPLETE
        else:
            status = SOURCE_STATUS_ERROR
        self.x_obj.db.update('sources',
                             {'status': status},
                             where={'module_name': sources_row['module_name']})

        if os.path.isfile(p_output_file_path):
            statinfo = os.stat(p_output_file_path)
            mode = statinfo.st_mode
            mode |= stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
            os.chmod(p_output_file_path, mode)
        with open(p_output_file_path, 'w') as f:
            #print(self.py_out)
            f.write('\n'.join(self.py_out)+'\n')
        mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        os.chmod(p_output_file_path, mode)

    def post_module_uses(self, uses_module_name):
        """Update the module uses table for one reference."""
        self.x_obj.db.update_insert('module_uses',
                        {
                            'source_module_name': self.sources_row['module_name'],
                            'uses_module_name': uses_module_name
                        },
                        where={
                            'source_module_name': self.sources_row['module_name'],
                            'uses_module_name': uses_module_name
                        })

    def get_module(self, module_name):
        sql_data = self.x_obj.db.select('sources', '*', where={'module_name': module_name})
        if len(sql_data) < 1:
            self.syntax_error("Unknown module '{}'.".format(module_name))
            return
        if sql_data[0]['status'] == SOURCE_STATUS_READY:
            XSource(self.x_obj, sql_data[0])
        elif sql_data[0]['status'] == SOURCE_STATUS_PROCESSING:
            self.syntax_error("Recursive loop with module '{}'.".format(module_name))

    def xpython_subst(self, src_line, ix, ix2):
        xpy_string = src_line[ix+1:ix2]  # NOQA E226
        if xpy_string[0] in ['"', "'"]:
            quote = xpy_string[0]
            xpy_string = xpy_string[1:]
        else:
            quote = ''
        parts = xpy_string.split('.')
        if len(parts) == 1:
            fld_values = {
                'module_name': self.sources_row['module_name'],
                'define_name': parts[0]
            }
        else:
            fld_values = {
                'module_name': parts[0],
                'define_name': parts[1]
            }
            self.get_module(parts[0])
            self.post_module_uses(parts[0])
        sql_data = self.x_obj.db.select('defines', '*', where=fld_values)
        if len(sql_data) != 1:
            self.syntax_error('Unknown substituion {}'.format(xpy_string))
            return ix2+1, src_line
        sub_string = '{}{}{}'.format(quote, sql_data[0]['value'], quote)
        new_line = src_line[:ix] + sub_string
        ix_next = len(new_line)
        new_line += src_line[ix2+1:]
        return ix_next, new_line

    def xpython_p(self, src_line):
        """ Process one line of python source. """
        ix_next = 0
        while True:
            ix = src_line.find('$', ix_next)
            if ix < 0:
                break
            ix2 = src_line.find('$', ix+1)  # NOQA E226
            if ix2 < 0:
                self.syntax_error('Unmatched substitution character.')
                break
            ix_next, src_line = self.xpython_subst(src_line, ix, ix2)
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
                'module_name': self.sources_row['module_name'],
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
        if self.stand_alone:
            self.base_dir = None
            self.project_conf_dir_path = None
            self.project_conf_file_path = None
            self.source_dirs = args.site_path
            self.project_db_path = sqlite_ez.SQLITE_IN_MEMORY_FN
        else:
            if len(args.site_path) < 1:
                self.base_dir = os.getcwd()
            else:
                self.base_dir = args.site_path[0]
            if not self.init_ezdev(args):
                return
        self.db = sqlite_ez.SqliteEz(self.project_db_path,
                                     db_dict=db_dict, debug=0)
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

    def scan_directory(self, search_dir, ext, recursive=False):
        """
        Scan a direcory and update the sources database.
        """
        dir_all = os.listdir(search_dir)
        dir_dir = []
        for this_file_name in dir_all:
            this_path = os.path.join(search_dir, this_file_name)
            if os.path.isdir(this_path):
                dir_dir.append(this_path)
            else:
                parts = os.path.splitext(this_path)
                if parts[1] == ext:
                    self.post_sources_table(this_path)
        if recursive:
            for this_subdir in dir_dir:
                self.scan_directory(this_subdir, ext, recursive=True)

    def process_xpy_files(self):
        """
        Scan directories to locate source files. Update the
        sources table and then process them.
        """
        self.db.update('sources', {'found': 0})
        for this_directory in self.source_dirs:
            self.scan_directory(this_directory, '.xpy')

        while True:
            # We re-select for each source because XSource
            # may process multiple sources recursively.
            # The to-do list is not static.
            sql_data = self.db.select('sources', '*',
                                       where={'status': SOURCE_STATUS_READY},
                                       limit=1)
            if len(sql_data) < 1:
                break
            XSource(self, sql_data[0])

    def post_sources_table(self, path):
        file_info = FileInfo(path)
        sql_data = self.db.select('sources', '*',
                                      where={'module_name':
                                             file_info.module_name})
        if len(sql_data) < 1:
            self.db.insert('sources', {
                            'module_name': file_info.module_name,
                            'path': file_info.path,
                            'found': 1,
                            'status': SOURCE_STATUS_READY,
                            'modification_time': file_info.modification_time
                            })
            return
        if len(sql_data) != 1:
                abend("Duplicate module name {}".format(this.module_name))
        flds = {'found': 1}
        if (this.modification_time != sql_data[0].modification_time) \
                        or (this.path != sql_data[0].path):
            # the source has been changed or moved.
            # mark it for processing
            flds['path'] = file_info.path
            flds['modification_time'] = file_info.modification_time
            flds['status'] = SOURCE_STATUS_READY
        # mark source as found, possibly modified
        self.db.update('sources', flds,
                               where={'module_name': file_info.module_name})
        sql_data = self.db.delete('module_uses',
                                      where={'source_module_name':
                                             file_info.module_name})

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('site_path',
                            action='store',
                            nargs='*',
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
