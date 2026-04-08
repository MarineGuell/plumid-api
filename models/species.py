from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text
from models.base import Base


class Species(Base):
    """
    Species model representing the 'species' table in the database.
    Stores reference data about bird species.
    """
    __tablename__ = "species"
    idspecies = Column(Integer, primary_key=True,
                       index=True, autoincrement=True)
    region = Column(String(45))
    environment = Column(String(45))
    information = Column(Text)
    species_name = Column(String(100))
    species_url_picture = Column(String(100))
