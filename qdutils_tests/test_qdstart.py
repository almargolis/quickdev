"""
pytest for qdstart.py.

This includes several classes and functions, including MakeQdChroot(),
that build an environment for testing that avoids writing to actual
system configuration files.
"""

import os

from qdbase import cliinput
from qdbase import exenv

from qdcore import qdsite

from qdutils import hosting
from qdutils import qdstart

INI_ACRONYM = "test"


class MakeQdChroot:
    """
    This makes a safe test environment for QuickDev utility
    testing so they don't write to the actual system
    directories.

    exenv.ExenvGlobals is designed for this, so most things
    don't have to be particularly test-aware in order to
    run in this artificial environment.
    """

    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        root_dpath = os.path.join(tmpdir, "root")
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
        except SystemExit as error_info:
            # SystemExit is a pytest exception
            if error_info.code != 0:
                raise

    def make_os_directories(self, root_dpath):  # pylint: disable=no-self-use
        """
        Make needed directories that live in /etc.
        This get called twice, first to create the directories
        under /etc and then under /private/etc.
        On MacOS the actual directories are under /private/etc
        and /etc is a symlink to that. I am making them
        separately so I can check where the actual writes get
        aimed. I'm not sure how that will work out in the long run.
        """
        etc_dpath = os.path.join(root_dpath, "etc")
        apache_dpath = os.path.join(etc_dpath, "apache2")
        sites_available_dpath = os.path.join(apache_dpath, "sites-available")
        os.mkdir(root_dpath)
        os.mkdir(etc_dpath)
        os.mkdir(apache_dpath)
        os.mkdir(sites_available_dpath)

    def make_qdsite_dpath(self, acronym):  # pylint: disable=no-self-use
        """Make a dpath to a qdsite."""
        return os.path.join(exenv.g.qdsites_dpath, acronym)


def make_qdsite(tmpdir):
    """Make a test qdsite within a chroot environment."""
    qd_chroot = MakeQdChroot(tmpdir)
    qdsite_dpath = qd_chroot.make_qdsite_dpath(INI_ACRONYM)
    cliinput.debug_input_answers["Do you want to use this VENV for this project?"] = "y"
    return qdstart.QdStart(qdsite_dpath=qdsite_dpath, force=True, debug=1)


def test_basic(tmpdir):
    """A simple test to make sure the basics are working."""
    qdsite_start = make_qdsite(tmpdir)
    # Create a new site object to verify that all persistent data
    # collected by QdStart() was actually saved.
    qdsite_info = qdsite.QdSite(qdsite_dpath=qdsite_start.qdsite_info.qdsite_dpath)
    assert qdsite_info.ini_data[qdsite.CONF_PARM_ACRONYM] == INI_ACRONYM
