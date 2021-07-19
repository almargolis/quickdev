"""
CliCommandLine analyzes the command line and calls an action functions.

This is an alternative to the standard python module arg_parser.
The main differences are that CliCommandLine calls an action function
while arg_parser just parses the command line to be processed
separately. CliCommandLine is also more explicit about value types
and is intentially similar to other EzDev dictionary components.
"""

import re
import sys

PARAMETER_BOOLEAN = 'bool'
PARAMETER_INTEGER = 'int'
PARAMETER_STRING = 'str'
PARAMETER_TYPES = [PARAMETER_BOOLEAN, PARAMETER_INTEGER, PARAMETER_STRING]

DEFAULT_ACTION_CODE = 'zZ11111'
DEFAULT_FILE_LIST_CODE = 'zZ22222'
ALL_DEFAULT_ARGUMENT_CODES = [DEFAULT_ACTION_CODE, DEFAULT_FILE_LIST_CODE]

def argument_code_str(argument_code):
    if argument_code in ALL_DEFAULT_ARGUMENT_CODES:
        if argument_code == DEFAULT_FILE_LIST_CODE:
            argument_code = '<files>'
        else:
            argument_code = '<default>'
    return argument_code

class CliCommandLineItem():
    __slots__ = ('argument_code', 'help_description', 'parent', 'security')
    def __init__(self, argument_code, help_description="", security=None):
        self.argument_code = argument_code
        self.help_description = help_description
        self.parent = None
        self.security = security

class CliCommandLineActionItem(CliCommandLineItem):
    __slots__ = ('action_function', 'function_parameters')
    """
    Describes a command line action and its correspondng function.

    argument_code defines the command line argument, that triggers
    the action.

    An argument code of DEFAULT_ACTION_CODE is the special case of
    an action to b triggered if no other action is specified.
    """
    def __init__(self, argument_code, action_function, help="", security=None):
        super().__init__(argument_code, help_description=help, security=security)
        self.action_function = action_function
        self.function_parameters = []

    def add_parameter(self, parm):
        if not parm.argument_code in self.parent.items:
            raise ValueError("Undefined argument_code '{}'.".format(parm.argument_code))
        self.function_parameters.append(parm)
        return parm

class CliCommandLineParameterItem(CliCommandLineItem):
    """
    Describes a command line argument/flag or an action function parameter.

    parameter_name is required for keyword function parameters.

    An argument_code of DEFAULT_FILE_LIST_CODE is the special case
    of a series of things following
    other parameters. Most commonly this is a list of files or directories
    to be processed.

    is_required is meaningful only for a function parameter. It can be specified
    for flags as documentation if all actions are expected to require it but it
    is checked only for function parameters while assembling the function parameters.
    """
    __slots__ = ('default_value', 'is_positional', 'is_required',
                 'parameter_name', 'value_type')
    def __init__(self, argument_code, default_value=None,
                 is_positional=False, is_required=False,
                 parameter_name=None,
                 value_type=PARAMETER_BOOLEAN, help="", security=None):
        super().__init__(argument_code, help_description=help, security=security)
        self.default_value = default_value
        if is_positional:
            self.is_positional = True
            self.is_required = True
        else:
            self.is_positional = False
            self.is_required = is_required

        self.parameter_name = parameter_name
        if value_type not in PARAMETER_TYPES:
            raise ValueError("Unknown parameter type '{}'.".format(value_type))
        self.value_type = value_type

class CliCommandLine():
    """
    CliCommandLine analyzes the command line and calls an action functions.

    This is an alternative to the standard python module arg_parser.
    The main differences are that CliCommandLine calls an action function
    while arg_parser just parses the command line to be processed
    separately. CliCommandLine is also more explicit about value types
    and is intentially similar to other EzDev dictionary components.
    """
    __slots__ = (
                 'action_function_args', 'action_function_kwargs',
                 'action_item',
                 'cli_argv', 'cli_data',
                 'debug', 'default_action_item',
                 'err_code', 'err_msg',
                 'file_list', 'file_list_item',
                 'items', 'positional_parameters', 'value_item')
    def __init__(self, cli_argv=sys.argv, debug=0):
        self.action_function_args = None
        self.action_function_kwargs = None
        self.action_item = None
        self.cli_argv = cli_argv
        self.cli_data = {}
        self.debug = debug
        self.default_action_item = None
        self.err_code = None
        self.err_msg = None
        self.file_list_item = None
        self.file_list = None
        self.items = {}                # actions and parameters
        self.positional_parameters = []
        self.value_item = None
        if self.debug > 0:
            print("cli.CliCommandLine(argv={}).".format(cli_argv))

    def add_item(self, item):
        item.parent = self
        if item.argument_code in self.items:
            raise ValueError("Duplicate CliCommandLine argument_code '{}'.".format(
                             argument_code_str(item.argument_code)))
        self.items[item.argument_code] = item
        if item.argument_code == DEFAULT_ACTION_CODE:
            if not isinstance(item, CliCommandLineActionItem):
                raise ValueError("Argument {} must be an CliCommandLineActionItem.".format(
                             argument_code_str(item.argument_code)))
            self.default_action_item = item
        if item.argument_code == DEFAULT_FILE_LIST_CODE:
            if not isinstance(item, CliCommandLineParameterItem):
                raise ValueError("Argument {} must be an CliCommandLineParameterItem.".format(
                             argument_code_str(item.argument_code)))
            self.file_list_item = item
        if isinstance(item, CliCommandLineParameterItem):
            if item.is_positional:
                self.positional_parameters.append(item)
        return item

    def show_help(self):
        prog = self.cli_argv[0]
        if prog == '':
            prog = 'python'
        elif prog == '-c':
            prog = 'python -c '
        else:
            prog = 'python ' + prog
        print("usage {}".format(prog))
        for this in self.items.values():
            if isinstance(this, CliCommandLineParameterItem):
                print("  {} {}".format(argument_code_str(this.argument_code),
                                   this.help_description))
            else:
                action = "  " + argument_code_str(this.argument_code)
                for this_parm in this.function_parameters:
                    action += ' ' + argument_code_str(this_parm.argument_code)
                print(action)

    def process_argument(self, argument_code, prefix, value=None):
        """
        Process an argument_code. If a parameter, either store its value if
        provided/implied or assign self.value_item to get from next element in
        in self.cli_argv.
        """
        if argument_code == '':
            self.err_code = 401
            self.err_msg = "Missing flags after '{}'.".format(prefix)
        if argument_code not in self.items:
            self.err_code = 402
            self.err_msg = "Unknown argument '{}'.".format(argument_code)
            return False
        argument_item = self.items[argument_code]
        if isinstance(argument_item, CliCommandLineActionItem):
            # this should be the action take for this command line
            if self.action_item is None:
                self.action_item = argument_item
                return True
            else:
                self.err_code = 403
                self.err_msg = "Duplicate actions '{}' and '{}'.".format(
                      argument_code, self.action_item.argument_code)
                return False
        assert(isinstance(argument_item, CliCommandLineParameterItem))
        if argument_code in self.cli_data:
            self.err_code = 404
            self.err_msg = "Duplicate argument '{}'.".format(argument_code)
            return False
        if argument_item.value_type == PARAMETER_BOOLEAN:
            self.cli_data[argument_code] = True
            return True
        if value in [None, '']:
            self.value_item = argument_item
            return True
        self.cli_data[argument_code] = value
        return True

    def scan_flags(self, flags):
        """
        flags can be a string of single character, boolean parameters.
        These are often called switches. If the parameter requires a
        value, that can either be concatenated to the code or the
        next self.cli_argv parameter. Only the last (or only) flag in a string of
        contatenated flags can be non boolean.
        """
        for this_ix, this in enumerate(flags):
            value = flags[this_ix+1:]
            if not self.process_argument(this, '-', value=value):
                return False
        return True

    def scan_command_line(self):
        """
        Scan cli_argv elements to determine parameter values and
        identify the action function.
        """
        self.cli_data = {}
        self.action_item = None
        self.value_item = None
        for this_ix, this in enumerate(self.cli_argv):
            if this_ix < 1:
                # self.cli_argv[0] is python module name as entered on command line.
                #    That could be either a relative or absolute path.
                continue
            if self.value_item is not None:
                # get value for previous argument
                self.cli_data[self.value_item.argument_code] = this
                self.value_item = None
                continue
            # get the next argument(s)
            if this[:2] == '--':
                if not self.process_argument(this[2:], '--'):
                    break
                continue
            if this[0] == '-':
                if not self.scan_flags(this[1:]):
                    break
                continue
            # this is an argument without a dash
            if self.action_item is None:
                # This should maybe be an explicit option or have
                # more conditions since "this" could be a file name
                # that happends to be the same as an action argument.
                if (this in self.items) \
                        and isinstance(self.items[this], CliCommandLineActionItem):
                    if not self.process_argument(this, ''):
                        break
                    continue
            if self.file_list_item is not None:
                if self.file_list is None:
                    self.file_list = []
                self.file_list.append(this)
                continue
            # this could be a flag(s) without a preceeding dash.
            # this is allowed if the command does not have
            # a file list but is potentially ambiguous.
            if not self.scan_flags(this, ''):
                break
        # All self.cli_argv tokens are processed, now cleanup.
        if self.file_list_item is not None:
            if self.file_list is not None:
                self.cli_data[self.file_list_item.argument_code] = self.file_list
        if self.value_item is not None:
            self.err_code = 303
            self.err_msg = "No value specified for argument '{}'.".format(
                                        self.value_item.argument_code)
        if self.action_item is None:
            self.action_item = self.default_action_item
        if self.action_item is None:
            self.err_code = 101
            self.err_msg = "No action specified."
        if self.err_code is None:
            return True
        else:
            return False

    def cli_run(self):
        self.build_action_function()
        if self.err_code is not None:
            print(self.err_code, self.err_msg)
            self.show_help()
            sys.exit(-1)
        if self.action_function_args is None:
            return self.action_item.action_function()
        return self.action_item.action_function(*self.action_function_args,
                                                **self.action_function_kwargs)

    def build_action_function(self):
        # This is separated from cli_run() so it can be tested
        # repetatively by pytest without actually calling the
        # action function. self.cli_argv can be replaced
        # between calls to test different command patterns.
        self.action_function_args = None
        self.action_function_kwargs = None
        self.err_code = None
        self.err_msg = None
        if not self.scan_command_line():
            return False
        if self.action_item.function_parameters is None:
            return True
        self.action_function_args = []
        self.action_function_kwargs = {}
        for this in self.action_item.function_parameters:
            this_value = None
            if this.argument_code in self.cli_data:
                this_value = self.cli_data[this.argument_code]
            else:
                if this.default_value is not None:
                    this_value = this.default_value
                else:
                    this_flag = self.items[this.argument_code]
                    if this_flag.default_value is not None:
                        this_value = this_flag.default_value
            if (this_value is None) and this.is_required:
                self.err_code = 102
                self.err_msg = "No value specified for action '{}' parameter '{}' flag '{}'".format(
                      argument_code_str(self.action_item.argument_code),
                      this.parameter_name,
                      argument_code_str(this.argument_code)
                      )
                return False
            if this_value is None:
                continue
            if this.is_positional:
                self.action_function_args.append(this_value)
            else:
                self.action_function_kwargs[this.parameter_name] = this_value
        return True

def cli_input(prompt, field_def=None, regex=None, value_hint=None, lower=False):
    if field_def == 'yn':
        regex = re.compile(r"[yn]", flags=re.IGNORECASE)
        value_hint = 'y/n'
    if regex is None:
        raise ValueError('No regex defined.')
    if value_hint is None:
        value_prompt = ''
    else:
        value_prompt = " [{}]".format(value_hint)
    while True:
        resp = input("{}{}: ".format(prompt, value_prompt))
        if regex.match(resp):
            break
    if lower:
        resp = resp.lower()
    return resp

def cli_input_symbol(prompt):
    regex = re.compile(r"[a-z]\w", flags=re.ASCII|re.IGNORECASE)
    return cli_input(prompt, regex=regex)

def cli_input_yn(prompt):
    resp = cli_input(prompt, field_def='yn', lower=True)
    if resp == 'y':
        return True
    else:
        return False
