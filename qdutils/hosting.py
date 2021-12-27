"""
Hosting manages the base configuration for computers that host EzDev sites.

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
from qdbase import qdsqlite

from qdcore import qdsite

from . import apache
from . import qdstart

HDB_SITES = "sites"
HDB_WEBSITES = "website"

hdb_dict = pdict.DbDict()

d = hdb_dict.add_table(pdict.DbTableDict(HDB_SITES))
d.add_column(pdict.Text(qdsite.CONF_PARM_ACRONYM))
d.add_column(pdict.Text(qdsite.CONF_PARM_UUID))
d.add_column(pdict.Text(qdsite.CONF_PARM_SITE_DPATH))
d.add_column(pdict.Text(qdsite.CONF_PARM_SITE_UDI))
d.add_index("ix_acronym", qdsite.CONF_PARM_ACRONYM)
d.add_index("ix_uuid", qdsite.CONF_PARM_UUID)
d.add_index("ix_site_dpath", qdsite.CONF_PARM_SITE_DPATH)
d.add_index("ix_udi", qdsite.CONF_PARM_SITE_UDI)

d = hdb_dict.add_table(pdict.DbTableDict(HDB_WEBSITES))
d.add_column(pdict.Text(qdsite.CONF_PARM_DOMAIN_NAME))
d.add_column(pdict.Text(qdsite.CONF_PARM_WEBSITE_SUBDIR))
d.add_index("ix_domain", qdsite.CONF_PARM_DOMAIN_NAME)

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
    exenv.make_directory(
        "Host configuraration", exenv.g.qdhost_dpath, force=force, raise_ex=True
    )
    db = qdsqlite.QdSqlite(exenv.g.qdhost_db_fpath, db_dict=hdb_dict)
    for this in exenv.g.qdhost_all_subdirs:
        this_dpath = os.path.join(exenv.g.qdhost_dpath, this)
        exenv.make_directory(
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
    site_acronym = site.ini_data.get(qdsite.CONF_PARM_ACRONYM, "")
    site_dpath = site.ini_data.get(qdsite.CONF_PARM_SITE_DPATH, "")
    site_uuid = site.ini_data.get(qdsite.CONF_PARM_UUID, "")
    site_udi = site.ini_data.get(qdsite.CONF_PARM_SITE_UDI, "")
    where = {qdsite.CONF_PARM_SITE_DPATH: site_dpath}
    db_rows = db.select(HDB_SITES, where=where)
    if len(db_rows) != 1:
        print("Ambiguous site_dpath '{}'".format(site_dpath))
        return False
    if db_rows[0][qdsite.CONF_PARM_ACRONYM] != site_acronym:
        print(
            "Inconsistant site acronym @host='{}' @site='{}'".format(
                db_rows[0][qdsite.CONF_PARM_ACRONYM], site_acronym
            )
        )
        return False
    if db_rows[0][qdsite.CONF_PARM_UUID] != site_uuid:
        print(
            "Inconsistant site uuid @host='{}' @site='{}'".format(
                db_rows[0][qdsite.CONF_PARM_UUID], site_uuid
            )
        )
        return False
    host_db_udi = str(db_rows[0][qdsite.CONF_PARM_SITE_UDI])
    if host_db_udi != str(site_udi):
        print(
            "Inconsistant site udi @host='{}' @site='{}'".format(
                db_rows[0][qdsite.CONF_PARM_SITE_UDI], site_udi
            )
        )
        return False
    return True


def check_if_site_registered(db, site):
    site_uuid = site.ini_data.get(qdsite.CONF_PARM_UUID, "")
    site_udi = site.ini_data.get(qdsite.CONF_PARM_SITE_UDI, "")
    if (site_uuid != "") or (site_udi != ""):
        return True
    where = {qdsite.CONF_PARM_SITE_DPATH: site.site_dpath}
    db_rows = db.select(HDB_SITES, where=where)
    if len(db_rows) > 0:
        return True
    return False


def register_site(site_dpath=None):
    """
    Register a site that has not previously been registered.
    """
    site = qdsite.QdSite(site_dpath=site_dpath)
    db = qdsqlite.QdSqlite(exenv.g.qdhost_db_fpath)
    if check_if_site_registered(db, site):
        print("Site appears to already be registered.")
        return
    site_uuid = str(uuid.uuid4().bytes)
    max_func = "MAX({})".format(qdsite.CONF_PARM_SITE_UDI)
    sum_rows = db.select(HDB_SITES, max_func)
    max_udi = sum_rows[0][max_func]
    if max_udi is None:  # if table is empty
        max_udi = 0
    max_udi += 1
    site_udi = str(max_udi)

    # Update hosting database
    devsite_row = {}
    devsite_row[qdsite.CONF_PARM_ACRONYM] = site.ini_data[qdsite.CONF_PARM_ACRONYM]
    devsite_row[qdsite.CONF_PARM_SITE_DPATH] = site.site_dpath
    devsite_row[qdsite.CONF_PARM_UUID] = site_uuid
    devsite_row[qdsite.CONF_PARM_SITE_UDI] = site_udi
    db.insert(HDB_SITES, devsite_row)

    # Update develelopment site conf file
    site.ini_data[qdsite.CONF_PARM_UUID] = site_uuid
    site.ini_data[qdsite.CONF_PARM_SITE_UDI] = site_udi
    site.write_site_ini()


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
            exenv.ARG_L_CONF_LOC, parameter_name="site_dpath"
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
