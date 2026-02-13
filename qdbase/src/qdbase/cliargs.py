"""
CliCommandLine analyzes the command line and calls an action functions.

This is an alternative to the standard python module arg_parser.
The main differences are that CliCommandLine calls an action function
while arg_parser just parses the command line to be processed
separately. CliCommandLine is also more explicit about value types
and is intentionally similar to other QuickDev dictionary components.
"""

import sys

PARAMETER_BOOLEAN = "bool"
PARAMETER_INTEGER = "int"
PARAMETER_STRING = "str"
PARAMETER_TYPES = [PARAMETER_BOOLEAN, PARAMETER_INTEGER, PARAMETER_STRING]

DEFAULT_ACTION_CODE = "zZ11111"
DEFAULT_FILE_LIST_CODE = "zZ22222"
ALL_DEFAULT_ARGUMENT_CODES = [DEFAULT_ACTION_CODE, DEFAULT_FILE_LIST_CODE]


def argument_code_str(argument_code):
    """
    Return help string representation of an argument.
    This mainly translates special arguments to a human
    understandable form, and adds the conventional dash prefix:
    single-char codes get '-', multi-char codes get '--'.
    """
    if argument_code in ALL_DEFAULT_ARGUMENT_CODES:
        if argument_code == DEFAULT_FILE_LIST_CODE:
            return "<files>"
        return "<default>"
    if len(argument_code) > 1:
        return f"--{argument_code}"
    return f"-{argument_code}"


class CliCommandLineItem:  # pylint: disable=too-few-public-methods
    """
    Base container for command line argument elements.
    This is essentially a virtual class that won't be
    directly instantiated.
    """

    __slots__ = ("argument_code", "help_description", "parent", "security")

    def __init__(self, argument_code, help_description="", security=None):
        self.argument_code = argument_code
        self.help_description = help_description
        self.parent = None
        self.security = security


class CliCommandLineActionItem(CliCommandLineItem):
    """
    Describes a command line action and its correspondng function.

    argument_code defines the command line argument, that triggers
    the action.

    An argument code of DEFAULT_ACTION_CODE is the special case of
    an action to be triggered if no other action is specified.
    """

    __slots__ = ("action_function", "function_parameters")

    def __init__(
        self, argument_code, action_function, help_description="", security=None
    ):
        super().__init__(
            argument_code, help_description=help_description, security=security
        )
        self.action_function = action_function
        self.function_parameters = []

    def __repr__(self):
        repr_args = []
        repr_args.append(self.argument_code)
        repr_args.append(self.action_function.__name__)
        return f"CliCommandLineActionItem({'', ''.join(repr_args)})"

    def add_parameter(self, parm):
        """
        Add a parameter to the action item.
        """
        if not parm.argument_code in self.parent.items:
            raise ValueError(f"Undefined argument_code '{parm.argument_code}'.")
        self.function_parameters.append(parm)
        return parm


class CliCommandLineParameterItem(
    CliCommandLineItem
):  # pylint: disable=too-few-public-methods
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

    default_none is used to disambiguate the difference between there being no
    default value and there being a default value of None. If default_none is
    True, it's assumed that default_value is None but that isn't verified.
    """

    __slots__ = (
        "default_none",
        "default_value",
        "is_multiple",
        "is_positional",
        "is_required",
        "parameter_name",
        "value_type",
    )

    def __init__(
        self,
        argument_code,
        default_none=False,
        default_value=None,
        is_multiple=False,
        is_positional=False,
        is_required=False,
        parameter_name=None,
        value_type=PARAMETER_BOOLEAN,
        help_description="",
        security=None,
    ):  # pylint: disable=too-many-arguments
        super().__init__(
            argument_code, help_description=help_description, security=security
        )
        self.default_none = default_none
        self.default_value = default_value
        self.is_multiple = is_multiple
        if is_positional:
            self.is_positional = True
            self.is_required = True
        else:
            self.is_positional = False
            self.is_required = is_required

        self.parameter_name = parameter_name
        if value_type not in PARAMETER_TYPES:
            raise ValueError(f"Unknown parameter type '{value_type}'.")
        self.value_type = value_type


class CliCommandLine:  # pylint: disable=too-many-instance-attributes
    """
    CliCommandLine analyzes the command line and calls an action functions.

    This is an alternative to the standard python module arg_parser.
    The main differences are that CliCommandLine calls an action function
    while arg_parser just parses the command line to be processed
    separately. CliCommandLine is also more explicit about value types
    and is intentionally similar to other QuickDev dictionary components.
    """

    __slots__ = (
        "action_function_args",
        "action_function_kwargs",
        "action_item",
        "cli_argv",
        "cli_data",
        "debug",
        "default_action_item",
        "err_code",
        "err_msg",
        "file_list",
        "file_list_item",
        "items",
        "positional_parameters",
        "value_item",
    )

    def __init__(
        self, cli_argv=sys.argv, debug=0
    ):  # pylint: disable=dangerous-default-value
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
        self.items = {}  # actions and parameters
        self.positional_parameters = []
        self.value_item = None
        if self.debug > 0:
            print(f"cli.CliCommandLine(argv={cli_argv}).")

    def add_item(self, item):
        """
        Add argument definition.
        """
        item.parent = self
        if item.argument_code in self.items:
            raise ValueError(
                f"Duplicate CliCommandLine argument_code '{argument_code_str(item.argument_code)}'."
            )
        self.items[item.argument_code] = item
        if item.argument_code == DEFAULT_ACTION_CODE:
            if not isinstance(item, CliCommandLineActionItem):
                raise ValueError(
                    f"Argument {argument_code_str(item.argument_code)}"
                    f" must be an CliCommandLineActionItem."
                )
            self.default_action_item = item
        if item.argument_code == DEFAULT_FILE_LIST_CODE:
            if not isinstance(item, CliCommandLineParameterItem):
                raise ValueError(
                    f"Argument {argument_code_str(item.argument_code)}"
                    f" must be an CliCommandLineParameterItem."
                )
            self.file_list_item = item
        if isinstance(item, CliCommandLineParameterItem):
            if item.is_positional:
                self.positional_parameters.append(item)
        return item

    def show_help(self):
        """
        Display command help message.
        """
        prog = self.cli_argv[0]
        if prog == "":
            prog = "python"
        elif prog == "-c":
            prog = "python -c "
        else:
            prog = "python " + prog
        print(f"usage {prog}")
        for this in self.items.values():
            if isinstance(this, CliCommandLineParameterItem):
                print(
                    f"  {argument_code_str(this.argument_code)}"
                    f" {this.help_description}"
                )
            else:
                action = "  " + argument_code_str(this.argument_code)
                for this_parm in this.function_parameters:
                    action += " " + argument_code_str(this_parm.argument_code)
                print(action)

    def process_argument(
        self, argument_code, prefix, value=None
    ):  # pylint: disable=too-many-return-statements
        """
        Process an argument_code. If a parameter, either store its value if
        provided/implied or assign self.value_item to get from next element in
        in self.cli_argv.
        """
        if argument_code == "":
            self.err_code = 401
            self.err_msg = f"Missing flags after '{prefix}'."
        if argument_code not in self.items:
            self.err_code = 402
            self.err_msg = f"Unknown argument '{argument_code}'."
            return False
        argument_item = self.items[argument_code]
        if isinstance(argument_item, CliCommandLineActionItem):
            # this should be the action taken for this command line
            if self.action_item is None:
                self.action_item = argument_item
                return True
            self.err_code = 403
            self.err_msg = (
                f"Duplicate actions '{argument_code}'"
                f" and '{self.action_item.argument_code}'"
            )
            return False
        assert isinstance(argument_item, CliCommandLineParameterItem)
        if argument_code in self.cli_data:
            # we have seen this flag before
            if not argument_item.is_multiple:
                self.err_code = 404
                self.err_msg = f"Duplicate argument '{argument_code}'."
                return False
        else:
            # this is first occurance of this argument
            if argument_item.is_multiple:
                self.cli_data[argument_code] = []
        if argument_item.value_type == PARAMETER_BOOLEAN:
            self.cli_data[argument_code] = True
            return True
        if value in [None, ""]:
            self.value_item = argument_item
            return True
        if argument_item.is_multiple:
            self.cli_data[argument_code].append(value)
        else:
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
            value = flags[this_ix + 1 :]
            if not self.process_argument(this, "-", value=value):
                return False
        return True

    def scan_command_line(self):  # pylint: disable=too-many-branches
        """
        Scan cli_argv elements to determine parameter values and
        identify the action function.
        """
        self.cli_data = {}
        self.action_item = None
        self.value_item = None
        for this_arg_ix, this_arg_value in enumerate(self.cli_argv):
            if this_arg_ix < 1:
                # self.cli_argv[0] is python module name as entered on command line.
                #    That could be either a relative or absolute path.
                continue
            if self.value_item is not None:
                # get value for previous argument
                if self.value_item.is_multiple:
                    self.cli_data[self.value_item.argument_code].append(this_arg_value)
                else:
                    self.cli_data[self.value_item.argument_code] = this_arg_value
                self.value_item = None
                continue
            # get the next argument(s)
            if this_arg_value[:2] == "--":
                if not self.process_argument(this_arg_value[2:], "--"):
                    break
                continue
            if this_arg_value[0] == "-":
                if not self.scan_flags(this_arg_value[1:]):
                    break
                continue
            # this is an argument without a dash
            if self.action_item is None:
                # This should maybe be an explicit option or have
                # more conditions since "this" could be a file name
                # that happens to be the same as an action argument.
                if (this_arg_value in self.items) and isinstance(
                    self.items[this_arg_value], CliCommandLineActionItem
                ):
                    if not self.process_argument(this_arg_value, ""):
                        break
                    continue
            if self.file_list_item is not None:
                if self.file_list is None:
                    self.file_list = []
                self.file_list.append(this_arg_value)
                continue
            # this could be a flag(s) without a preceeding dash.
            # this is allowed if the command does not have
            # a file list but is potentially ambiguous.
            if not self.scan_flags(this_arg_value):
                break
        # All self.cli_argv tokens are processed, now cleanup.
        if self.file_list_item is not None:
            if self.file_list is not None:
                self.cli_data[self.file_list_item.argument_code] = self.file_list
        if self.value_item is not None:
            self.err_code = 303
            self.err_msg = (
                f"No value specified for argument '{self.value_item.argument_code}'."
            )
        if self.action_item is None:
            self.action_item = self.default_action_item
        if self.action_item is None:
            self.err_code = 101
            self.err_msg = "No action specified."
        return bool(self.err_code is None)

    def cli_run(self):
        """
        Evaluate command line and execute requested action.
        """
        self.build_action_function()
        if self.err_code is not None:
            print(self.err_code, self.err_msg)
            self.show_help()
            sys.exit(-1)
        if self.action_function_args is None:
            return self.action_item.action_function()
        return self.action_item.action_function(
            *self.action_function_args, **self.action_function_kwargs
        )

    def build_action_function(self):
        """
        Evaluate command line and construct action function call.

        This is separated from cli_run() so it can be tested
        repetatively by pytest without actually calling the
        action function. self.cli_argv can be replaced
        between calls to test different command patterns.
        """
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
            this_none = False
            this_value = None
            if this.argument_code in self.cli_data:
                this_value = self.cli_data[this.argument_code]
            else:
                if this.default_none or (this.default_value is not None):
                    this_none = this.default_none
                    this_value = this.default_value
                else:
                    this_flag = self.items[this.argument_code]
                    if this_flag.default_none or (this_flag.default_value is not None):
                        this_none = this_flag.default_none
                        this_value = this_flag.default_value
            if (this_value is None) and (not this_none) and this.is_required:
                self.err_code = 102
                self.err_msg = (
                    f"No value specified for action"
                    f" '{argument_code_str(self.action_item.argument_code)}'"
                    f" parameter '{this.parameter_name}'"
                    f" flag '{argument_code_str(this.argument_code)}'"
                )
                return False
            if (this_value is None) and (not this_none):
                continue
            if this.is_positional:
                self.action_function_args.append(this_value)
            else:
                self.action_function_kwargs[this.parameter_name] = this_value
        return True
