# File system mappings

This started as "copying the code" from the talk [Build powerful, new data structures with Python's abstract base classes](https://www.youtube.com/watch?v=S_ipdVNSFlo) by [Raymond Hettinger](https://twitter.com/raymondh) since I couldn't find it anywhere.

After that I started modifying the code and creating new utilities.

Install with:

```sh
pip install fsdict
```

## `flightcryptofiledict.py`

Dictionary implementation that saves everything to files in disk.

**Features**

When a value is going it be written to the disk a new salt is created. Then this salt is passed to the hashing function. The values are encrypted using [`PBKDF2HMAC`](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC). The salt is generated for each entry. It is saved in the filename separated by a quadruple underscore. **Don't use quadruple underscore** in your variable names when setting/getting the dictionary, it will break, you can use double and triple underscores. It can be fixed adding a couple of `if` statements inside, but so far I have never had to create a key/value name with `4*_` inside.

The salt is 64 bytes long and it's created using [`secrets.token_urlsafe`](https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe). The salt is created as a string and then encoded to bytes so that it's easier to implement a static salt that you can keep as an environment variable.

### Installation

It is a single self-contained 200 lines-of-code file. The only dependency is `cryptography`. Install it with:

```
pip install cryptography
```

If you don't want to add another dependecy to your project, just copy and pasting the contents of the file to your project. When copying the file you may extend it adding more functionality to it. That functionality may be useful to other users so please consider openning a pull request to add it to the current project.

### Usage

You need to provide a `password` when creating the dictionary object or set an environment variable:

**Creating an environment variable (recommended):**

```bash
export PASS=mypass
```

**When creating the dictionary:**

```python
from fsdict.flightcryptofiledict import FileDict

d = FileDict("newname", password="secretpassword")
```

**Using different data types**

If the dictionary values need to be something different from strings a custom encoder/decoder can be passed. The only condition is that those functions should return a `bytes` object. Examples:

```python
>>> from fsdict.flightcryptofiledict import FileDict
>>> enc_filedict = FileDict("cryptest", password="password")

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

**Compressing to file**

Create a tarfile with the same name as the dictionary.

```python
enc_filedict.compress()
```

You can use a different filename. The `**kwargs` passed to the function will be passed to the tarfile function.

```python
enc_filedict.compress(filename="compressed", compresslevel=7)
```

The command above will generate the file: `compressed.tar.gz`

## `cryptofiledict.py`

More or less the same as before but the salt is static. The salt is parsed as a base64 encoded string. It will be less secure but faster. You can pass the salt as a string when creating a new dictionary. If not, it will try to get it from the environment variables.

## `sqldict.py`

Uses an SQLite database instead of the filesystem. **This module doest NOT implement the encoding/decoding capabilities**. Right now it works as a key-value storage for string-like objects. This is planned for the 0.6.0 release.

## `flightcryptosqldict.py`

Same as `flightcryptofiledict.py`, but uses an sqlite database instead of the file system. It only needs a password and generates a different salt for each item. The salt is stored in a table column and the data in another one.

## Notes for SQLite

Bith sqldict and flightcryptosqldict include an option called `fast`. By default it's set to `True`. This makes SQLite use [WAL mode](https://www.sqlite.org/wal.html) plus a few other optimizations to increase performance.

## Performance

The performance method for each dictionary is calculated like this (adapted to each case):

```
In [1]: from fsdict.cryptosqldict import SQLDict as d

In [2]: dd = d("perf_test", password="mypass")

In [3]: from string import ascii_lowercase as letters

In [4]: from random import choice

In [5]: def randstr(n):
   ...:     return "".join([choice(letters) for _ in range(n)])

In [6]: %%timeit
   ...: dd[randstr(10)] = randstr(100)
```

The SQLite results were done without the speedup optimizations mentioned in the notes above.

**RESULTS:**

`flightcryptosqldict.py`: 67.4 ms ± 2.6 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)

`sqldict.py`: 1.26 ms ± 261 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)

`filedict.py`: 578 µs ± 40.3 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)

`cryptofiledict.py`: 809 µs ± 35.2 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)

`flightcryptofiledict.py`: 68.9 ms ± 1.87 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)

## Meta

Ricardo Ander-Egg Aguilar – [@ricardoanderegg](https://twitter.com/ricardoanderegg) –

- [ricardoanderegg.com](http://ricardoanderegg.com/)
- [github.com/polyrand](https://github.com/polyrand/)
- [linkedin.com/in/ricardoanderegg](http://linkedin.com/in/ricardoanderegg)

Distributed under the MIT license. See `LICENSE` for more information.

## Contributing

1. Fork it (<https://github.com/polyrand/produtils/fork>)
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Create a new Pull Request


## Changelog


* 0.6
    * Make `fsdict.sqldict` store values as blobs instead of text
    * Add doctests
    * Add `fsdict.cryptosqldict`
    * Better PASS/SALT handling when passing environment variables
* 0.5.3
    * Add check_same_thread option to class initialization 
    * Better naming for the modules
    * Update README with missing information
