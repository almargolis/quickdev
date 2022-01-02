"""
test exenv.py
"""

import os

from qdbase import exenv


def test_safe_join():
    """Test safe_join()"""
    assert exenv.safe_join("/", "/etc") == "/etc"
    assert exenv.safe_join("/", "etc") == "/etc"


def test_make_directory(tmpdir):
    """Test make_directory()"""
    d_name = "something"
    d_path = tmpdir.join(d_name)
    with open(d_path, "w", encoding="utf-8") as f:
        f.write("xxx")
    # assert not os.path.exists(d_path)
    assert not exenv.make_directory("Test Directory", d_path, force=True)
    assert exenv.return_code == 101
    assert os.path.exists(d_path)


def print_msg(msg):
    """Print message for error analysis."""
    print(msg)


def test_symlink_file(tmpdir):
    """
    Target is the original file we are pointing to.
    Link is the symlink we are creating.
    """
    content = "some content"
    target_file_name = "t"
    bad_target_file_name = "bad"
    link_file_name = "L"
    target_file_path = tmpdir.join(target_file_name)
    link_file_path = tmpdir.join(link_file_name)
    with open(target_file_path, "w", encoding="utf-8") as f_targ:
        f_targ.write(content)
    assert not exenv.make_symlink_to_file(
        tmpdir, bad_target_file_name, tmpdir, link_file_name, error_func=print_msg
    )
    assert exenv.make_symlink_to_file(
        tmpdir, target_file_name, tmpdir, link_file_name, error_func=print_msg
    )
    with open(link_file_path, encoding="utf-8") as f_link:
        read_content = f_link.read()
    assert read_content == content
