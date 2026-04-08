# api/models/users.py
from __future__ import annotations

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    func,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from models.base import Base


class Users(Base):
    """
    User model representing the 'users' table in the database.
    Stores authentication details and user profile information.
    """
    __tablename__ = "users"

    idusers = Column(Integer, primary_key=True, index=True, autoincrement=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(45))
    mail = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    username = Column(String(100))

    is_active = Column(
        Boolean,
        nullable=False,
        server_default="1",
    )
    is_verified = Column(
        Boolean,
        nullable=False,
        server_default="0",
    )
    email_verified_at = Column(
        DateTime,
        nullable=True,
    )

    # Relations
    pictures = relationship("Pictures", back_populates="user", lazy="select")

    __table_args__ = (
        UniqueConstraint("mail", name="uniq_users_mail"),
    )
