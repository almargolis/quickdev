from . import virtfile
from . import filedriver

def test_swap(tmpdir):
    print(tmpdir)
    path = tmpdir.join("config.ini")
    swap = tmpdir.join("config.ini.swap")
    lock = tmpdir.join("config.ini.lock")
    f = virtfile.VirtFile(debug=3)
    assert f.open(file_name=path, mode=filedriver.MODE_S)
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
