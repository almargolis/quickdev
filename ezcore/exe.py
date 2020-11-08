import os

from ezcore import ezconst
from ezcore import inifile

class EzExe():
    __slots__ = ('conf_dir_path', 'conf_info', 'site_dir_path')

    def __init__(self):
        self.site_dir_path = os.getcwd()
        self.conf_dir_path = os.path.join(self.site_dir_path, ezconst.SITE_CONF_DIR_NAME)
        self.conf_info = inifile.read_ini_directory(self.conf_dir_path,
                                                    ext=ezconst.CONF_EXT, debug=1)
