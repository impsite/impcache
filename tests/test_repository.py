import os
from uuid import uuid4

import pytest
import redis.asyncio as aioredis
from impcache import RedisCacheRepository

REDIS_DSN = os.getenv("REDIS_DSN")


class TestRedisCacheRepository:

    @staticmethod
    def get_key() -> str:
        return f"test_{uuid4()}"

    @pytest.fixture
    async def redis_repository(self):
        repository = RedisCacheRepository(dsn=REDIS_DSN)
        yield repository
        await repository.session._session.connection_pool.disconnect()

    @pytest.fixture
    async def redis_connection(self):
        connection = aioredis.from_url(REDIS_DSN)
        yield connection
        await connection.close(close_connection_pool=True)

    @pytest.mark.anyio
    async def test_can_set(self, redis_repository, redis_connection):
        key = self.get_key()
        result = await redis_repository.set(key, b"test-set-value", expire=100)
        assert result is True
        assert await redis_connection.get(key) == b"test-set-value"
        assert await redis_connection.ttl(key) == 100
        await redis_connection.delete(key)

    @pytest.mark.anyio
    async def test_can_set_nx(self, redis_repository, redis_connection):
        key = self.get_key()
        result1 = await redis_repository.set_nx(key, b"test-nx-value1", expire=100)
        result2 = await redis_repository.set_nx(key, b"test-nx-value2", expire=200)
        assert result1 is True
        assert result2 is False
        assert await redis_connection.get(key) == b"test-nx-value1"
        assert await redis_connection.ttl(key) == 100
        await redis_connection.delete(key)

    @pytest.mark.anyio
    async def test_can_set_many(self, redis_repository, redis_connection):
        key1 = self.get_key()
        key2 = self.get_key()
        data = {
            key1: b"test-many-value1",
            key2: b"test-many-value2",
        }
        result = await redis_repository.set_many(data, expire=100)
        assert result is True
        assert await redis_connection.get(key1) == b"test-many-value1"
        assert await redis_connection.ttl(key1) == 100
        assert await redis_connection.get(key2) == b"test-many-value2"
        assert await redis_connection.ttl(key2) == 100
        await redis_connection.delete(key1, key2)

    @pytest.mark.anyio
    async def test_can_get(self, redis_repository, redis_connection):
        key = self.get_key()
        await redis_connection.set(key, b"test-get-value", ex=100)
        assert await redis_repository.get(key) == b"test-get-value"
        assert await redis_repository.get("non-existing-key") is None
        await redis_connection.delete(key)

    @pytest.mark.anyio
    async def test_can_get_many(self, redis_repository, redis_connection):
        key1 = self.get_key()
        key2 = self.get_key()
        await redis_connection.set(key1, b"test-get-many-value1", ex=100)
        await redis_connection.set(key2, b"test-get-many-value2", ex=100)
        assert await redis_repository.get_many([key1, "non-existing-key", key2]) == [
            b"test-get-many-value1",
            None,
            b"test-get-many-value2"
        ]
        await redis_connection.delete(key1, key2)

    @pytest.mark.anyio
    async def test_can_delete(self, redis_repository, redis_connection):
        key = self.get_key()
        await redis_connection.set(key, b"test-delete-value", ex=100)
        assert await redis_repository.delete(key) == 1
        assert await redis_repository.delete("non-existing-key") == 0
        assert await redis_repository.get(key) is None

    @pytest.mark.anyio
    async def test_can_delete_many(self, redis_repository, redis_connection):
        key1 = self.get_key()
        key2 = self.get_key()
        await redis_connection.set(key1, b"test-delete-many-value1", ex=100)
        await redis_connection.set(key2, b"test-delete-many-value2", ex=100)
        assert await redis_repository.delete_many([key1, "non-existing-key", key2]) == 2
        assert await redis_repository.get(key1) is None
        assert await redis_repository.get(key2) is None

    @pytest.mark.anyio
    async def test_can_delete_pattern_1(self, redis_repository, redis_connection):
        # h?llo matches hello, hallo and hxllo
        prefix = self.get_key()
        key1 = prefix + "hello"
        key2 = prefix + "hallo"
        key3 = prefix + "hxllo"
        key4 = prefix + "not-a-pattern"
        await redis_connection.set(key1, b"test-delete-pattern-1-value1", ex=100)
        await redis_connection.set(key2, b"test-delete-pattern-1-value2", ex=100)
        await redis_connection.set(key3, b"test-delete-pattern-1-value3", ex=100)
        await redis_connection.set(key4, b"test-delete-pattern-1-value4", ex=100)
        pattern = prefix + "h?llo"
        assert await redis_repository.delete_pattern(pattern) == 3
        assert await redis_repository.get(key1) is None
        assert await redis_repository.get(key2) is None
        assert await redis_repository.get(key3) is None
        assert await redis_repository.get(key4) == b"test-delete-pattern-1-value4"
        await redis_connection.delete(key4)

    @pytest.mark.anyio
    async def test_can_delete_pattern_2(self, redis_repository, redis_connection):
        # h*llo matches hllo and heeeello
        prefix = self.get_key()
        key1 = prefix + "hllo"
        key2 = prefix + "heeeello"
        key3 = prefix + "not-a-pattern"
        await redis_connection.set(key1, b"test-delete-pattern-2-value1", ex=100)
        await redis_connection.set(key2, b"test-delete-pattern-2-value2", ex=100)
        await redis_connection.set(key3, b"test-delete-pattern-2-value3", ex=100)
        pattern = prefix + "h*llo"
        assert await redis_repository.delete_pattern(pattern) == 2
        assert await redis_repository.get(key1) is None
        assert await redis_repository.get(key2) is None
        assert await redis_repository.get(key3) == b"test-delete-pattern-2-value3"
        await redis_connection.delete(key3)

    @pytest.mark.anyio
    async def test_can_delete_pattern_3(self, redis_repository, redis_connection):
        # h[ae]llo matches hello and hallo, but not hillo
        prefix = self.get_key()
        key1 = prefix + "hello"
        key2 = prefix + "hallo"
        key3 = prefix + "hillo"
        await redis_connection.set(key1, b"test-delete-pattern-3-value1", ex=100)
        await redis_connection.set(key2, b"test-delete-pattern-3-value2", ex=100)
        await redis_connection.set(key3, b"test-delete-pattern-3-value3", ex=100)
        pattern = prefix + "h[ae]llo"
        assert await redis_repository.delete_pattern(pattern) == 2
        assert await redis_repository.get(key1) is None
        assert await redis_repository.get(key2) is None
        assert await redis_repository.get(key3) == b"test-delete-pattern-3-value3"
        await redis_connection.delete(key3)

    @pytest.mark.anyio
    async def test_can_delete_pattern_4(self, redis_repository, redis_connection):
        # h[^e]llo matches hallo, hbllo, ... but not hello
        prefix = self.get_key()
        key1 = prefix + "hallo"
        key2 = prefix + "hbllo"
        key3 = prefix + "hello"
        await redis_connection.set(key1, b"test-delete-pattern-4-value1", ex=100)
        await redis_connection.set(key2, b"test-delete-pattern-4-value2", ex=100)
        await redis_connection.set(key3, b"test-delete-pattern-4-value3", ex=100)
        pattern = prefix + "h[^e]llo"
        assert await redis_repository.delete_pattern(pattern) == 2
        assert await redis_repository.get(key1) is None
        assert await redis_repository.get(key2) is None
        assert await redis_repository.get(key3) == b"test-delete-pattern-4-value3"
        await redis_connection.delete(key3)

    @pytest.mark.anyio
    async def test_can_delete_pattern_5(self, redis_repository, redis_connection):
        # h[a-b]llo matches hallo and hbllo, but not hello
        prefix = self.get_key()
        key1 = prefix + "hallo"
        key2 = prefix + "hbllo"
        key3 = prefix + "hello"
        await redis_connection.set(key1, b"test-delete-pattern-5-value1", ex=100)
        await redis_connection.set(key2, b"test-delete-pattern-5-value2", ex=100)
        await redis_connection.set(key3, b"test-delete-pattern-5-value3", ex=100)
        pattern = prefix + "h[a-b]llo"
        assert await redis_repository.delete_pattern(pattern) == 2
        assert await redis_repository.get(key1) is None
        assert await redis_repository.get(key2) is None
        assert await redis_repository.get(key3) == b"test-delete-pattern-5-value3"
        await redis_connection.delete(key3)
