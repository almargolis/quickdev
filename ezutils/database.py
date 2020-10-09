# datbae.py - CommerceNode database utilities
#

import sys

from cncore import cli
from cncore import configutils
from cncore import rdbms
from cncore import tupledict

#
# the following are host dependent globals
#
platform_name = sys.platform

def init_hosting():
    pass

def init_site(site_name):
    resp = cli.cli_input("Do you want to initialize or repair site '{}'?".format(site_name), "yn")

if __name__ == "__main__":
    menu = cli.CliMenu()
    #
    menu.append(cli.CliMenuItem('hinit', init_hosting, None, desc="Initialize host"))
    #
    tdict = tupledict.TupleDictionary()
    tdict.define_positional_parameter('site_name')
    m = menu.append(cli.CliMenuItem('sinit', init_site, None, desc="Initialize site"))
    m.tdict = tdict
    #
    env = configutils.ExecutionEnvironment(__name__)
    if not env.check_version():
        sys.exit(-1)
    menu.cli_run()

