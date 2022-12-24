from abc import abstractmethod
from typing import Optional, Literal

from .tools import RedisSession, RedisConnection


class IRepository:
    @abstractmethod
    async def set(self, key: str, value: bytes, expire: int) -> Literal[True]:
        """
        Set the value at key name to value with expiration
        :param key: Key name
        :param value: Bytes
        :param expire: Expiration time, in seconds
        :return: True
        """

    @abstractmethod
    async def set_nx(self, key: str, value: bytes, expire: int) -> bool:
        """
        Set the value at key name to value with expiration only if key does not exist
        :param key: Key name
        :param value: Bytes
        :param expire: Expiration time, in seconds
        :return: False if key exists, True otherwise
        """

    @abstractmethod
    async def set_many(self, data: dict[str, bytes], expire: int) -> Literal[True]:
        """
        Sets key/values based on a data dict
        :param data: dict with key/value
        :param expire: Expiration time, in seconds
        :return: True
        """

    @abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        """
        Return the value at key name, or None if the key doesn't exist
        :param key: Key name
        :return: Value or None
        """

    @abstractmethod
    async def get_many(self, keys: list[str]) -> list[Optional[bytes]]:
        """
        Returns a list of values
        :param keys: List of keys
        :return: Returns a list of values ordered identically to keys, for every key
        that does not hold a value or does not exist, None is returned
        """

    @abstractmethod
    async def delete(self, key) -> int:
        """
        Delete the key
        :param key: Key name
        :return: Amount of keys removed (1 or 0)
        """

    @abstractmethod
    async def delete_many(self, keys: list[str]) -> int:
        """
        Delete keys specified by keys list
        :param keys: List of keys
        :return: Amount of keys removed
        """

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys specified by pattern

        Supported patterns:
        - h?llo matches hello, hallo and hxllo
        - h*llo matches hllo and heeeello
        - h[ae]llo matches hello and hallo, but not hillo
        - h[^e]llo matches hallo, hbllo, ... but not hello
        - h[a-b]llo matches hallo and hbllo

        :param pattern: Pattern string
        :return: Amount of keys removed
        """


class RedisCacheRepository(IRepository):
    def __init__(self, dsn: str):
        self.session = RedisSession(
            connection=RedisConnection(dsn=dsn).connection,
        )

    async def set(self, key: str, value: bytes, expire: int) -> Literal[True]:
        async with self.session as session:
            await session.set(name=key, value=value, ex=expire)
        return True

    async def set_nx(self, key: str, value: bytes, expire: int) -> bool:
        async with self.session as session:
            result = await session.set(name=key, value=value, ex=expire, nx=True)
        return result is not None

    async def set_many(self, data: dict[str, bytes], expire: int) -> Literal[True]:
        async with self.session as session:
            async with session.pipeline(transaction=True) as pipe:
                await pipe.mset(data)  # type: ignore
                for key in data.keys():
                    await pipe.expire(name=key, time=expire)
                await pipe.execute()
        return True

    async def get(self, key: str) -> Optional[bytes]:
        async with self.session as session:
            return await session.get(name=key)

    async def get_many(self, keys: list[str]) -> list[Optional[bytes]]:
        async with self.session as session:
            return await session.mget(keys=keys)

    async def delete(self, key) -> int:
        async with self.session as session:
            return await session.delete(key)

    async def delete_many(self, keys: list[str]) -> int:
        async with self.session as session:
            return await session.delete(*keys)

    async def delete_pattern(self, pattern: str) -> int:
        chunk_size: int = 1000
        removed_keys: int = 0
        async with self.session as session:
            cursor: int = 0
            while True:
                cursor, keys = await session.scan(cursor, match=pattern, count=chunk_size)
                if keys:
                    removed_keys += await session.delete(*keys)
                if cursor == 0:
                    break
        return removed_keys
