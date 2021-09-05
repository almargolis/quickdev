"""
Classes and methods for processing XSynth and Python source code.

This is used by the XSynth preprocessor for developer written code and
by EzStart for program stubs and other generated files. Because it is
use for bootstraping the EzDev environment, it cannot use any XSynth
features.
"""

import os
import sqlite3
import stat
import sys

import qdbase.qdsqlite as qdsqlite
import qdbase.pdict as pdict
import qdbase.simplelex as simplelex


"""
XDB is the database built while synthesizing an EZDev application.
Most of the data is retrieved from source files processed by XSource.
Tables should be referenced by using the XDB_XXXXX constants instead
of literals in order to make it easier to locate table references in
the source code.
"""
MODULE_STATUS_READY = 'R'
MODULE_STATUS_PROCESSING = 'P'
MODULE_STATUS_SYNTHESIZED = 'S'
MODULE_STATUS_ERROR = 'E'

FILE_MODE_SOURCE ='s'
FILE_MODE_TARGET ='t'
FILE_MODE_OTHER ='o'

MODULE_TYPE_SYNTH = 's'
MODULE_TYPE_NO_SYNTH = 'n'
MODULE_TYPE_UNKNOWN = 'u'

NO_INDENT = -1

XDB_DATABASE_FN = 'xsynth.db'
XDB_ACTIONS = 'actions'
XDB_CLASSES = 'classes'
XDB_DEFINES = 'defines'
XDB_DEFS = 'defs'
XDB_DICTS = 'dicts'
XDB_DICT_ELEMENTS = 'dict_elements'
XDB_MODULES = 'modules'
XDB_MODULE_USES = 'module_uses'
XDB_PROGS = 'progs'
XDB_FILES = 'files'
XDB_DIRS = 'dirs'

XSOURCE_TARGET_EXT = ['.html', '.js', '.py']
XSOURCE_SOURCE_EXT = ['.x'+e[1:] for e in XSOURCE_TARGET_EXT]
PSUEDO_MODULE_QDICT = 'qdict'
RESERVED_MODULE_NAMES = ['xlocal', PSUEDO_MODULE_QDICT]

xdb_dict = pdict.DbDict()

# XDB_MODULES contains one entry for each module.
# A module is generally the basename of a file
# of a type that xsource supports, such as python
# or javascript files. Such files are represented
# in the modules table even if they are not actually
# synthesized (i.e. a *.py file with no corresponding
# *.xpy file). Module names are globally unique
# regardless of language or directory.
d = xdb_dict.add_table(pdict.DbTableDict(XDB_MODULES))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('module_type', default_value=MODULE_TYPE_UNKNOWN))
d.add_column(pdict.Text('status', default_value=MODULE_STATUS_READY))
d.add_column(pdict.Text('source_path', default_value=''))
d.add_column(pdict.Text('source_ext', default_value=''))
d.add_column(pdict.Number('source_modification_time', default_value=0))
d.add_column(pdict.Text('source_found', default_value='N'))
d.add_column(pdict.Text('target_path', default_value=''))
d.add_column(pdict.Text('target_ext', default_value=''))
d.add_column(pdict.Number('target_modification_time', default_value=0))
d.add_column(pdict.Text('target_found', default_value='N'))
d.add_index('ix_modules', 'module_name')

# XDB_DIRS contains one entry for each project directory.
d = xdb_dict.add_table(pdict.DbTableDict(XDB_DIRS))
d.add_column(pdict.Text('path'))
d.add_column(pdict.Text('found', default_value='N'))
d.add_index('ix_dir_paths', 'path')

# XDB_FILES contains one entry for each file
# in the project directories except for explicitly
# ignored files.
d = xdb_dict.add_table(pdict.DbTableDict(XDB_FILES))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('ext'))
d.add_column(pdict.Text('path'))
d.add_column(pdict.Text('mode'))
d.add_column(pdict.Number('modification_time'))
d.add_column(pdict.Text('found', default_value='N'))
d.add_index('ix_sources', ['module_name', 'ext'], is_unique=False)
d.add_index('ix_file_paths', 'path')

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

# XDB_DICTS contains one entry for each project dictionary.
d = xdb_dict.add_table(pdict.DbTableDict(XDB_DICTS))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('dict_name'))
d.add_index('ix_dict_names', 'dict_name')

# XDB_DICT_ELEMENTS contains one entry for each dictionary element`.
d = xdb_dict.add_table(pdict.DbTableDict(XDB_DICT_ELEMENTS))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('dict_name'))
d.add_column(pdict.Text('element_name'))
d.add_column(pdict.Text('ptype'))
d.add_index('ix_element_names', ('dict_name', 'element_name'))


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

        ext should include a leading period. e.g.: ".py"
        """
        if ext in ['', None]:
            fn = self.module_name
        else:
            fn = self.module_name + ext
        return os.path.join(self.dir_name, fn)

def abend(msg):
    """Report critical error and exit xpython (abnormal end). """
    print(msg)
    print("Unable to continue")
    sys.exit(-1)

def open_xdb(db_path, db_reset=False, debug=0):
    if db_reset and (db_path != qdsqlite.SQLITE_IN_MEMORY_FN):
        try:
            os.unlink(db_path)
        except FileNotFoundError:
            pass
    return qdsqlite.QdSqlite(db_path,
                             db_dict=xdb_dict,
                             detailed_exceptions=True,
                             debug=debug)

def post_module_table(db, file_info, file_mode):
    module_data = db.lookup(XDB_MODULES,
                          where={'module_name': file_info.module_name})
    if file_mode == FILE_MODE_SOURCE:
        if module_data is not None:
            if (module_data['source_found'] == 'Y') \
                and (module_data['source_source'] != file_info.path):
                abend("Duplicate module name {}".format(file_info.module_name))
        uflds = {}
        uflds['module_type'] = MODULE_TYPE_SYNTH
        uflds['source_path'] = file_info.path
        uflds['source_ext'] = file_info.file_ext
        uflds['source_modification_time'] = file_info.modification_time
        uflds['source_found'] = 'Y'
    else:
        uflds = {}
        uflds['target_path'] = file_info.path
        uflds['target_ext'] = file_info.file_ext
        uflds['target_modification_time'] = file_info.modification_time
        uflds['target_found'] = 'Y'
    db.update_insert(XDB_MODULES, uflds,
                          where={'module_name': file_info.module_name})
    return

def post_files_table(db, file_info):
    "Updates the modules and files tables for a file."
    file_data = db.lookup(XDB_FILES, where={'path': file_info.path})
    if file_data is not None:
        if file_data['modification_time'] == file_info.modification_time:
            # Don't do anything with unchanged file
            return
    if file_info.file_ext in XSOURCE_SOURCE_EXT:
        file_mode = FILE_MODE_SOURCE
        if file_info.module_name in RESERVED_MODULE_NAMES:
            abend("Reserved module name {}".format(file_info.module_name))
        is_module = True
    elif file_info.file_ext in XSOURCE_TARGET_EXT:
        file_mode = FILE_MODE_TARGET
        is_module = True
    else:
        file_mode = FILE_MODE_OTHER
        is_module = False
    if is_module:
        post_module_table(db, file_info, file_mode)
    db.update_insert(XDB_FILES, {
                            'module_name': file_info.module_name,
                            'ext': file_info.file_ext,
                            'path': file_info.path,
                            'mode': file_mode,
                            'modification_time': file_info.modification_time,
                            'found': 'Y'
                            },
                            {'path': file_info.path})
    return

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
        try:
            self.source_obj.db.insert(XDB_CLASSES, fld_values)
        except sqlite3.IntegrityError:
            self.source_obj.syntax_error('Duplicate class ' + repr(fld_values))
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

class CodeBlock:
    __slots__ = ('block_type', 'block_name',
                 'dictionary_name', 'dictionary_data',
                 'loop_flags','loop_items',
                 'loop_ix','loop_variable', 'xsource')
    def __init__(self, xsource, block_type):
        self.block_type = block_type
        self.block_name = None
        self.dictionary_name = None
        self.dictionary_data = None
        self.loop_flags = None
        self.loop_items = None
        self.loop_ix = None
        self.loop_variable = None
        self.xsource = None

    def initialize_loop(self):
        self.dictionary_data = self.xsource.db.require(XDB_DICTS,
                               where={'dict_name': self.dictionary_name})
        self.loop_items = self.xsource.db.select(XDB_DICT_ELEMENTS,
                               where={'dict_name': self.dictionary_name})
        self.loop_ix = 0

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

    source_ext and target_ext are the extensions for the source and destination files,
    including the dot (ex: .py).

    """
    __slots__ = ('blocks', 'built_ins',
                 'db', 'debug', 'defines_only', 'dir_path',
                 'err_ct', 'lex', 'module_name',
                 'python_parser',
                 'source_ext', 'source_line_ct', 'source_path',
                 'target_dir', 'target_ext', 'target_lines', 'target_path'
                 )

    def __init__(self, module_name, db=None,
                 source_path=None, source_ext=None,
                 target_dir=None, target_path=None, target_ext=None,
                 source_lines=None, debug=0, defines_only=False):
        if debug > 0:
            print("XSource: {} {} '{}' {} '{}'".format(module_name,
                                               source_path, source_ext,
                                               target_path, target_ext))
        self.blocks = []
        self.built_ins = {}
        self.lex = simplelex.SimpleLex()
        self.module_name = module_name
        self.defines_only = defines_only
        self.python_parser = PythonParse(self)
        self.db = db
        self.debug = debug
        if source_ext is None:
            # either source_path or source_ext must be specified.
            # source_path is None if source_lines is specified.
            source_ext = os.path.splitext(source_path)[1]
        elif source_path is None:
            source_path = module_name + source_ext
        if target_ext is None:
            target_ext = '.' + source_ext[2:]
        if target_path is None:
            if target_dir is None:
                target_dir = os.path.dirname(source_path)
            target_path = os.path.join(target_dir, module_name + target_ext)
        self.source_ext = source_ext
        self.source_path = source_path
        self.target_ext = target_ext
        self.target_path = target_path
        print("Processing {} {} -> {}".format(self.module_name, self.source_path, self.target_path))
        self.db.delete(XDB_MODULE_USES,
                                      where={'source_module_name':
                                             module_name})
        self.db.update(XDB_MODULES,
                     {'status': MODULE_STATUS_PROCESSING},
                     where={'module_name': module_name})
        self.target_lines = []                # output python lines
        self.err_ct = 0
        self.source_line_ct = 0
        if source_lines is None:
            f = open(self.source_path, 'r')
            source_lines = f.read().splitlines()
        for this_line in source_lines:
            self.source_line_ct += 1
            if this_line[:2] == '#$':
                self.xsynth_parse(this_line[2:])
            else:
                if self.defines_only: pass
                else: self.xsynth_python(this_line)
        while len(self.blocks) > 0:
            this = self.blocks.pop()
            err_msg = "Missing 'end' for {} block".format(this.block_type)
            if this.block_name is not None:
                err_msg += ' ' + this.block_name
            self.syntax_error(err_msg)
        if self.err_ct == 0:
            status = MODULE_STATUS_SYNTHESIZED
        else:
            status = MODULE_STATUS_ERROR
        if self.debug > 0:
            print("XSource {} {}".format(self.module_name, status))
        self.db.update(XDB_MODULES,
                             {'status': status},
                             where={'module_name': module_name})
        if self.defines_only: pass
        else: self.write_output_file()

    def write_output_file(self):
        if os.path.isfile(self.target_path):
            statinfo = os.stat(self.target_path)
            mode = statinfo.st_mode
            mode |= stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
            os.chmod(self.target_path, mode)
        with open(self.target_path, 'w') as f:
            #print(self.target_lines)
            f.write('\n'.join(self.target_lines)+'\n')
        mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        os.chmod(self.target_path, mode)

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

    def validate_module_name(self, module_name):
        """
        Make sure module_name is valid and has been synthesied,
        otherwise, report an error.
        """
        module_data = self.db.lookup(XDB_MODULES,
                                  where={'module_name': module_name})
        if module_data is None:
            self.syntax_error("Unknown module '{}'.".format(module_name))
            return
        if module_data['status'] == MODULE_STATUS_READY:
            print("R", module_data['status'], module_name)
            XSource(module_name=module_data['module_name'],
                    db=self.db,
                    source_path=module_data['source_path'],
                    )
        elif module_data['status'] == MODULE_STATUS_PROCESSING:
            print("P", module_data['status'], module_name)
            self.syntax_error("Recursive loop with module '{}'.".format(module_name))
        elif module_data['status'] == MODULE_STATUS_SYNTHESIZED:
            pass
        else:
            print("U", module_data['status'], module_name)
            raise ValueError("Unknown status {} for module {}.".format(
                             module_data['status'], module_name
            ))

    def xsynth_lookup_qdict(self, parts):
        try:
            sql_data = self.db.select(XDB_DICT_ELEMENTS, where={'dict_name': parts[1]})
        except KeyError:
            self.syntax_error('Unknown dictionary {}'.format(parts[1]))
            return None
        # If the qdict were a real object, parts[2] would be a property.
        # If this gets too long, making it an object is the solution.
        ix = parts[2].find('(')
        if ix < 0:
            property = parts[2]
            parms = []
        else:
            if parts[2][-1] != ')':
                self.syntax_error("Missing ')'")
                return
            property = parts[2][:ix]
            parm_str = parts[2][ix+1:-1]
            parm_parts = [p.strip() for p in parm_str.split(',')]
            parms = []
            for this in parm_parts:
                # This puts values into parms. At this point
                # it just removes quotes. At some point it may
                # obtain values of symbols.
                if this[0] in ['"', "'"]:
                    parms.append(this[1:-1])
        if property == 'as_comma_list':
            flds = []
            for this in sql_data:
                flds.append(this['element_name'])
            return ', '.join(flds)
        elif property == 'as_subst_list':
            flds = ['%s' for x in range(len(sql_data))]
            return ', '.join(flds)
        elif property == 'as_dict_extract_list':
            flds = []
            for this in sql_data:
                fld_str = "{}['{}']".format(parms[0], this['element_name'])
                if this['ptype'] == 'int':
                    fld_str = 'int(' + fld_str + ')'
                flds.append(fld_str)
            return ', '.join(flds)
        self.syntax_error("Unknown qdict property {}".format(property))
        return None

    def xsynth_lookup_subst(self, key):
        if key in self.built_ins:
            return self.built_ins[key]
        parts = key.split('.')
        if parts[0] == PSUEDO_MODULE_QDICT:
            return self.xsynth_lookup_qdict(parts)
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
            self.validate_module_name(parts[0])
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
        self.target_lines.append(src_line)

    def syntax_error(self, msg):
        """Format and print an xpython syntax error."""
        # Print the module name as part of the message because
        # recursive module search can result in intermingled messages.
        self.err_ct += 1
        print("{} Line {}: {}".format(self.module_name, self.source_line_ct, msg))

    def xsynth_action(self, parts):
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

    def xsynth_define(self, parts):
        if parts[1] in RESERVED_MODULE_NAMES:
            # Using these module names as define variable names
            # potentially results in ambiguous syntax.
            # It's probably never helpful so its not allowed.
            self.syntax_error('Reserved define name {}'.format(parts[1]))
            return
        where_values = {
            'module_name': self.module_name,
            'define_name': parts[1]
        }
        fld_values = {
            'module_name': self.module_name,
            'define_name': parts[1],
            'value': parts[2]
        }
        try:
            self.db.insert_unique(XDB_DEFINES, fld_values, where=where_values)
        except KeyError:
            self.syntax_error('Duplicate define {}'.format(parts[1]))

    def xsynth_dict(self, parts):
        where_values = {
            'dict_name': parts[1]
        }
        fld_values = {
            'module_name': self.module_name,
            'dict_name': parts[1],
        }
        try:
            self.db.insert_unique(XDB_DICTS, fld_values, where=where_values)
        except KeyError:
            self.syntax_error('Duplicate dict {}'.format(parts[1]))
        block = CodeBlock(self, 'dict')
        block.block_name = parts[1]
        self.blocks.append(block)

    def xsynth_element(self, parts):
        if (len(self.blocks) < 1) or (self.blocks[-1].block_type != 'dict'):
            self.syntax_error("XSynth directive 'element' outside of 'dict'")
            return
        where_values = {
            'dict_name': self.blocks[-1].block_name,
            'element_name': parts[1]
        }
        fld_values = {
            'module_name': self.module_name,
            'dict_name': self.blocks[-1].block_name,
            'element_name': parts[1],
        }
        for this in parts[2:]:
            parm = this.split('=')
            fld_values[parm[0]] = parm[1]
        try:
            self.db.insert_unique(XDB_DICT_ELEMENTS, fld_values, where=where_values)
        except KeyError:
            self.syntax_error('Duplicate dict element {}'.format(parts[1]))

    def xsynth_end(self, parts):
        if (len(self.blocks) > 0) and (self.blocks[-1].block_type == parts[1]):
            # this might need clean-up code. maybe a method of the block.
            self.blocks.pop()
            return
        self.syntax_error("Unmatched 'end' directive.")

    def xsynth_for(self, parts):
        """
        for x in dict[flag]
        """
        block = CodeBlock(self, 'for')
        block.loop_variable = parts[1]
        if parts[2] != 'in':
            self.syntax_error("missing keyword 'in'")
            return
        open_bracket_ix = parts[3].find('[')
        if open_bracket_ix < 0:
            self.dictionary_name = parts[3]
            self.loop_flags = None
        else:
            if parts[3][-1] != ']':
                self.syntax_error("missing closing bracket ']'")
                return
            self.dictionary_name = parts[3][:open_bracket_ix]
            self.loop_flags = parts[3][open_bracket_ix+1:-1]
        block.initialize_loop()
        self.blocks.append(block)
        return

    def xsynth_prog(self, parts):
        fld_values = {
            'prog_name': parts[1],
            'prog_type': 'p',
            'action_name': parts[2],
            'trigger_name': parts[3]
        }
        self.db.insert(XDB_PROGS, fld_values)
        return

    def xsynth_parse(self, src_line):
        """Parse and process an XSynth directive line."""
        parts = [x.strip() for x in src_line.split()]
        if self.debug > 0:
            print('xsynth_parse:', parts)
        if len(parts) < 1:
            return
        if parts[0] == 'define':
            self.xsynth_define(parts)
            return
        if self.defines_only:
            self.syntax_error('Output command in defines-only module')
            return
        if parts[0] == 'action': self.xsynth_action(parts)
        elif parts[0] == 'dict': self.xsynth_dict(parts)
        elif parts[0] == 'element': self.xsynth_element(parts)
        elif parts[0]  == 'end': self.xsynth_end(parts)
        elif parts[0]  == 'for': self.xsynth_for(parts)
        elif parts[0] == 'prog': self.xsynth_prog(parts)
        else: self.syntax_error("Unknown XSynth directive '{}'".format(parts[0]))
