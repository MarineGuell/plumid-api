# api/dependencies/auth.py
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from core.security import decode_access_token
from crud.users import get_user_by_id
from db import get_db
from models.users import Users

# Utilisé pour documenter l'auth dans OpenAPI (Swagger)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Users:
    """
    Récupère l'utilisateur courant à partir du Bearer token.

    - Décode le JWT
    - Récupère l'utilisateur par ID
    - Lève 401 si token invalide ou utilisateur introuvable
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exception

    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception

    try:
        user_id = int(sub)
    except ValueError:
        raise credentials_exception

    user = get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: Annotated[Users, Depends(get_current_user)],
) -> Users:
    """
    Vérifie que le compte est actif.

    - Lève 403 si `is_active` est False
    """
    if current_user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé. Contacte un administrateur.",
        )
    return current_user


def require_admin(
    current_user: Annotated[Users, Depends(get_current_active_user)],
) -> Users:
    """
    Vérifie que l'utilisateur a un rôle administrateur.

    - Lève 403 si le rôle n'est pas 'admin'
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs.",
        )
    return current_user
