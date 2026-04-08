# api/middlewares/body_limit.py
from __future__ import annotations
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse

class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        received = 0
        chunks = []

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                received += len(body)
                if received > self.max_bytes:
                    resp = JSONResponse({"detail": "Request entity too large"}, status_code=413)
                    await resp(scope, receive, send)
                    return {"type": "http.disconnect"}
                # bufferise pour anti-replay/déps qui relisent le corps
                if body:
                    chunks.append(body)
                if not message.get("more_body", False):
                    # fin du body -> expose un cache lisible par la suite
                    state = scope.setdefault("state", {})
                    state["_cached_body"] = b"".join(chunks)
            return message

        await self.app(scope, limited_receive, send)
