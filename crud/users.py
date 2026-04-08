# api/crud/users.py
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from core.security import hash_password, verify_password
from models.users import Users


def get_user_by_id(db: Session, user_id: int) -> Optional[Users]:
    return db.query(Users).filter(Users.idusers == user_id).first()


def get_user_by_mail(db: Session, mail: str) -> Optional[Users]:
    return db.query(Users).filter(Users.mail == mail).first()


def create_user(
    db: Session,
    *,
    mail: str,
    username: str,
    password: str,
    role: Optional[str] = None,
) -> Users:
    """Crée un utilisateur avec hash du mot de passe."""
    password_hash = hash_password(password)

    user = Users(
        mail=mail,
        username=username,
        password_hash=password_hash,
        role=role or "user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(
    db: Session,
    *,
    mail: str,
    password: str,
) -> Optional[Users]:
    """
    Retourne l'utilisateur si mail + password sont valides, sinon None.
    """
    user = get_user_by_mail(db, mail=mail)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def update_user_password(
    db: Session,
    *,
    user: Users,
    new_password: str,
) -> Users:
    """
    Met à jour le mot de passe d'un utilisateur (avec hash).

    Ne gère que le mot de passe, commit inclus.
    """
    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
