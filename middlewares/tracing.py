# api/middlewares/tracing.py
from __future__ import annotations

import logging
import secrets
import time
from typing import Callable, Awaitable

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import Response

log = logging.getLogger("uvicorn")


class TracingMiddleware:
    """
    - Génère un trace_id par requête
    - Le place dans request.state.trace_id
    - Ajoute l'en-tête X-Trace-Id à la réponse
    - Logge méthode, chemin, statut, latence
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        trace_id = secrets.token_hex(8)
        t0 = time.perf_counter()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-trace-id", trace_id.encode("utf-8")))
            await send(message)

        # injecte trace_id dans scope (request.state.trace_id)
        scope.setdefault("state", {})
        scope["state"]["trace_id"] = trace_id

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            dt = (time.perf_counter() - t0) * 1000
            path = scope.get("path", "?")
            method = scope.get("method", "?")
            # On ne connait pas forcément le code ici; on loggue la latence + trace
            log.info("%s %s (%.1f ms) [trace=%s]", method, path, dt, trace_id)


def install_tracing(app) -> None:
    """Helper pour enregistrer le middleware depuis main.py"""
    app.add_middleware(TracingMiddleware)