from qdcore import rdbms

def test_swap(tmpdir):
    path = tmpdir.join("test.db")
    rdb = rdbms.RdbmsSqLite(path=path)
