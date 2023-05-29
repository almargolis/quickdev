"""
  QdJson is a wrapper around json that makes it a bit easier to use
  by eliminating some odd syntax and supporting QickDev best practices.

  As this develops, its should be consisten with qdcore/inifile.py.
"""

import json

from . import qdserializer

class QdJson(qdserializer.QdSerializer):
    def __init__(self, fpath=None):
        super().__init__(fpath=fpath)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem(self, key, value):
        self.data[key] = value
        return value

    def load(self, fpath=None):
        self.data = None
        if fpath is not None:
            self.load_blob(fpath)
        if self.blob is not None:
            self.data = json.loads(self.blob)
        return self.data

    def dump(self, fpath=None):
        if fpath is None:
            fpath = self.fpath
        with open(fpath, 'w') as f:
            self.data = yaml.dump(self.data, f)
