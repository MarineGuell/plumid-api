from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class FeathersBase(BaseModel):
    """
    Base properties for a Feather.
    """
    side: str | None = None
    type: str | None = None
    body_zone: str | None = None
    species_idspecies: int | None = None


class FeathersCreate(FeathersBase):
    """
    Payload for creating a new Feather.
    """
    pass


class FeathersOut(FeathersBase):
    """
    Output model representing a Feather returned by the API.
    """
    idfeathers: int
    model_config = ConfigDict(from_attributes=True)
