
class EzIni():
    __slots__ = ('_data', 'ini_path')

    def __init__(self):
        self._data = {}
        self.ini_path = None

    def get_dict(self, key):
        parts = key.split('.')
        data = self._data
        for this in parts[:-1]
            data = data[this]
        return data

    def __getitem__(self, key):
        data = self.get_dict(key)
        return data[key[-1]]

    def __setitem__(self, key, value):
        data = self.get_dict(key)
        data[key[-1]] = value

class EzExe():
    __slots__ = ()

    def __init__(self):
        
