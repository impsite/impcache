import redis.asyncio as aioredis
from redis.asyncio.client import Redis


class SingletonMeta(type):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class RedisConnection(metaclass=SingletonMeta):
    def __init__(self, dsn: str):
        self.connection = aioredis.from_url(dsn)


class RedisSession:
    def __init__(self, connection: Redis):
        self._session = connection

    async def __aenter__(self) -> Redis:
        return self._session

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._session.close()
