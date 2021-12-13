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
        etc = self.root.mkdir('etc')
        apache = etc.mkdir('apache2')
        apache.mkdir('sites-available')
        private = self.root.mkdir('private')
        private_etc = private.mkdir('etc')
        private_apache = private_etc.mkdir('apache2')
        private_apache.mkdir('sites-available')
        var = self.root.mkdir('var')
        var.mkdir('www')
        exenv.g.init(self.root)
        try:
            hosting.init_hosting(force=True)
        except SystemExit as e:
            # SystemExit is a pytest exception
            if e.code != 0:
                raise

def test_init(tmpdir):
    q = MakeQdev(tmpdir)
