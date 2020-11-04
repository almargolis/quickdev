import os

from ezcore import inifile


def test_read_ini_file(tmpdir):
    print(tmpdir)
    f = tmpdir.join("config.ini")
    f.write("""
[application]
user  =  foo
password = secret
""")

    """
    print(fh.basename)
    print(fh.dirname)
    filename = os.path.join( fh.dirname, fh.basename )

    config = configparser.ConfigParser()
    config.read(filename)

    assert config.sections() == ['application']
    assert config['application'], {
       "user" : "foo",
       "password" : "secret"
    }
    """

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
    source['sub1'] = sub1

    assert inifile.write_ini_file(source, path=test_path)

    result = inifile.read_ini_file(file_name=test_path)
    assert  source == result
