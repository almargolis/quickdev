"""
QdSite provides access to site information.
"""

import os
import werkzeug

from qdbase import exenv
from qdcore import qdconst
from qdcore import inifile

CONF_ETC_ORG = "etc_org"

CONF_SUBDIRECTORIES = [CONF_ETC_ORG]

HDB_DEVSITES = "qdsites"
HDB_WEBSITES = "website"

CONF_PARM_ACRONYM = "acronym"
CONF_PARM_UUID = "uuid"
CONF_PARM_HOST_NAME = "domain_name"
CONF_PARM_WEBSITE_SUBDIR = "website_subdir"
CONF_PARM_SITE_DPATH = "qdsite_dpath"
CONF_PARM_SITE_UDI = "site_udi"
CONF_PARM_VENV_DPATH = "venv_dpath"

VENV_ACTIVATE_SUB_FPATH = 'bin/activate'

def identify_site(site=None):
    """
    Returns QdSite() object if a site can be identified using the site
    parameter or the current working directory.
    """
    cwd = os.getcwd()
    return None


class hold:
    def init_qddev(self, args):
        if qdconst is None:
            print("QdDev not inintialied. Run {}. (E1)".format(qdstart.QDSTART_PATH))
            return False

        self.conf_dir_path = os.path.join(self.base_dir, qdconst.SITE_CONF_DIR_NAME)
        self.project_db_path = os.path.join(self.conf_dir_path, qdconst.PROJECT_DB_FN)
        if not os.path.isdir(self.conf_dir_path):
            print("QdDev not inintialied. Run {}. (E2)".format(qdstart.QDSTART_PATH))
            return False
        if not self.load_conf():
            print("XSynth source files not processed.")
            return False
        return True

    def load_conf(self):
        self.conf_info = inifile.read_ini_directory(
            dir=self.conf_dir_path, ext=qdconst.CONF_EXT
        )
        if self.conf_info is None:
            return False
        self.sources = self.conf_info["site.sources"]
        return True


def get_site_by_acronym(acronym):
    dev_ini_fpath = werkzeug.utils.safe_join(
        exenv.g.qdhost_qdsites_dpath, acronym + ".ini"
    )
    dev_ini_data = inifile.IniReader(file_name=dev_ini_fpath)
    qdsite_dpath = dev_ini_data["qdsite_dpath"]
    return QdSite(qdsite_dpath=qdsite_dpath, host_site_ini=dev_ini_data)


class QdSite:
    """
    QdSite is a container for core information regarding a site.

    QdSite only reflects existing information. It does not create
    site information or directories. Use QdStart to initialize
    or repair a site.

    A global instance is created within exenv.ExecutionEnvironment()
    which describes the site where the current program is executing,
    which could be an development site
    for QdDev itself or a host management site. Programs run from there
    may create additional instances for a site being configured.
    """

    __slots__ = ("conf_dpath", "host_site_data", "ini_data", "ini_fpath", "qdsite_dpath")

    def __init__(self, qdsite_dpath=None, host_site_ini=None):
        if qdsite_dpath is None:
            qdsite_dpath = os.getcwd()
        self.qdsite_dpath = os.path.abspath(qdsite_dpath)
        if not os.path.isdir(self.qdsite_dpath):
            raise ValueError(f"Invalid qdsite path '{self.qdsite_dpath}'.'")
        acronym = os.path.basename(self.qdsite_dpath)
        if acronym == "":
            raise ValueError(f"Invalid qdsite acronym '{self.qdsite_dpath}' '{acronym}'")
        self.conf_dpath = os.path.join(self.qdsite_dpath, qdconst.SITE_CONF_DIR_NAME)
        self.ini_fpath = os.path.join(self.conf_dpath, qdconst.SITE_CONF_FILE_NAME)
        self.ini_data = inifile.IniReader(file_name=self.ini_fpath)
        ini_data_changed = False
        if self.ini_data is None:
            self.ini_data = {}
        if not CONF_PARM_SITE_DPATH in self.ini_data:
            self.ini_data[CONF_PARM_SITE_DPATH] = self.qdsite_dpath
            ini_data_changed = True
        if not CONF_PARM_ACRONYM in self.ini_data:
            self.ini_data[CONF_PARM_ACRONYM] = acronym
            ini_data_changed = True
        if ini_data_changed:
            if os.path.isdir(self.conf_dpath):
                # The directory may not exist yet, particularly if called
                # by QdStart()
                self.write_site_ini()
        if (self.ini_data.get(CONF_PARM_SITE_DPATH, "") != self.qdsite_dpath) or (
            self.ini_data.get(CONF_PARM_ACRONYM, "") != acronym
        ):
            raise ValueError(f"Invalid qdsite ini '{self.qdsite_dpath}' '{acronym}' {self.ini_data}")
        self.host_site_data = host_site_ini

    def __str__(self):
        return f"{self.qdsite_dpath}, {self.ini_fpath}: {self.ini_data}."

    def get_venv_activate_fpath(self):
        """
        This attempts to get the fpath to the VENV activate script.
        If the site hasn't been fully configured, it uses the current VENV
        if it finds one.
        """
        venv_dpath = self.ini_data.get(CONF_PARM_VENV_DPATH, None)
        if venv_dpath is None:
            venv_dpath = os.environ.get(exenv.OS_ENV_VIRTUAL_ENV, None)
        if venv_dpath is None:
            return None
        return os.path.join(venv_dpath, VENV_ACTIVATE_SUB_FPATH)

    def write_site_ini(self, debug=0):
        if not inifile.write_ini_file(
            source=self.ini_data, fpath=self.ini_fpath, debug=debug
        ):
            raise Exception(
                "Unable to write site ini file '{}'.".format(self.ini_fpath)
            )

    @property
    def synthesis_db_path(self):
        return None
