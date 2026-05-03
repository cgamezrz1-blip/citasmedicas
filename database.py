from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, Date, Time, Text, Float, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# ── Configuracion ──────────────────────────────────────────────
DATABASE_URL = (
    "sqlite:////home/site/wwwroot/citasmedicas.db"
    if os.getenv("WEBSITE_SITE_NAME")
    else "sqlite:///./citasmedicas.db"
)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ══════════════════════════════════════════════════════════════
# MODELOS
# ══════════════════════════════════════════════════════════════

class Usuario(Base):
    __tablename__ = "usuarios"
    id               = Column(Integer, primary_key=True, index=True)
    nombre           = Column(String(100), nullable=False)
    email            = Column(String(150), unique=True, index=True, nullable=False)
    password         = Column(String(255), nullable=False)
    rol              = Column(String(20), default="paciente")  # paciente | medico | admin
    activo           = Column(Boolean, default=True)
    telefono         = Column(String(20), nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)
    reset_token      = Column(String(100), nullable=True)   # token recuperacion contrasena
    reset_expira     = Column(DateTime, nullable=True)       # expiracion del token
    creado_en        = Column(DateTime, default=datetime.utcnow)

    medico_perfil    = relationship("MedicoPerfil", back_populates="usuario", uselist=False)
    citas_paciente   = relationship("Cita", foreign_keys="Cita.paciente_id", back_populates="paciente")
    notificaciones   = relationship("Notificacion", back_populates="usuario")


class Especialidad(Base):
    __tablename__ = "especialidades"
    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    activa      = Column(Boolean, default=True)

    medicos     = relationship("MedicoPerfil", back_populates="especialidad")


class MedicoPerfil(Base):
    __tablename__ = "medico_perfiles"
    id               = Column(Integer, primary_key=True, index=True)
    usuario_id       = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    especialidad_id  = Column(Integer, ForeignKey("especialidades.id"), nullable=True)
    registro_medico  = Column(String(50), unique=True, nullable=True)
    consultorio      = Column(String(100), nullable=True)
    tarifa_consulta  = Column(Float, default=0.0)

    usuario          = relationship("Usuario", back_populates="medico_perfil")
    especialidad     = relationship("Especialidad", back_populates="medicos")
    horarios         = relationship("Horario", back_populates="medico")
    citas            = relationship("Cita", foreign_keys="Cita.medico_id", back_populates="medico")


class Horario(Base):
    __tablename__ = "horarios"
    id          = Column(Integer, primary_key=True, index=True)
    medico_id   = Column(Integer, ForeignKey("medico_perfiles.id"), nullable=False)
    dia_semana  = Column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    hora_inicio = Column(String(5), nullable=False)  # "08:00"
    hora_fin    = Column(String(5), nullable=False)   # "17:00"
    activo      = Column(Boolean, default=True)

    medico      = relationship("MedicoPerfil", back_populates="horarios")


class Cita(Base):
    __tablename__ = "citas"
    id              = Column(Integer, primary_key=True, index=True)
    paciente_id     = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    medico_id       = Column(Integer, ForeignKey("medico_perfiles.id"), nullable=False)
    fecha           = Column(String(10), nullable=False)   # "YYYY-MM-DD"
    hora            = Column(String(5), nullable=False)    # "HH:MM"
    motivo          = Column(Text, nullable=False)
    estado          = Column(String(20), default="pendiente")  # pendiente | confirmada | cancelada
    costo           = Column(Float, default=0.0)
    notas_medico    = Column(Text, nullable=True)
    creado_en       = Column(DateTime, default=datetime.utcnow)
    cancelado_en    = Column(DateTime, nullable=True)

    paciente        = relationship("Usuario", foreign_keys=[paciente_id], back_populates="citas_paciente")
    medico          = relationship("MedicoPerfil", foreign_keys=[medico_id], back_populates="citas")
    notificaciones  = relationship("Notificacion", back_populates="cita")


class Notificacion(Base):
    __tablename__ = "notificaciones"
    id         = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cita_id    = Column(Integer, ForeignKey("citas.id"), nullable=True)
    tipo       = Column(String(30), nullable=False)   # recordatorio | confirmacion | cancelacion
    mensaje    = Column(Text, nullable=False)
    leida      = Column(Boolean, default=False)
    creado_en  = Column(DateTime, default=datetime.utcnow)

    usuario    = relationship("Usuario", back_populates="notificaciones")
    cita       = relationship("Cita", back_populates="notificaciones")


# ── Inicializar DB y datos base ────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_data()

def _seed_data():
    """Crea datos iniciales si no existen."""
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = SessionLocal()
    try:
        # Admin por defecto
        if not db.query(Usuario).filter(Usuario.email == "admin@citasmedicas.com").first():
            db.add(Usuario(
                nombre="Administrador",
                email="admin@citasmedicas.com",
                password=pwd.hash("Admin123!"),
                rol="admin",
            ))

        # Especialidades base
        especialidades = ["Medicina General", "Pediatria", "Cardiologia",
                          "Dermatologia", "Ginecologia", "Ortopedia"]
        for nombre in especialidades:
            if not db.query(Especialidad).filter(Especialidad.nombre == nombre).first():
                db.add(Especialidad(nombre=nombre))

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error en seed: {e}")
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
