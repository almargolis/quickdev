"""
Hosting manages the base configuration for commercenode sites and
commercenode development.

This is called hosting because it will most commonly be used to
configure internet servers of various kinds, but it also is used
for development workstations and CLI applications.
"""

import os
import sys

from cncore import configutils
from cncore import cli
from cncore import tupledict
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
hosting_conf_path = os.path.join(configutils.commercenode_dir, hosting_conf_fn)
hosting_conf = None

def init_hosting():
    if cli.cli_input_yn("Do you want to initialize or repair this host?"):
        print("yes")
        configutils.make_directory(configutils.commercenode_dir)
    else:
        print("no")
    print(repr(configutils.execution_user))

def init_site(site_name):
    resp = cli.cli_input("Do you want to initialize or repair site '{}'?".format(site_name), "yn")

def load_hosting_conf():
    global hosting_conf
    hosting_conf = None
    if os.path.isfile(hosting_conf_path):
        inifile.load(hosting_conf, ini_path=hosting_conf_path)

if __name__ == "__main__":
    # StartupMode = StartupDirect
    # Main()
    menu = cli.CliMenu()
    #
    menu.append(cli.CliMenuItem('hinit', init_hosting, None, desc="Initialize host"))
    #
    tdict = tupledict.TupleDict()
    tdict.define_positional_parameter('site_name')
    m = menu.append(cli.CliMenuItem('sinit', init_site, None, desc="Initialize site"))
    m.tdict = tdict
    #
    env = configutils.ExecutionEnvironment(__name__)
    if not env.check_version():
        sys.exit(-1)
    menu.cli_run()
