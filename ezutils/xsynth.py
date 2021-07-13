#!python
"""
XSynth is a preprocessor for that adds data modeling and
structured programming features without interfering with the
fundamentals of the source language.

XSynth was developed for EzDev but has both a stand-alone and
EzDev mode. In stand-alone mode it has minimal EzDev dependencies,
it just processes the files in a directory. This means that almost all
EzDev modules but XSynth can use XSynth features.

"""

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

"""
The first import from ezcore has exception processing in
case ezcore is not yet in the python package search path.
This is a bootstrap issue initializing an EZDev application
before the virtual environment has been fully configured.
"""

xsynth_target_ext = ['js', 'py']
xsynth_source_ext = ['x'+x for x in xsynth_target_ext]

import ezstart

try:
    from ezcore import ezsqlite
except ModuleNotFoundError:
    ezsqlite = None
if ezsqlite is None:
    sys.path.append(EZCORE_PATH)
    from ezcore import ezsqlite

from ezcore import cli
from ezcore import xsource
from ezcore import exenv

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

def abend(msg):
    """Report critical error and exit xpython (abnormal end). """
    print(msg)
    print("Unable to continue")
    sys.exit(-1)

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
        if self.file_ext.startswith('.'):
            self.file_ext = self.file_ext[1:]
        self.modification_time = stats_obj[stat.ST_MTIME]

    def new_path(self, ext):
        """
        Provide the path for a derivative file named by changing
        the extension.

        ext should not include a leading period. e.g.: "py"
        """
        return os.path.join(self.dir_name, self.module_name + '.' + ext)

class XSynth:
    """ Main XSynth implementation class."""
    __slots__ = ('base_dir', 'db', 'debug',
                 'conf_info',
                 'conf_dir_path',
                    'project_db_path', 'quiet',
                    'source_dirs', 'stand_alone',
                    'xpy_files', 'xpy_files_changed')

    def __init__(self, quiet=False, sources=[], stand_alone=False, debug=0):
        self.conf_info = None
        self.conf_dir_path = None
        self.debug = debug
        self.quiet = quiet
        self.stand_alone = stand_alone
        if self.stand_alone:
            self.base_dir = None
            self.source_dirs = sources
            self.project_db_path = ezsqlite.SQLITE_IN_MEMORY_FN
        else:
            if len(args.site_path) < 1:
                self.base_dir = os.getcwd()
            else:
                self.base_dir = args.site_path[0]
            if not self.init_ezdev(args):
                return
        self.db = ezsqlite.EzSqlite(self.project_db_path,
                                     db_dict=xsource.xdb_dict, debug=0)
        self.process_xpy_files()

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
        if args.reset:
            try:
                os.unlink(self.project_db_path)
            except FileNotFoundError:
                pass
        if not self.load_conf():
            print('XSynth source files not processed.')
            return False
        return True

    def load_conf(self):
        self.conf_info = inifile.read_ini_directory(dir=self.conf_dir_path,
                                                    ext=ezconst.CONF_EXT)
        if self.conf_info is None:
            return False
        self.source_dirs = self.conf_info['site.source_dirs']
        return True

    def scan_directory(self, search_dir, source_exts, target_exts, recursive=False):
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
                ext = parts[1]
                if ext.startswith('.'):
                    ext = ext[1:]
                if ext in source_exts:
                    self.post_sources_table(this_path, is_source=True)
                elif ext == target_exts:
                    self.post_sources_table(this_path, is_source=False)
        if recursive:
            for this_subdir in dir_dir:
                self.scan_directory(this_subdir, source_ext, output_ext, recursive=True)

    def process_xpy_files(self):
        """
        Scan directories to locate source files. Update the
        sources table and then process them.
        """
        self.db.update(xsource.XDB_MODULES,
                       {'source_path': '',
                        'source_ext': '',
                        'output_path': '',
                        'output_ext': '',
                        'is_xsource': 'N',
                        'is_translated': 'N'})
        self.db.update(xsource.XDB_SOURCES, {'found': 0})
        for this_directory in self.source_dirs:
            self.scan_directory(this_directory,
                                xsynth_source_ext, xsynth_target_ext,
                                recursive=True)
        self.db.update(xsource.XDB_MODULES, {'is_xsource': 'Y'},
                       where={'source_path': ('', '!=')})

        while True:
            # We re-select for each source because XSource
            # may process multiple sources recursively.
            # The to-do list is not static.
            sql_data = self.db.select(xsource.XDB_SOURCES, '*',
                                       where={'status': xsource.SOURCE_STATUS_READY},
                                       limit=1)
            if len(sql_data) < 1:
                break
            xsource.XSource(module_name=sql_data[0]['module_name'],
                            src_ext='xpy', dest_ext='py',
                            dir_path=os.path.dirname(sql_data[0]['path']), db=self.db)

    def post_sources_table(self, path, is_source):
        "Updates the modules and sources tables for a file."
        file_info = FileInfo(path)
        if file_info.module_name in RESERVED_MODULE_NAMES:
            abend("Reserved module name {}".format(file_info.module_name))
        sql_data = self.db.select(xsource.XDB_SOURCES, '*',
                                      where={'module_name':
                                             file_info.module_name})
        if len(sql_data) < 1:
            self.db.insert(xsource.XDB_SOURCES, {
                            'module_name': file_info.module_name,
                            'ext': file_info.file_ext,
                            'path': file_info.path,
                            'status': xsource.SOURCE_STATUS_READY,
                            'found': 1,
                            'modification_time': file_info.modification_time
                            })
            return
        if len(sql_data) != 1:
                abend("Duplicate module name {}".format(this.module_name))
        flds = {'found': 1}
        print(ezsqlite.row_repr(sql_data[0]))
        if (file_info.modification_time != sql_data[0]['modification_time']) \
                        or (file_info.path != sql_data[0]['path']):
            # the source has been changed or moved.
            # mark it for processing
            flds['path'] = file_info.path
            flds['modification_time'] = file_info.modification_time
            flds['status'] = xsource.SOURCE_STATUS_READY
        # mark source as found, possibly modified
        self.db.update(xsource.XDB_SOURCES, flds,
                               where={'module_name': file_info.module_name})
        sql_data = self.db.delete(xsource.XDB_MODULE_USES,
                                      where={'source_module_name':
                                             file_info.module_name})

if __name__ == '__main__':

    menu = cli.CliCommandLine()
    exenv.command_line_quiet(menu)
    exenv.command_line_site(menu)
    exenv.command_line_no_conf(menu)
    menu.add_item(cli.CliCommandLineParameterItem(cli.DEFAULT_FILE_LIST_CODE,
                  help="Specify files or directory to synthesise in stand-alone mode.",
                  value_type=cli.PARAMETER_STRING
                  ))

    m = menu.add_item(cli.CliCommandLineActionItem(cli.DEFAULT_ACTION_CODE,
                                                   init_site,
                                                   help="Synthesize directory."))
    m.add_parameter(cli.CliCommandLineParameterItem('q', parameter_name='quiet',
                                                    is_positional=False))
    m.add_parameter(cli.CliCommandLineParameterItem('s', parameter_name='site',
                                                    is_positional=False))
    m.add_parameter(cli.CliCommandLineParameterItem(cli.DEFAULT_FILE_LIST_CODE,
                                                    parameter_name='sources',
                                                    is_positional=False))


    exenv.execution_env.set_run_name(__name__)
    menu.cli_run()
