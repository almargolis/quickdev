import os

from ezcore import inifile

def test_write_ini_file(tmpdir):
    f = tmpdir.join("config.ini")
    test_path = os.path.join( f.dirname, f.basename )
    print("write_ini_file", test_path)

    source = {}
    source['base1'] = 'abc'
    source['base2'] = 32
    sub1 = {}
    sub1['child1'] = 'def'
    sub1['child2'] = 45
    sub1['list'] = ['a', 'b', 'c']
    source['sub1'] = sub1

    assert inifile.write_ini_file(source, path=test_path)

    with open(test_path) as outf:
        out_lines = outf.readlines()
    print('** INI FILE START **')
    print(out_lines)
    print('** INI FILE END **')

    result = inifile.read_ini_file(file_name=test_path)
    assert  source == result

root_ini_content = """root1 = a
root2 = b
root3 = c
[Sub1]
child1 = aa
child2 = bb
"""
db1_ini_content = """db1_1 = a
db1_2 = b
db1_3 = c
"""

def test_read_ini_directory(tmpdir):
    print(tmpdir)
    db_dir = tmpdir.mkdir('db')
    root_ini_file = tmpdir.join("site.ini")
    root_ini_file.write(root_ini_content)
    db1_ini_file = db_dir.join('db1.ini')
    db1_ini_file.write(db1_ini_content)
    ini_tree = inifile.read_ini_directory(tmpdir, ext='ini', debug=1)
    print(ini_tree)

    # check indexing using hierarchy notation
    assert ini_tree['site.root1']  == 'a'
    assert ini_tree['db.db1.db1_2'] == 'b'

    # check access using single-level index
    db_container = ini_tree['db']
    db1_container = db_container['db1']
    assert db1_container['db1_3'] == 'c'

    # check path attributes
    assert ini_tree._is_directory is True
    assert ini_tree._source_file_path == tmpdir
    print("Sub1", ini_tree['site.Sub1']._is_directory,
          ini_tree['site.Sub1']._source_file_path)
    assert ini_tree['site.Sub1']._is_directory is False
    assert ini_tree['site.Sub1']._source_file_path == ''
