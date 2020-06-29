import base64
from collections.abc import MutableMapping
from contextlib import suppress
import os
from typing import Callable

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC  # , ByteString


class FileDict(MutableMapping):

    """A password can be provided, default is from env.

    The salt is expected as `str` to make it easy to set as an environment variable.
    After being processed it returns `bytes`

    The encoder/decoder can be overridden. The default value expected is a string so the default
    encoder/decoder is string.encode() and string.decode().

    Example:
    _______

    >>> from cryptofiledict import FileDict
    >>> enc_filedict = FileDict("cryptest")

    >>> import pickle
    >>> import math

    >>> enc_filedict.encoder = lambda x: pickle.dumps(x)
    >>> enc_filedict.decoder = lambda x: pickle.loads(x)

    >>> enc_filedict["myfunc"] = math.cos
    >>> enc_filedict["myfunc"]
    <function math.cos(x, /)>

    >>> enc_filedict["myfunc"](23)
    -0.5328330203333975

    >>> import json
    >>> enc_filedict.encoder = lambda x: json.dumps(x).encode()
    >>> enc_filedict.decoder = lambda x: json.loads(x.decode())

    >>> enc_filedict["mydict"] = {"a": 12}
    >>> enc_filedict["mydict"]
    {'a': 12}

    >>> enc_filedict["mydict"]["a"]
    12

    _______

    """

    def __init__(
        self,
        dirname: str,
        pairs=(),
        password: str = None,
        salt: str = None,
        encoder: Callable = lambda x: x.encode(),
        decoder: Callable = lambda x: x.decode(),
        **kwargs,
    ):
        self.dirname: str = dirname
        # get PASS from env if it is not provided
        self.password: bytes = os.getenv(
            "PASS"
        ).encode() if not password else password.encode()
        self.salt: bytes = base64.decodebytes(
            os.getenv("SALT").encode().decode("unicode_escape").encode()
        ) if not salt else salt.encode()  # provided as base64 string (not bytes)
        self.kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend(),
        )
        self.key = base64.urlsafe_b64encode(self.kdf.derive(self.password))
        self.fernet = Fernet(self.key)

        # define encoder / decoder
        self.encoder = encoder
        self.decoder = decoder

        with suppress(FileExistsError):
            os.mkdir(dirname)
        self.update(pairs, **kwargs)

    def __setitem__(self, key, value):
        fullname = os.path.join(self.dirname, key)
        value = self.encoder(value)
        with open(fullname, "wb") as f:
            value = self.fernet.encrypt(value)
            f.write(value)

    def __getitem__(self, key):
        fullname = os.path.join(self.dirname, key)
        try:
            with open(fullname, "rb") as f:
                value = f.read()
                decrypt = self.fernet.decrypt(value)
                return self.decoder(decrypt)
                # return f.read()
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
