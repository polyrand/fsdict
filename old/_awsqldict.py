from collections.abc import MutableMapping
from contextlib import suppress
from operator import itemgetter
import sqlite3
import asyncio
import uvloop
import aiosqlite


class SQLDict(MutableMapping):
    def __init__(self, dbname, items=[], **kwargs):
        self.dbname = dbname
        uvloop.install()
        self.conn = sqlite3.connect(dbname)
        c = self.conn.cursor()
        with suppress(sqlite3.OperationalError):
            c.execute("CREATE TABLE Dict (key text, value text)")
            c.execute("CREATE UNIQUE INDEX Kndx ON Dict (key)")
        self.update(items, **kwargs)

    async def asetitem(self, key, value):
        async with aiosqlite.connect(self.dbname) as db:
            await db.execute("INSERT INTO  Dict VALUES (?, ?)", (key, value))

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        asyncio.run(self.asetitem(key, value))

    async def agetitem(self, key):
        async with aiosqlite.connect(self.dbname) as db:
            async with db.execute("SELECT value FROM Dict WHERE Key=?", (key,)) as c:
                await c.fetchone()

    def __getitem__(self, key):
        row = asyncio.run(self.agetitem(key))
        if row is None:
            raise KeyError(key)
        return row[0]

    async def adelitem(self, key):
        async with aiosqlite.connect(self.dbname) as db:
            db.execute("DELETE FROM Dict WHERE key=?", (key,))

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        asyncio.run(self.adelitem(key))

    def __len__(self):
        return next(self.conn.execute("SELECT COUNT(*) FROM Dict"))[0]

    def __iter__(self):
        c = self.conn.execute("SELECT key FROM Dict")
        return map(itemgetter(0), c.fetchall())

    def __repr__(self):
        return (
            f"{type(self).__name__}(dbname={self.dbname!r}, items={list(self.items())})"
        )

    def close(self):
        self.conn.close()
