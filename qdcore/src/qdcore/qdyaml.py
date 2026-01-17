"""
QdYaml is a wrapper around yaml that makes it a bit easier to use
by eliminating some odd syntax and supporting QickDev best practices.

As this develops, its should be consisten with qdcore/inifile.py.
"""

import yaml
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


class QdYaml:
    def __init__(self, fpath=None):
        self.data = None
        self.fpath = None
        if fpath is not None:
            self.load(fpath)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem(self, key, value):
        self.data[key] = value
        return value

    def load(self, fpath):
        with open(fpath, "r") as f:
            self.data = yaml.load(f, Loader=Loader)
        self.fpath = fpath
        return self.data

    def dump(self, fpath=None):
        if fpath is None:
            fpath = self.fpath
        with open(fpath, "w") as f:
            self.data = yaml.dump(self.data, f)
