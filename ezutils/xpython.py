#!python
"""
Xpython is a preprocessor for python that adds data modeling and
structured programming features without interfering with normal
python fundamentals.

Xpython was developed for EzDev but has both a stand-alone and
EzDev mode. In stand-alone mode it has minimal EzDev dependencies,
it just processes the files in a directory. This means that almost all
EzDev modules but XPython can use XPython features.

"""

import argparse
import os
import stat
import sys

# These paths and the ezcore import exception logic below are
# required for when xpython is run before ezstart has
# has configured the python virtual environment.

THIS_MODULE_PATH = os.path.abspath(__file__)
EZUTILS_PATH = os.path.dirname(THIS_MODULE_PATH)
EZDEV_PATH = os.path.dirname(EZUTILS_PATH)
EZCORE_PATH = os.path.join(EZDEV_PATH, 'ezcore')
RESERVED_MODULE_NAMES = ['xlocal']

try:
    from ezcore import pdict
except ModuleNotFoundError:
    pdict = None
if pdict is None:
    sys.path.append(EZCORE_PATH)
    from ezcore import pdict

from ezcore import ezsqlite
from ezcore import xsource

try:
    from ezcore import ezconst
except ModuleNotFoundError:
    # May not be found because its an xpy that might not
    # have been gen'd.
    ezconst = None
except SyntaxError:
    # Might be xpython translate failed.
    ezconst = None

try:
    from ezcore import inifile
except ModuleNotFoundError:
    # May not be found because its an xpy that might not
    # have been gen'd.
    inifile = None
except SyntaxError:
    # Might be xpython translate failed.
    inifile = None

db_dict = pdict.DbDict()

d = db_dict.add_table(pdict.DbTableDict('sources'))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('path'))
d.add_column(pdict.Number('status'))
d.add_column(pdict.Number('found'))
d.add_column(pdict.Number('modification_time'))
d.add_index('ix_sources', 'module_name')

d = db_dict.add_table(pdict.DbTableDict('module_uses'))
d.add_column(pdict.Text('source_module_name'))
d.add_column(pdict.Text('uses_module_name'))
d.add_index('ix_module_uses', 'source_module_name', 'uses_module_name')

d = db_dict.add_table(pdict.DbTableDict('defines'))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('define_name'))
d.add_column(pdict.Text('value'))
d.add_index('ix_defines', 'module_name', 'define_name')

d = db_dict.add_table(pdict.DbTableDict('classes'))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('class_name'))
d.add_column(pdict.Text('base_class'))
d.add_index('ix_classes', 'module_name', 'class_name')

d = db_dict.add_table(pdict.DbTableDict('defs'))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('class_name'))
d.add_column(pdict.Text('def_name'))
d.add_column(pdict.Text('decorator'))
d.add_index('ix_defs', 'module_name', 'class_name', 'def_name', 'decorator')

d = db_dict.add_table(pdict.DbTableDict('actions'))
d.add_column(pdict.Text('module_name'))
d.add_column(pdict.Text('action_name'))
d.add_column(pdict.Text('action_type'))
d.add_index('ix_actions', 'action_name')

d = db_dict.add_table(pdict.DbTableDict('progs'))
d.add_column(pdict.Text('prog_name'))
d.add_column(pdict.Text('prog_type'))
d.add_column(pdict.Text('action_name'))
d.add_column(pdict.Text('trigger_name'))
d.add_index('ix_progs', 'prog_name')

def abend(msg):
    """Report critical error and exit xpython (abnormal end). """
    print(msg)
    print("Unable to continue")
    sys.exit(-1)

def input_yn(prompt, default='y'):
    """CLI input with validation of y/n response."""
    if default is None:
        display_choices = ' (y/n)'
    elif default == 'y':
        display_choices = ' (Y/n)'
    else:
        display_choices = ' (y/N)'
    display_prompt = prompt + display_choices
    resp = 'x'
    while resp not in 'yn':
        resp = input(display_prompt)
        if resp == '':
            if default == 'y':
                resp = 'y'
            else:
                resp = 'n'
    return resp == 'y'


class FileInfo:  # pylint: disable=too-few-public-methods
    """
    FileInfo is a container for file metadata and
    processing state.
    """
    __slots__ = ('dir_name', 'file_name', 'file_ext',
                 'modification_time', 'module_name', 'path')

    def __init__(self, path):
        stats_obj = os.stat(path)
        self.path = os.path.abspath(path)
        self.dir_name, self.file_name = os.path.split(path)
        self.module_name, self.file_ext = os.path.splitext(self.file_name)
        self.modification_time = stats_obj[stat.ST_MTIME]

    def new_path(self, ext):
        """
        Provide the path for a derivative file named by changing
        the extension.

        ext should include the leading period. e.g.: ".py"
        """
        return os.path.join(self.dir_name, self.module_name) + ext

class XPython:
    """ Main XPython implementation class."""
    __slots__ = ('base_dir', 'db', 'debug',
                 'conf_info',
                 'conf_dir_path',
                    'project_db_path', 'quiet',
                    'source_dirs', 'stand_alone',
                    'xpy_files', 'xpy_files_changed')

    def __init__(self, args, debug=0):
        self.conf_info = None
        self.conf_dir_path = None
        self.debug = debug
        self.quiet = args.quiet
        self.stand_alone = args.stand_alone
        if self.stand_alone:
            self.base_dir = None
            self.source_dirs = args.site_path
            self.project_db_path = ezsqlite.SQLITE_IN_MEMORY_FN
        else:
            if len(args.site_path) < 1:
                self.base_dir = os.getcwd()
            else:
                self.base_dir = args.site_path[0]
            if not self.init_ezdev(args):
                return
        self.db = ezsqlite.EzSqlite(self.project_db_path,
                                     db_dict=db_dict, debug=0)
        self.process_xpy_files()

    def init_ezdev(self, args):
        if ezconst is None:
            print('EzDev not inintialied. Run EzStart. (E1)')
            return False

        self.conf_dir_path = os.path.join(self.base_dir,
                                                  ezconst.SITE_CONF_DIR_NAME)
        self.project_db_path = os.path.join(self.conf_dir_path,
                                            ezconst.PROJECT_DB_FN)
        if not os.path.isdir(self.conf_dir_path):
            print('EzDev not inintialied. Run EzStart. (E2)')
            return False
        if args.reset:
            try:
                os.unlink(self.project_db_path)
            except FileNotFoundError:
                pass
        if not self.load_conf():
            print('XPython source files not processed.')
            return False
        return True

    def load_conf(self):
        self.conf_info = inifile.read_ini_directory(dir=self.conf_dir_path,
                                                    ext=ezconst.CONF_EXT)
        if self.conf_info is None:
            return False
        self.source_dirs = self.conf_info['site.source_dirs']
        return True

    def scan_directory(self, search_dir, ext, recursive=False):
        """
        Scan a direcory and update the sources database.
        """
        dir_all = os.listdir(search_dir)
        dir_dir = []
        for this_file_name in dir_all:
            this_path = os.path.join(search_dir, this_file_name)
            if os.path.isdir(this_path):
                dir_dir.append(this_path)
            else:
                parts = os.path.splitext(this_path)
                if parts[1] == ext:
                    self.post_sources_table(this_path)
        if recursive:
            for this_subdir in dir_dir:
                self.scan_directory(this_subdir, ext, recursive=True)

    def process_xpy_files(self):
        """
        Scan directories to locate source files. Update the
        sources table and then process them.
        """
        self.db.update('sources', {'found': 0})
        for this_directory in self.source_dirs:
            self.scan_directory(this_directory, '.xpy')

        while True:
            # We re-select for each source because XSource
            # may process multiple sources recursively.
            # The to-do list is not static.
            sql_data = self.db.select('sources', '*',
                                       where={'status': xsource.SOURCE_STATUS_READY},
                                       limit=1)
            if len(sql_data) < 1:
                break
            xsource.XSource(module_name=sql_data[0]['module_name'],
                            dir_path=os.path.dirname(sql_data[0]['path']), db=self.db)

    def post_sources_table(self, path):
        file_info = FileInfo(path)
        if file_info.module_name in RESERVED_MODULE_NAMES:
            abend("Reserved module name {}".format(file_info.module_name))
        sql_data = self.db.select('sources', '*',
                                      where={'module_name':
                                             file_info.module_name})
        if len(sql_data) < 1:
            self.db.insert('sources', {
                            'module_name': file_info.module_name,
                            'path': file_info.path,
                            'found': 1,
                            'status': xsource.SOURCE_STATUS_READY,
                            'modification_time': file_info.modification_time
                            })
            return
        if len(sql_data) != 1:
                abend("Duplicate module name {}".format(this.module_name))
        flds = {'found': 1}
        if (this.modification_time != sql_data[0].modification_time) \
                        or (this.path != sql_data[0].path):
            # the source has been changed or moved.
            # mark it for processing
            flds['path'] = file_info.path
            flds['modification_time'] = file_info.modification_time
            flds['status'] = xsource.SOURCE_STATUS_READY
        # mark source as found, possibly modified
        self.db.update('sources', flds,
                               where={'module_name': file_info.module_name})
        sql_data = self.db.delete('module_uses',
                                      where={'source_module_name':
                                             file_info.module_name})

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('site_path',
                            action='store',
                            nargs='*',
                            default=None,
                            help='Path of site root directory.')
    arg_parser.add_argument('-q',
                            action='store_true',
                            dest='quiet',
                            help='Display as few messages as possible.')
    arg_parser.add_argument('-r',
                            action='store_true',
                            dest='reset',
                            help='Reset (clear) EzDev process.')
    arg_parser.add_argument('-s',
                            action='store_true',
                            dest='stand_alone',
                            help='Stand-alone operation. No conf file.')
    run_args = arg_parser.parse_args()
    xp = XPython(run_args)
