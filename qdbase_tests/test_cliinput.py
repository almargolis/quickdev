from io import StringIO

from qdbase import cliinput
from qdbase import pdict


def test_form(monkeypatch):
    form_data = {"thing_1": "data_one", "other_2": "some_two", "what_3": "yup_three"}
    tdict = pdict.DbTableDict("test", is_rowid_table=False)
    tdict.add_column(pdict.Text("dict_a", default_value="aye"))
    f = cliinput.CliForm(form_data, tdict=tdict)
    print(f.working_data)
    assert len(f.working_data) == len(form_data) + 1
    f.show()
    monkeypatch.setattr("sys.stdin", StringIO("q\n"))
    f.form_menu()
