"""
Classes and methods for processing XPython and Python source code.

This is used by the XPython preprocessor for developer written code and
by EzStart for program stubs and other generated files. Because it is
use for bootstraping the EzDev environment, it cannot use any XPython
features.
"""

import os
import stat

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
        self.source_obj.db.insert('classes', fld_values)
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
            self.source_obj.db.insert('defs', fld_values)
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
    Class to process one XPython source file.

    XSource does not modify the source in any way. All modifications
    go to the output file. This is important so as to not accidentally
    subvert developer intent and so source_lines, if provided, can be
    effectively constant. The latter is assumed by EzConfig so it can
    re-use a single stub model for multiple output files.
    """
    __slots__ = ('built_ins', 'db', 'dir_path', 'err_ct', 'lex', 'module_name',
                 'output_file_path', 'parse',
                 'py_out', 'src_line_ct')

    def __init__(self, module_name, dir_path, db, source_lines=None):
        self.built_ins = {}
        self.lex = SimpleLex()
        self.parse = PythonParse(self)
        self.db = db
        self.module_name = module_name
        self.dir_path = dir_path
        print("Processing {}".format(self.module_name))
        self.db.update('sources',
                     {'status': SOURCE_STATUS_PROCESSING},
                     where={'module_name': self.module_name})
        self.py_out = []                # output python lines
        self.err_ct = 0
        self.src_line_ct = 0
        self.output_file_path = os.path.join(self.dir_path, self.module_name + '.py')
        xp_input_file_path = os.path.join(self.dir_path, self.module_name + '.xpy')
        if source_lines is None:
            f = open(xp_input_file_path, 'r')
            source_lines = f.read().splitlines()
        for this_line in source_lines:
            self.src_line_ct += 1
            if this_line[:2] == '#$':
                self.xpython_x(this_line[2:])
            else:
                self.xpython_p(this_line)
        if self.err_ct == 0:
            status = SOURCE_STATUS_COMPLETE
        else:
            status = SOURCE_STATUS_ERROR
        self.db.update('sources',
                             {'status': status},
                             where={'module_name': self.module_name})

        if os.path.isfile(self.output_file_path):
            statinfo = os.stat(self.output_file_path)
            mode = statinfo.st_mode
            mode |= stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
            os.chmod(p_output_file_path, mode)
        with open(self.output_file_path, 'w') as f:
            #print(self.py_out)
            f.write('\n'.join(self.py_out)+'\n')
        mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        os.chmod(self.output_file_path, mode)

    def post_module_uses(self, uses_module_name):
        """Update the module uses table for one reference."""
        self.db.update_insert('module_uses',
                        {
                            'source_module_name': self.module_name,
                            'uses_module_name': uses_module_name
                        },
                        where={
                            'source_module_name': self.module_name,
                            'uses_module_name': uses_module_name
                        })

    def get_module(self, module_name):
        sql_data = self.db.select('sources', '*', where={'module_name': module_name})
        if len(sql_data) < 1:
            self.syntax_error("Unknown module '{}'.".format(module_name))
            return
        if sql_data[0]['status'] == SOURCE_STATUS_READY:
            XSource(module_name=sql_data[0]['module_name'],
                    dir_path=os.path.dirname(sql_data[0]['path']), db=self.db)
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
        sql_data = self.db.select('defines', '*', where=fld_values)
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
        """
        Process one line of python source.

        Remember: the src_line may either be directly from the
        source file or generated from an XPython directive.
        """
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
            sql_data = self.db.select('defines', '*', where=fld_values)
            if len(sql_data) > 0:
                self.syntax_error('Duplicate define {}'.format(parts[1]))
                return
            fld_values['value'] = parts[2]
            self.db.insert('defines', fld_values)
        elif parts[0] == 'action':
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
            self.db.insert('actions', fld_values)
            self.xpython_p('class {}({}):'.format(parts[1], parts[2]))
            self.xpython_p('    def __init__(self):')
            self.xpython_p('        super().__init__()')
        elif parts[0] == 'prog':
            fld_values = {
                'prog_name': parts[1],
                'prog_type': 'p',
                'action_name': parts[2],
                'trigger_name': parts[3]
            }
            self.db.insert('progs', fld_values)
