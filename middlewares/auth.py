# api/middlewares/auth.py
from __future__ import annotations
from fastapi import Header, HTTPException
from settings import settings

def require_api_key(authorization: str = Header(default="")) -> None:
    """
    Dépendance FastAPI (à utiliser dans routes) :
      dependencies=[Depends(require_api_key)]
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.plum_id_api_key:  # <-- rename
        raise HTTPException(status_code=403, detail="Invalid token")
