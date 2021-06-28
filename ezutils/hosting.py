"""
Hosting manages the base configuration for computers that host EzDev sites.

This is called hosting because it will most commonly be used to
configure internet servers of various kinds, but it also is used
for development workstations and CLI applications.
"""

import os
import sys

from ezcore import exenv
from ezcore import cli
from ezcore import tupledict
import apache

#
# the following are host dependent globals
#
platform_name = sys.platform
apache_hosting = apache.ApacheHosting(platform_name)

class HostingConf(object):
    __slots__ = ('execution_user')

    def __init__(self):
        self.execution_user = None

hosting_conf_fn = 'hosting.conf'
hosting_conf_path = os.path.join(exenv.execution_env.ezdev_dir, hosting_conf_fn)
hosting_conf = None

def init_hosting():
    if cli.cli_input_yn("Do you want to initialize or repair this host?"):
        if not exenv.make_directory(exenv.execution_env.ezdev_dir):
            sys.exit(-1)
    print(repr(exenv.execution_user))
    print("Host {} initialized.".format(exenv.execution_env.ezdev_dir))
    sys.exit(0)

def init_site(site_name):
    resp = cli.cli_input("Do you want to initialize or repair site '{}'?".format(site_name), "yn")

def load_hosting_conf():
    global hosting_conf
    hosting_conf = None
    if os.path.isfile(hosting_conf_path):
        inifile.load(hosting_conf, ini_path=hosting_conf_path)

def show_hosting():
    exenv.execution_env.show()

if __name__ == "__main__":
    # StartupMode = StartupDirect
    # Main()
    menu = cli.CliMenu()
    #
    menu.add_action(cli.CliMenuActionItem('hinit', init_hosting, None, desc="Initialize host"))
    menu.add_action(cli.CliMenuActionItem('show', show_hosting, None, desc="Show host information"))
    #
    tdict = tupledict.TupleDict()
    tdict.define_positional_parameter('site_name')
    m = menu.add_action(cli.CliMenuActionItem('sinit', init_site, None, desc="Initialize site"))
    m.tdict = tdict
    #
    exenv.execution_env.set_run_name(__name__)
    menu.cli_run()
