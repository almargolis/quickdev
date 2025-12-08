"""
EzExe provides the operating environment for normal EzDev application
execution. It provides common services so application code can be small
and focussed on direct application functionality.

Application functionality is defined by EzAction objects. Many applications
capabilities can be provided through standard EzAction subclasses which
do things like update databases or serve web forms. Application can
subclass EzAction for application specific actions.

"""

import os

from ezcore import ezconst
from ezcore import inifile


class EzEnv:
    __slots__ = ("conf_dir_path", "conf_info", "site_dir_path")

    def __init__(self):
        self.site_dir_path = os.getcwd()
        self.conf_dir_path = os.path.join(
            self.site_dir_path, ezconst.SITE_CONF_DIR_NAME
        )
        self.conf_info = inifile.read_ini_directory(
            self.conf_dir_path, ext=ezconst.CONF_EXT, debug=1
        )


class EzAction:
    __slots__ = ("ez_env",)

    def __init__(self, ez_env=None):
        self.ez_env = ez_env
