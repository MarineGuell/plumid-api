from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from datetime import date


class PicturesBase(BaseModel):
    """
    Base properties for a Picture.
    """
    url: str | None = None
    longitude: str | None = None
    latitude: str | None = None
    date_collected: date | None = None
    feathers_idfeathers: int | None = None
    users_idusers: int | None = None


class PicturesCreate(PicturesBase):
    """
    Payload for creating a new Picture.
    """
    pass


class PicturesOut(PicturesBase):
    """
    Output model representing a Picture returned by the API.
    """
    idpictures: int
    model_config = ConfigDict(from_attributes=True)
