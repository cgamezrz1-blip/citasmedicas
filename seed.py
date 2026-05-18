"""
DESPUES — Patron SRP
Archivo: seed.py (nuevo archivo separado)
Responsabilidad unica: datos iniciales del sistema.

ANTES: La funcion _seed() estaba dentro de database.py
       mezclada con los modelos ORM y la configuracion.
       Pylint reporto C0415 (import fuera del nivel superior)
       y W0718 (excepcion muy general).
DESPUES: Seed separado en su propio modulo con
         manejo de excepciones especifico.
"""
import random
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import Usuario, Especialidad

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

COLORES = [
    "#1a56db", "#059669", "#7c3aed",
    "#d97706", "#dc2626", "#0891b2",
    "#db2777", "#65a30d"
]

ESPECIALIDADES_INICIALES = [
    "Medicina General",
    "Pediatria",
    "Cardiologia",
    "Dermatologia",
    "Ginecologia",
    "Ortopedia",
]


def crear_admin(db: Session) -> None:
    """Crea el usuario administrador si no existe."""
    if db.query(Usuario).filter(Usuario.email == "admin@citasmedicas.com").first():
        return
    admin = Usuario(
        nombre="Administrador",
        email="admin@citasmedicas.com",
        password=_pwd.hash("Admin123!"),
        rol="admin",
        aprobado=True,
        color_avatar="#7c3aed",
        pregunta_seguridad="Nombre de tu primera mascota",
        respuesta_seguridad="admin",
    )
    db.add(admin)
    db.commit()


def crear_especialidades(db: Session) -> None:
    """Crea las especialidades medicas iniciales si no existen."""
    for nombre in ESPECIALIDADES_INICIALES:
        if not db.query(Especialidad).filter(Especialidad.nombre == nombre).first():
            db.add(Especialidad(nombre=nombre))
    db.commit()


def run_seed() -> None:
    """
    Ejecuta el seed completo de datos iniciales.
    Maneja excepciones especificas en lugar de Exception general.
    Resuelve: W0718 Pylint (broad-exception-caught).
    """
    db = SessionLocal()
    try:
        crear_admin(db)
        crear_especialidades(db)
        print("Seed completado exitosamente")
    except IntegrityError as e:
        db.rollback()
        print(f"Error de integridad en seed: {e}")
    except Exception as e:
        db.rollback()
        print(f"Error inesperado en seed: {e}")
        raise
    finally:
        db.close()
