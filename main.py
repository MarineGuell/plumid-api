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

from db import engine
from models import Base, Users

# Auth dependency for protected endpoints
from dependencies.auth import get_current_user

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
# Schema management is handled by Alembic at container startup (see
# scripts/run_migrations.py invoked by entrypoint.sh). The create_all
# call below is kept as a defence-in-depth no-op for environments where
# the entrypoint isn't used (e.g. running the app directly during dev).
# It fails silently when the application role lacks CREATE on `public`,
# which is the expected, healthy state in production.
try:
    Base.metadata.create_all(bind=engine)
except Exception as exc:  # noqa: BLE001
    log.warning(
        "Skipping Base.metadata.create_all (probable insufficient privileges, "
        "expected when DB schema is managed by Alembic): %s",
        exc,
    )

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
# Upload d'une plume + identification par le service modèle
# ---------------------------------------------------------------------------
# Authentification : Bearer JWT classique (pas de HMAC). L'app récupère
# le token via POST /auth/login et le pose dans le header Authorization.
#
# Flow :
#   1. L'app envoie l'image en multipart sur /upload/feather.
#   2. On forwarde l'image vers le service modèle (/predict).
#   3. Le service modèle gère le préprocessing + l'inférence et peut
#      renvoyer :
#        - 200 avec une prédiction → on relaye à l'app
#        - 422 avec warning_code (NO_FEATHER / TOO_MANY_FEATHERS) → on
#          relaye tel quel pour que l'app affiche le message à l'user
#        - 503 si le classifier n'est pas encore prêt → on relaye 503
#   4. Si MODEL_SERVICE_URL n'est pas configuré, on renvoie un stub pour
#      faciliter le développement local sans le service modèle.
# ---------------------------------------------------------------------------


@app.post("/upload/feather")
async def upload_feather(
    file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user),
):
    """
    Identifie l'espèce d'oiseau à partir d'une photo de plume.

    Auth : Bearer token JWT (obtenu via POST /auth/login).

    Réponses
    --------
    200 — prédiction réussie ::

        {
          "ok": true,
          "filename": "...",
          "bytes": 12345,
          "prediction": {
            "species_id": 4,
            "species_name": "Geai des chênes (Garrulus glandarius)",
            "model_class": "Geai_des_chene_Passiform_garulus_glandarius",
            "confidence": 52.38,
            "top_k": [...],
            ...
          }
        }

    422 — préprocessing a rejeté l'image (pas de plume / plumes multiples) ::

        {
          "ok": false,
          "warning_code": "NO_FEATHER" | "TOO_MANY_FEATHERS",
          "message": "Aucune plume n'a été reconnue sur l'image..."
        }

    503 — service modèle injoignable ou pas prêt
    502 — erreur réseau entre l'API et le service modèle
    """
    import httpx  # import local pour ne pas alourdir le démarrage

    content = await file.read()

    # ---- Mode dégradé sans service modèle (utile pour le dev local) ----
    if not settings.model_service_url:
        log.warning(
            "MODEL_SERVICE_URL non configuré, upload_feather renvoie un stub."
        )
        return {
            "ok": True,
            "filename": file.filename,
            "bytes": len(content),
            "prediction": None,
            "detail": "MODEL_SERVICE_URL not configured (stub mode)",
        }

    model_url = settings.model_service_url.rstrip("/") + "/predict"

    try:
        async with httpx.AsyncClient(timeout=settings.model_service_timeout) as cli:
            resp = await cli.post(
                model_url,
                files={
                    "file": (
                        file.filename or "feather.jpg",
                        content,
                        file.content_type or "application/octet-stream",
                    )
                },
            )
    except httpx.HTTPError as exc:
        log.exception("Appel au service modèle KO: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Model service unreachable: {exc!s}",
        ) from exc

    # ---- 422 : préprocessing a rejeté l'image (warning code) ----
    # On relaye proprement à l'app : même status, même body.
    if resp.status_code == 422:
        try:
            warning_body = resp.json()
        except Exception:  # noqa: BLE001
            warning_body = {
                "ok": False,
                "warning_code": "UNKNOWN",
                "message": resp.text,
            }
        log.info(
            "Model preprocessing rejected the image: user=%s warning=%s",
            current_user.idusers,
            warning_body.get("warning_code"),
        )
        return JSONResponse(status_code=422, content=warning_body)

    # ---- 503 : modèle pas prêt ----
    if resp.status_code == 503:
        raise HTTPException(
            status_code=503,
            detail=(
                "Le service de prédiction n'est pas encore prêt. "
                "Réessaye dans quelques secondes."
            ),
        )

    # ---- Autres erreurs du service modèle ----
    if resp.status_code >= 400:
        log.error(
            "Model service returned %d: %s",
            resp.status_code, resp.text[:200],
        )
        raise HTTPException(
            status_code=502,
            detail=f"Model service error ({resp.status_code})",
        )

    # ---- Succès ----
    try:
        prediction: Dict[str, Any] = resp.json()
    except Exception as exc:  # noqa: BLE001
        log.exception("Réponse modèle invalide: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Model service returned an invalid JSON",
        ) from exc

    log.info(
        "predict: user=%s filename=%s species_id=%s confidence=%s",
        current_user.idusers,
        file.filename,
        prediction.get("species_id"),
        prediction.get("confidence"),
    )

    return {
        "ok": True,
        "filename": file.filename,
        "bytes": len(content),
        "prediction": prediction,
    }

# ---------------------------------------------------------------------------
# Mount routers
# ---------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(species_router)
app.include_router(feathers_router)
app.include_router(pictures_router)
app.include_router(auth_router)
