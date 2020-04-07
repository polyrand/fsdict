# Produtils


This started as "copying the code" from the talk [Build powerful, new data structures with Python's abstract base classes](https://www.youtube.com/watch?v=S_ipdVNSFlo) by [Raymond Hettinger](https://twitter.com/raymondh) since I couldn't find it anywhere.

After that I started modifying the files.

## `flightcryptofiledict.py`

Dictionary implementation that saves everything to files in disk.

**Features**

When a value is going it be written to the disk a new salt is created. Then this salt is passed to the hashing function. The values are encrypted using [`PBKDF2HMAC`](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC). The salt is generated for each entry. It is saved in the filename separated by a quadruple underscore. **Don't use quadruple underscore** in your variable names when setting/getting the dictionary, it will break, you can use double and triple underscores.	 It can be fixed adding a couple of `if` statements inside, but so far I have never had to create a key/value name with `4*_` inside. 

The salt is 64 bytes long and it's created using [`secrets.token_urlsafe`](https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe). The salt is created as a string and then encoded to bytes so that it's easier to implement a static salt that you can keep as an environment variable.

### Installation

It is a single self-contained 200 lines-of-code file. The only dependency is `cryptography`. Install it with:

```
pip install cryptography
```

The best way to use it is just copying and pasting the contents of the file to your project and avoid adding one more dependency. When copying the file you may extend it adding more functionality to it. That functionality may be useful to other users so please consider openning a pull request to add it to the current project.

### Usage

You need to provide a `password` when creating the dictionary object or set an environment variable:

**Creating an environment variable (recommended):**

```bash
export PASS=mypass
```

**When creating the dictionary:**

```python
from flightcryptofiledict import FileDict

d = FileDict("newname", password="secretpassword")
```


If the dictionary values need to be something different from strings a custom encoder/decoder can be passed. The only condition is that those functions should return a `bytes` object. Examples:

```python
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
```


## `cryptofiledict.py`

More or less the same as before but the salt is static. The salt is parsed as a base64 encoded string. It will be less secure but faster.


## Meta

Ricardo Ander-Egg Aguilar – [@ricardoanderegg](https://twitter.com/ricardoanderegg) –

Distributed under the MIT license. See ``LICENSE`` for more information.

[https://github.com/polyrand/](https://github.com/polyrand/)

## Contributing

1. Fork it (<https://github.com/polyrand/produtils/fork>)
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Create a new Pull Request
