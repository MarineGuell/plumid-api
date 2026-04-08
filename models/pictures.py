from __future__ import annotations
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from models.base import Base


class Pictures(Base):
    """
    Pictures model representing the 'pictures' table in the database.
    Stores metadata for uploaded feather images.
    """
    __tablename__ = "pictures"
    idpictures = Column(Integer, primary_key=True,
                        index=True, autoincrement=True)
    url = Column(String(255))
    longitude = Column(String(45))
    latitude = Column(String(45))
    date_collected = Column(Date)

    feathers_idfeathers = Column(Integer, ForeignKey(
        "feathers.idfeathers", ondelete="CASCADE", onupdate="CASCADE"), index=True)
    feathers = relationship("Feathers", backref="pictures", lazy="joined")

    users_idusers = Column(Integer, ForeignKey(
        "users.idusers", ondelete="CASCADE", onupdate="CASCADE"), nullable=True, index=True)
    user = relationship("Users", back_populates="pictures", lazy="joined")


Index("idx_pictures_feathers", Pictures.feathers_idfeathers)
