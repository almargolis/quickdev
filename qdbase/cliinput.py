import re

debug_input_strings = []
debug_input_ix = 0
debug_input_answers = {}

def set_debug_input(debug_strings):
    global debug_input_strings
    global debug_input_ix
    debug_input_strings = debug_strings
    debug_input_ix = 0

def cli_input(prompt, regex=None, value_hint=None, lower=False, debug=0):
    global debug_input_ix
    if value_hint is None:
        value_prompt = ""
    else:
        value_prompt = " [{}]".format(value_hint)
    while True:
        if debug > 0:
            print("cli_input() '{}' '{}'".format(prompt, value_prompt))
        if debug_input_ix < len(debug_input_strings):
            resp = debug_input_strings[debug_input_ix]
            print("cli_input() ix={} '{}'".format(debug_input_ix, resp))
            debug_input_ix += 1
        elif prompt in debug_input_answers:
            resp = debug_input_answers[prompt]
        else:
            resp = input("{}{}".format(prompt, value_prompt))
        if (regex is None) or regex.match(resp):
            break
    if lower:
        resp = resp.lower()
    return resp


def cli_input_symbol(prompt, debug=0):
    regex = re.compile(r"[a-z]\w", flags=re.ASCII | re.IGNORECASE)
    return cli_input(prompt, regex=regex, debug=debug)


def cli_input_yn(prompt, debug=0):
    regex = re.compile(r"[yn]", flags=re.IGNORECASE)
    resp = cli_input(prompt, regex=regex, value_hint="y/n", lower=True, debug=debug)
    if resp == "y":
        return True
    else:
        return False


def cli_chooser(items, debug=0):
    menu_display = []
    menu_match = []
    for this in items:
        menu_display.append("{}({})".format(this[0], this[1:]))
        menu_match.append(this[0])
    regex = re.compile(
        r"[{}]".format("".join(menu_match)), flags=re.ASCII | re.IGNORECASE
    )
    return cli_input(", ".join(menu_display), regex=regex, lower=True, debug=debug)

STATUS_DEFINED = ' '
STATUS_UNDEFINED = '?'

class CliFormItem:
    __slots__ = ("ix", "is_read_only", "key", "status", "value")

    def __init__(self, status, ix, key, value, is_read_only=False):
        self.status = status
        self.is_read_only = is_read_only
        self.ix = ix
        self.key = key
        self.value = value

    def __repr__(self):
        return "CliFormItem({}, {}, {}, {})".format(
            self.status, self.ix, self.key, self.value
        )


class CliForm:
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
                if this.name in self.working_data:
                    self.working_data[this.name].status = STATUS_DEFINED
                    self.working_data[this.name].is_read_only = this.is_read_only
                else:
                    self.append_item(
                        STATUS_DEFINED,
                        this.name,
                        this.default_value,
                        is_read_only=this.is_read_only,
                    )
                    self.dirty = True
        if run:
            self.form_run()

    def append_item(self, status, key, value, is_read_only=False):
        self.max_ix += 1
        self.working_data[key] = CliFormItem(
            status, self.max_ix, key, value, is_read_only=is_read_only
        )

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
                print("Key '{}' already in collection.".format(key))
                continue
            value = cli_input("Item Value:")
            self.append_item(STATUS_UNDEFINED, key, value)
            return True

    def get_item(self):
        while True:
            key = cli_input("Item Index:")
            if key == "":
                return None
            ix = int(key)
            if ix is None:
                if key in self.working_data:
                    return self.working_data[key]
                else:
                    print("Key '{}' not in collection.".format(key))
                    continue
            item = self.item_by_ix(ix)
            if item is not None:
                return item
            print("Index '{}' not in collection.".format(ix))

    def item_by_ix(self, ix):
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
        prompt = "Delete [{}. {}: {}]".format(item.ix, item.key, item.value)
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
        prompt = "Edit [{}. {}: {}]".format(item.ix, item.key, item.value)
        item.value = cli_input(prompt, debug=self.debug)
        return True

    def form_menu(self):
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
                if not cli_input_yn("Unsaved changes. Do you want to quit?", debug=self.debug):
                    return True
            return False
        elif choice == "s":
            self.source_data.save(new_data=self.working_data)
            self.dirty = False
            return True
        elif choice == "a":
            if self.add_item():
                self.dirty = True
            return True
        elif choice == "d":
            if self.del_item():
                self.dirty = True
            return True
        elif choice == "e":
            if self.edit_item():
                self.dirty = True
            return True
        elif choice == "l":
            self.show_data()
            return True
        else:
            return True

    def form_run(self, show=True):
        if show:
            self.show_data()
        while True:
            if not self.form_menu():
                break

    def show_data(self):
        for this in self.working_data.values():
            print(this)
