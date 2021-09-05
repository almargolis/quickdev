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

# These paths and the qdcore import exception logic below are
# required for when xpython is run before qdstart has
# has configured the python virtual environment.

THIS_MODULE_PATH = os.path.abspath(__file__)
XSYNTH_DIR = os.path.dirname(THIS_MODULE_PATH)
IGNORE_FILE_NAMES = ['.DS_Store']
IGNORE_FILE_EXTENSIONS = ['pyc']
IGNORE_DIRECTORY_NAMES = ['.git', '.pytest_cache', '__pycache__']
IGNORE_DIRECTORY_EXTENSIONS = ['venv']

"""
The first import from qdcore has exception processing in
case qdcore is not yet in the python package search path.
This is a bootstrap issue initializing an EZDev application
before the virtual environment has been fully configured.

The first few imports are for required capabilities but
they may have reduced capabiities due to the system not
being fully configured.
"""

BOOTSTRAP_MODE = False

import qdbase.qdsqlite as qdsqlite
"""
try:
    from qdcore import qdsqlite
except ModuleNotFoundError:
    qdsqlite = None
if qdsqlite is None:
    sys.path.append(EZCORE_PATH)
    from qdcore import qdsqlite
"""
import qdbase.cli as cli
import qdbase.exenv as exenv
from . import xsource

try:
    from qdcore import qdconst
    from qdcore import qdsite
    from qdcore import inifile
except (ModuleNotFoundError, SyntaxError):
    # May not be found because its an xpy that might not
    # have been gen'd.
    BOOTSTRAP_MODE = True
    qdconst = None
    qdsite = None
    inifile = None

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
    __slots__ = ('db', 'debug',
                    'synthesis_db_path', 'quiet',
                    'site',
                    'sources', 'source_dirs', 'source_files', 'no_site',
                    'verbose',
                    'xpy_files', 'xpy_files_changed')

    def __init__(self, site=None, db_location=None, db_reset=False,
                 scan_all_dirs=True, no_site=False,
                 synth_all=False,
                 sources=[], quiet=False, verbose=False, debug=0):
        self.debug = debug
        self.verbose = verbose
        if self.debug > 0:
            self.verbose = True
            print("XSynth.__init__[start](site={}, sources={}, no_site={}, quiet={}, debug={})".format(
                  site, sources, no_site, quiet, debug))
        self.no_site = no_site
        self.quiet = quiet
        #
        # Identify site, if any
        #
        if BOOTSTRAP_MODE or no_site:
            self.site = None
        else:
            self.site = qdsite.identify_site(site)
        #
        # Open synthesis database
        #
        site = exenv.execution_env.execution_site
        self.synthesis_db_path = None
        if db_location is not None:
            if os.path.isdir(db_location):
                db_location = os.path.join(db_location,
                                           xsource.XDB_DATABASE_FN)

            self.synthesis_db_path = os.path.abspath(db_location)
        elif no_site or (site is None):
            self.synthesis_db_path = qdsqlite.SQLITE_IN_MEMORY_FN
        else:
            self.synthesis_db_path = site.synthesis_db_path
        db_debug = self.debug
        db_debug = 0
        self.db = xsource.open_xdb(self.synthesis_db_path,
                                   db_reset=db_reset,
                                   debug=db_debug)
        #
        # Handle CLI directory / file list
        #
        # if self.no_site:
        if sources is None:
            self.sources = [os.getcwd()]
        else:
            self.sources = sources
        self.source_dirs = []
        self.source_files = []
        for this in self.sources:
            this_path = os.path.abspath(this)
            if os.path.isdir(this_path):
                self.source_dirs.append(this_path)
            else:
                self.source_files.append(this_path)
        if scan_all_dirs:
            self.prepare_db_to_scan_all_directories()
        if debug > 0:
            print("XSynth.__init__[end](site={}, dirs={}. sources={}, no_site={}, quiet={}, debug={})".format(
                  self.site, self.sources, self.no_site, self.source_dirs, self.quiet, self.debug))
        for this in self.source_files:
            xsource.post_files_table(self.db, xsource.FileInfo(this))
        for this in self.source_dirs:
            self.scan_directory(this,
                                recursive=True)
        self.update_db_after_scan()
        if synth_all:
            self.db.update(xsource.XDB_MODULES,
                           {'status': xsource.MODULE_STATUS_READY},
                            where={'module_type': xsource.MODULE_TYPE_SYNTH})
        self.process_xpy_files()

    def prepare_db_to_scan_all_directories(self):
        if self.debug > 0:
            print("XSynth.prepare_db_to_scan_all_directories()")
        self.db.update(xsource.XDB_MODULES,
                {
                'module_type': xsource.MODULE_TYPE_UNKNOWN,
                'status': xsource.MODULE_STATUS_READY,
                'source_found': 'N',
                'target_found': 'N'
                })
        self.db.update(xsource.XDB_FILES,
                {
                'found': 'N',
                })
        self.db.update(xsource.XDB_DIRS,
                {'found': 'N'})

    def update_db_after_scan(self):
        if self.debug > 0:
            print("XSynth.update_db_after_scan()")
        self.db.update(xsource.XDB_MODULES,
                {'module_type': xsource.MODULE_TYPE_SYNTH},
                where={'source_found': 'Y'})
        self.db.update(xsource.XDB_MODULES,
                {'module_type': xsource.MODULE_TYPE_NO_SYNTH},
                where={'source_found': 'N', 'target_found': 'Y'})
        self.db.update(xsource.XDB_MODULES,
                {'status': xsource.MODULE_STATUS_SYNTHESIZED},
                where={'module_type': 'MODULE_TYPE_SYNTH',
                'target_modification_time':
                ('>', qdsqlite.AttributeName('source_modification_time'))})

    def scan_directory(self, search_dir, recursive=False):
        """
        Scan a direcory tree and update the sources database.
        """
        if self.verbose:
            print("XSynth.scan_directory({}, recursive={}).".format(
                  search_dir, recursive
            ))
        dir_all = os.listdir(search_dir)
        dir_dir = []
        for this_file_name in dir_all:
            this_path = os.path.join(search_dir, this_file_name)
            if os.path.islink(this_path):
                continue
            file_info = xsource.FileInfo(this_path)
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
                xsource.post_files_table(self.db, file_info)
        if recursive:
            for this_subdir in dir_dir:
                self.scan_directory(this_subdir, recursive=True)

    def process_xpy_files(self):
        if self.debug > 0:
            print("XSynth.process_xpy_files()")
        while True:
            # We re-select for each source because XSource
            # may process multiple sources recursively.
            # The to-do list is not static.
            sql_data = self.db.select(xsource.XDB_MODULES, '*',
                                       where={'module_type': xsource.MODULE_TYPE_SYNTH,
                                              'status': xsource.MODULE_STATUS_READY
                                              },
                                       limit=1)
            if len(sql_data) < 1:
                break
            xsource.XSource(module_name=sql_data[0]['module_name'], db=self.db,
                            source_ext=sql_data[0]['source_ext'],
                            source_path=sql_data[0]['source_path'],
                            debug=self.debug
                            )


def synth_site(site=None, db_location=None, no_site=None, sources=None,
               quiet=False, verbose=False):
    XSynth(site=site, db_location=db_location, no_site=no_site, db_reset=True,
           sources=sources, synth_all=True, quiet=quiet, debug=1)
    print("Execution Complete")

def main():
    """
    XSynth can operate in either qddev or stand-alone mode.

    If -n is specified, xsynth operates in stand-alone mode, not looking for
    an qddev site configuration and using a temporary xsynth database.

    If -s is specified, xsynth processes that qddev site, regardless of the current
    working directory (cwd).

    If neither is specified, xsynth checks if the cwd seems to be an qddev site.
    If so, it processes that qddev site as if it were specified with -s.
    If not, it behaves as if -n was specified.

    If no file list is provided, xsynth processes either the entire site (-s mode)
    or the cwd and all subdirectories (-n mode).
    """
    menu = cli.CliCommandLine()
    exenv.command_line_site(menu)
    exenv.command_line_loc(menu)
    exenv.command_line_no_conf(menu)
    exenv.command_line_quiet(menu)
    exenv.command_line_verbose(menu)

    menu.add_item(cli.CliCommandLineParameterItem(cli.DEFAULT_FILE_LIST_CODE,
                  help="Specify files or directory to synthesise in stand-alone mode.",
                  value_type=cli.PARAMETER_STRING
                  ))

    m = menu.add_item(cli.CliCommandLineActionItem(cli.DEFAULT_ACTION_CODE,
                                                   synth_site,
                                                   help="Synthesize directory."))
    m.add_parameter(cli.CliCommandLineParameterItem('n', parameter_name='no_site',
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

if __name__ == '__main__':
    main()
