from ezcore import ezsqlite
from ezcore import xsource
from ezutils import xpython

class data_xpython_action:
    """ Data for test_xpython_action """
    __slots__ = ('example_x', 'expected_p')
    def __init__(self):
        self.example_x = []
        self.example_x.append('#$ action act1 exe')

        self.expected_p = []
        self.expected_p.append('class act1(exe):')
        self.expected_p.append('    def __init__(self):')
        self.expected_p.append('        super().__init__()')

def test_xpython_action(tmpdir):
    """ Test xpython action declaration. """
    test_data = data_xpython_action()
    db_path = tmpdir.join("db.sql")
    db = ezsqlite.EzSqlite(db_path, db_dict=xpython.db_dict, debug=0)
    print(db_path)
    x = xsource.XSource('test', tmpdir, db, source_lines=test_data.example_x)
    print(x.output_file_path)
    with open(x.output_file_path) as outf:
        out_lines = outf.readlines()
    for ix, this_line in enumerate(out_lines):
        if this_line[-1] == '\n':
            this_line = this_line[:-1]
        if ix >= len(test_data.expected_p):
            expected_line = ''
        else:
            expected_line = test_data.expected_p[ix]
        print('** {} ** {} **'.format(this_line, expected_line))
        assert this_line == expected_line
    # Test lenght after comparison so we comparison print() for debugging
    assert len(test_data.expected_p) == len(out_lines)
