from . import cli

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

def test_cli(tmpdir):

    menu = cli.CliCommandLine(debug=1)
    menu.add_item(cli.CliCommandLineParameterItem('q',
                  default_value=False,
                  help="Display as few messages as possible.",
                  value_type=cli.PARAMETER_BOOLEAN
                  ))
    menu.add_item(cli.CliCommandLineParameterItem('s',
                      help="Specify site to configure.",
                      value_type=cli.PARAMETER_STRING
                      ))
    menu.add_item(cli.CliCommandLineParameterItem(cli.DEFAULT_FILE_LIST_CODE,
                  help="Specify files or directory to synthesise in stand-alone mode.",
                  value_type=cli.PARAMETER_STRING
                  ))

    m = menu.add_item(cli.CliCommandLineActionItem(cli.DEFAULT_ACTION_CODE,
                                                   action_function,
                                                   help="Synthesize directory."))
    m.add_parameter(cli.CliCommandLineParameterItem('s', parameter_name='site',
                                                    is_positional=False))

    print_help(menu)

    some_file_names = ['file1', 'dir1/', 'something_else']

    menu.cli_argv = ['python', 'prog.py']
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code == 102

    menu.cli_argv = ['python', 'prog.py', '-s', 'which_site']
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None

    m.add_parameter(cli.CliCommandLineParameterItem(cli.DEFAULT_FILE_LIST_CODE,
                                                    parameter_name='sources',
                                                    is_positional=False))
    print_help(menu)

    menu.cli_argv = ['python', 'prog.py', '-s', 'which_site'] + some_file_names
    menu.build_action_function()
    print_actions_function(menu)
    assert menu.err_code is None
