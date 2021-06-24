"""
Classes and methods for processing XSynth and Python source code.

This is used by the XSynth preprocessor for developer written code and
by EzStart for program stubs and other generated files. Because it is
use for bootstraping the EzDev environment, it cannot use any XSynth
features.
"""

import os
import stat

from ezcore import pdict
from ezcore import simplelex


"""
XDB is the database built while synthesizing an EZDev application.
Most of the data is retrieved from source files processed by XSource.
Tables should be referenced by using the XDB_XXXXX constants instead
of literals in order to make it easier to locate table references in
the source code.
"""

XDB_ACTIONS = 'actions'
XDB_CLASSES = 'classes'
XDB_DEFINES = 'defines'
XDB_DEFS = 'defs'
XDB_MODULES = 'modules'
XDB_MODULE_USES = 'module_uses'
XDB_PROGS = 'progs'
XDB_SOURCES = 'sources'

xdb_dict = pdict.DbDict()

# XDB_MODULES contains one entry for each module
d = xdb_dict.add_table(pdict.DbTableDict(XDB_MODULES))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('is_translated'))
d.add_column(pdict.Text('is_xsource'))
d.add_column(pdict.Text('source_path'))
d.add_column(pdict.Text('source_ext'))
d.add_column(pdict.Text('output_path'))
d.add_column(pdict.Text('output_ext'))
d.add_index('ix_modules', 'module_name')

# XDB_SOURCES contains one entry for each supported file
# in the project directories.
d = xdb_dict.add_table(pdict.DbTableDict(XDB_SOURCES))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('ext'))
d.add_column(pdict.Text('path'))
d.add_column(pdict.Number('status'))
d.add_column(pdict.Number('found'))
d.add_column(pdict.Number('modification_time'))
d.add_index('ix_sources', ['module_name', 'ext'])
d.add_index('ix_paths', 'path')

d = xdb_dict.add_table(pdict.DbTableDict(XDB_MODULE_USES))
d.add_column(pdict.Text('source_module_name'))
d.add_column(pdict.Text('uses_module_name'))
d.add_index('ix_module_uses', ['source_module_name', 'uses_module_name'])

d = xdb_dict.add_table(pdict.DbTableDict(XDB_DEFINES))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('define_name'))
d.add_column(pdict.Text('value'))
d.add_index('ix_defines', ['module_name', 'define_name'])

d = xdb_dict.add_table(pdict.DbTableDict(XDB_CLASSES))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('class_name'))
d.add_column(pdict.Text('base_class'))
d.add_index('ix_classes', ['module_name', 'class_name'])

d = xdb_dict.add_table(pdict.DbTableDict(XDB_DEFS))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('class_name'))
d.add_column(pdict.Text('def_name'))
d.add_column(pdict.Text('decorator'))
d.add_index('ix_defs', ['module_name', 'class_name', 'def_name', 'decorator'])

d = xdb_dict.add_table(pdict.DbTableDict(XDB_ACTIONS))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('action_name'))
d.add_column(pdict.Text('action_type'))
d.add_index('ix_actions', 'action_name')

d = xdb_dict.add_table(pdict.DbTableDict(XDB_PROGS))
d.add_column(pdict.Text('prog_name'))
d.add_column(pdict.Text('prog_type'))
d.add_column(pdict.Text('action_name'))
d.add_column(pdict.Text('trigger_name'))
d.add_index('ix_progs', 'prog_name')

SOURCE_STATUS_READY = 0
SOURCE_STATUS_PROCESSING = 1
SOURCE_STATUS_COMPLETE = 2
SOURCE_STATUS_ERROR = 3

NO_INDENT = -1

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
        self.source_obj.db.insert(XDB_CLASSES, fld_values)
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
            self.source_obj.db.insert(XDB_DEFS, fld_values)
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
    """
    Class to process one XSynth source file.

    XSource does not modify the source in any way. All modifications
    go to the output file. This is important so as to not accidentally
    subvert developer intent and so source_lines, if provided, can be
    effectively constant. The latter is assumed by EzConfig so it can
    re-use a single stub model for multiple output files.

    The goal is for XSource to eventually accept abstract XSource code
    and then generate output code in a variety of languages.
    That is many steps away but slowly the code is migrating from hard-coded
    python expectations to something more general.

    src_ext and dest_ext are the extensions for the source and destination files,
    including the dot (ex: .py).

    """
    __slots__ = ('built_ins', 'db', 'defines_only', 'dest_ext', 'dir_path',
                 'err_ct', 'lex', 'module_name',
                 'output_file_path', 'python_parser',
                 'py_out', 'src_ext', 'src_line_ct')

    def __init__(self, module_name, dir_path=None, src_ext='', dest_ext='',
                 db=None, source_lines=None, defines_only=False):
        self.built_ins = {}
        self.lex = simplelex.SimpleLex()
        self.python_parser = PythonParse(self)
        self.db = db
        self.dir_path = dir_path
        self.dest_ext = dest_ext
        self.module_name = module_name
        self.defines_only = defines_only
        self.src_ext = src_ext
        print("Processing {}".format(self.module_name))
        self.db.update(XDB_SOURCES,
                     {'status': SOURCE_STATUS_PROCESSING},
                     where={'module_name': self.module_name})
        self.py_out = []                # output python lines
        self.err_ct = 0
        self.src_line_ct = 0
        self.output_file_path = os.path.join(self.dir_path, self.module_name + '.' + self.dest_ext)
        if source_lines is None:
            xp_input_file_path = os.path.join(self.dir_path, self.module_name + '.' + self.src_ext)
            f = open(xp_input_file_path, 'r')
            source_lines = f.read().splitlines()
        for this_line in source_lines:
            self.src_line_ct += 1
            if this_line[:2] == '#$':
                self.xsynth_parse(this_line[2:])
            else:
                if self.defines_only: pass
                else: self.xsynth_python(this_line)
        if self.err_ct == 0:
            status = SOURCE_STATUS_COMPLETE
        else:
            status = SOURCE_STATUS_ERROR
        self.db.update(XDB_SOURCES,
                             {'status': status},
                             where={'module_name': self.module_name})
        if self.defines_only: pass
        else: self.write_output_file()

    def write_output_file(self):
        if os.path.isfile(self.output_file_path):
            statinfo = os.stat(self.output_file_path)
            mode = statinfo.st_mode
            mode |= stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
            os.chmod(self.output_file_path, mode)
        with open(self.output_file_path, 'w') as f:
            #print(self.py_out)
            f.write('\n'.join(self.py_out)+'\n')
        mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        os.chmod(self.output_file_path, mode)

    def post_module_uses(self, uses_module_name):
        """Update the module uses table for one reference."""
        self.db.update_insert(XDB_MODULE_USES,
                        {
                            'source_module_name': self.module_name,
                            'uses_module_name': uses_module_name
                        },
                        where={
                            'source_module_name': self.module_name,
                            'uses_module_name': uses_module_name
                        })

    def get_module(self, module_name):
        sql_data = self.db.select(XDB_SOURCES,
                                  '*', where={'module_name': module_name})
        if len(sql_data) < 1:
            self.syntax_error("Unknown module '{}'.".format(module_name))
            return
        if sql_data[0]['status'] == SOURCE_STATUS_READY:
            XSource(module_name=sql_data[0]['module_name'],
                    src_ext='xpy', dest_ext='py',
                    dir_path=os.path.dirname(sql_data[0]['path']), db=self.db)
        elif sql_data[0]['status'] == SOURCE_STATUS_PROCESSING:
            self.syntax_error("Recursive loop with module '{}'.".format(module_name))

    def xsynth_lookup_subst(self, key):
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
        sql_data = self.db.select(XDB_DEFINES, '*', where=fld_values)
        if len(sql_data) != 1:
            return None
        return sql_data[0]['value']

    def xsynth_subst(self, src_line, ix, ix2):
        xpy_string = src_line[ix+1:ix2]  # NOQA E226
        if xpy_string[0] in ['"', "'"]:
            quote = xpy_string[0]
            xpy_string = xpy_string[1:]
        else:
            quote = ''
        value = self.xsynth_lookup_subst(xpy_string)
        if value is None:
            self.syntax_error('Unknown substituion {}'.format(xpy_string))
            return ix2+1, src_line
        sub_string = '{}{}{}'.format(quote, value, quote)
        new_line = src_line[:ix] + sub_string
        ix_next = len(new_line)
        new_line += src_line[ix2+1:]
        return ix_next, new_line

    def xsynth_python(self, src_line):
        """
        Process one line of python source.

        Remember: the src_line may either be directly from the
        source file or generated from an XSynth directive.
        """
        self.lex.lex(src_line)
        self.python_parser.parse_line(self.lex)
        ix_next = 0
        while True:
            ix = src_line.find('$', ix_next)
            if ix < 0:
                break
            ix2 = src_line.find('$', ix+1)  # NOQA E226
            if ix2 < 0:
                self.syntax_error('Unmatched substitution character.')
                break
            ix_next, src_line = self.xsynth_subst(src_line, ix, ix2)
        self.py_out.append(src_line)

    def syntax_error(self, msg):
        """Format and print an xpython syntax error."""
        # Print the module name as part of the message because
        # recursive module search can result in intermingled messages.
        self.err_ct += 1
        print("{} Line {}: {}".format(self.module_name, self.src_line_ct, msg))

    def xsynth_parse(self, src_line):
        """Parse and process an XSynth directive line."""
        parts = [x.strip() for x in src_line.split()]
        print(parts)
        if len(parts) < 1:
            return
        if parts[0] == 'define':
            fld_values = {
                'module_name': self.module_name,
                'define_name': parts[1],
            }
            sql_data = self.db.select(XDB_DEFINES, '*', where=fld_values)
            if len(sql_data) > 0:
                self.syntax_error('Duplicate define {}'.format(parts[1]))
                return
            fld_values['value'] = parts[2]
            self.db.insert(XDB_DEFINES, fld_values)
            return
        if self.defines_only:
            self.syntax_error('Output command in defines-only module')
            return
        if parts[0] == 'action':
            if len(parts) < 2:
                self.syntax_error('Missing action_name')
                return
            if len(parts) < 3:
                self.syntax_error('Missing action_type')
                return
            fld_values = {
                'module_name': self.module_name,
                'action_name': parts[1],
                'action_type': parts[2]
            }
            self.db.insert(XDB_ACTIONS, fld_values)
            self.xsynth_python('class {}({}):'.format(parts[1], parts[2]))
            self.xsynth_python('    def __init__(self):')
            self.xsynth_python('        super().__init__()')
            return
        if parts[0] == 'prog':
            fld_values = {
                'prog_name': parts[1],
                'prog_type': 'p',
                'action_name': parts[2],
                'trigger_name': parts[3]
            }
            self.db.insert(XDB_PROGS, fld_values)
            return
