# impcache
*Simple async cache with high performance. Easy to use & ready for production.*

[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://github.com/impsite/impcache/blob/main/LICENSE)
[![python](https://img.shields.io/badge/Python-3.11-brightgreen.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![mypy](https://img.shields.io/badge/mypy-checked-brightgreen.svg?style=flat)](http://mypy-lang.org/)
[![Code coverage](https://img.shields.io/badge/code%20coverage-100%25-brightgreen)](https://github.com/PyCQA/pylint)
[![PyPI](https://img.shields.io/pypi/v/impcache?color=brightgreen&label=pypi%20package)](https://pypi.python.org/pypi/impcache/)
[![Linting: pylint](https://img.shields.io/badge/linting-pylint-brightgreen)](https://github.com/PyCQA/pylint)
[![Code style: flake8](https://img.shields.io/badge/code%20style-flake8-brightgreen.svg)](https://github.com/psf/black)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[![Tests](https://github.com/impsite/impcache/actions/workflows/tests.yaml/badge.svg?branch=main&event=push)](https://github.com/impsite/impcache/actions/workflows/tests.yaml)

## Usage

### Cache backend
impcache uses [Redis](https://redis.io) as a cache backend. To begin you’ll need a Redis server 
running either locally or on a remote machine.

### Dependencies
Under the hood, impcache uses async [redis-py](https://pypi.org/project/redis/) with hiredis support 
for faster performance. For serialization and deserialization we're using 
[orjson](https://pypi.org/project/orjson/) - the fastest Python library for JSON 
([benchmarks](https://github.com/ijl/orjson#performance)).

### Install

To install a wheel from PyPI:
```sh
pip install --upgrade impcache
```

### Quickstart

This is an example of setting and getting key from cache:

```python
import asyncio

from impcache import Cache, RedisCacheRepository


async def main():
    cache = Cache(
        repository=RedisCacheRepository(dsn="redis://redis:6379/0"),
        key_prefix="cache",
        version=1,
    )
    await cache.set("key", "value", expire=100)
    result = await cache.get("key")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

### Cache arguments
Cache can be configured to control caching behavior. These settings are provided as arguments for the Cache class. 
Valid arguments are as follows:
- **repository**: Only _RedisCacheRepository_ supported at the moment.
- **key_prefix**: A string that will be automatically prepended to all cache keys. 
See the [cache key prefixing](#cache-key-prefixing) for more information.
- **version**: The default version number generated for cache keys (can be string or integer). 
See the [cache versioning](#cache-versioning) for more information.

### Cache key prefixing
To prevent cache key collision, impcache provides the ability to prefix all cache keys. When a particular cache key 
is saved or retrieved, impcache will automatically prefix the cache key with the value of the **key_prefix** argument.

### Cache versioning
When you change running code that uses cached values, you may need to purge any existing cached values. 
The easiest way to do this is to use the version identifier, specified using the **version** argument for the Cache 
class or on primitive cache functions level.

By default, any key automatically includes the version "1".

For example:

```python
>>> # Set version 2 of a cache key
>>> await cache.set("key", "value", expire=100, version=2)
>>> # Get the default version (assuming version=1)
>>> await cache.get("key")
None
# Get version 2 of the same key
>>> await cache.get("key", version=2)
value
```

### Cache key format
As described in the previous two sections, the cache key provided by a user is not used verbatim – it is combined 
with the cache prefix and key version to provide a final cache key. By default, the three parts are joined 
using colons to produce a final string:
```python
f"{key_prefix}:{key_version}:{key}"
```

### Cache API
#### set(key: str, value: JSON, expire: int, version: Optional[int | str] = None) -> Literal[True]:

Sets the value at key name to value with expiration.
```python
>>> await cache.set("key", "value", expire=100)
True
```

#### set_nx(key: str, value: JSON, expire: int, version: Optional[int | str] = None) -> bool:

Sets the value at key name to value with expiration only if key does not exist. 
Returns False if key exists, True otherwise.

```python
>>> await cache.set_nx("key", "value", expire=100)
True
>>> await cache.set_nx("key", "value", expire=100)
False
```

#### set_many(data: dict[str, JSON], expire: int, version: Optional[int | str] = None) -> Literal[True]:

Sets key/values based on a dictionary of key-value pairs.

```python
>>> await cache.set_many({"key1": "value1", "key2": "value2"}, expire=100)
True
```

#### get(key: str, version: Optional[int | str] = None) -> Optional[JSON]:

Returns the value at key name, or None if the key doesn't exist.

```python
>>> await cache.set("key", "value", expire=100)
True
>>> await cache.get("key")
value
>>> await cache.get("non-existing-key")
None
```

#### get_many(keys: list[str], version: Optional[int | str] = None) -> list[Optional[JSON]]:

Returns a list of values ordered identically to keys, for every key that does not hold a value or does not exist, 
None is returned.

```python
>>> await cache.set_many({"key1": "value1", "key2": "value2"}, expire=100)
True
>>> await cache.get_many(["key1", "non-existing-key", "key2"])
["value1", None, "value2"]
```

#### delete(key: str, version: Optional[int | str] = None) -> int:

Deletes the key, returns the number of keys removed.

```python
>>> await cache.set("key", "value", expire=100)
True
>>> await cache.delete("key")
1
```

#### delete_many(keys: list[str], version: Optional[int | str] = None) -> int:

Deletes keys specified by keys list, returns the number of keys removed.

```python
>>> await cache.set_many({"key1": "value1", "key2": "value2"}, expire=100)
True
>>> await cache.delete_many(["key1", "non-existing-key", "key2"])
2
```

#### delete_pattern(pattern: str, version: Optional[int | str] = None) -> int:

Deletes keys specified by pattern, returns the number of keys removed.

Supported patterns:
- h?llo matches hello, hallo and hxllo
- h*llo matches hllo and heeeello
- h[ae]llo matches hello and hallo, but not hillo
- h[^e]llo matches hallo, hbllo, ... but not hello
- h[a-b]llo matches hallo and hbllo

```python
>>> await cache.set_many({"hllo": "value1", "heeeello": "value2"}, expire=100)
True
>>> # h*llo matches hllo and heeeello
>>> await cache.delete_pattern("h*llo")
2
```

## Examples

### FastAPI

All dependencies should be async to avoid running in the external threadpool, even if they just return an instance. 
See the [FastAPI dependencies](https://fastapi.tiangolo.com/async/#dependencies) documentation for more information.

depencies.py:
```python
from impcache import Cache, ICache, RedisCacheRepository

async def cache_dependency() -> ICache:
    return Cache(
        repository=RedisCacheRepository(dsn="redis://redis:6379/0"),
        key_prefix="cache",
        version=1,
    )
```

api.py:
```python
from fastapi import APIRouter, Depends
from impcache import ICache

from .depencies import cache_dependency

router = APIRouter()


@router.get("/test-cache")
async def test_cache(
        cache: ICache = Depends(cache_dependency),
):
    await cache.set("key", "value", expire=100)
    cached_value = await cache.get("key")
    return {"cached_value": cached_value}
```

## License
This project is licensed under the terms of the MIT license.
