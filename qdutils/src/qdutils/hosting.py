"""
Hosting manages the base configuration for computers that host QuickDev sites.

This is called hosting because it will most commonly be used to
configure internet servers of various kinds, but it also is used
for development workstations and CLI applications.
"""

import os
import sys
import uuid

from qdbase import exenv
from qdbase import cliargs
from qdbase import cliinput
from qdbase import pdict
from qdbase import qdos
from qdbase import qdsqlite

# qdsite was merged into exenv; constants are now in exenv

from . import apache
from . import qdstart

hdb_dict = pdict.DbDictDb()

d = hdb_dict.add_table(pdict.DbDictTable(exenv.HDB_DEVSITES))
d.add_column(pdict.Text(exenv.CONF_PARM_ACRONYM))
d.add_column(pdict.Text(exenv.CONF_PARM_UUID))
d.add_column(pdict.Text(exenv.CONF_PARM_SITE_DPATH))
d.add_column(pdict.Text(exenv.CONF_PARM_SITE_UDI))
d.add_index("ix_acronym", exenv.CONF_PARM_ACRONYM)
d.add_index("ix_uuid", exenv.CONF_PARM_UUID)
d.add_index("ix_qdsite_dpath", exenv.CONF_PARM_SITE_DPATH)
d.add_index("ix_udi", exenv.CONF_PARM_SITE_UDI)

d = hdb_dict.add_table(pdict.DbDictTable(exenv.HDB_WEBSITES))
d.add_column(pdict.Text(exenv.CONF_PARM_UUID))
d.add_column(pdict.Text(exenv.CONF_PARM_HOST_NAME))
d.add_column(pdict.Text(exenv.CONF_PARM_WEBSITE_SUBDIR))
d.add_index("ix_host_name", exenv.CONF_PARM_HOST_NAME)

#
# the following are host dependent globals
#
platform_name = sys.platform
apache_hosting = apache.ApacheHosting()


class HostingConf(object):
    __slots__ = "execution_user"

    def __init__(self):
        self.execution_user = None


hosting_conf_fn = "hosting.conf"
hosting_conf_path = os.path.join(exenv.g.qdhost_dpath, hosting_conf_fn)
hosting_conf = None


def init_hosting(force=False):
    if not force:
        if not cliinput.cli_input_yn("Do you want to initialize or repair this host?"):
            sys.exit(-1)
    qdos.make_directory(
        "Host configuraration", exenv.g.qdhost_dpath, force=force, raise_ex=True
    )
    db = qdsqlite.QdSqlite(exenv.g.qdhost_db_fpath, db_dict=hdb_dict)
    for this in exenv.g.qdhost_all_subdirs:
        this_dpath = os.path.join(exenv.g.qdhost_dpath, this)
        qdos.make_directory(
            "Host conf subdirectory", this_dpath, force=force, raise_ex=True
        )
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


def verify_site_registration(site):
    """
    Verify that the site configuration and the hosting
    database are consistent.
    """
    db = qdsqlite.QdSqlite(exenv.g.qdhost_db_fpath)
    site_acronym = site.qdsite_prefix or ""
    qdsite_dpath = site.qdsite_dpath or ""
    # UUID and SITE_UDI are now stored via qdconf
    site_uuid = site.qdconf.get('site.uuid', "") if site.qdconf else ""
    site_udi = site.qdconf.get('site.site_udi', "") if site.qdconf else ""
    where = {exenv.CONF_PARM_SITE_DPATH: qdsite_dpath}
    db_rows = db.select(exenv.HDB_DEVSITES, where=where)
    if len(db_rows) != 1:
        print("Ambiguous qdsite_dpath '{}'".format(qdsite_dpath))
        return False
    if db_rows[0][exenv.CONF_PARM_ACRONYM] != site_acronym:
        print(
            "Inconsistant site acronym @host='{}' @site='{}'".format(
                db_rows[0][exenv.CONF_PARM_ACRONYM], site_acronym
            )
        )
        return False
    if db_rows[0][exenv.CONF_PARM_UUID] != site_uuid:
        print(
            "Inconsistant site uuid @host='{}' @site='{}'".format(
                db_rows[0][exenv.CONF_PARM_UUID], site_uuid
            )
        )
        return False
    host_db_udi = str(db_rows[0][exenv.CONF_PARM_SITE_UDI])
    if host_db_udi != str(site_udi):
        print(
            "Inconsistant site udi @host='{}' @site='{}'".format(
                db_rows[0][exenv.CONF_PARM_SITE_UDI], site_udi
            )
        )
        return False
    return True


def check_if_site_registered(db, site):
    # UUID and SITE_UDI are now stored via qdconf
    site_uuid = site.qdconf.get('site.uuid', "") if site.qdconf else ""
    site_udi = site.qdconf.get('site.site_udi', "") if site.qdconf else ""
    if (site_uuid != "") or (site_udi != ""):
        return True
    where = {exenv.CONF_PARM_SITE_DPATH: site.qdsite_dpath}
    db_rows = db.select(exenv.HDB_DEVSITES, where=where)
    if len(db_rows) > 0:
        return True
    return False


def register_qdsite(qdsite_dpath=None):
    """
    Register a qdsite that has not previously been registered.
    """
    site = exenv.QdSite(qdsite_dpath=qdsite_dpath)
    db = qdsqlite.QdSqlite(exenv.g.qdhost_db_fpath)
    if check_if_site_registered(db, site):
        print("Site appears to already be registered.")
        return
    site_uuid = str(uuid.uuid4().bytes)
    max_func = "MAX({})".format(exenv.CONF_PARM_SITE_UDI)
    sum_rows = db.select(exenv.HDB_DEVSITES, max_func)
    max_udi = sum_rows[0][max_func]
    if max_udi is None:  # if table is empty
        max_udi = 0
    max_udi += 1
    site_udi = str(max_udi)

    # Update hosting database
    qdsite_row = {}
    qdsite_row[exenv.CONF_PARM_ACRONYM] = site.qdsite_prefix
    qdsite_row[exenv.CONF_PARM_SITE_DPATH] = site.qdsite_dpath
    qdsite_row[exenv.CONF_PARM_UUID] = site_uuid
    qdsite_row[exenv.CONF_PARM_SITE_UDI] = site_udi
    db.insert(exenv.HDB_DEVSITES, qdsite_row)

    # Update development site conf file with host registration data
    if site.qdconf is not None:
        site.qdconf['site.uuid'] = site_uuid
        site.qdconf['site.site_udi'] = site_udi
        site.qdconf.write_conf_file('site')


if __name__ == "__main__":
    # There is a great deal of symetry between hosting.py and apache.py
    # commands. If you change one, check the other to see if similar
    # changes are needed.
    menu = cliargs.CliCommandLine()
    exenv.command_line_loc(menu)
    exenv.command_line_site(menu)
    #
    menu.add_item(
        cliargs.CliCommandLineActionItem("hinit", init_hosting, help="Initialize host")
    )
    m = menu.add_item(
        cliargs.CliCommandLineActionItem("sregit", init_hosting, help="Register site.")
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(
            exenv.ARG_L_CONF_LOC, parameter_name="qdsite_dpath"
        )
    )
    menu.add_item(
        cliargs.CliCommandLineActionItem(
            "show", show_hosting, help="Show host information"
        )
    )
    #
    exenv.execution_env.set_run_name(__name__)
    menu.cli_run()
