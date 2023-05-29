from qdcore import tupledict

def test_simple():
    td = tupledict.TupleDict()
    td.AddScalarElementNumber('First')
    td.AddScalarElement('Second')
