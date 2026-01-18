#!python
"""
XSynth is a preprocessor for that adds data modeling and
structured programming features without interfering with the
fundamentals of the source language.

XSynth was developed for QuickDev but has both a stand-alone and
QuickDev mode. In stand-alone mode it has minimal QuickDev dependencies,
it just processes the files in a directory. This means that almost all
QuickDev modules but XSynth can use XSynth features.

"""

import os
import sys

# Bootstrap path setup for running before packages are installed
THIS_MODULE_PATH = os.path.abspath(__file__)
QDUTILS_PATH = os.path.dirname(THIS_MODULE_PATH)
QDDEV_PATH = os.path.dirname(QDUTILS_PATH)
QDBASE_SRC_PATH = os.path.join(QDDEV_PATH, "qdbase", "src")
QDCORE_SRC_PATH = os.path.join(QDDEV_PATH, "qdcore", "src")

try:
    from qdbase import qdsqlite
except ModuleNotFoundError:
    # Bootstrap mode: packages use src/ layout
    sys.path.insert(0, QDBASE_SRC_PATH)
    sys.path.insert(0, QDCORE_SRC_PATH)
    from qdbase import qdsqlite

from qdbase import cliargs
from qdbase import exenv
from qdbase import xsource

try:
    from qdcore import qdsite

    BOOTSTRAP_MODE = False
except (ModuleNotFoundError, SyntaxError):
    # May not be found because its an xpy that might not
    # have been gen'd.
    BOOTSTRAP_MODE = True
    qdsite = None  # pylint: disable=invalid-name

# These paths and the qdcore import exception logic below are
# required for when xpython is run before qdstart has
# has configured the python virtual environment.

THIS_MODULE_PATH = os.path.abspath(__file__)
XSYNTH_DIR = os.path.dirname(THIS_MODULE_PATH)
IGNORE_FILE_NAMES = [".DS_Store"]
IGNORE_FILE_EXTENSIONS = ["pyc"]
IGNORE_DIRECTORY_NAMES = [".git", ".pytest_cache", "__pycache__"]
IGNORE_DIRECTORY_EXTENSIONS = ["venv"]

"""
The first import from qdcore has exception processing in
case qdcore is not yet in the python package search path.
This is a bootstrap issue initializing an QuickDev application
before the virtual environment has been fully configured.

The first few imports are for required capabilities but
they may have reduced capabiities due to the system not
being fully configured.
"""


#
# Permutations of processing to consider:
# - Build new database where no synthesised code is in directories.
# - Build new database where some synthesised code is in directories.
# - Existing database where
# - - file moved between subdirectories
# - - file no longer exists (it has been deleted or renamed)
# - - a non-synthesised file has been changed to sysnthesized or vice-versa
#
class XSynth:  # pylint: disable=too-many-instance-attributes
    """Main XSynth implementation class."""

    __slots__ = (
        "db",
        "debug",
        "synthesis_db_path",
        "quiet",
        "site",
        "sources",
        "source_dirs",
        "source_files",
        "no_site",
        "verbose",
        "xpy_files",
        "xpy_files_changed",
    )

    def __init__(
        self,
        site=None,
        db_location=None,
        db_reset=False,
        scan_all_dirs=True,
        no_site=False,
        synth_all=False,
        sources=None,
        quiet=False,
        verbose=False,
        debug=0,
    ):  # pylint: disable=too-many-arguments, too-many-branches, too-many-statements
        # When I get a chance, break this into pieces to make pylint happy.
        # I'm note sure it will actually simplify things, but it can't hurt.
        self.debug = debug
        self.verbose = verbose
        if self.debug > 0:
            self.verbose = True
            print(
                f"XSynth.__init__[start](site={site},"
                f" sources={sources},"
                f" no_site={no_site},"
                f" quiet={quiet},"
                f" debug={debug})"
            )
        self.no_site = no_site
        self.quiet = quiet
        #
        # Identify site, if any
        #
        if BOOTSTRAP_MODE or no_site:
            self.site = None
        else:
            self.site = qdsite.identify_site(  # pylint: disable=assignment-from-none
                site
            )
        #
        # Open synthesis database
        #
        site = exenv.execution_env.execution_site
        self.synthesis_db_path = None
        if db_location is not None:
            if os.path.isdir(db_location):
                db_location = os.path.join(db_location, xsource.XDB_DATABASE_FN)

            self.synthesis_db_path = os.path.abspath(db_location)
        elif no_site or (site is None):
            self.synthesis_db_path = qdsqlite.SQLITE_IN_MEMORY_FN
        else:
            self.synthesis_db_path = site.synthesis_db_path
        if self.synthesis_db_path is None:
            self.synthesis_db_path = qdsqlite.SQLITE_IN_MEMORY_FN
        if debug > 0:
            msg = (
                "XSynth.__init__() [DB] db_location: '{}' self.synthesis_db_path: '{}'"
            )
            msg += " site.synthesis_db_path: '{}'"
            msg = msg.format(
                db_location, self.synthesis_db_path, site.synthesis_db_path
            )
            print(msg)
        db_debug = self.debug
        db_debug = 0
        self.db = xsource.open_xdb(
            self.synthesis_db_path, db_reset=db_reset, debug=db_debug
        )
        #
        # Build directory list from command line and conf
        #
        if self.site:
            self.sources = self.site.get_source_directories()
        else:
            self.sources = []
        if sources is not None:
            self.sources += sources
        if len(self.sources) < 1:
            self.sources = [os.getcwd()]
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
            print(
                f"XSynth.__init__[end](site={self.site},"
                f" dirs={self.source_dirs}."
                f" sources={self.sources},"
                f" no_site={self.no_site},"
                f" quiet={self.quiet},"
                f" debug={self.debug})"
            )
        for this in self.source_files:
            xsource.post_files_table(self.db, xsource.FileInfo(this))
        for this in self.source_dirs:
            self.scan_directory(this, recursive=True)
        self.update_db_after_scan()
        if synth_all:
            self.db.update(
                xsource.XDB_MODULES,
                {"status": xsource.MODULE_STATUS_READY},
                where={"module_type": xsource.MODULE_TYPE_SYNTH},
            )
        self.process_xpy_files()
        if self.site:
            self.sources = self.site.save_source_directories(self.source_dirs)

    def prepare_db_to_scan_all_directories(self):
        """
        Initialize database to prepare for full directory scan.
        """
        if self.debug > 0:
            print("XSynth.prepare_db_to_scan_all_directories()")
        self.db.update(
            xsource.XDB_MODULES,
            {
                "module_type": xsource.MODULE_TYPE_UNKNOWN,
                "status": xsource.MODULE_STATUS_READY,
                "source_found": "N",
                "target_found": "N",
            },
        )
        self.db.update(
            xsource.XDB_FILES,
            {
                "found": "N",
            },
        )
        self.db.update(xsource.XDB_DIRS, {"found": "N"})

    def update_db_after_scan(self):
        """
        Update database after scanning directories.
        """
        if self.debug > 0:
            print("XSynth.update_db_after_scan()")
        self.db.update(
            xsource.XDB_MODULES,
            {"module_type": xsource.MODULE_TYPE_SYNTH},
            where={"source_found": "Y"},
        )
        self.db.update(
            xsource.XDB_MODULES,
            {"module_type": xsource.MODULE_TYPE_NO_SYNTH},
            where={"source_found": "N", "target_found": "Y"},
        )
        self.db.update(
            xsource.XDB_MODULES,
            {"status": xsource.MODULE_STATUS_SYNTHESIZED},
            where={
                "module_type": "MODULE_TYPE_SYNTH",
                "target_modification_time": (
                    ">",
                    qdsqlite.AttributeName("source_modification_time"),
                ),
            },
        )

    def scan_directory(self, search_dir, recursive=False):
        """
        Scan a direcory tree and update the sources database.
        The scanner follows subdirectories but not links.
        """
        if self.verbose:
            print(f"XSynth.scan_directory({search_dir}, recursive={search_dir}).")
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
        """
        Process all the *.x* source files that we found.
        """
        if self.debug > 0:
            print("XSynth.process_xpy_files()")
        while True:
            # We re-select for each source because XSource
            # may process multiple sources recursively.
            # The to-do list is not static.
            sql_data = self.db.select(
                xsource.XDB_MODULES,
                "*",
                where={
                    "module_type": xsource.MODULE_TYPE_SYNTH,
                    "status": xsource.MODULE_STATUS_READY,
                },
                limit=1,
            )
            if len(sql_data) < 1:
                break
            xsource.XSource(
                module_name=sql_data[0]["module_name"],
                db=self.db,
                source_ext=sql_data[0]["source_ext"],
                source_path=sql_data[0]["source_path"],
                debug=self.debug,
            )


def synth_site(
    site=None,
    db_location=None,
    no_site=None,
    sources=None,
    quiet=False,
    verbose=False,
    debug=0,
):  # pylint: disable=too-many-arguments
    """
    Action function to synthesise a site.
    """
    XSynth(
        site=site,
        db_location=db_location,
        no_site=no_site,
        db_reset=True,
        sources=sources,
        synth_all=True,
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )
    print(exenv.execution_env.execution_site)
    print("Execution Complete")


def main(debug=0):
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
    menu = cliargs.CliCommandLine()
    exenv.command_line_debug(menu)
    exenv.command_line_site(menu)
    exenv.command_line_loc(menu)
    exenv.command_line_no_conf(menu)
    exenv.command_line_quiet(menu)
    exenv.command_line_verbose(menu)

    menu.add_item(
        cliargs.CliCommandLineParameterItem(
            cliargs.DEFAULT_FILE_LIST_CODE,
            help_description="Specify files or directory to synthesise in stand-alone mode.",
            value_type=cliargs.PARAMETER_STRING,
        )
    )

    action_item = menu.add_item(
        cliargs.CliCommandLineActionItem(
            cliargs.DEFAULT_ACTION_CODE,
            synth_site,
            help_description="Synthesize directory.",
        )
    )
    action_item.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "n", parameter_name="no_site", default_value=False, is_positional=False
        )
    )
    action_item.add_parameter(
        cliargs.CliCommandLineParameterItem(
            exenv.ARG_D_DEBUG,
            parameter_name="debug",
            default_value=debug,
            is_positional=False,
        )
    )
    action_item.add_parameter(
        cliargs.CliCommandLineParameterItem(
            "q", parameter_name="quiet", is_positional=False
        )
    )
    action_item.add_parameter(
        cliargs.CliCommandLineParameterItem(
            cliargs.DEFAULT_FILE_LIST_CODE,
            parameter_name="sources",
            default_value=None,
            is_positional=False,
        )
    )

    exenv.execution_env.set_run_name(__name__)
    menu.cli_run()


if __name__ == "__main__":
    main()
