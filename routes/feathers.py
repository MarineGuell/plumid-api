from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models.feathers import Feathers
from schemas.feathers import FeathersCreate, FeathersOut

router = APIRouter(prefix="/feathers", tags=["feathers"])


@router.post("", response_model=FeathersOut, status_code=201)
def create_feathers(payload: FeathersCreate, db: Session = Depends(get_db)):
    """
    Create a new feather record in the database.
    """
    obj = Feathers(**payload.model_dump(exclude_unset=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{idfeathers}", response_model=FeathersOut)
def get_feathers(idfeathers: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific feather by its ID.
    Raises 404 if not found.
    """
    obj = db.get(Feathers, idfeathers)
    if not obj:
        raise HTTPException(status_code=404, detail="Feathers not found")
    return obj


@router.delete("/{idfeathers}", status_code=204)
def delete_feathers(idfeathers: int, db: Session = Depends(get_db)):
    """
    Delete a specific feather by its ID.
    Raises 404 if not found.
    """
    obj = db.get(Feathers, idfeathers)
    if not obj:
        raise HTTPException(status_code=404, detail="Feathers not found")
    db.delete(obj)
    db.commit()
