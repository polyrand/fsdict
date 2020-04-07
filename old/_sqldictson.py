from collections.abc import MutableMapping
from contextlib import suppress
from operator import itemgetter

# import sqlite3
from orjson import loads, dumps
import aiosqlite
import asyncio
import uvloop

# from aiostream.stream import map

uvloop.install()

# https://stackoverflow.com/questions/42009202/how-to-call-a-async-function-contained-in-a-class
# https://stackoverflow.com/questions/59984012/coroutines-in-magic-methods
# https://stackoverflow.com/questions/42009202/how-to-call-a-async-function-contained-in-a-class
# https://www.integralist.co.uk/posts/python-asyncio/#event-loop
# https://stackoverflow.com/questions/48052217/how-to-use-an-async-for-loop-to-iterate-over-a-list
# https://aiostream.readthedocs.io/en/latest/operators.html#aiostream.stream.map


class SQLDict(MutableMapping):
    async def __aenter__(self, dbname, items=[], **kwargs):
        self.dbname = "aio"
        uvloop.install()
        self.loop = asyncio.get_event_loop()
        self.conn = await aiosqlite.connect(dbname)
        c = await self.conn.cursor()
        with suppress(aiosqlite.OperationalError):
            await c.execute("CREATE TABLE Dict (key text, value text)")
            await c.execute("CREATE UNIQUE INDEX Indx ON Dict (key)")
        self.update(items, **kwargs)

    async def __aexit__(self):
        await self.conn.close()

    async def __setitem__(self, key, value):
        value = await self.loop.run_in_executor(None, loads(value))
        if key in self:
            del self[key]
        async with self.conn as c:
            await c.execute("INSERT INTO  Dict VALUES (?, ?)", (key, value))

    async def __getitem__(self, key):
        c = await self.conn.execute("SELECT value FROM Dict WHERE Key=?", (key,))
        row = await c.fetchone()
        if row is None:
            raise KeyError(key)
        result = await self.loop.run_in_executor(None, dumps(row[0]))
        return result

    async def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        async with self.conn as c:
            await c.execute("DELETE FROM Dict WHERE key=?", (key,))

    async def __len__(self):
        return next(await self.conn.execute("SELECT COUNT(*) FROM Dict"))[0]

    async def __iter__(self):
        c = await self.conn.execute("SELECT key FROM Dict")
        result = await asyncio.gather(map(itemgetter(0), await c.fetchall()))
        return result

    def __repr__(self):
        return (
            f"{type(self).__name__}(dbname={self.dbname!r}, items={list(self.items())})"
        )

    async def close(self):
        await self.conn.close()
