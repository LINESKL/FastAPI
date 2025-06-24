from aioredis import Redis, create_redis_pool
from fastapi import Request, Response
from fastapi.concurrency import run_in_threadpool
from functools import wraps
import pickle
import json
from typing import Optional, Callable, Any
import hashlib

class RedisCache:
    def __init__(self):
        self.redis: Optional[Redis] = None

    async def init_redis(self):
        self.redis = await create_redis_pool("redis://redis:6379/0")
        return self

    async def close(self):
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()

    def cache(
        self,
        key_prefix: str = "",
        ttl: int = 300,
        ignore_args: list = None,
        serializer: str = "pickle"
    ):
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.redis:
                    await self.init_redis()

                cache_kwargs = kwargs.copy()
                if ignore_args:
                    for arg in ignore_args:
                        cache_kwargs.pop(arg, None)

                cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(json.dumps(cache_kwargs).encode()).hexdigest()}"

                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    if serializer == "json":
                        return json.loads(cached_data)
                    return pickle.loads(cached_data)
                result = await func(*args, **kwargs)

                if result is not None:
                    if serializer == "json":
                        await self.redis.setex(cache_key, ttl, json.dumps(result))
                    else:
                        await self.redis.setex(cache_key, ttl, pickle.dumps(result))

                return result
            return wrapper
        return decorator

    async def invalidate_by_prefix(self, prefix: str):
        if not self.redis:
            await self.init_redis()

        keys = []
        async for key in self.redis.scan_iter(f"{prefix}:*"):
            keys.append(key)
        
        if keys:
            await self.redis.delete(*keys)

redis_cache = RedisCache()