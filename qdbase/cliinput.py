import re


def cli_input(prompt, regex=None, value_hint=None, lower=False):
    if value_hint is None:
        value_prompt = ""
    else:
        value_prompt = " [{}]".format(value_hint)
    while True:
        resp = input("{}{}".format(prompt, value_prompt))
        if (regex is None) or regex.match(resp):
            break
    if lower:
        resp = resp.lower()
    return resp


def cli_input_symbol(prompt):
    regex = re.compile(r"[a-z]\w", flags=re.ASCII | re.IGNORECASE)
    return cli_input(prompt, regex=regex)


def cli_input_yn(prompt):
    regex = re.compile(r"[yn]", flags=re.IGNORECASE)
    resp = cli_input(prompt, regex=regex, value_hint="y/n", lower=True)
    if resp == "y":
        return True
    else:
        return False


def cli_chooser(items):
    menu_display = []
    menu_match = []
    for this in items:
        menu_display.append("{}({})".format(this[0], this[1:]))
        menu_match.append(this[0])
    regex = re.compile(
        r"[{}]".format("".join(menu_match)), flags=re.ASCII | re.IGNORECASE
    )
    return cli_input(", ".join(menu_display), regex=regex, lower=True)


class CliFormItem:
    __slots__ = ("ix", "key", "value")

    def __init__(self, ix, key, value):
        self.ix = ix
        self.key = key
        self.value = value

    def __repr__(self):
        return "CliFormItem({}, {}, {})".format(self.ix, self.key, self.value)


class CliForm:
    def __init__(self, data, tdict=None, run=True):
        self.source_data = data
        self.working_data = {}
        for ix, (key, value) in enumerate(data.items()):
            self.working_data[key] = CliFormItem(ix, key, value)
        if tdict is not None:
            for this in tdict.columns.values():
                if this.name in self.working_data:
                    continue
                else:
                    self.append_item(this.name, this.default_value)
        if run:
            self.form_run()

    def append_item(self, key, value):
        ix = len(self.working_data)
        self.working_data[key] = CliFormItem(ix, key, value)

    def add_item(self):
        """
        The return value can be used to set a data dirty flag. True inidicates that
        data was changed. False indicates that no changes were made.
        """
        while True:
            key = input("Item Key:")
            if key == "":
                return False
            if key in self.working_data:
                print("Key '{}' already in collection.".format(key))
                continue
            value = input("Item Value:")
            self.append_item(key, value)
            return True

    def get_item(self):
        while True:
            key = input("Item Index:")
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

    def del_item(self):
        """
        The return value can be used to set a data dirty flag. True inidicates that
        data was changed. False indicates that no changes were made.
        """
        item = self.get_item()
        if item is None:
            return False
        prompt = "Delete [{}. {}: {}]".format(item.ix, item.key, item.value)
        if cli_input_yn(prompt):
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
        prompt = "Delete [{}. {}: {}]".format(item.ix, item.key, item.value)

    def form_menu(self):
        menu_choices = []
        menu_choices.append("Add")
        menu_choices.append("Del")
        menu_choices.append("Edit")
        menu_choices.append("List")
        menu_choices.append("Save")
        menu_choices.append("Quit")
        choice = cli_chooser(menu_choices)
        if choice == "q":
            return False
        elif choice == "s":
            self.source_data.save(new_data=self.working_data)
            return True
        elif choice == "a":
            self.add_item()
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
