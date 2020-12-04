from ezcore import ezsqlite
from ezcore import xsource
from ezutils import xpython

def test_lex():
    lex = xsource.SimpleLex()
    lex.lex('class thing:')
    assert lex.tokens == ['class', 'thing', ':']

example_x = []
example_x.append('#$ action act1 exe')

expected_p = []
expected_p.append('class act1(exe):')
expected_p.append('    def __init__(self):')
expected_p.append('        super().__init__()')

def test_xpython_action(tmpdir):
    db_path = tmpdir.join("db.sql")
    db = ezsqlite.EzSqlite(db_path, db_dict=xpython.db_dict, debug=0)
    print(db_path)
    x = xsource.XSource('test', tmpdir, db, source_lines=example_x)
    print(x.output_file_path)
    with open(x.output_file_path) as outf:
        out_lines = outf.readlines()
    for ix, this_line in enumerate(out_lines):
        if this_line[-1] == '\n':
            this_line = this_line[:-1]
        if ix >= len(expected_p):
            expected_line = ''
        else:
            expected_line = expected_p[ix]
        print('** {} ** {} **'.format(this_line, expected_line))
        assert this_line == expected_line
    # Test lenght after comparison so we comparison print() for debugging
    assert len(expected_p) == len(out_lines)
