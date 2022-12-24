import decimal
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from impcache import Cache, JsonEncodeError, JsonDecodeError
from impcache.repository import IRepository
from impcache.service import JsonSerializerMixin


class TestJsonSerializer:
    @pytest.fixture
    def serializer(self):
        return JsonSerializerMixin()

    def test_can_dumps(self, serializer):
        assert serializer.dumps({"key": "value"}) == b'{"key":"value"}'

    def test_can_loads(self, serializer):
        assert serializer.loads(b'{"key":"value"}') == {"key": "value"}

    def test_raises_error_on_dumps(self, serializer):
        with pytest.raises(JsonEncodeError):
            serializer.dumps(decimal.Decimal("0.01"))

    def test_raises_error_on_loads(self, serializer):
        with pytest.raises(JsonDecodeError):
            serializer.loads("invalid data")


class TestCacheService:

    @pytest.fixture
    def repository(self):
        return Mock(spec=IRepository)

    @pytest.fixture
    def cache(self, repository):
        return Cache(repository=repository)

    def test_key_generation(self, repository):
        cache_service1 = Cache(repository=repository)
        cache_service2 = Cache(repository=repository, key_prefix="test_key_prefix")
        cache_service3 = Cache(repository=repository, key_prefix="test_key_prefix", version=2)
        cache_service4 = Cache(repository=repository, key_prefix="test_key_prefix", version="v2.3.4")
        assert cache_service1.make_key("test_key") == "cache:1:test_key"
        assert cache_service2.make_key("test_key") == "test_key_prefix:1:test_key"
        assert cache_service3.make_key("test_key") == "test_key_prefix:2:test_key"
        assert cache_service4.make_key("test_key") == "test_key_prefix:v2.3.4:test_key"

    @pytest.mark.anyio
    async def test_can_set(self, cache):
        await cache.set("key", "value", expire=100)
        cache._repository.set.assert_called_once_with(key="cache:1:key", value=b'"value"', expire=100)

    @pytest.mark.anyio
    async def test_can_set_with_version(self, cache):
        await cache.set("key", "value", expire=100, version=8)
        cache._repository.set.assert_called_once_with(key="cache:8:key", value=b'"value"', expire=100)

    @pytest.mark.anyio
    async def test_can_set_nx(self, cache):
        await cache.set_nx("key", "value", expire=100)
        cache._repository.set_nx.assert_called_once_with(key="cache:1:key", value=b'"value"', expire=100)

    @pytest.mark.anyio
    async def test_can_set_nx_with_version(self, cache):
        await cache.set_nx("key", "value", expire=100, version="v4.2.3")
        cache._repository.set_nx.assert_called_once_with(key="cache:v4.2.3:key", value=b'"value"', expire=100)

    @pytest.mark.anyio
    async def test_can_set_many(self, cache):
        data = {
            "key1": "value",  # str
            "key2": 222,  # int
            "key3": 1.1,  # float
            "key4": True,  # bool
            "key5": UUID("32bef872-f78b-4f18-82d2-e3b9376c738e"),  # UUID
            "key6": None,  # None
            "key7": {"key": "value"},  # dict
            "key8": [1, 2, "3"],  # list
        }
        await cache.set_many(data, expire=100)
        cache._repository.set_many.assert_called_once_with(data={
            'cache:1:key1': b'"value"',
            'cache:1:key2': b'222',
            'cache:1:key3': b'1.1',
            'cache:1:key4': b'true',
            'cache:1:key5': b'"32bef872-f78b-4f18-82d2-e3b9376c738e"',
            'cache:1:key6': b'null',
            'cache:1:key7': b'{"key":"value"}',
            'cache:1:key8': b'[1,2,"3"]',
        }, expire=100)

    @pytest.mark.anyio
    async def test_can_set_many_with_version(self, cache):
        data = {
            "key1": "value",  # str
            "key2": 222,  # int
            "key3": 1.1,  # float
            "key4": True,  # bool
            "key5": UUID("32bef872-f78b-4f18-82d2-e3b9376c738e"),  # UUID
            "key6": None,  # None
            "key7": {"key": "value"},  # dict
            "key8": [1, 2, "3"],  # list
        }
        await cache.set_many(data, expire=100, version="v5.7.1")
        cache._repository.set_many.assert_called_once_with(data={
            'cache:v5.7.1:key1': b'"value"',
            'cache:v5.7.1:key2': b'222',
            'cache:v5.7.1:key3': b'1.1',
            'cache:v5.7.1:key4': b'true',
            'cache:v5.7.1:key5': b'"32bef872-f78b-4f18-82d2-e3b9376c738e"',
            'cache:v5.7.1:key6': b'null',
            'cache:v5.7.1:key7': b'{"key":"value"}',
            'cache:v5.7.1:key8': b'[1,2,"3"]',
        }, expire=100)

    @pytest.mark.anyio
    async def test_can_get(self, cache):
        with patch.object(cache._repository, "get", return_value=b'{"key":"value"}') as repository_get_mock:
            result = await cache.get("key")
            repository_get_mock.assert_called_once_with(key="cache:1:key")
        assert result == {"key": "value"}

    @pytest.mark.anyio
    async def test_can_get_with_version(self, cache):
        with patch.object(cache._repository, "get", return_value=b'{"key":"value"}') as repository_get_mock:
            result = await cache.get("key", version=2)
            repository_get_mock.assert_called_once_with(key="cache:2:key")
        assert result == {"key": "value"}

    @pytest.mark.anyio
    async def test_can_get_many(self, cache):
        return_value = [b'"value1"', None, b'"value2"']
        with patch.object(cache._repository, "get_many", return_value=return_value) as repository_get_many_mock:
            result = await cache.get_many(["key1", "non-existing-key", "key2"])
            repository_get_many_mock.assert_called_once_with(
                keys=['cache:1:key1', 'cache:1:non-existing-key', 'cache:1:key2']
            )
        assert result == ["value1", None, "value2"]

    @pytest.mark.anyio
    async def test_can_get_many_with_version(self, cache):
        return_value = [b'"value1"', None, b'"value2"']
        with patch.object(cache._repository, "get_many", return_value=return_value) as repository_get_many_mock:
            result = await cache.get_many(["key1", "non-existing-key", "key2"], version=3)
            repository_get_many_mock.assert_called_once_with(
                keys=['cache:3:key1', 'cache:3:non-existing-key', 'cache:3:key2']
            )
        assert result == ["value1", None, "value2"]

    @pytest.mark.anyio
    async def test_can_delete(self, cache):
        with patch.object(cache._repository, "delete", return_value=1) as repository_delete_mock:
            result = await cache.delete("key1")
            repository_delete_mock.assert_called_once_with(key="cache:1:key1")
        assert result == 1

    @pytest.mark.anyio
    async def test_can_delete_with_version(self, cache):
        with patch.object(cache._repository, "delete", return_value=1) as repository_delete_mock:
            result = await cache.delete("key1", version="v2.3.4")
            repository_delete_mock.assert_called_once_with(key="cache:v2.3.4:key1")
        assert result == 1

    @pytest.mark.anyio
    async def test_can_delete_many(self, cache):
        with patch.object(cache._repository, "delete_many", return_value=2) as repository_delete_many_mock:
            result = await cache.delete_many(["key1", "key2"])
            repository_delete_many_mock.assert_called_once_with(keys=['cache:1:key1', 'cache:1:key2'])
        assert result == 2

    @pytest.mark.anyio
    async def test_can_delete_many_with_version(self, cache):
        with patch.object(cache._repository, "delete_many", return_value=2) as repository_delete_many_mock:
            result = await cache.delete_many(["key1", "key2"], version=4)
            repository_delete_many_mock.assert_called_once_with(keys=['cache:4:key1', 'cache:4:key2'])
        assert result == 2

    @pytest.mark.anyio
    async def test_can_delete_pattern(self, cache):
        with patch.object(cache._repository, "delete_pattern", return_value=2) as repository_delete_pattern_mock:
            result = await cache.delete_pattern(pattern="h*llo")
            repository_delete_pattern_mock.assert_called_once_with(pattern="cache:1:h*llo")
        assert result == 2

    @pytest.mark.anyio
    async def test_can_delete_pattern_with_version(self, cache):
        with patch.object(cache._repository, "delete_pattern", return_value=2) as repository_delete_pattern_mock:
            result = await cache.delete_pattern(pattern="h*llo", version=17)
            repository_delete_pattern_mock.assert_called_once_with(pattern="cache:17:h*llo")
        assert result == 2
