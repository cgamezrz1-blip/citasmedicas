"""
DESPUES — Patron Facade + SRP
Archivo: database.py (refactorizado)
Responsabilidad unica: solo configuracion de conexion a la BD.
Los modelos se movieron a models.py
El seed se movio a seed.py

Base de datos: PostgreSQL 16 en Azure
Host: citasmedicas-pg-2026.postgres.database.azure.com
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL en Azure — configurado via variable de entorno DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "Variable de entorno DATABASE_URL no configurada. "
        "Debe apuntar a PostgreSQL en Azure."
    )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Generador de sesiones de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
