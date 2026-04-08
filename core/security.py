# api/core/security.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
import bcrypt
from settings import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt directement."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie la correspondance mot de passe / hash avec bcrypt directement."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Crée un JWT signé HS256.

    data doit contenir au minimum un "sub" (string) = user_id.
    """
    to_encode = data.copy()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, settings.auth_secret, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Décode un JWT et retourne le payload.

    Lève JWTError si invalide ou expiré.
    """
    payload = jwt.decode(token, settings.auth_secret, algorithms=[ALGORITHM])
    return payload


def create_email_verification_token(user_id: int, expires_hours: int = 24) -> str:
    """
    Crée un JWT dédié à la vérification d'email.

    - sub  : identifiant utilisateur
    - scope: 'email_verify'
    - exp  : maintenant + expires_hours (par défaut 24h)
    """
    from datetime import timedelta  # pour éviter les imports circulaires

    return create_access_token(
        data={"sub": str(user_id), "scope": "email_verify"},
        expires_delta=timedelta(hours=expires_hours),
    )


def create_password_reset_token(user_id: int, expires_minutes: int = 60) -> str:
    """
    Crée un JWT dédié à la réinitialisation de mot de passe.

    - sub  : identifiant utilisateur
    - scope: 'password_reset'
    - exp  : maintenant + expires_minutes (par défaut 60 min)
    """
    from datetime import timedelta  # local pour éviter certains cycles tordus

    return create_access_token(
        data={"sub": str(user_id), "scope": "password_reset"},
        expires_delta=timedelta(minutes=expires_minutes),
    )
