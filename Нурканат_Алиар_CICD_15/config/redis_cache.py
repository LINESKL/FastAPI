from redis.asyncio import Redis, from_url
from fastapi import Request, Response
from functools import wraps
import pickle
import json
from typing import Optional, Callable, Any
import hashlib

class RedisCache:
    def __init__(self):
        self.redis: Optional[Redis] = None

    async def init_redis(self, url: str):
        self.redis = await from_url(url)
        return self

    async def close(self):
        if self.redis:
            await self.redis.close()

    def cache(self, key_prefix: str = "", ttl: int = 300):
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.redis:
                    raise RuntimeError("Redis not initialized")
                
                cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(json.dumps(kwargs).encode()).hexdigest()}"
                
                cached = await self.redis.get(cache_key)
                if cached:
                    return pickle.loads(cached)
                
                result = await func(*args, **kwargs)
                
                await self.redis.setex(cache_key, ttl, pickle.dumps(result))
                return result
            return wrapper
        return decorator

    async def invalidate(self, prefix: str):
        if not self.redis:
            return
        
        keys = []
        async for key in self.redis.scan_iter(f"{prefix}:*"):
            keys.append(key)
        
        if keys:
            await self.redis.delete(*keys)

redis_cache = RedisCache()