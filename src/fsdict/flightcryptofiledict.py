import base64
import os
import secrets
import tarfile
from collections.abc import MutableMapping
from contextlib import suppress
from glob import glob
from typing import Callable

# import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from methodtools import lru_cache


class FileDict(MutableMapping):

    """A password can be provided, default is from env.

    The salt is generated for each entry. The salt is saved in the filename
    separated by a quadruple underscore (so don't use that in your variable names,
    you can use double and triple underscores).

    After being processed it returns a `ByteString`

    The encoder/decoder can be overridden. The default value expected is a string so the default
    encoder/decoder is string.encode() and string.decode().

    Example:
    _______

    >>> from flightcryptofiledict import FileDict
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
        encoder: Callable = lambda x: x.encode(),
        decoder: Callable = lambda x: x.decode(),
        **kwargs,
    ):
        self.dirname: str = dirname
        # get PASS from env if it is not provided
        self.password: bytes = os.getenv(
            "PASS"
        ).encode() if not password else password.encode()
        # self.kdfgen = lambda newsalt: PBKDF2HMAC(
        #     algorithm=hashes.SHA256(),
        #     length=32,
        #     salt=newsalt,
        #     iterations=100000,
        #     backend=default_backend(),
        # )
        # self.keygen = lambda kdf: base64.urlsafe_b64encode(kdf.derive(self.password))
        # # self.key = base64.urlsafe_b64encode(self.kdf.derive(self.password))
        # self.fernetgen = lambda key: Fernet(key)

        # define encoder / decoder
        self.encoder = encoder
        self.decoder = decoder

        with suppress(FileExistsError):
            os.mkdir(dirname)
        self.update(pairs, **kwargs)

    # 234375 == using 15mb of memory to cache fernet objects
    @lru_cache(maxsize=234375)
    def fernetgen(self, newsalt):
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
        # delete file if exists. Since the salt is generated
        # on creation, the same key is saved with different filenames
        # so just writing on it will not overwrite
        fullpath = os.path.join(self.dirname, key)
        fullnames: list = glob(f"{fullpath}____*")
        if len(fullnames) > 0:
            # for f in fullnames:
            os.remove(fullnames[0])

        # key adaptation
        salt = secrets.token_urlsafe(64)
        # print("salt:", salt)
        key = f"{key}____{salt}"
        fullname = os.path.join(self.dirname, key)
        value = self.encoder(value)

        # new hasher generation
        newsalt = salt.encode()
        fernet = self.fernetgen(newsalt)
        #  kdf = self.kdfgen(newsalt)
        #  # use passkey, variable key is used before as the dictionary key
        #  passkey = self.keygen(kdf)
        #  fernet = self.fernetgen(passkey)
        # salt = fullname.split("____")[1]

        with open(fullname, "wb") as f:
            value = fernet.encrypt(value)
            f.write(value)

    def __getitem__(self, key):
        # key adaptation
        fullpath = os.path.join(self.dirname, key)
        try:
            fullname = glob(f"{fullpath}____*")[0]
        except IndexError:
            raise KeyError("key not found")

        # new hashser generation
        salt = fullname.split("____")[1]
        # print("salt:", salt)
        newsalt = salt.encode()
        fernet = self.fernetgen(newsalt)
        # kdf = self.kdfgen(newsalt)
        # key = self.keygen(kdf)
        # fernet = self.fernetgen(key)

        try:
            with open(fullname, "rb") as f:
                value = f.read()
                decrypt = fernet.decrypt(value)
                return self.decoder(decrypt)
                # return f.read()
        except FileNotFoundError:
            raise KeyError(key) from None

    def __delitem__(self, key):
        # key adaptation
        fullpath = os.path.join(self.dirname, key)
        fullname = glob(f"{fullpath}____*")[0]

        # fullname = os.path.join(self.dirname, key)
        try:
            os.remove(fullname)
        except FileNotFoundError:
            raise KeyError(key) from None

    def __len__(self):
        return len(os.listdir(self.dirname))

    def __iter__(self):
        files = [file.split("____")[0] for file in os.listdir(self.dirname)]
        return iter(files)

    def __repr__(self):
        # files = [file.split("____")[0] for file in os.listdir(self.dirname)]
        return f"FileDict{tuple(self.items())}"

    def compress(self, filename: str = None, **kwargs):
        """Create tar.gz file with the same name as the dictionary."""

        if not filename:
            filename = self.dirname

        with tarfile.open(filename + ".tar.gz", mode="w:gz", **kwargs) as tar:
            tar.add(self.dirname, arcname=filename, recursive=True)
