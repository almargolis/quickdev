"""
QdSite provides access to site information.
"""

import os
import werkzeug

from qdbase import exenv
from qdcore import qdconst
from qdcore import inifile

CONF_ETC_ORG = 'etc_org'

CONF_SUBDIRECTORIES = [CONF_ETC_ORG]

def identify_site(site=None):
    """
    Returns QdSite() object if a site can be identified using the site
    parameter or the current working directory.
    """
    cwd = os.getcwd()
    return None

class hold():
    def init_qddev(self, args):
        if qdconst is None:
            print('QdDev not inintialied. Run {}. (E1)'.format(qdstart.QDSTART_PATH))
            return False

        self.conf_dir_path = os.path.join(self.base_dir,
                                                  qdconst.SITE_CONF_DIR_NAME)
        self.project_db_path = os.path.join(self.conf_dir_path,
                                            qdconst.PROJECT_DB_FN)
        if not os.path.isdir(self.conf_dir_path):
            print('QdDev not inintialied. Run {}. (E2)'.format(qdstart.QDSTART_PATH))
            return False
        if not self.load_conf():
            print('XSynth source files not processed.')
            return False
        return True

    def load_conf(self):
        self.conf_info = inifile.read_ini_directory(dir=self.conf_dir_path,
                                                    ext=qdconst.CONF_EXT)
        if self.conf_info is None:
            return False
        self.sources = self.conf_info['site.sources']
        return True

def get_site_by_acronym(acronym):
    dev_ini_fpath = werkzeug.utils.safe_join(exenv.g.qdhost_devsites_dpath, acronym + '.ini')
    dev_ini_data = inifile.read_ini_file(file_name=dev_ini_fpath)
    site_dpath = dev_ini_data['site_dpath']
    return QdSite(site_dpath=site_dpath, host_site_ini=dev_ini_data)

class QdSite():
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
    __slots__ = ('conf_path', 'host_site_data', 'ini_data', 'ini_path', 'site_dpath')
    def __init__(self, site_dpath=None, host_site_ini=None):
        if site_dpath is None:
            site_dpath = os.getcwd()
        self.site_dpath = os.path.abspath(site_dpath)
        self.conf_path = os.path.join(self.site_dpath, qdconst.SITE_CONF_DIR_NAME)
        self.ini_path = os.path.join(self.conf_path, qdconst.SITE_CONF_FILE_NAME)
        self.ini_data = inifile.read_ini_file(file_name=self.ini_path)
        print("QdSite", self.ini_path, self.ini_data)
        self.host_site_data = host_site_ini
        if self.ini_data is None:
            self.ini_data = {}
            self.ini_data['site_dir'] = self.site_dpath

    def __str__(self):
        return "{site_dpath}, {ini_path}: {ini_data}.".format(
               site_dpath=self.site_dpath, ini_path=self.ini_path,
               ini_data=str(self.ini_data))

    def write_site_ini(self):
        if not inifile.write_ini_file(source=self.ini_data, path=self.ini_path):
            raise Exception("Unable to write site ini file '{}'.".format(self.ini_path))

    @property
    def synthesis_db_path(self):
        return None
