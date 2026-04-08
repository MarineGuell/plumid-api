# api/schemas/users.py
from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserBase(BaseModel):
    mail: Optional[EmailStr] = None
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    email_verified_at: Optional[datetime] = None


class UserCreate(BaseModel):
    mail: EmailStr = Field(..., description="Adresse mail de l'utilisateur")
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Mot de passe en clair",
    )


class UserLogin(BaseModel):
    mail: EmailStr
    password: str


class UserOut(UserBase):
    idusers: int

    # Permet de mapper directement depuis un objet SQLAlchemy Users
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    # Identifiant utilisateur (string dans le payload JWT)
    sub: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None
    # Scope du token : ex. "access", "email_verify", "password_reset"
    scope: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """
    Payload pour demander une réinitialisation de mot de passe.
    """
    mail: EmailStr = Field(...,
                           description="Adresse email du compte à réinitialiser")


class PasswordResetConfirm(BaseModel):
    """
    Payload pour appliquer une réinitialisation de mot de passe.
    """
    token: str = Field(...,
                       description="Token de réinitialisation reçu par email")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Nouveau mot de passe",
    )


class ResendVerificationRequest(BaseModel):
    """
    Payload pour redemander un email de vérification.
    """
    mail: EmailStr = Field(
        ...,
        description="Adresse email du compte à vérifier",
    )
