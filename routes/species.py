from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models.species import Species
from schemas.species import SpeciesCreate, SpeciesOut

router = APIRouter(prefix="/species", tags=["species"])


@router.post("", response_model=SpeciesOut, status_code=201)
def create_species(payload: SpeciesCreate, db: Session = Depends(get_db)):
    """
    Create a new species record in the database.
    """
    obj = Species(**payload.model_dump(exclude_unset=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{idspecies}", response_model=SpeciesOut)
def get_species(idspecies: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific species by its ID.
    Raises 404 if not found.
    """
    obj = db.get(Species, idspecies)
    if not obj:
        raise HTTPException(status_code=404, detail="Species not found")
    return obj


@router.delete("/{idspecies}", status_code=204)
def delete_species(idspecies: int, db: Session = Depends(get_db)):
    """
    Delete a specific species by its ID.
    Raises 404 if not found.
    """
    obj = db.get(Species, idspecies)
    if not obj:
        raise HTTPException(status_code=404, detail="Species not found")
    db.delete(obj)
    db.commit()
