import base64
import os
import secrets
import sqlite3
from collections.abc import MutableMapping
from contextlib import suppress
from operator import itemgetter
from typing import ByteString, Callable, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from methodtools import lru_cache


class SQLDict(MutableMapping):

    # 234375 == using 15mb of memory to cache fernet objects
    # cache_n = 234375

    def __init__(
        self,
        dbname,
        items=[],
        password: Optional[str] = None,
        encoder: Callable = lambda x: x.encode(),
        decoder: Callable = lambda x: x.decode(),
        cache_size: Union[float, int] = None,
        **kwargs,
    ):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname)
        c = self.conn.cursor()
        self.password: ByteString = os.getenv(
            "PASS"
        ).encode() if not password else password.encode()
        self.encoder = encoder
        self.decoder = decoder

        # 6.4e-05 is de size in MB of a fernet object that can
        # encrypt / decrypt data (measured with sys.getsizeof)
        # 234375 == using 15mb of memory to cache fernet objects
        # if cache_size:
        #     nonlocal cache_n
        #     cache_n = cache_size / 6.4e-05

        with suppress(sqlite3.OperationalError):
            c.execute("CREATE TABLE Dict (key text, value blob, salt text)")
            c.execute("CREATE UNIQUE INDEX KIndx ON Dict (key)")

        self.update(items, **kwargs)

    # 234375 == using 15mb of memory to cache fernet objects
    @lru_cache(maxsize=234375)
    def _fernetgen(self, newsalt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=newsalt,
            iterations=100000,
            backend=default_backend(),
        )

        key = base64.urlsafe_b64encode(kdf.derive(self.password))

        return Fernet(key)

    def __setitem__(self, key, value):
        if key in self:
            del self[key]

        salt = secrets.token_urlsafe(64)
        value = self.encoder(value)
        newsalt = salt.encode()
        fernet = self._fernetgen(newsalt)
        value = fernet.encrypt(value)
        with self.conn as c:
            c.execute("INSERT INTO  Dict VALUES (?, ?, ?)", (key, value, salt))

    def __getitem__(self, key):
        c = self.conn.execute("SELECT value, salt FROM Dict WHERE Key=?", (key,))
        row = c.fetchone()
        if row is None:
            raise KeyError(key)
        value = row[0]
        salt = row[1]
        newsalt = salt.encode()
        fernet = self._fernetgen(newsalt)
        value = fernet.decrypt(value)
        return self.decoder(value)

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
        return f"{type(self).__name__}(dbname={self.dbname!r})"  # , items={list(self.items())})"

    def vacuum(self):
        with self.conn as c:
            c.execute("VACUUM;")

    def close(self):
        self.conn.close()
