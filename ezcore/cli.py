import re
import sys

class CliMenuItem(object):
    __slots__ = ('cmd', 'desc', 'func', 'security', 'tdict')
    def __init__(self, cmd, func, security, desc=""):
        self.cmd = cmd
        self.func = func
        self.security = security
        self.desc = desc
        self.tdict = None

class CliMenu(object):
    __slots__ = ('items')
    def __init__(self):
        self.items = {}

    def append(self, item):
        if item.cmd in self.items:
            raise ValueError("Duplicate CliMenu cmd '{}'".format(item.cmd))
        self.items[item.cmd] = item
        return item

    def help(self, prog):
        print("usage {}".format(prog))
        for this in self.items.values():
            print("  {} {}".format(this.cmd, this.desc))

    def cli_run(self):
        prog = sys.argv[0]
        if prog == '':
            prog = 'python'
        elif prog == '-c':
            prog = 'python -c '
        else:
            prog = 'python ' + prog
        print(prog, '/', sys.argv)
        if len(sys.argv) == 1:
            self.help(prog)
            sys.exit(-1)
        cmd = sys.argv[1]
        if cmd[0] == '-':
            cmd = cmd[1:]
        try:
            item = self.items[cmd]
        except KeyError:
            self.help(prog)
            sys.exit(-1)
        if item.tdict is None:
            return item.func()
        else:
            args, kwargs = item.tdict.cli_to_function_parms(sys.argv[2:])
            return item.func(*args, **kwargs)

def cli_input(prompt, field_def=None, regex=None, value_prompt=None, lower=False):
    if field_def == 'yn':
        regex = re.compile(r"[yn]", flags=re.IGNORECASE)
        value_prompt = 'y/n'
    if regex is None:
        raise ValueError('No regex defined.')
    if value_prompt is None:
        raise ValueError('No value prompt defined.')
    while True:
        resp = input("{} [{}]: ".format(prompt, value_prompt))
        if regex.match(resp):
            break
    if lower:
        resp = resp.lower()
    return resp

def cli_input_symbol(prompt):
    regex = re.compile(r"[a-z]\w", flags=re.ASCII|re.IGNORECASE)
    return cli_input(prompt, regex=regex, value_prompt="directory name")

def cli_input_yn(prompt):
    resp = cli_input(prompt, field_def='yn', lower=True)
    if resp == 'y':
        return True
    else:
        return False
