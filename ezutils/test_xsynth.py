import xsynth

test_xpy = []
test_xpy.append("class thing:")
test_xpy.append("    def inner():")
test_xpy.append("$__class_name__$")
test_xpy.append("$__def_name__$")

def test_xsynth(tmpdir):
    print(tmpdir)
    f = tmpdir.join("test.xpy")
    f.write("\n".join(test_xpy))

    x = xsynth.XSynth(sources=[f], stand_alone=True, debug=1)

    outf_name = tmpdir.join('test.py')
    with open(outf_name) as outf:
        out_lines = outf.readlines()

    assert out_lines[2] == 'thing\n'
    assert out_lines[3] == 'inner\n'
