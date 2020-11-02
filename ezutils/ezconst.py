"""
These are constants and utiities for the EzDev environment.

This module is located in ezutils so it can be imported by
other utilities prior to the full environment being established.
This is primarily an issue for ezstart.py and xpython.py.

"""
SITE_CONF_DIR_NAME = 'conf'                 # relative to site_path
SITE_CONF_FILE_NAME = 'site.conf'
PROJECT_DB_FN = 'project_db.sql'
PROJECT_CONF_FN = 'xpython.conf'


class serialized_file():
    """ File object with path tracking. Supports with statement. """
    __slots__ = ('f', 'mode', 'path', 'target')

    def __init__(self, target, path=None, mode='r'):
        self.f = None
        self.mode = mode
        self.target = target
        self.path = path
        if self.path is None:
            self.path = getattr(target, '_serialized_file_path', None)
        if hasattr(target, '_serialized_file_path'):
            setattr(target, '_serialized_file_path', self.path)

    def __enter__(self):
        self.f = textfile.open(self.path, self.mode)
        if self.f is None:
            return None
        self.f.ConfigureStripEOL()
        return self.f

    def __exit__(self):
        self.f.close()
        self.f = None
