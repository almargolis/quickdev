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
import sqlite3
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
    from ezcore import pdict

from ezcore import ezsqlite

try:
    from ezcore import ezconst
except ModuleNotFoundError:
    # May not be found because its an xpy that might not
    # have been gen'd.
    ezconst = None
except SyntaxError:
    # Might be xpython translate failed.
    ezconst = None

try:
    from ezcore import inifile
except ModuleNotFoundError:
    # May not be found because its an xpy that might not
    # have been gen'd.
    inifile = None
except SyntaxError:
    # Might be xpython translate failed.
    inifile = None

SOURCE_STATUS_READY = 0
SOURCE_STATUS_PROCESSING = 1
SOURCE_STATUS_COMPLETE = 2
SOURCE_STATUS_ERROR = 3

SEP_WHITE_SPACE = " \t"
SEP_GRAMMAR = "()[]:#,@"
SEP_ALL = SEP_WHITE_SPACE + SEP_GRAMMAR
LEX_STATE_SCAN_LINE = 0
LEX_STATE_SCAN_TOKEN = 1
NO_INDENT = -1

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

d = db_dict.add_table(pdict.DbTableDict('classes'))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('class_name'))
d.add_column(pdict.Text('base_class'))
d.add_index('ix_classes', 'module_name', 'class_name')

d = db_dict.add_table(pdict.DbTableDict('defs'))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('class_name'))
d.add_column(pdict.Text('def_name'))
d.add_column(pdict.Text('decorator'))
d.add_index('ix_defs', 'module_name', 'class_name', 'def_name', 'decorator')


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

class SimpleLex:
    __slots__ = ('debug', 'start_ixs', 'state', 'token', 'token_ix', 'tokens')

    def __init__(self, debug=0):
        self.debug = debug
        self.state = LEX_STATE_SCAN_LINE

    def save_token(self):
        self.tokens.append(self.token)
        self.start_ixs.append(self.token_ix)
        self.token = ''
        self.token_ix = -1

    def save_c(self, c, ix):
        self.tokens.append(c)
        self.start_ixs.append(ix)

    def lex(self, src_line):
        if self.debug >= 1:
            print('LEX Line', src_line)
        self.tokens = []
        self.start_ixs = []
        self.token = ''
        self.token_ix = 0
        self.state = LEX_STATE_SCAN_LINE
        for ix, c in enumerate(src_line):
            if self.debug >= 1:
                print("'{}', {}, {} '{}'".format(self.token, self.state, ix, c))
            if self.state == LEX_STATE_SCAN_LINE:
                if c in SEP_WHITE_SPACE:
                    continue
                if c in SEP_GRAMMAR:
                    self.save_c(c, ix)
                    continue
                self.token = c
                self.token_ix = ix
                self.state = LEX_STATE_SCAN_TOKEN
            elif self.state == LEX_STATE_SCAN_TOKEN:
                if c in SEP_ALL:
                    self.save_token()
                    if c in SEP_GRAMMAR:
                        self.save_c(c, ix)
                    self.state = LEX_STATE_SCAN_LINE
                else:
                    self.token += c
        if self.state == LEX_STATE_SCAN_TOKEN:
            self.save_token()

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

class PythonParse:
    """ Class to parse python. """
    ___slots___ = ('class_indent', 'class_name',
                   'decorator', 'debug', 'def_indent', 'def_name', 'source_obj')

    def __init__(self, source_obj, debug=0):
        self.debug = debug
        self.source_obj = source_obj
        self.new_module()

    def new_module(self):
        self.class_indent = NO_INDENT
        self.class_name = ''
        self.decorator = ''
        self.def_indent = NO_INDENT
        self.def_name = ''

    def new_class(self, lex):
        self.class_name = lex.tokens[1]
        self.class_indent = lex.start_ixs[0]
        if (len(lex.tokens) >= 5) and (lex.tokens[2] == '(') \
           and (lex.tokens[4] == ')'):
             # this doesn't recognize multiple inheritence
             base_class = lex.tokens[3]
        else:
            base_class = ''
        if base_class == 'object':
            base_class = ''
        self.source_obj.built_ins['__class_name__'] = self.class_name
        fld_values = {'module_name': self.source_obj.module_name,
                'class_name': self.class_name,
                'base_class': base_class}
        self.source_obj.x_obj.db.insert('classes', fld_values)
        self.decorator = ''

    def end_class(self):
        self.class_indent = NO_INDENT
        self.class_name = ''

    def new_def(self, lex):
        self.def_name = lex.tokens[1]
        self.def_indent = lex.start_ixs[0]
        self.source_obj.built_ins['__def_name__'] = self.def_name
        fld_values = {'module_name': self.source_obj.module_name,
                'class_name': self.class_name,
                'def_name': self.def_name,
                'decorator': self.decorator}
        try:
            self.source_obj.x_obj.db.insert('defs', fld_values)
        except sqlite3.IntegrityError:
            self.source_obj.syntax_error('Duplicate function ' + repr(fld_values))
        self.decorator = ''

    def end_def(self):
        self.def_indent = NO_INDENT
        self.def_name = ''

    def parse_line(self, lex):
        if self.debug >= 1:
            print(self.lex.tokens)
        if (len(lex.tokens) < 1) or (lex.tokens[0] == '#'):
            return
        if lex.start_ixs[0] <= self.class_indent:
            self.end_class()
        if lex.start_ixs[0] <= self.def_indent:
            self.end_def()
        if lex.tokens[0] == '@':
            self.decorator = lex.tokens[1]
        if lex.tokens[0] == 'class':
            self.new_class(lex)
            return
        if lex.tokens[0] == 'def':
            self.new_def(lex)
            return

class XSource:
    """ Class to process one XPython source file. """
    __slots__ = ('built_ins', 'err_ct', 'lex', 'module_name', 'parse',
                 'path', 'py_out', 'src_line_ct', 'x_obj')

    def __init__(self, x_obj, sources_row):
        self.built_ins = {}
        self.lex = SimpleLex()
        self.parse = PythonParse(self)
        self.x_obj = x_obj
        self.module_name = sources_row['module_name']
        self.path = sources_row['path']
        print("Processing {}".format(self.module_name))
        self.x_obj.db.update('sources',
                     {'status': SOURCE_STATUS_PROCESSING},
                     where={'module_name': self.module_name})
        self.py_out = []                # output python lines
        self.err_ct = 0
        self.src_line_ct = 0
        p_output_file_path = self.path[:-3] + 'py'
        with open(self.path, 'r') as f:
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
                             where={'module_name': self.module_name})

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
                            'source_module_name': self.module_name,
                            'uses_module_name': uses_module_name
                        },
                        where={
                            'source_module_name': self.module_name,
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

    def xpython_lookup_subst(self, key):
        if key in self.built_ins:
            return self.built_ins[key]
        parts = key.split('.')
        if len(parts) == 1:
            fld_values = {
                'module_name': self.module_name,
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
            return None
        return sql_data[0]['value']

    def xpython_subst(self, src_line, ix, ix2):
        xpy_string = src_line[ix+1:ix2]  # NOQA E226
        if xpy_string[0] in ['"', "'"]:
            quote = xpy_string[0]
            xpy_string = xpy_string[1:]
        else:
            quote = ''
        value = self.xpython_lookup_subst(xpy_string)
        if value is None:
            self.syntax_error('Unknown substituion {}'.format(xpy_string))
            return ix2+1, src_line
        sub_string = '{}{}{}'.format(quote, value, quote)
        new_line = src_line[:ix] + sub_string
        ix_next = len(new_line)
        new_line += src_line[ix2+1:]
        return ix_next, new_line

    def xpython_p(self, src_line):
        """ Process one line of python source. """
        self.lex.lex(src_line)
        self.parse.parse_line(self.lex)
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
        # Print the module name as part of the message because
        # recursive module search can result in intermingled messages.
        self.err_ct += 1
        print("{} Line {}: {}".format(self.module_name, self.src_line_ct, msg))

    def xpython_x(self, src_line):
        """Parse and process an xpython directive line."""
        parts = [x.strip() for x in src_line.split()]
        print(parts)
        if len(parts) < 1:
            return
        if parts[0] == 'define':
            fld_values = {
                'module_name': self.module_name,
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
    __slots__ = ('base_dir', 'db', 'debug',
                 'conf_info',
                 'conf_dir_path',
                    'project_db_path', 'quiet',
                    'source_dirs', 'stand_alone',
                    'xpy_files', 'xpy_files_changed')

    def __init__(self, args, debug=0):
        self.conf_info = None
        self.conf_dir_path = None
        self.debug = debug
        self.quiet = args.quiet
        self.stand_alone = args.stand_alone
        if self.stand_alone:
            self.base_dir = None
            self.source_dirs = args.site_path
            self.project_db_path = ezsqlite.SQLITE_IN_MEMORY_FN
        else:
            if len(args.site_path) < 1:
                self.base_dir = os.getcwd()
            else:
                self.base_dir = args.site_path[0]
            if not self.init_ezdev(args):
                return
        self.db = ezsqlite.EzSqlite(self.project_db_path,
                                     db_dict=db_dict, debug=0)
        self.process_xpy_files()

    def init_ezdev(self, args):
        if ezconst is None:
            print('EzDev not inintialied. Run EzStart. (E1)')
            return False

        self.conf_dir_path = os.path.join(self.base_dir,
                                                  ezconst.SITE_CONF_DIR_NAME)
        self.project_db_path = os.path.join(self.conf_dir_path,
                                            ezconst.PROJECT_DB_FN)
        if not os.path.isdir(self.conf_dir_path):
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

    def load_conf(self):
        self.conf_info = inifile.read_ini_directory(dir=self.conf_dir_path,
                                                    ext=ezconst.CONF_EXT)
        self.source_dirs = self.conf_info['site.source_dirs']

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
