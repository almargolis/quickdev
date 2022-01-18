"""
test cliargs.py
"""

from qdbase import cliargs

SOME_FILE_NAMES = ["file1", "dir1/", "something_else"]


def action_function():
    """
    Dummy action function.
    """
    pass  # pylint: disable=unnecessary-pass


def print_actions_function(menu):
    """
    Print action function data for error analysis.
    """
    print(">>>>>>>>>>>>>>>>> ACTION <<<<<<<<<<<<<<<<")
    print("ERR:", menu.err_code, menu.err_msg)
    print("CLI Args:", menu.cli_argv)
    print("CLI Data:", menu.cli_data)
    print("Action Func:", menu.action_item.action_function.__name__)
    print("Action Args:", menu.action_function_args, menu.action_function_kwargs)


def print_help(menu):
    """
    Print help menu for error analysis.
    """
    print(">>>>>>>>>> HELP <<<<<<<<<<<")
    print("Menu:", menu.items)
    menu.show_help()


def make_menu():
    """
    Create the test menu.
    """
    menu = cliargs.CliCommandLine(debug=1)
    menu.add_item(
        cliargs.CliCommandLineParameterItem(
            "q",
            default_value=False,
            help_description="Display as few messages as possible.",
            value_type=cliargs.PARAMETER_BOOLEAN,
        )
    )
    menu.add_item(
        cliargs.CliCommandLineParameterItem(
            "s",
            help_description="Specify site to configure.",
            value_type=cliargs.PARAMETER_STRING,
        )
    )
    menu.add_item(
        cliargs.CliCommandLineParameterItem(
            "n",
            default_value=False,
            help_description="Stand-alone operation. No conf file.",
            value_type=cliargs.PARAMETER_BOOLEAN,
        )
    )
    menu.add_item(
        cliargs.CliCommandLineParameterItem(
            cliargs.DEFAULT_FILE_LIST_CODE,
            help_description="Specify files or directory to synthesise in stand-alone mode.",
            value_type=cliargs.PARAMETER_STRING,
        )
    )
    return menu


def add_default_action(menu, s_is_required=False):
    """
    Add a default action.
    """
    menu_item = menu.add_item(
        cliargs.CliCommandLineActionItem(
            cliargs.DEFAULT_ACTION_CODE,
            action_function,
            help_description="Synthesize directory.",
        )
    )
    menu_item.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "s", parameter_name="site", is_positional=False, is_required=s_is_required
        )
    )
    menu_item.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "n", parameter_name="stand_alone", default_value=False, is_positional=False
        )
    )
    return menu_item


def add_additional_action(menu):
    """
    Add a secondary action.
    """
    menu_item = menu.add_item(
        cliargs.CliCommandLineActionItem(
            "e", action_function, help_description="Edit site conf file."
        )
    )
    menu_item.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "s", parameter_name="qdsite_dpath", default_none=True, is_positional=False
        )
    )
    return menu_item


def test_cli_clean():
    """
    Test normal / expected results.
    """

    menu = make_menu()
    action_item = add_default_action(menu)
    print_help(menu)

    menu.cli_argv = ["prog.py"]
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None

    menu.cli_argv = ["prog.py", "-s", "which_site"]
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_function_kwargs["site"] == "which_site"

    menu.cli_argv = ["prog.py", "-n"]
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_function_kwargs["stand_alone"] is True

    action_item.add_parameter(
        cliargs.CliCommandLineParameterItem(
            cliargs.DEFAULT_FILE_LIST_CODE,
            parameter_name="sources",
            is_positional=False,
        )
    )
    print_help(menu)

    menu.cli_argv = ["prog.py", "-s", "which_site"]
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_function_kwargs["site"] == "which_site"

    menu.cli_argv = ["prog.py", "-s", "which_site"] + SOME_FILE_NAMES
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_function_kwargs["site"] == "which_site"
    assert menu.file_list == SOME_FILE_NAMES

    add_additional_action(menu)
    print_help(menu)

    menu.cli_argv = ["prog.py", "-e", "-s", "which_site"]
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_item.argument_code == "e"


def test_cli_errors():
    """
    Test error messages.
    """

    menu = make_menu()
    add_default_action(menu, s_is_required=True)
    print_help(menu)

    menu.cli_argv = ["prog.py"]
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code == 102  # -s not specified
