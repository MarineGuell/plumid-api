# api/main.py
from __future__ import annotations

import logging
import secrets
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from settings import settings
from middlewares.tracing import install_tracing
from middlewares.body_limit import BodySizeLimitMiddleware
from middlewares.rate_limit import RateLimitMiddleware
from security.antireplay import require_signed_request

from db import engine
from models import Base

# Routers
from routes.health import router as health_router
from routes.species import router as species_router
from routes.feathers import router as feathers_router
from routes.pictures import router as pictures_router
from routes.auth import router as auth_router

log = logging.getLogger("uvicorn")

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
# Initialisation de la base de données (création des tables manquantes)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Plum'ID - API", version=settings.api_version)

# --- Tracing (X-Trace-Id + logs latence) ---
install_tracing(app)

# --- Cap global de la taille des requêtes (413 si dépassement) ---
app.add_middleware(
    BodySizeLimitMiddleware,
    max_bytes=settings.max_request_body_bytes,
)

# --- Rate limit (token-bucket mémoire / Redis si branché) ---
# Option Redis (à activer si settings.redis_url est défini et accessible)
# import redis.asyncio as redis_async
# _redis = redis_async.from_url(settings.redis_url) if settings.redis_url else None
_redis = None

app.add_middleware(
    RateLimitMiddleware,
    settings=settings,
    redis=_redis,
)

# --- CORS ---
# Utilise la liste depuis settings si disponible, sinon ouvre en dev.
allow_origins = getattr(settings, "cors_origins", None) or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def _problem_json(
    *,
    status: int,
    code: str,
    message: str,
    trace_id: str,
    hint: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    payload: Dict[str, Any] = {
        "error": {"code": code, "message": message, "trace_id": trace_id}
    }
    if hint:
        payload["error"]["hint"] = hint
    if details:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    trace = getattr(request.state, "trace_id", secrets.token_hex(8))
    msg = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    return _problem_json(
        status=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=msg,
        trace_id=trace,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    trace = getattr(request.state, "trace_id", secrets.token_hex(8))
    return _problem_json(
        status=422,
        code="VALIDATION_ERROR",
        message="Invalid request payload",
        trace_id=trace,
        details={"errors": exc.errors()},
        hint="Vérifie les champs requis et leurs types.",
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    trace = getattr(request.state, "trace_id", secrets.token_hex(8))
    logging.exception("INTERNAL ERROR [trace=%s]: %s", trace, exc)
    return _problem_json(
        status=500,
        code="INTERNAL_ERROR",
        message="Unexpected server error",
        trace_id=trace,
        hint="Consulte les logs serveur avec ce trace_id.",
    )

# ---------------------------------------------------------------------------
# Exemple d’endpoint sensible signé (HMAC + anti-replay)
# ---------------------------------------------------------------------------
require_sig = require_signed_request(settings, _redis)


@app.post("/upload/feather", dependencies=[Depends(require_sig)])
async def upload_feather(file: UploadFile = File(...)):
    """
    Endpoint d’upload protégé par signature HMAC + nonce anti-replay.
    - En-têtes requis côté client : X-Timestamp, X-Nonce, X-Signature
    - Voir clients/python/plumid_sign.py pour générer la signature.
    """
    # TODO: intégrer ton pipeline (enregistrement, queue, inference, etc.)
    return {"ok": True, "filename": file.filename}

# ---------------------------------------------------------------------------
# Mount routers
# ---------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(species_router)
app.include_router(feathers_router)
app.include_router(pictures_router)
app.include_router(auth_router)
