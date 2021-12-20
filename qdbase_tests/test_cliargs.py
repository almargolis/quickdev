import sys
import qdbase.cliargs as cliargs

SOME_FILE_NAMES = ['file1', 'dir1/', 'something_else']

def action_function():
    pass

def print_actions_function(menu):
    print(">>>>>>>>>>>>>>>>> ACTION <<<<<<<<<<<<<<<<")
    print("ERR:", menu.err_code, menu.err_msg)
    print("CLI Args:", menu.cli_argv)
    print("CLI Data:", menu.cli_data)
    print("Action Func:", menu.action_item.action_function.__name__)
    print("Action Args:", menu.action_function_args, menu.action_function_kwargs)

def print_help(menu):
    print(">>>>>>>>>> HELP <<<<<<<<<<<")
    print("Menu:", menu.items)
    menu.show_help()

def make_menu():
    menu = cliargs.CliCommandLine(debug=1)
    menu.add_item(cliargs.CliCommandLineParameterItem('q',
                  default_value=False,
                  help="Display as few messages as possible.",
                  value_type=cliargs.PARAMETER_BOOLEAN
                  ))
    menu.add_item(cliargs.CliCommandLineParameterItem('s',
                      help="Specify site to configure.",
                      value_type=cliargs.PARAMETER_STRING
                      ))
    menu.add_item(cliargs.CliCommandLineParameterItem('n',
                  default_value=False,
                  help="Stand-alone operation. No conf file.",
                  value_type=cliargs.PARAMETER_BOOLEAN
                  ))
    menu.add_item(cliargs.CliCommandLineParameterItem(cliargs.DEFAULT_FILE_LIST_CODE,
                  help="Specify files or directory to synthesise in stand-alone mode.",
                  value_type=cliargs.PARAMETER_STRING
                  ))
    return menu

def add_default_action(menu):
    m = menu.add_item(cliargs.CliCommandLineActionItem(cliargs.DEFAULT_ACTION_CODE,
                                                   action_function,
                                                   help="Synthesize directory."))
    m.add_parameter(cliargs.CliCommandLineParameterItem('s', parameter_name='site',
                                                    is_positional=False))
    m.add_parameter(cliargs.CliCommandLineParameterItem('n', parameter_name='stand_alone',
                                                    default_value=False,
                                                    is_positional=False))
    return m

def add_additional_action(menu):
    m = menu.add_item(cliargs.CliCommandLineActionItem('e',
                                                   action_function,
                                                   help="Edit site conf file."))
    m.add_parameter(cliargs.CliCommandLineParameterItem('s',
                                                    parameter_name='site_dpath',
                                                    default_none=True,
                                                    is_positional=False))
    return m

def test_cli_clean(tmpdir):

    menu = make_menu()
    m = add_default_action(menu)
    print_help(menu)

    menu.cli_argv = ['prog.py']
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None

    menu.cli_argv = ['prog.py', '-s', 'which_site']
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_function_kwargs['site'] == 'which_site'

    menu.cli_argv = ['prog.py', '-n']
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_function_kwargs['stand_alone'] is True


    m.add_parameter(cliargs.CliCommandLineParameterItem(cliargs.DEFAULT_FILE_LIST_CODE,
                                                    parameter_name='sources',
                                                    is_positional=False))
    print_help(menu)

    menu.cli_argv = ['prog.py', '-s', 'which_site']
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_function_kwargs['site'] == 'which_site'


    menu.cli_argv = ['prog.py', '-s', 'which_site'] + SOME_FILE_NAMES
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_function_kwargs['site'] == 'which_site'
    assert menu.file_list == SOME_FILE_NAMES

    add_additional_action(menu)
    print_help(menu)

    menu.cli_argv = ['prog.py', '-e', '-s', 'which_site']
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
    assert menu.action_item.argument_code == 'e'

def test_cli_errors(tmpdir):

    menu = make_menu()
    m = add_default_action(menu)
    print_help(menu)

    menu.cli_argv = ['prog.py']
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code == 102         # -s not specified
