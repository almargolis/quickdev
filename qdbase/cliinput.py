"""
cliinput.py provides a functions and classes to
handle command line data input with consistent
presentation and basic data validation.
"""

import re

debug_input_strings = []  # pylint: disable=invalid-name
debug_input_ix = 0  # pylint: disable=invalid-name
debug_input_answers = {}  # pylint: disable=invalid-name


def set_debug_input(debug_strings):
    """
    Store simulated input values.
    """
    global debug_input_strings  # pylint: disable=global-statement,invalid-name
    global debug_input_ix  # pylint: disable=global-statement, invalid-name
    debug_input_strings = debug_strings
    debug_input_ix = 0


def cli_input(prompt, regex=None, value_hint=None, lower=False, debug=0):
    """
    This is an extension of the standard input function that
    provides data validation and simulated data for debugging.
    """
    global debug_input_ix  # pylint: disable=global-statement, invalid-name
    if value_hint is None:
        value_prompt = ""
    else:
        value_prompt = f" [{value_hint}]"
    while True:
        if debug > 0:
            print(f"cli_input() '{prompt}' '{value_prompt}'")
        if debug_input_ix < len(debug_input_strings):
            resp = debug_input_strings[debug_input_ix]
            print(f"cli_input() ix={debug_input_ix} '{resp}'")
            debug_input_ix += 1
        else:
            # The following can't be a get() because input()
            # gets evaluated every time.
            if prompt in debug_input_answers:  # pylint: disable=consider-using-get
                resp = debug_input_answers[prompt]
            else:
                resp = input(f"{prompt}{value_prompt}")
        if (regex is None) or regex.match(resp):
            break
    if lower:
        resp = resp.lower()
    return resp


def cli_input_symbol(prompt, debug=0):
    """
    input a value that validates as a program variable name.
    """
    regex = re.compile(r"[a-z]\w", flags=re.ASCII | re.IGNORECASE)
    return cli_input(prompt, regex=regex, debug=debug)


def cli_input_yn(prompt, debug=0):
    """
    input a value that validates as y/n. Return a boolean response.
    """
    regex = re.compile(r"[yn]", flags=re.IGNORECASE)
    resp = cli_input(prompt, regex=regex, value_hint="y/n", lower=True, debug=debug)
    return bool(resp == "y")


def cli_chooser(items, debug=0):
    """
    input a value that validates as the first character of one
    of the words in the items parameter. These will usually
    be menu choices.
    """
    menu_display = []
    menu_match = []
    for this in items:
        menu_display.append(f"{this[0]}({this[1:]})")
        menu_match.append(this[0])
    regex = re.compile(f"[{''.join(menu_match)}]", flags=re.ASCII | re.IGNORECASE)
    return cli_input(", ".join(menu_display), regex=regex, lower=True, debug=debug)


STATUS_DEFINED = " "
STATUS_UNDEFINED = "?"


class CliFormItem:  # pylint: disable=too-few-public-methods
    """
    Container for an entry in an input form.
    """

    __slots__ = ("ix", "is_read_only", "key", "status", "value")

    def __init__(
        self, status, ix, key, value, is_read_only=False
    ):  # pylint: disable=too-many-arguments
        self.status = status
        self.is_read_only = is_read_only
        self.ix = ix
        self.key = key
        self.value = value

    def __repr__(self):
        return f"CliFormItem({self.status}, {self.ix}, {self.key}, {self.value})"


class CliForm:
    """
    Command line edit form. This is generally used to edit
    ini or yaml files.
    """

    def __init__(self, data, tdict=None, run=True, debug=0):
        self.source_data = data
        self.working_data = {}
        self.max_ix = 0
        self.dirty = False
        self.debug = debug
        for ix, (key, value) in enumerate(data.items()):
            self.working_data[key] = CliFormItem(STATUS_UNDEFINED, ix, key, value)
            self.max_ix = ix
        if tdict is not None:
            for this in tdict.columns.values():
                self.define_item(
                    STATUS_DEFINED,
                    this.name,
                    this.default_value,
                    is_read_only=this.is_read_only,
                )
        if run:
            self.form_run()

    def define_item(self, status, key, value, is_read_only=False):
        """
        Define an item in the working_data.
        Create if it doesn't exist.
        """
        if key in self.working_data:
            self.working_data[key].status = status
            self.working_data[key].is_read_only = is_read_only
            return
        self.max_ix += 1
        self.working_data[key] = CliFormItem(
            status, self.max_ix, key, value, is_read_only=is_read_only
        )
        self.dirty = True

    def add_item(self):
        """
        The return value can be used to set a data dirty flag. True inidicates that
        data was changed. False indicates that no changes were made.
        """
        while True:
            key = cli_input("Item Key:")
            if key == "":
                return False
            if key in self.working_data:
                print(f"Key '{key}' already in collection.")
                continue
            value = cli_input("Item Value:")
            self.define_item(STATUS_UNDEFINED, key, value)
            return True

    def get_item(self):
        """
        Prompt the user to enter an index to one of the
        items in working_data.
        """
        while True:
            key = cli_input("Item Index:")
            if key == "":
                return None
            ix = int(key)
            if ix is None:
                if key in self.working_data:
                    return self.working_data[key]
                print(f"Key '{key}' not in collection.")
                continue
            item = self.item_by_ix(ix)
            if item is not None:
                return item
            print(f"Index '{ix}' not in collection.")
            return None

    def item_by_ix(self, ix):
        """
        Scan working_data to find an item based on ix.
        This needs to be a scan because add / insert
        can result in the dictionary being out of order.
        """
        for this in self.working_data.values():
            if this.ix == ix:
                return this
        return None

    def del_item(self):
        """
        The return value can be used to set a data dirty flag. True inidicates that
        data was changed. False indicates that no changes were made.
        """
        item = self.get_item()
        if item is None:
            return False
        if item.is_read_only:
            print("Read only item. Caanot be deleted.")
            return False
        prompt = f"Delete [{item.ix}. {item.key}: {item.value}]"
        if cli_input_yn(prompt, debug=self.debug):
            self.working_data.pop(item.key)
            return True
        return False

    def edit_item(self):
        """
        The return value can be used to set a data dirty flag. True inidicates that
        data was changed. False indicates that no changes were made.
        """
        item = self.get_item()
        if item is None:
            return False
        if item.is_read_only:
            print("Read only item. Caanot be edited.")
            return False
        prompt = f"Edit [{item.ix}. {item.key}: {item.value}]"
        item.value = cli_input(prompt, debug=self.debug)
        return True

    def form_menu(self):  # pylint: disable=too-many-return-statements
        """
        Prompt the user for a form action.
        """
        menu_choices = []
        menu_choices.append("Add")
        menu_choices.append("Del")
        menu_choices.append("Edit")
        menu_choices.append("List")
        menu_choices.append("Save")
        menu_choices.append("Quit")
        choice = cli_chooser(menu_choices, debug=self.debug)
        if choice == "q":
            if self.dirty:
                if not cli_input_yn(
                    "Unsaved changes. Do you want to quit?", debug=self.debug
                ):
                    return True
            return False
        if choice == "s":
            self.source_data.save(new_data=self.working_data)
            self.dirty = False
            return True
        if choice == "a":
            if self.add_item():
                self.dirty = True
            return True
        if choice == "d":
            if self.del_item():
                self.dirty = True
            return True
        if choice == "e":
            if self.edit_item():
                self.dirty = True
            return True
        if choice == "l":
            self.show_data()
            return True
        return True

    def form_run(self, show=True):
        """
        Display the form and prompt the user for
        actions until the user quits.
        """
        if show:
            self.show_data()
        while True:
            if not self.form_menu():
                break

    def show_data(self):
        """
        Display working_data
        """
        for this in self.working_data.values():
            print(this)
