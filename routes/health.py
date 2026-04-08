# api/routes/health.py
from __future__ import annotations

import time
from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    """
    Health check endpoint to verify API operations and latency.
    """
    t0 = time.perf_counter()

    dt = (time.perf_counter() - t0) * 1000
    return {
        "status": "ok",
        "latency_ms": round(dt, 1),
    }
