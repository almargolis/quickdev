"""
test xsynth.py
"""

import os
import stat

from qdbase import qdsqlite
from qdbase import xsource
from qdutils import xsynth

test_xpy = []
test_xpy.append("class thing:")
test_xpy.append("    def inner():")
test_xpy.append("$__class_name__$")
test_xpy.append("$__def_name__$")

test_py = []
test_py.append("class thing:")
test_py.append("    def inner():")
test_py.append("error_c")
test_py.append("error_m")


def print_db_table(db, table_name):
    """Print the contents of a database table for error analysis."""
    data = db.select(table_name)
    print(f"<<< {len(data)} {table_name} processed.")
    for ix, this in enumerate(data):
        print(f"{ix} >>> {qdsqlite.row_repr(this)}")


def set_file_time(older, newer, interval=5):
    """Set file timestamp."""
    older_stats_obj = os.stat(older)
    older_modification_time = older_stats_obj[stat.ST_MTIME]
    new_time = older_modification_time + interval
    os.utime(newer, times=(new_time, new_time))


def test_xsynth(tmpdir):
    """Test XSynth process."""
    print(tmpdir)
    xlib = tmpdir.mkdir("xlib")
    f1x = xlib.join("test1.xpy")
    f1x.write("\n".join(test_py))
    f1p = xlib.join("test1.py")
    f1p.write("\n".join(test_py))
    set_file_time(f1x, f1p)  # shouldn't be synthesized
    f2x = xlib.join("test2.xpy")
    f2x.write("\n".join(test_xpy))
    f2p = xlib.join("test2.py")
    f2p.write("\n".join(test_py))
    set_file_time(f2p, f2x)  # should be synthesized

    x = xsynth.XSynth(sources=[xlib], no_site=True, debug=1)
    print_db_table(x.db, xsource.XDB_MODULES)
    print_db_table(x.db, xsource.XDB_FILES)
    print("Directory:", os.listdir(tmpdir))

    targetf1_name = xlib.join("test1.py")
    with open(targetf1_name, encoding="utf-8") as targetf:
        target1_lines = targetf.readlines()
    assert target1_lines[2] == "error_c\n"
    assert target1_lines[3] == "error_m\n"

    targetf2_name = xlib.join("test2.py")
    with open(targetf2_name, encoding="utf-8") as targetf:
        target2_lines = targetf.readlines()
    assert target2_lines[2] == "thing\n"
    assert target2_lines[3] == "inner\n"


def test_main():
    """This makes sure XSynth() initializes, which was failing."""
    xsynth.main(debug=1)
