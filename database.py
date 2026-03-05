from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# ── Configuración de SQLite ────────────────────────────────────
import os
DATABASE_URL = "sqlite:////home/site/wwwroot/citasmedicas.db" if os.getenv("WEBSITE_SITE_NAME") else "sqlite:///./citasmedicas.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # necesario para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Modelo de Usuario ──────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id       = Column(Integer, primary_key=True, index=True)
    nombre   = Column(String, nullable=False)
    email    = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    rol      = Column(String, default="paciente")  # paciente | medico
    activo   = Column(Boolean, default=True)
    creado   = Column(DateTime, default=datetime.utcnow)

# ── Crear las tablas si no existen ────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)

# ── Dependencia para obtener sesión de DB ─────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
