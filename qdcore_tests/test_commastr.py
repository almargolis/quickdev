from qdcore import commastr


def test_is_empty_list(tmpdir):
    assert commastr.is_empty_list(["", "", "", None, None])
    assert not commastr.is_empty_list(["", "", "something", None, None])
