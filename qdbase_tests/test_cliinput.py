"""
test cliinput.py
"""

from qdbase import cliinput
from qdbase import pdict


def test_form():
    """
    Test ini file editing form.
    """
    form_data = {"thing_1": "data_one", "other_2": "some_two", "what_3": "yup_three"}
    tdict = pdict.DbDictTable("test", is_rowid_table=False)
    tdict.add_column(pdict.Text("dict_a", default_value="aye"))
    cliinput.set_debug_input(["q", "y"])
    f = cliinput.CliForm(form_data, tdict=tdict, run=False, debug=1)
    print("test_form()", f.working_data)
    assert len(f.working_data) == len(form_data) + 1
    f.show_data()
    f.form_menu()
