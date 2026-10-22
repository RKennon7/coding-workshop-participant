"""Declarative base class that every ORM model inherits from.

Base.metadata collects all tables; scripts/create_tables.py calls Base.metadata.create_all on it.
"""
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Root of the model hierarchy. Holds no columns itself."""
    pass