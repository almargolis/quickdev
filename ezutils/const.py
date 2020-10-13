
SITE_CONF_DIR_NAME = 'conf'                 # relative to site_path
SITE_CONF_FILE_NAME = 'site.conf'
PROJECT_DB_FN = 'project_db.sql'
PROJECT_CONF_FN = 'xpython.conf'

def list_files(self, search_dir, ext, dir_files=None, recursive=False):
    """
    Build a list of files in a directory (or tree) that match
    the specified extension.
    """
    dir_all = os.listdir(search_dir)
    dir_dir = []
    if dir_files is None:
        dir_files = []
    for this in dir_all:
        this_path = os.path.join(search_dir, this)
        if os.path.isdir(this_path):
            dir_dir.append(this_path)
        else:
            parts = os.path.splitext(this_path)
            if parts[1] == ext:
                dir_files.append(FileInfo(this_path))
    if recursive:
        for this_subdir in dir_dir:
            self.list_files(this_subdir, ext, dir_files=dir_files)
    return dir_files
