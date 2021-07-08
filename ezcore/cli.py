import re
import sys

PARAMETER_BOOLEAN = 'bool'
PARAMETER_INTEGER = 'int'
PARAMETER_STRING = 'str'
PARAMETER_TYPES = [PARAMETER_BOOLEAN, PARAMETER_INTEGER, PARAMETER_STRING]

class CliCommandLineItem():
    __slots__ = ('argument_code', 'help_description', 'security')
    def __init__(self, argument_code, help_description="", security=None):
        self.argument_code = argument_code
        self.help_description = help_description
        self.security = security

class CliCommandLineActionItem(CliCommandLineItem):
    __slots__ = ('action_function', 'function_parameters')
    def __init__(self, argument_code, action_function, help="", security=None):
        super().__init__(argument_code, help_description=help, security=security)
        self.action_function = action_function
        self.function_parameters = []

    def add_parameter(self, parm):
        self.function_parameters.append(parm)
        return parm

class CliCommandLineParameterItem(CliCommandLineItem):
    """
    Describes a command line argument/flag or an action function parameter.

    parameter_name is required for keyword function parameters.

    is_required is meaningful only for a function parameter. It can be specified
    for flags as documentation if all actions are expected to require it but it
    is checked only for function parameters while assembling the function parameters.
    """
    __slots__ = ('default_value', 'is_positional', 'is_required',
                 'parameter_name', 'value_count', 'value_type')
    def __init__(self, argument_code, default_value=None,
                 is_positional=False, is_required=False,
                 parameter_name=None,
                 value_count=0, value_type=None, help="", security=None):
        super().__init__(argument_code, help_description=help, security=security)
        self.default_value = default_value
        self.is_positional = is_positional
        self.is_required = is_required
        self.parameter_name = parameter_name
        self.value_count = value_count
        if (value_count == 0) and (value_type is None):
            value_type = PARAMETER_BOOLEAN
        if value_type is None:
            value_type = PARAMETER_STRING
        if (value_count < 0) or (value_count > 1):
            # support for multiple values should be added
            raise ValueError("Unexpected parameter count '{}'.".format(value_count))
        if value_type not in PARAMETER_TYPES:
            raise ValueError("Unknown parameter type '{}'.".format(value_type))

class CliCommandLine():
    """
    CliCommandLine analyzes the command line and call command functions.

    This is an alternative to the standard python module arg_parser.
    The main differences are that CliCommandLine calls an action function
    while arg_parser just parses the command line to be processed
    separately. CliCommandLine is also more explicit about value types
    and is intentially similar to other EzDev dictionary components.
    """
    __slots__ = ('action_data', 'action_item', 'items', 'positional_parameters')
    def __init__(self):
        self.action_data = {}
        self.action_item = None
        self.items = {}                # actions and parameters
        self.positional_parameters = []

    def add_item(self, item):
        if item.argument_code in self.items:
            raise ValueError("Duplicate CliCommandLine argument_code '{}'".format(items.argument_code))
        self.items[item.argument_code] = item
        if isinstance(item, CliCommandLineParameterItem):
            if item.is_positional:
                self.positional_parameters.append(item)
        return item

    def show_help(self):
        prog = sys.argv[0]
        if prog == '':
            prog = 'python'
        elif prog == '-c':
            prog = 'python -c '
        else:
            prog = 'python ' + prog
        print("usage {}".format(prog))
        for this in self.items.values():
            print("  {} {}".format(this.argument_code, this.help_description))

    def get_parameter(self, argument_code):
        if argument_code not in self.items:
            print("Unknown argument '{}'.".format(argument_code))
            self.show_help()
            sys.exit(-1)
        return self.items[argument_code]

    def scan_flags(self, argument_ix, flags):
        """
        flags can be a string of single character, boolean parameters.
        These are often called switches. If the parameter requires a
        value, that can either be concatenated to the code or the
        next sys.argv parameter. Only the last (or only) flag can be non boolean.
        """
        for this_ix, this in enumerate(flags):
            this_parameter = self.get_parameter(this)
            if not isinstance(this_parameter, CliCommandLineParameterItem):
                print("Argument '{}' is not a parameter.".format(this))
                self.show_help()
                sys.exit(-1)
            if this_parameter.argument_code in self.action_data:
                print("Duplicate argument '{}'.".format(this))
                self.show_help()
                sys.exit(-1)
            if this_parameter.value_count == 0:
                self.action_data[this_parameter.argument_code] = True
            else:
                # This assumes 1 value, should eventually support multiple
                if (this_ix+1) < len(flags):
                    value = flags[this_ix+1:]
                    self.action_data[this_parameter.argument_code] = value
                    return None
                else:
                    if (argument_ix+1) >= len(sys.argv):
                        print("No value specified for argument '{}'.".format(this))
                        self.show_help()
                        sys.exit(-1)
                    return this_parameter
            return None

    def scan_command_line(self):
        self.action_data = {}
        self.action_item = None
        value_parameter = None
        for this_ix, this in enumerate(sys.argv):
            if this_ix == 0:
                continue                # first parameter is program name
            if value_parameter is not None:
                # get value for previous argument
                self.action_data[value_parameter.argument_code] = this
                value_parameter = None
                continue
            # get the next argument(s)
            if this[0] == '-':
                if len(this) > 1:
                    value_parameter = self.scan_flags(this_ix, this[1:])
                    continue
                print('Missing flags after dash.')
                self.show_help()
                sys.exit(-1)
            # this is an argument without a dash
            this_parameter = self.get_parameter(this)
            if isinstance(this_parameter, CliCommandLineActionItem):
                # this should be the action take for this command line
                if self.action_item is None:
                    self.action_item = this_parameter
                    continue
                print("Duplicate actions '{}' and '{}'.".format(
                      argument_code, self.action_item.argument_code))
                self.show_help()
                sys.exit(-1)
            # this is a flag(s) without a preceeding dash.
            # this is allowed but is potentially ambiguous.
            value_parameter = self.scan_flags(this_ix, this)

    def cli_run(self):
        self.scan_command_line()
        if self.action_item is None:
            print("No action specified.")
            self.show_help()
            sys.exit(-1)
        if self.action_item.function_parameters is None:
            return self.action_item.action_function()
        args = []
        kwargs = {}
        for this in self.action_item.function_parameters:
            if this.argument_code in self.action_data:
                this_value = self.action_data[this.argument_code]
            elif this.default_value is not None:
                this_value = this.default_value
            else:
                print("No value specified for action '{}' parameter '{}' flag '{}'".format(
                      self.action_item.argument_code, this.parameter_name,
                      this.argument_code
                      ))
                self.show_help()
                sys.exit(-1)
            if this.is_positional:
                args.append(this_value)
            else:
                kwargs[this.parameter_name] = this_value
        return self.action_item.action_function(*args, **kwargs)


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
