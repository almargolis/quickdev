# datbae.py - CommerceNode database utilities
#

import sys


class DbShell:
    __slots__ = ("commands", "dbs")

    def __init__(self):
        self.commands = {}
        self.commands["help"] = self.cmd_help
        self.commands["listdb"] = self.cmd_listdb
        self.dbs = {}

    def cmd_help(self, tokens):
        for this_cmd, this_func in self.commands.items():
            print("CMD: {}".format(this_cmd))

    def cmd_listdb(self, tokens):
        if len(self.dbs) == 0:
            print("No databases configured.")
        else:
            for this in dbs.keys():
                print("DB: {}".format(this))

    def run(self):
        while True:
            cmd = input("DB> ")
            tokens = cmd.split(" ")
            if tokens[0] in self.commands:
                self.commands[tokens[0]](tokens)
            else:
                print("Unknown command '{}'.".format(tokens[0]))


if __name__ == "__main__":
    shell = DbShell()
    shell.run()
