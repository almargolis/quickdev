"""
  QdSerializer is virtual base class for qdjson, qdyaml and other serialized
  text objects. It provides helper functions to simplify coding those
  modules and making them consisten.
"""

import requests

class QdSerializer:
    __slots__ = ('blob', 'data', 'fpath')
    def __init__(self, fpath=None):
        self.blob = None
        self.data = None
        self.fpath = fpath
        if fpath is not None:
            self.load_blob(fpath)
            self.load()

    def load_blob(self, fpath):
        self.blob = None
        if fpath.startswith('https:'):
            r_resp = requests.get(fpath)
            if r_resp.status_code == 200:
                self.blob = r_resp.text
            else:
                raise Exception(f"QdSerializer() url '{fpath}' not found.")
            return
        if fpath.startswith('file:'):
            file_path = fpath.removeprefix('file:')
            with open(file_path, 'r') as f:
                self.blob = f.read()
            return
