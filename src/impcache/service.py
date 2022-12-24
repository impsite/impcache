from abc import ABC, abstractmethod
from typing import TypeAlias, Optional, Literal
from uuid import UUID

import orjson

from .exceptions import JsonDecodeError, JsonEncodeError
from .repository import IRepository

JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | UUID | None


class ICache(ABC):
    def __init__(self, key_prefix: str = "cache", version: int | str = 1):
        self.key_prefix = key_prefix
        self.version = version

    def make_key(self, key: str, version: Optional[int | str] = None):
        key_version = version if version is not None else self.version
        return f"{self.key_prefix}:{key_version}:{key}"

    @abstractmethod
    async def set(self, key: str, value: JSON, expire: int, version: Optional[int | str] = None) -> Literal[True]:
        """
        Sets the value at key name to value with expiration
        :param key: Key name
        :param value: JSON-serializable data
        :param expire: Expiration time, in seconds
        :param version: Optional cache version
        :return: True
        """

    @abstractmethod
    async def set_nx(self, key: str, value: JSON, expire: int, version: Optional[int | str] = None) -> bool:
        """
        Sets the value at key name to value with expiration only if key does not exist
        :param key: Key name
        :param value: JSON-serializable data
        :param expire: Expiration time, in seconds
        :param version: Optional cache version
        :return: False if key exists, True otherwise
        """

    @abstractmethod
    async def set_many(self, data: dict[str, JSON], expire: int, version: Optional[int | str] = None) -> Literal[True]:
        """
        Sets key/values based on a data dict
        :param data: dict with key/value
        :param expire: Expiration time, in seconds
        :param version: Optional cache version
        :return: True
        """

    @abstractmethod
    async def get(self, key: str, version: Optional[int | str] = None) -> Optional[JSON]:
        """
        Returns the value at key name, or None if the key doesn't exist
        :param key: Key name
        :param version: Optional cache version
        :return: Value or None
        """

    @abstractmethod
    async def get_many(self, keys: list[str], version: Optional[int | str] = None) -> list[Optional[JSON]]:
        """
        Returns a list of values
        :param keys: List of keys
        :param version: Optional cache version
        :return: Returns a list of values ordered identically to keys, for every key
        that does not hold a value or does not exist, None is returned
        """

    @abstractmethod
    async def delete(self, key: str, version: Optional[int | str] = None) -> int:
        """
        Deletes the key
        :param key: Key name
        :param version: Optional cache version
        :return: Number of keys removed (1 or 0)
        """

    @abstractmethod
    async def delete_many(self, keys: list[str], version: Optional[int | str] = None) -> int:
        """
        Deletes keys specified by keys list
        :param keys: List of keys
        :param version: Optional cache version
        :return: Number of keys removed
        """

    @abstractmethod
    async def delete_pattern(self, pattern: str, version: Optional[int | str] = None) -> int:
        """
        Deletes keys specified by pattern

        Supported patterns:
        - h?llo matches hello, hallo and hxllo
        - h*llo matches hllo and heeeello
        - h[ae]llo matches hello and hallo, but not hillo
        - h[^e]llo matches hallo, hbllo, ... but not hello
        - h[a-b]llo matches hallo and hbllo

        :param pattern: Pattern string
        :param version: Optional cache version
        :return: Number of keys removed
        """


class JsonSerializerMixin:
    @staticmethod
    def loads(payload: bytes) -> JSON:
        try:
            json = orjson.loads(payload)
        except orjson.JSONDecodeError as exc_info:
            raise JsonDecodeError from exc_info
        return json

    @staticmethod
    def dumps(json: JSON) -> bytes:
        try:
            result = orjson.dumps(json)
        except TypeError as exc_info:
            raise JsonEncodeError from exc_info
        return result


class Cache(JsonSerializerMixin, ICache):
    def __init__(
        self,
        *args,
        repository: IRepository,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._repository = repository

    async def set(self, key: str, value: JSON, expire: int, version: Optional[int | str] = None) -> Literal[True]:
        return await self._repository.set(key=self.make_key(key, version), value=self.dumps(value), expire=expire)

    async def set_nx(self, key: str, value: JSON, expire: int, version: Optional[int | str] = None) -> bool:
        return await self._repository.set_nx(key=self.make_key(key, version), value=self.dumps(value), expire=expire)

    async def set_many(self, data: dict[str, JSON], expire: int, version: Optional[int | str] = None) -> Literal[True]:
        _data = {}
        for key, value in data.items():
            _data[self.make_key(key, version)] = self.dumps(value)
        return await self._repository.set_many(data=_data, expire=expire)

    async def get(self, key: str, version: Optional[int | str] = None) -> Optional[JSON]:
        raw = await self._repository.get(key=self.make_key(key, version))
        return self.loads(raw) if raw is not None else None

    async def get_many(self, keys: list[str], version: Optional[int | str] = None) -> list[Optional[JSON]]:
        data = await self._repository.get_many(keys=[self.make_key(key, version) for key in keys])
        return [self.loads(value) if value is not None else None for value in data]

    async def delete(self, key: str, version: Optional[int | str] = None) -> int:
        return await self._repository.delete(key=self.make_key(key, version))

    async def delete_many(self, keys: list[str], version: Optional[int | str] = None) -> int:
        return await self._repository.delete_many(keys=[self.make_key(key, version) for key in keys])

    async def delete_pattern(self, pattern: str, version: Optional[int | str] = None) -> int:
        return await self._repository.delete_pattern(pattern=self.make_key(pattern, version))
