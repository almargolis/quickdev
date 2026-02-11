import os

from qdbase import exenv
from qdbase import pdict

from qdutils import hosting
from qdutils import qdstart

from . import test_qdstart


def test_init(tmpdir):
    qd_chroot = test_qdstart.MakeQdChroot(tmpdir)


def test_site_register(tmpdir):
    start = test_qdstart.make_qdsite(tmpdir)
    print("DEV SITE CONF", start.qdsite_info)
    hosting.register_qdsite(qdsite_dpath=start.qdsite_info.qdsite_dpath)
    qdsite_info = exenv.QdSite(qdsite_dpath=start.qdsite_info.qdsite_dpath)
    assert hosting.verify_site_registration(qdsite_info)
 