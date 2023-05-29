from qdcore import virtfile
from qdcore import filedriver

def test_swap(tmpdir):
    print(tmpdir)
    path = tmpdir.join("config.ini")
    swap = tmpdir.join("config.ini.swap")
    lock = tmpdir.join("config.ini.lock")
    f = virtfile.VirtFile(debug=3)
    f.open(file_name=path, mode=filedriver.MODE_S)
    assert f.err_code == 0
    print(f.driver)
    print('f.path:', f.path)
    print('path:', path)
    assert f.path == path
    assert not path.check(exists=1)
    assert swap.check(exists=1)
    assert lock.check(exists=1)
    f.keep()
    assert path.check(exists=1)
    assert not swap.check(exists=1)
    assert not lock.check(exists=1)

test_file = []
test_file.append("Line One")
test_file.append("Line Two")
test_file.append("Line Three")

def test_low_level_read(tmpdir):
    test_buf_size = 10
    path = tmpdir.join("config.ini")
    test_file_content = '\n'.join(test_file)
    path.write(test_file_content)
    f = virtfile.VirtFile(debug=4)
    f.buf_size = test_buf_size
    mode = filedriver.MODE_R
    backup = False
    f.open(path, mode=mode, backup=backup)
    assert f.read_ahead_mode
    assert f.buf_ix == 0
    assert f.buf_len == test_buf_size
    test_start_ix = 0
    test_end_lim = test_buf_size
    assert f.buf == bytes(test_file_content[test_start_ix:test_end_lim], encoding='utf-8')
    f.read_block()
    assert f.buf_ix == 0
    assert f.buf_len == test_buf_size
    test_start_ix = test_end_lim
    test_end_lim = test_start_ix + test_buf_size
    assert f.buf == bytes(test_file_content[test_start_ix:test_end_lim], encoding='utf-8')
    f.close()

def test_read_lines_simple(tmpdir):
    test_buf_size = 10
    path = tmpdir.join("config.ini")
    path.write('\n'.join(test_file))
    f = virtfile.VirtFile(debug=4)
    f.buf_size = test_buf_size
    mode = filedriver.MODE_R
    backup = False
    f.open(path, mode=mode, backup=backup)
    for ix, this in enumerate(f.readlines()):
        assert test_file[ix]+'\n' == this
    f.close()
    f.open(path, mode=mode, backup=backup)
    f.strip_eol = True
    for ix, this in enumerate(f.readlines()):
        assert test_file[ix] == this
    f.close()
