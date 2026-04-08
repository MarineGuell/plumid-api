# api/models/__init__.py
from __future__ import annotations

from .base import Base
from .users import Users
from .species import Species
from .feathers import Feathers
from .pictures import Pictures

__all__ = ["Base", "Users", "Species", "Feathers", "Pictures"]
