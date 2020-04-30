import base64
from collections.abc import MutableMapping
from contextlib import suppress
from operator import itemgetter
import os
import secrets
import sqlite3
from threading import RLock
from typing import ByteString, Callable, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from methodtools import lru_cache

_NOT_FOUND = object()

# copied directly from python 3.8 source
class cached_property:
    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__
        self.lock = RLock()

    def __set_name__(self, owner, name):
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                f"({self.attrname!r} and {name!r})."
            )

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                "Cannot use cached_property instance without calling __set_name__ on it."
            )
        try:
            cache = instance.__dict__
        except AttributeError:  # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {self.attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            with self.lock:
                # check if another thread filled cache while we awaited lock
                val = cache.get(self.attrname, _NOT_FOUND)
                if val is _NOT_FOUND:
                    val = self.func(instance)
                    try:
                        cache[self.attrname] = val
                    except TypeError:
                        msg = (
                            f"The '__dict__' attribute on {type(instance).__name__!r} instance "
                            f"does not support item assignment for caching {self.attrname!r} property."
                        )
                        raise TypeError(msg) from None
        return val


# try:
#     from functools import cached_property as cache
# except ImportError:
#     from functools import wraps

#     # decorator that does nothing and just runs the function, but accepts its kwargs
#     # I'm not sure if this is the best option
#     def cache(maxsize):
#         def wrapper(f):
#             @wraps(f)
#             def wrapped(*args, **kwargs):
#                 return f(*args, **kwargs)

#             return wrapped

#         return wrapper


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

    # if cache:
    #     _fernetgen = cache(maxsize=self.cache_n)(_fernetgen)

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
