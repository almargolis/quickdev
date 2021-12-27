import os

from qdbase import exenv
from qdbase import pdict

from qdcore import qdsite

from qdutils import hosting
from qdutils import qdstart

from . import test_qdstart

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
        self.root = tmpdir.mkdir("root")
        etc = self.root.mkdir("etc")
        apache = etc.mkdir("apache2")
        apache.mkdir("sites-available")
        private = self.root.mkdir("private")
        private_etc = private.mkdir("etc")
        private_apache = private_etc.mkdir("apache2")
        private_apache.mkdir("sites-available")
        var = self.root.mkdir("var")
        var.mkdir("www")
        exenv.g.init(self.root)
        try:
            hosting.init_hosting(force=True)
        except SystemExit as e:
            # SystemExit is a pytest exception
            if e.code != 0:
                raise


def test_init(tmpdir):
    q = MakeQdev(tmpdir)

def test_site_register(tmpdir):
    q = MakeQdev(tmpdir)
    site_dpath = os.path.join(exenv.g.devsites_dpath, 'tester')
    start = test_qdstart.make_site(site_dpath)
    print("DEV SITE CONF", start.dev_site.ini_data)
    hosting.register_site(site_dpath=site_dpath)
    site = qdsite.QdSite(site_dpath=site_dpath)
    assert hosting.verify_site_registration(site)
