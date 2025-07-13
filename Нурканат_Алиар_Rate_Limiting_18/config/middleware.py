from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from redis.asyncio import Redis, from_url
from config.settings import settings
import time
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis = None

    async def get_redis(self):
        if self.redis is None:
            self.redis = from_url(str(settings.REDIS_URL), max_connections=settings.REDIS_POOL_SIZE)
        return self.redis

    async def dispatch(self, request: Request, call_next):
        try:
            redis = await self.get_redis()
            client_ip = request.client.host
            current_time = int(time.time())
            key = f"rate_limit:{client_ip}"

            data = await redis.hgetall(key)
            if not data:
                await redis.hset(key, mapping={"count": 1, "timestamp": current_time})
                await redis.expire(key, settings.RATE_LIMIT_WINDOW)
                return await call_next(request)

            count = int(data.get("count", 0))
            timestamp = int(data.get("timestamp", 0))

            if current_time - timestamp > settings.RATE_LIMIT_WINDOW:
                await redis.hset(key, mapping={"count": 1, "timestamp": current_time})
                return await call_next(request)

            if count >= settings.RATE_LIMIT_REQUESTS:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."}
                )

            await redis.hincrby(key, "count", 1)
            
            return await call_next(request)
        except Exception as e:
            # If Redis is unavailable, allow the request to proceed without rate limiting
            print(f"Redis error in rate limiter: {e}")
            return await call_next(request)