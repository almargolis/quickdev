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

HierarchySeparatorCharacter = '.'
#$define SERIALIZED_FILE_PATH _serialized_file_path

def open_serialized_file(target, path=None):
    """
    Open a serialized text file.

    Returns open textfile.TextFile() object if succesful or None if not.
    """
    if path is None:
        path = getattr(target, $'SERIALIZED_FILE_PATH$, None)
    if path is None:
        return None
    f = textfile.open(wsFilePath, 'r')
    if f is None:
        return None
    f.ConfigureStripEOL()
    if hasattr(target, $'SERIALIZED_FILE_PATH$):
        setattr(target, $'SERIALIZED_FILE_PATH$, path)
    return f
