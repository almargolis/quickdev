from qdbase import exenv

from qdutils import hosting

class MakeQdev:
    """
    This makes a safe test environment for QuickDev utility
    testing so they don't write to the actual system
    directories.

    exenv.ExenvGlobals is designed for this, so most things
    don't have to be particularly test-aware in order to
    run in this artificail environment.
    """
    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        self.root = tmpdir.mkdir('root')
        self.root.mkdir('etc')
        exenv.g.init(self.root)
        try:
            hosting.init_hosting(force=True)
        except SystemExit as e:
            # SystemExit is a pytest exception
            if e.code != 0:
                raise

def test_init(tmpdir):
    q = MakeQdev(tmpdir)
