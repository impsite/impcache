class CacheError(Exception):
    pass


class JsonEncodeError(CacheError):
    pass


class JsonDecodeError(CacheError):
    pass
