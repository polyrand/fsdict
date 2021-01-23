import sqlite3
import json
from typing import Callable
from collections.abc import MutableMapping
from contextlib import suppress
from operator import itemgetter

# Code from the talk [Build powerful, new data structures with Python's abstract base classes]
# (https://www.youtube.com/watch?v=S_ipdVNSFlo) by [Raymond Hettinger](https://twitter.com/raymondh).


class SQLDict(MutableMapping):
    """
    Dictionary persisted to a SQLite database.

    Example:
    _______

    >>> from fsdict.sqldict import SQLDict
    >>> enc_sqldict = SQLDict("test.db")

    >>> import pickle
    >>> import math

    >>> enc_sqldict.encoder = lambda x: pickle.dumps(x)
    >>> enc_sqldict.decoder = lambda x: pickle.loads(x)

    >>> enc_sqldict["myfunc"] = math.cos
    >>> enc_sqldict["myfunc"]
    <built-in function cos>

    >>> enc_sqldict["myfunc"](23)
    -0.5328330203333975

    >>> import json
    >>> enc_sqldict.encoder = lambda x: json.dumps(x).encode()
    >>> enc_sqldict.decoder = lambda x: json.loads(x.decode())

    >>> enc_sqldict["mydict"] = {"a": 12}
    >>> enc_sqldict["mydict"]
    {'a': 12}

    >>> enc_sqldict["mydict"]["a"]
    12

    _______

    """

    def __init__(
        self,
        dbname,
        items=[],
        check_same_thread=True,
        fast=True,
        encoder: Callable = lambda x: x.encode(),
        decoder: Callable = lambda x: x.decode(),
        **kwargs,
    ):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname, check_same_thread=check_same_thread)
        c = self.conn.cursor()
        self.encoder = encoder
        self.decoder = decoder

        with suppress(sqlite3.OperationalError):
            # converted value from text -> blob so that it accepts
            # non-string values
            c.execute("CREATE TABLE Dict (key text, value blob)")
            c.execute("CREATE UNIQUE INDEX KIndx ON Dict (key)")
            if fast:
                c.execute("PRAGMA journal_mode = 'WAL';")
                c.execute("PRAGMA synchronous = 1;")
                c.execute(f"PRAGMA cache_size = {-1 * 64_000};")

        self.update(items, **kwargs)

    def __setitem__(self, key, value):
        # if key in self:
        #     with self.conn as c:
        #         c.execute(
        #             "UPDATE Dict SET value = ? WHERE key = ?",
        #             (self.encoder(value), key),
        #         )
        #     return

        # del self[key]
        with self.conn as c:
            c.execute(
                "INSERT OR REPLACE INTO  Dict VALUES (?, ?)", (key, self.encoder(value))
            )

    def __getitem__(self, key):
        c = self.conn.execute("SELECT value FROM Dict WHERE Key=?", (key,))
        row = c.fetchone()
        if row is None:
            raise KeyError(key)
        return self.decoder(row[0])

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        with self.conn as c:
            c.execute("DELETE FROM Dict WHERE key=?", (key,))

    def __len__(self):
        return next(self.conn.execute("SELECT COUNT(*) FROM Dict"))[0]

    def __iter__(self):
        c = self.conn.execute("SELECT key FROM Dict")
        return map(itemgetter(0), c.fetchall())

    def __repr__(self):
        return (
            f"{type(self).__name__}(dbname={self.dbname!r}, items={list(self.items())})"
        )

    def vacuum(self):
        with self.conn as c:
            c.execute("VACUUM;")

    def close(self):
        self.conn.close()


class StringSQLDict(MutableMapping):
    def __init__(
        self,
        dbname,
        check_same_thread=False,
        fast=True,
        encoder: Callable = lambda x: json.dumps(x),
        decoder: Callable = lambda x: json.loads(x),
        **kwargs,
    ):
        self.dbname = dbname
        self.conn = sqlite3.connect(
            self.dbname, check_same_thread=check_same_thread, **kwargs
        )
        self.encoder = encoder
        self.decoder = decoder

        with self.conn as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS Dict (key text NOT NULL PRIMARY KEY, value text)"
            )

            c.execute(
                "CREATE TABLE IF NOT EXISTS Counter (key text NOT NULL PRIMARY KEY, value integer)"
            )

            if fast:
                c.execute("PRAGMA journal_mode = 'WAL';")
                c.execute("PRAGMA synchronous = 1;")
                c.execute(f"PRAGMA cache_size = {-1 * 64_000};")

    def __setitem__(self, key: str, value):
        with self.conn as c:
            c.execute(
                "INSERT OR REPLACE INTO  Dict VALUES (?, ?)", (key, self.encoder(value))
            )

    def __getitem__(self, key: str):
        c = self.conn.execute("SELECT value FROM Dict WHERE Key=?", (key,))
        row = c.fetchone()
        if row is None:
            raise KeyError(key)
        return self.decoder(row[0])

    def __delitem__(self, key: str):
        if key not in self:
            raise KeyError(key)
        with self.conn as c:
            c.execute("DELETE FROM Dict WHERE key=?", (key,))

    def __len__(self):
        return next(self.conn.execute("SELECT COUNT(*) FROM Dict"))[0]

    def __iter__(self):
        c = self.conn.execute("SELECT key FROM Dict")
        return map(itemgetter(0), c.fetchall())

    def __repr__(self):
        return (
            f"{type(self).__name__}(dbname={self.dbname!r}, items={list(self.items())})"
        )

    def glob(self, pat: str):
        c = self.conn.execute("SELECT value FROM Dict WHERE Key GOLB ?", (pat,))
        row = c.fetchone()
        if row is None:
            raise KeyError(pat)
        return self.decoder(row[0])

    def vacuum(self):
        with self.conn as c:
            c.execute("VACUUM;")

    def close(self):
        self.conn.close()
