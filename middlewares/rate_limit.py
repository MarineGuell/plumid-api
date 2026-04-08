# api/middlewares/rate_limit.py
from __future__ import annotations
import asyncio
import json
import time
from typing import Optional, Tuple
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse
from starlette.datastructures import Headers

class _MemoryBucket:
    """Token-bucket en mémoire (thread-safe via lock asyncio)."""
    def __init__(self):
        self._store = {}  # key -> (tokens, last_ts)
        self._lock = asyncio.Lock()

    async def take(self, key: str, rate_per_sec: float, burst: int, cost: int = 1) -> Tuple[bool, int]:
        now = time.monotonic()
        async with self._lock:
            tokens, last_ts = self._store.get(key, (burst, now))
            # refill
            tokens = min(burst, tokens + (now - last_ts) * rate_per_sec)
            allowed = tokens >= cost
            if allowed:
                tokens -= cost
            self._store[key] = (tokens, now)
            # Retry-After (arrondi)
            retry_after = 0
            if not allowed:
                needed = cost - tokens
                retry_after = max(0, int(needed / rate_per_sec))
            return allowed, retry_after

class _RedisBucket:
    """Implémentation Redis optionnelle (si redis_url est présent)."""
    def __init__(self, redis):
        self.redis = redis

    async def take(self, key: str, rate_per_sec: float, burst: int, cost: int = 1) -> Tuple[bool, int]:
        # script lua token-bucket (atomique)
        script = """
        local key=KEYS[1]
        local now=tonumber(ARGV[1])
        local rate=tonumber(ARGV[2])
        local burst=tonumber(ARGV[3])
        local cost=tonumber(ARGV[4])
        local data=redis.call('GET', key)
        local tokens, last
        if not data then
            tokens=burst
            last=now
        else
            local obj=cjson.decode(data)
            tokens=obj.tokens
            last=obj.last
        end
        tokens = math.min(burst, tokens + (now-last)*rate)
        local allowed = tokens >= cost
        if allowed then
            tokens = tokens - cost
        end
        local out = cjson.encode({tokens=tokens, last=now})
        redis.call('SET', key, out)
        if not allowed then
            local needed = cost - tokens
            local retry_after = math.max(0, math.floor(needed / rate))
            return {0, retry_after}
        end
        return {1, 0}
        """
        res = await self.redis.eval(script, keys=[f"ratelimit:{key}"],
                                    args=[time.monotonic(), rate_per_sec, burst, cost])
        allowed = bool(res[0] == 1)
        retry_after = int(res[1])
        return allowed, retry_after

class RateLimitMiddleware:
    """
    Limiteur global configurable. Clé = (IP, API-Key, route).
    - Défauts: settings.rl_default_per_min / rl_burst
    - /auth/login : settings.rl_login_per_min
    """
    def __init__(self, app: ASGIApp, settings, redis=None):
        self.app = app
        self.settings = settings
        self.backend = _RedisBucket(redis) if redis else _MemoryBucket()

    def _route_bucket(self, path: str) -> int:
        if path.startswith("/auth/login"):
            return self.settings.rl_login_per_min
        return self.settings.rl_default_per_min

    def _key(self, scope: Scope) -> str:
        headers = Headers(scope=scope)
        ip = (scope.get("client") or ("0.0.0.0", 0))[0]
        apikey = headers.get("authorization", "").split()[-1] if headers.get("authorization") else "-"
        path = scope.get("path", "/")
        return f"{ip}:{apikey}:{path}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # pas de limite pour /health
        path = scope.get("path", "")
        if path.startswith("/health"):
            await self.app(scope, receive, send)
            return

        per_min = self._route_bucket(path)
        rate_per_sec = per_min / float(self.settings.rl_window_seconds)
        burst = int(self.settings.rl_burst)
        key = self._key(scope)

        allowed, retry_after = await self.backend.take(key, rate_per_sec, burst, cost=1)
        if not allowed:
            payload = {"detail": "Too Many Requests", "retry_after": retry_after}
            await JSONResponse(payload, status_code=429, headers={
                "Retry-After": str(retry_after)
            })(scope, receive, send)
            return

        await self.app(scope, receive, send)
