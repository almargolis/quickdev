from qdcore import qddict

def test_basic():
    ez = qddict.QdDict()
    ez['z'] = 1
    ez['Z'] = 2
    assert ez['z'] == 2

def test_equivalence_to_dict():
    ez = qddict.QdDict()
    ez['A'] = 100
    ez2 = qddict.QdDict()
    ez2['a'] = 1
    ez2['b'] = 2
    ez['sub1'] = ez2
    ez['sub1.c'] = 3

    d = {}
    d2 = {}
    d2['a'] = 1
    d2['b'] = 2
    d2['c'] = 3
    d['A'] = 100
    d['sub1'] = d2

    assert d == ez

    # keys(), values() and items() return views which are not directly comparable.
    # So we use this long form approach.

    dk = []
    for this in d.keys():
        dk.append(this)
    print("d.keys()", dk)
    ezk = []
    for this in ez.keys():
        ezk.append(this)
    print("ez.keys()", ezk)
    assert len(ez) == len(ezk)
    assert dk == ezk

    dv = []
    for this in d.values():
        dv.append(this)
    print("d.values()", dv)
    ezv = []
    for this in ez.values():
        ezv.append(this)
    print("ez.values()", ezv)
    assert len(dv) == len(ezv)
    assert dv == ezv

    di = []
    for this in d.items():
        di.append(this)
    print("d.items()", di)
    ezi = []
    for this in ez.items():
        ezi.append(this)
    print("ez.items()", ezi)
    assert len(di) == len(ezi)
    assert di == ezi
