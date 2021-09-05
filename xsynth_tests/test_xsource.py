import qdbase.qdsqlite as qdsqlite
import xsynth.xsource as xsource

ex1_src = []
ex1_src.append("#$ dict sample")
ex1_src.append("#$ element fld1 ptype=int")
ex1_src.append("#$ element fld2 ptype=str")
ex1_src.append("#$ end dict")
ex1_src.append("sql_stmt = 'insert into crud ($qdict.sample.as_comma_list$)")
ex1_src.append("values ($qdict.sample.as_subst_list$);'")
ex1_src.append("sql_parm = ($qdict.sample.as_dict_extract_list('args')$)")

ex1_out = []
ex1_out.append("sql_stmt = 'insert into crud (fld1, fld2)")
ex1_out.append("values (%s, %s);'")
ex1_out.append("sql_parm = (int(args['fld1']), args['fld2'])")

ex2_src = []
ex2_src.append('#$ action act1 exe')

ex2_out = []
ex2_out.append('class act1(exe):')
ex2_out.append('    def __init__(self):')
ex2_out.append('        super().__init__()')

def test_dict(tmpdir):
    """
    Test dictionary and for loop capability to produce flask database
    statements.

    These are python sample statements to insert records using
    flaskext.mysql:

        sql_stmt = 'insert into crud (fld1, fld2) values (%s, %s);'
        sql_parm = (int(args['fld1']), args['fld2'])

    These are jinja2 statements in a template. The fields would
    have to correspond to the database logic in the python code.

        <form method="POST" action="/inv_submit">
            {{ form.csrf_token }}
            {{ form.name.label }} {{ form.name(size=20) }}
            <input type="submit" value="Go">
        </form>
    """
    run_and_test(tmpdir, ex1_src, ex1_out)

def test_xsource_action(tmpdir):
    """ Test xsource action declaration. """
    run_and_test(tmpdir, ex2_src, ex2_out)

def run_and_test(tmpdir, test_src, expected_out):
    db_path = tmpdir.join("db.sql")
    db = qdsqlite.QdSqlite(db_path, db_dict=xsource.xdb_dict, debug=0)
    assert db is not None
    print(db_path)
    x = xsource.XSource('test', db=db,
                        source_ext='.xpy',
                        source_lines=test_src,
                        target_dir=tmpdir
                        )
    print(x.target_path)
    assert x.err_ct == 0
    with open(x.target_path) as outf:
        out_lines = outf.readlines()
    for ix, this_line in enumerate(out_lines):
        if this_line[-1] == '\n':
            this_line = this_line[:-1]
        if ix >= len(expected_out):
            expected_line = ''
        else:
            expected_line = expected_out[ix]
        print('** {} ** {} **'.format(this_line, expected_line))
        assert this_line == expected_line
    # Test length after comparison so we show comparison print() for debugging
    assert len(expected_out) == len(out_lines)
