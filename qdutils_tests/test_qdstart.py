import os

from qdbase import cliinput

from qdcore import qdsite

from qdutils import qdstart

INI_ACRONYM = 'test'

def make_site(tmpdir):
    cliinput.debug_input_answers['Site Acronym'] = INI_ACRONYM
    cliinput.debug_input_answers["Do you want to use this VENV for this project?"] = 'y'
    return qdstart.QdStart(site_dpath=tmpdir, force=True, debug=1)

def test_basic(tmpdir):
    start = make_site(tmpdir)
    # Create a new site object to verify that all persistent data
    # collected by QdStart() was actually saved.
    site = qdsite.QdSite(site_dpath=tmpdir)
    assert site.ini_data[qdsite.CONF_PARM_ACRONYM] == INI_ACRONYM
