# api/security/antireplay.py
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import time
from typing import Optional
from fastapi import HTTPException, Request, Depends

# backend nonce: mémoire fallback
class _MemoryNonceStore:
    def __init__(self):
        self._seen = {}  # nonce -> expire_ts

    def put_if_absent(self, nonce: str, ttl_sec: int) -> bool:
        now = time.time()
        self._gc(now)
        if nonce in self._seen and self._seen[nonce] > now:
            return False
        self._seen[nonce] = now + ttl_sec
        return True

    def _gc(self, now: float):
        rem = [k for k, v in self._seen.items() if v <= now]
        for k in rem:
            del self._seen[k]

class AntiReplay:
    def __init__(self, settings, redis=None):
        self.settings = settings
        self.redis = redis
        self.mem = _MemoryNonceStore()

    async def _nonce_check(self, nonce: str) -> bool:
        if self.redis:
            # setnx + expire
            key = f"nonce:{nonce}"
            ok = await self.redis.setnx(key, "1")
            if not ok:
                return False
            await self.redis.expire(key, self.settings.anti_replay_ttl_sec)
            return True
        return self.mem.put_if_absent(nonce, self.settings.anti_replay_ttl_sec)

    def _signing_string(self, method: str, path: str, timestamp: str, nonce: str, body_bytes: bytes) -> bytes:
        # corps en SHA256 hex pour compacité
        body_hash = hashlib.sha256(body_bytes or b"").hexdigest()
        raw = f"{method.upper()}|{path}|{timestamp}|{nonce}|{body_hash}"
        return raw.encode("utf-8")

    async def verify(self, request: Request):
        s = self.settings
        hdr = request.headers
        sig_b64 = hdr.get("x-signature", "")
        ts = hdr.get("x-timestamp", "")
        nonce = hdr.get("x-nonce", "")
        if not sig_b64 or not ts or not nonce:
            raise HTTPException(status_code=401, detail="Missing signature headers")

        try:
            ts_val = int(ts)
        except ValueError:
            raise HTTPException(status_code=400, detail="Bad timestamp")

        now = int(time.time())
        if abs(now - ts_val) > s.max_clock_skew_sec:
            raise HTTPException(status_code=401, detail="Stale timestamp")

        # ← utilise le cache si présent (posé par BodySizeLimitMiddleware)
        cached = request.scope.get("state", {}).get("_cached_body")
        if cached is not None:
            body = cached
        else:
            body = await request.body()

        base = self._signing_string(request.method, request.url.path, ts, nonce, body)
        mac = hmac.new(s.app_hmac_secret.encode("utf-8"), base, hashlib.sha256).digest()
        expected = base64.b64encode(mac).decode("ascii")

        if not hmac.compare_digest(expected, sig_b64):
            raise HTTPException(status_code=401, detail="Bad signature")

        if not await self._nonce_check(nonce):
            raise HTTPException(status_code=409, detail="Replay detected")

        return True

# Dépendance FastAPI utilisable par route:
def require_signed_request(settings, redis=None):
    guard = AntiReplay(settings, redis)
    async def _dep(request: Request):
        return await guard.verify(request)
    return _dep
