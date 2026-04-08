from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class SpeciesBase(BaseModel):
    """
    Base properties for a Species.
    """
    region: str | None = None
    environment: str | None = None
    information: str | None = None
    species_name: str | None = None
    species_url_picture: str | None = None


class SpeciesCreate(SpeciesBase):
    """
    Payload for creating a new Species.
    """
    pass


class SpeciesOut(SpeciesBase):
    """
    Output model representing a Species returned by the API.
    """
    idspecies: int
    model_config = ConfigDict(from_attributes=True)
