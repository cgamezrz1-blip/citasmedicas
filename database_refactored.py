"""
DESPUES — Patron Facade + SRP
Archivo: database.py (refactorizado)
Responsabilidad unica: solo configuracion de conexion a la BD.
Los modelos se movieron a models.py
El seed se movio a seed.py
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuracion de conexion — unica responsabilidad de este archivo
_PG_URL = os.getenv("DATABASE_URL")

if _PG_URL:
    DATABASE_URL = _PG_URL
    engine = create_engine(DATABASE_URL)
else:
    DATABASE_URL = "sqlite:///./citasmedicas.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Generador de sesiones de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
