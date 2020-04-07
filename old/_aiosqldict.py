from collections.abc import MutableMapping
from contextlib import suppress
from operator import itemgetter
import sqlite3
import aiosqlite


class SQLDict(MutableMapping):
    def __init__(self, dbname, items=[], **kwargs):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname)
        self.aconn = aiosqlite.connect(dbname)
        c = self.conn.cursor()
        with suppress(sqlite3.OperationalError):
            c.execute("CREATE TABLE Dict (key text, value text)")
            c.execute("CREATE UNIQUE INDEX Kndx ON Dict (key)")
        self.update(items, **kwargs)

    async def __setitem__(self, key, value):
        if key in self:
            del self[key]
        async with self.aconn as c:
            await c.execute("INSERT INTO  Dict VALUES (?, ?)", (key, value))

    async def __getitem__(self, key):
        async with self.aconn as db:
            async with db.execute("SELECT value FROM Dict WHERE Key=?", (key,)) as c:
                async for row in c.fetchone():
                    if row is None:
                        raise KeyError(key)
                    return row[0]

    async def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        async with self.conn as c:
            await c.execute("DELETE FROM Dict WHERE key=?", (key,))

    def __len__(self):
        return next(self.conn.execute("SELECT COUNT(*) FROM Dict"))[0]

    async def __iter__(self):
        async with self.aconn as db:
            async with db.execute("SELECT key FROM Dict") as c:
                async for i in c.fetchall():
                    return itemgetter(0, i)

    def __repr__(self):
        return (
            f"{type(self).__name__}(dbname={self.dbname!r}, items={list(self.items())})"
        )

    def close(self):
        self.conn.close()
