import xpython

class XPythonArgs:
    quiet = False
    stand_alone = True
    site_path = []

def test_xpython(tmpdir):
    print(tmpdir)
    args = XPythonArgs()
    setattr(args, 'site_path', [tmpdir])
    f = tmpdir.join("test.xpy")
    f.write("""class thing:
        def inner():
$__class_name__$
$__def_name__$
""")

    x = xpython.XPython(args, debug=1)

    outf_name = tmpdir.join('test.py')
    with open(outf_name) as outf:
        out_lines = outf.readlines()

    assert out_lines[2] == 'thing\n'
    assert out_lines[3] == 'inner\n'
