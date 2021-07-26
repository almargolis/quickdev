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
XSYNTH_TARGET_EXT = ['js', 'py']
XSYNTH_SOURCE_EXT = ['x'+x for x in XSYNTH_TARGET_EXT]
IGNORE_FILE_NAMES = ['.DS_Store']
IGNORE_FILE_EXTENSIONS = ['pyc']
IGNORE_DIRECTORY_NAMES = ['.git', '.pytest_cache']
IGNORE_DIRECTORY_EXTENSIONS = ['venv']

"""
The first import from ezcore has exception processing in
case ezcore is not yet in the python package search path.
This is a bootstrap issue initializing an EZDev application
before the virtual environment has been fully configured.
"""


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
        if ext in ['', None]:
            fn = self.module_name
        else:
            fn = self.module_name + '.' + ext
        return os.path.join(self.dir_name, fn)

#
# Permutations of processing to consider:
# - Build new database where no synthesised code is in directories.
# - Build new database where some synthesised code is in directories.
# - Existing database where
# - - file moved between subdirectories
# - - file no longer exists (it has been deleted or renamed)
# - - a non-synthesised file has been changed to sysnthesized or vice-versa
#
class XSynth:
    """ Main XSynth implementation class."""
    __slots__ = ('base_dir', 'db', 'debug',
                 'conf_info',
                 'conf_dir_path',
                    'project_db_path', 'quiet',
                    'site', 'sources', 'stand_alone',
                    'xpy_files', 'xpy_files_changed')

    def __init__(self, site=None, db_location=None, stand_alone=False,
                 reset_db=False, sources=[], quiet=False, debug=0):
        if debug > 0:
            print("XSynth(site={}, sources={}, stand_alone={}, quiet={}, debug={})".format(
                  site, sources, stand_alone, quiet, debug))
        self.conf_info = None
        self.conf_dir_path = None
        self.debug = debug
        self.quiet = quiet
        if (ezconst is None) or (inifile is None):
            # EzDev is not configured, can't be a site.
            site = None
        else:
            if (site is None) and (db_location is None) and (not stand_alone):
                # no operating mode specified, guess
                site = ezsite.identify_cwd_site()
        self.site = site
        #if site is None
        self.stand_alone = stand_alone
        if self.stand_alone:
            self.base_dir = None
            if sources is None:
                self.sources = [os.getcwd()]
            else:
                self.sources = sources
            self.project_db_path = ezsqlite.SQLITE_IN_MEMORY_FN
        else:
            if (sources is None) or (len(sources) < 1):
                self.base_dir = os.getcwd()
            else:
                self.base_dir = args.site_path[0]
            if not self.init_ezdev(args):
                return
        if debug > 0:
            print("XSynth(site={}, sources={}, stand_alone={}, quiet={}, debug={})".format(
                  self.site, self.sources, self.stand_alone, self.quiet, self.debug))

        self.db = ezsqlite.EzSqlite(self.project_db_path,
                                     db_dict=xsource.xdb_dict,
                                     detailed_exceptions=True, debug=0)
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
        self.sources = self.conf_info['site.sources']
        return True

    def scan_all_directories(self):
        self.db.update(xsource.XDB_MODULES,
                {
                'module_type': xsource.MODULE_TYPE_UNKNOWN,
                'is_synthesised': 'N',
                'source_found': 'N',
                'target_found': 'N'
                })
        self.db.update(xsource.XDB_FILES,
                {'found': 'N'})
        ### >>> scan directories
        self.db.update(xsource.XDB_MODULES,
                {'module_type': xsource.MODULE_TYPE_SYNTH},
                where={'source_found': 'Y'})
        self.db.update(xsource.XDB_MODULES,
                {'module_type': xsource.MODULE_TYPE_NO_SYNTH},
                where={'source_found': 'N', 'target_found': 'Y'})
        self.db.update(xsource.XDB_MODULES,
                {'is_synthesised': 'Y'},
                where={'module_type': 'MODULE_TYPE_SYNTH',
                'target_modification_time':
                ('>', ezsqlite.AttributeName('source_modification_time'))})

    def scan_directory(self, search_dir, recursive=False):
        """
        Scan a direcory tree and update the sources database.
        """
        if self.debug > 0:
            print("XSynth.scan_directory({}, recursive={}).".format(
                  search_dir, recursive
            ))
        dir_all = os.listdir(search_dir)
        dir_dir = []
        for this_file_name in dir_all:
            this_path = os.path.join(search_dir, this_file_name)
            if os.path.islink(this_path):
                continue
            file_info = FileInfo(this_path)
            if os.path.isdir(this_path):
                if this_file_name in IGNORE_DIRECTORY_NAMES:
                    continue
                if file_info.file_ext in IGNORE_DIRECTORY_EXTENSIONS:
                    continue
                dir_dir.append(this_path)
            else:
                if this_file_name in IGNORE_FILE_NAMES:
                    continue
                if file_info.file_ext in IGNORE_FILE_EXTENSIONS:
                    continue
                self.post_files_table(file_info)
        if recursive:
            for this_subdir in dir_dir:
                self.scan_directory(this_subdir, recursive=True)

    def process_xpy_files(self):
        """
        Scan directories to locate source files. Update the
        sources table and then process them.
        """
        for this in self.sources:
            if os.path.isfile(this):
                self.post_files_table(this)
            else:
                self.scan_directory(this,
                                recursive=True)

        while True:
            # We re-select for each source because XSource
            # may process multiple sources recursively.
            # The to-do list is not static.
            sql_data = self.db.select(xsource.XDB_MODULES, '*',
                                       where={'source_path': ('!=', ''),
                                       'source_modification_time': ('<',
                                       ezsqlite.AttributeName('target_modification_time'))},
                                       limit=1)
            if len(sql_data) < 1:
                break
            xsource.XSource(module_name=sql_data[0]['module_name'],
                            source_ext=sql_data[0]['source_ext'], target_ext='py',
                            dir_path=os.path.dirname(sql_data[0]['source_path']), db=self.db)

    def post_module_table(self, file_info, file_mode):
        if file_mode == xsource.FILE_MODE_SOURCE:
            uflds = {}
            uflds['source_path'] = file_info.path
            uflds['source_ext'] = file_info.file_ext
            uflds['source_modification_time'] = file_info.modification_time
            uflds['source_found'] = 'Y'
        else:
            uflds = {}
            uflds['target_path'] = file_info.path
            uflds['target_ext'] = file_info.file_ext
            uflds['target_modification_time'] = file_info.modification_time
            uflds['target_found'] = 'Y'
        self.db.update_insert(xsource.XDB_MODULES, uflds,
                              where={'module_name': file_info.module_name})

    def post_files_table(self, file_info):
        "Updates the modules and files tables for a file."
        if self.stand_alone:
            sql_data = []
        else:
            sql_data = self.db.select(xsource.XDB_FILES, where={'path', file_info.path})
            if len(sql_data) > 0:
                if sql_data[0]['modification_time'] == file_info.modification_time:
                    # Don't bother with unchanged file
                    return
        if file_info.file_ext in XSYNTH_SOURCE_EXT:
            file_mode = xsource.FILE_MODE_SOURCE
            if file_info.module_name in RESERVED_MODULE_NAMES:
                abend("Reserved module name {}".format(file_info.module_name))
            is_module = True
        elif file_info.file_ext == XSYNTH_TARGET_EXT:
            file_mode = xsource.FILE_MODE_TARGET
            is_module = True
        else:
            file_mode = xsource.FILE_MODE_OTHER
            is_module = False
        self.post_module_table(file_info, file_mode)
        self.db.update_insert(xsource.XDB_FILES, {
                            'module_name': file_info.module_name,
                            'ext': file_info.file_ext,
                            'path': file_info.path,
                            'mode': file_mode,
                            'modification_time': file_info.modification_time,
                            'found': 'Y'
                            },
                            {'path': file_info.path})
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
            flds['status'] = xsource.FILE_STATUS_READY
        # mark source as found, possibly modified
        self.db.update(xsource.XDB_FILES, flds,
                               where={'module_name': file_info.module_name})
        sql_data = self.db.delete(xsource.XDB_MODULE_USES,
                                      where={'source_module_name':
                                             file_info.module_name})

def synth_site(site=None, db_location=None, stand_alone=None, sources=None, quiet=False):
    XSynth(site=site, db_location=db_location, stand_alone=stand_alone,
           sources=sources, quiet=quiet, debug=0)


if __name__ == '__main__':
    """
    XSynth can operate in either ezdev or stand-alone mode.

    If -n is specified, xsynth operates in stand-alone mode, not looking for
    an ezdev site configuration and using a temporary xsynth database.

    If -s is specified, xsynth processes that ezdev site, regardless of the current
    working directory (cwd).

    If neither is specified, xsynth checks if the cwd seems to be an ezdev site.
    If so, it processes that ezdev site as if it were specified with -s.
    If not, it behaves as if -n was specified.

    If no file list is provided, xsynth processes either the entire site (-s mode)
    or the cwd and all subdirectories (-n mode).
    """
    menu = cli.CliCommandLine()
    exenv.command_line_site(menu)
    exenv.command_line_loc(menu)
    exenv.command_line_no_conf(menu)
    exenv.command_line_quiet(menu)
    menu.add_item(cli.CliCommandLineParameterItem(cli.DEFAULT_FILE_LIST_CODE,
                  help="Specify files or directory to synthesise in stand-alone mode.",
                  value_type=cli.PARAMETER_STRING
                  ))

    m = menu.add_item(cli.CliCommandLineActionItem(cli.DEFAULT_ACTION_CODE,
                                                   synth_site,
                                                   help="Synthesize directory."))
    m.add_parameter(cli.CliCommandLineParameterItem('n', parameter_name='stand_alone',
                                                    default_value=False,
                                                    is_positional=False))
    m.add_parameter(cli.CliCommandLineParameterItem('l', parameter_name='db_location',
                                                    default_value=None,
                                                    is_positional=False))
    m.add_parameter(cli.CliCommandLineParameterItem('q', parameter_name='quiet',
                                                    is_positional=False))
    m.add_parameter(cli.CliCommandLineParameterItem(cli.DEFAULT_FILE_LIST_CODE,
                                                    parameter_name='sources',
                                                    default_value=None,
                                                    is_positional=False))


    exenv.execution_env.set_run_name(__name__)
    menu.cli_run()
