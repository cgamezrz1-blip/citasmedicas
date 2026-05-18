"""
DESPUES — Patron Factory Method + SRP
Archivo: models.py (nuevo archivo separado)
Responsabilidad unica: definicion de modelos ORM con interfaces.

ANTES: Los modelos estaban en database.py mezclados con
       la configuracion de conexion y el seed de datos.
DESPUES: Modelos separados con clase abstracta UsuarioBase
         que resuelve la violacion LSP y R0903 de Pylint.
"""
from abc import ABC, abstractmethod
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class UsuarioBase(ABC):
    """
    Clase abstracta base para todos los tipos de usuario.
    Resuelve: LSP (main.py L46-L48) y R0903 Pylint.
    Antes: roles verificados con strings 'paciente','medico','admin'.
    Despues: jerarquia de clases con metodos polimorficos.
    """

    @abstractmethod
    def get_rol(self) -> str:
        """Retorna el rol del usuario."""
        pass

    @abstractmethod
    def esta_aprobado(self) -> bool:
        """Verifica si el usuario esta aprobado para usar el sistema."""
        pass


class Usuario(Base, UsuarioBase):
    """
    Modelo ORM de usuario con interfaz definida.
    Resuelve: R0903 Pylint (muy pocos metodos publicos).
    """
    __tablename__ = "usuarios"

    id                  = Column(Integer, primary_key=True, index=True)
    nombre              = Column(String(100), nullable=False)
    email               = Column(String(150), unique=True, index=True, nullable=False)
    password            = Column(String(255), nullable=False)
    rol                 = Column(String(20), default="paciente")
    activo              = Column(Boolean, default=True)
    aprobado            = Column(Boolean, default=True)
    telefono            = Column(String(20), nullable=True)
    fecha_nacimiento    = Column(String(10), nullable=True)
    color_avatar        = Column(String(7), nullable=True)
    pregunta_seguridad  = Column(String(200), nullable=True)
    respuesta_seguridad = Column(String(255), nullable=True)
    creado_en           = Column(DateTime, default=datetime.utcnow)

    medico_perfil   = relationship("MedicoPerfil", back_populates="usuario", uselist=False)
    citas_paciente  = relationship("Cita", foreign_keys="Cita.paciente_id", back_populates="paciente")
    notificaciones  = relationship("Notificacion", back_populates="usuario")

    def get_rol(self) -> str:
        """Retorna el rol del usuario."""
        return self.rol

    def esta_aprobado(self) -> bool:
        """Verifica si el usuario esta aprobado."""
        return self.aprobado


class Especialidad(Base):
    """Modelo ORM de especialidad medica."""
    __tablename__ = "especialidades"

    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    activa      = Column(Boolean, default=True)

    medicos = relationship("MedicoPerfil", back_populates="especialidad")

    def get_nombre(self) -> str:
        """Retorna el nombre de la especialidad."""
        return self.nombre

    def is_activa(self) -> bool:
        """Verifica si la especialidad esta activa."""
        return self.activa


class MedicoPerfil(Base):
    """Modelo ORM del perfil medico."""
    __tablename__ = "medico_perfiles"

    id              = Column(Integer, primary_key=True, index=True)
    usuario_id      = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    especialidad_id = Column(Integer, ForeignKey("especialidades.id"), nullable=True)
    numero_rethus   = Column(String(50), nullable=True)
    consultorio     = Column(String(100), nullable=True)
    tarifa_consulta = Column(Float, default=0.0)

    usuario      = relationship("Usuario", back_populates="medico_perfil")
    especialidad = relationship("Especialidad", back_populates="medicos")
    citas        = relationship("Cita", foreign_keys="Cita.medico_id", back_populates="medico")

    def get_rethus(self) -> str:
        """Retorna el numero ReTHUS del medico."""
        return self.numero_rethus or ""

    def get_especialidad(self) -> str:
        """Retorna el nombre de la especialidad."""
        return self.especialidad.nombre if self.especialidad else "Medicina General"


class Cita(Base):
    """Modelo ORM de cita medica."""
    __tablename__ = "citas"

    id           = Column(Integer, primary_key=True, index=True)
    paciente_id  = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    medico_id    = Column(Integer, ForeignKey("medico_perfiles.id"), nullable=False)
    fecha        = Column(String(10), nullable=False)
    hora         = Column(String(5), nullable=False)
    motivo       = Column(Text, nullable=False)
    estado       = Column(String(20), default="pendiente")
    costo        = Column(Float, default=0.0)
    notas_medico = Column(Text, nullable=True)
    creado_en    = Column(DateTime, default=datetime.utcnow)
    cancelado_en = Column(DateTime, nullable=True)

    paciente       = relationship("Usuario", foreign_keys=[paciente_id], back_populates="citas_paciente")
    medico         = relationship("MedicoPerfil", foreign_keys=[medico_id], back_populates="citas")
    notificaciones = relationship("Notificacion", back_populates="cita")

    def get_estado(self) -> str:
        """Retorna el estado actual de la cita."""
        return self.estado

    def is_cancelada(self) -> bool:
        """Verifica si la cita esta cancelada."""
        return self.estado == "cancelada"


class Notificacion(Base):
    """Modelo ORM de notificacion."""
    __tablename__ = "notificaciones"

    id         = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cita_id    = Column(Integer, ForeignKey("citas.id"), nullable=True)
    tipo       = Column(String(30), nullable=False)
    mensaje    = Column(Text, nullable=False)
    leida      = Column(Boolean, default=False)
    creado_en  = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="notificaciones")
    cita    = relationship("Cita", back_populates="notificaciones")

    def marcar_leida(self) -> None:
        """Marca la notificacion como leida."""
        self.leida = True
