"""
Hosting manages the base configuration for computers that host EzDev sites.

This is called hosting because it will most commonly be used to
configure internet servers of various kinds, but it also is used
for development workstations and CLI applications.
"""

import os
import sys

import qdbase.exenv as exenv
import qdbase.cliargs as cliargs
import qdbase.cliinput as cliinput
from . import apache
from . import qdstart

#
# the following are host dependent globals
#
platform_name = sys.platform
apache_hosting = apache.ApacheHosting()

class HostingConf(object):
    __slots__ = ('execution_user')

    def __init__(self):
        self.execution_user = None

hosting_conf_fn = 'hosting.conf'
hosting_conf_path = os.path.join(exenv.g.qdhost_dpath, hosting_conf_fn)
hosting_conf = None

def init_hosting(force=False):
    if not force:
        if not cliinput.cli_input_yn("Do you want to initialize or repair this host?"):
            sys.exit(-1)
    exenv.make_directory('Host configuraration',
                                    exenv.g.qdhost_dpath,
                                    force=force,
                                    raise_ex=True)
    for this in exenv.g.qdhost_all_subdirs:
        this_dpath = os.path.join(exenv.g.qdhost_dpath, this)
        exenv.make_directory('Host conf subdirectory',
                                this_dpath,
                                force=force,
                                raise_ex=True)
    print(repr(exenv.execution_env.execution_user))
    print("Host {} initialized.".format(exenv.g.qdhost_dpath))
    sys.exit(0)

def load_hosting_conf():
    global hosting_conf
    hosting_conf = None
    if os.path.isfile(hosting_conf_path):
        inifile.load(hosting_conf, ini_path=hosting_conf_path)

def show_hosting():
    exenv.execution_env.show()

def register_site(site_dpath=None):
    if site_dpath is None:
        site_dpath = os.getcwd()
    site = qdsite.QdSite(site_dpath=site_dpath)

if __name__ == "__main__":
    # There is a great deal of symetry between hosting.py and apache.py
    # commands. If you change one, check the other to see if similar
    # changes are needed.
    menu = cliargs.CliCommandLine()
    exenv.command_line_loc(menu)
    exenv.command_line_site(menu)
    #
    menu.add_item(cliargs.CliCommandLineActionItem('hinit', init_hosting, help="Initialize host"))
    m = menu.add_item(cliargs.CliCommandLineActionItem('sregit', init_hosting, help="Register site."))
    m.add_parameter(cliargs.CliCommandLineParameterItem(exenv.ARG_L_CONF_LOC, parameter_name='site_dpath'))
    menu.add_item(cliargs.CliCommandLineActionItem('show', show_hosting, help="Show host information"))
    #
    exenv.execution_env.set_run_name(__name__)
    menu.cli_run()
