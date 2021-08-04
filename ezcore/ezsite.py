"""
EzSite provides access to site information.
"""

import os

from ezcore import ezconst
from ezcore import inifile

CONF_ETC_ORG = 'etc_org'

CONF_SUBDIRECTORIES = [CONF_ETC_ORG]

def identify_site(site=None):
    """
    Returns EzSite() object if a site can be identified using the site
    parameter or the current working directory.
    """
    cwd = os.getcwd()
    return None

class hold():
    def init_ezdev(self, args):
        if ezconst is None:
            print('EzDev not inintialied. Run {}. (E1)'.format(ezstart.EZSTART_PATH))
            return False

        self.conf_dir_path = os.path.join(self.base_dir,
                                                  ezconst.SITE_CONF_DIR_NAME)
        self.project_db_path = os.path.join(self.conf_dir_path,
                                            ezconst.PROJECT_DB_FN)
        if not os.path.isdir(self.conf_dir_path):
            print('EzDev not inintialied. Run {}. (E2)'.format(ezstart.EZSTART_PATH))
            return False
        if not self.load_conf():
            print('XSynth source files not processed.')
            return False
        return True

    def load_conf(self):
        self.conf_info = inifile.read_ini_directory(dir=self.conf_dir_path,
                                                    ext=ezconst.CONF_EXT)
        if self.conf_info is None:
            return False
        self.sources = self.conf_info['site.sources']
        return True


class EzSite():
    """
    EzSite is a container for core information regarding a site.

    A global instance is created within exenv.ExecutionEnvironment()
    which describes the site where the current program is executing,
    which could be an development site
    for EzDev itself or a host management site. Programs run from there
    may create additional instances for a site being configured.
    """
    __slots__ = ('conf_path', 'ini_info', 'ini_path', 'site_path')
    def __init__(self, site_path=None):
        if site_path is None:
            self.site_path = os.getcwd()
        else:
            self.site_path = site_path
        self.site_path = os.path.abspath(self.site_path)
        self.conf_path = os.path.join(self.site_path, ezconst.SITE_CONF_DIR_NAME)
        self.ini_path = os.path.join(self.conf_path, ezconst.SITE_CONF_FILE_NAME)
        self.ini_info = inifile.read_ini_file(file_name=self.ini_path)
        if self.ini_info is None:
            self.ini_info = {}
            self.ini_info['site_dir'] = self.site_path

    def __repr__(self):
        return self.site_path

    def write_site_ini(self):
        inifile.write_ini_file(source=self.ini_info, path=self.ini_path)

    @property
    def synthesis_db_path(self):
        return None
