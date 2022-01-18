import os

from qdbase import cliinput
from qdbase import exenv

from qdcore import qdsite

from qdutils import hosting
from qdutils import qdstart

INI_ACRONYM = 'test'

class MakeQdev:
    """
    This makes a safe test environment for QuickDev utility
    testing so they don't write to the actual system
    directories.

    exenv.ExenvGlobals is designed for this, so most things
    don't have to be particularly test-aware in order to
    run in this artificail environment.
    """

    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        root_dpath = os.path.join(tmpdir, 'root')
        self.make_os_directories(root_dpath)
        private_dpath = os.path.join(root_dpath, "private")
        self.make_os_directories(private_dpath)
        var_dpath = os.path.join(root_dpath, "var")
        www_dpath = os.path.join(var_dpath, "www")
        os.mkdir(var_dpath)
        os.mkdir(www_dpath)
        exenv.g.init(root_dpath)
        try:
            hosting.init_hosting(force=True)
        except SystemExit as e:
            # SystemExit is a pytest exception
            if e.code != 0:
                raise

    def make_os_directories(self, root_dpath):
        etc_dpath = os.path.join(root_dpath, 'etc')
        apache_dpath = os.path.join(etc_dpath, "apache2")
        sites_available_dpath = os.path.join(apache_dpath, "sites-available")
        os.mkdir(root_dpath)
        os.mkdir(etc_dpath)
        os.mkdir(apache_dpath)
        os.mkdir(sites_available_dpath)

    def make_qdsite_dpath(self, acronym):
        return os.path.join(exenv.g.qdsites_dpath, acronym)


def make_site(tmpdir):
    qd_chroot = MakeQdev(tmpdir)
    qdsite_dpath = qd_chroot.make_qdsite_dpath(INI_ACRONYM)
    cliinput.debug_input_answers["Do you want to use this VENV for this project?"] = 'y'
    return qdstart.QdStart(qdsite_dpath=qdsite_dpath, force=True, debug=1)

def test_basic(tmpdir):
    start = make_site(tmpdir)
    # Create a new site object to verify that all persistent data
    # collected by QdStart() was actually saved.
    qdsite_info = qdsite.QdSite(qdsite_dpath=start.qdsite_info.qdsite_dpath)
    assert qdsite_info.ini_data[qdsite.CONF_PARM_ACRONYM] == INI_ACRONYM
