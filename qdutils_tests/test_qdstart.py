import os

from qdutils import qdstart

def test_check_directory(tmpdir):
    d_name = 'something'
    d_path = tmpdir.join(d_name)
    f = open(d_path, 'w')
    f.write('xxx')
    f.close()
    #assert not os.path.exists(d_path)
    assert qdstart.check_directory('Test Directory', d_path, force=True)
    assert os.path.exists(d_path)
