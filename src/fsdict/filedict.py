from collections.abc import MutableMapping
from contextlib import suppress
import os


class FileDict(MutableMapping):
    def __init__(self, dirname, pairs=(), **kwargs):
        self.dirname = dirname
        with suppress(FileExistsError):
            os.mkdir(dirname)
        self.update(pairs, **kwargs)

    def __setitem__(self, key, value):
        fullname = os.path.join(self.dirname, key)
        with open(fullname, "w") as f:
            f.write(value)

    def __getitem__(self, key):
        fullname = os.path.join(self.dirname, key)
        try:
            with open(fullname) as f:
                return f.read()
        except FileNotFoundError:
            raise KeyError(key) from None

    def __delitem__(self, key):
        fullname = os.path.join(self.dirname, key)
        try:
            os.remove(fullname)
        except FileNotFoundError:
            raise KeyError(key) from None

    def __len__(self):
        return len(os.listdir(self.dirname))

    def __iter__(self):
        return iter(os.listdir(self.dirname))

    def __repr__(self):
        return f"FileDict{tuple(self.items())}"
