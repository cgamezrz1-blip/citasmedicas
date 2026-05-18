"""
Patron 1 — Factory Method
Archivo: services/usuario_factory.py
Resuelve: OCP y SRP en POST /auth/registro (main.py L129-L163)
"""
from datetime import date, datetime
from abc import ABC, abstractmethod
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from models import Usuario, MedicoPerfil

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UsuarioCreator(ABC):
    """
    Interfaz (Creator) — define el contrato de creacion de usuarios.
    Cada subclase implementa crear_usuario() segun el tipo de rol.
    """

    @abstractmethod
    def crear_usuario(self, datos, db: Session) -> Usuario:
        """Metodo abstracto — implementado por cada subclase."""

    def registrar(self, datos, db: Session) -> dict:
        """
        Metodo template — llama a crear_usuario() sin conocer
        el tipo concreto. Cumple el principio OCP.
        """
        usuario = self.crear_usuario(datos, db)
        return {
            "mensaje": "Registro exitoso",
            "usuario": {
                "id": usuario.id,
                "nombre": usuario.nombre,
                "email": usuario.email,
                "rol": usuario.rol,
            }
        }


class PacienteCreator(UsuarioCreator):
    """
    Creator Concreto — crea usuarios con rol paciente.
    aprobado=True porque no requiere verificacion.
    """

    def crear_usuario(self, datos, db: Session) -> Usuario:
        nuevo = Usuario(
            nombre=datos.nombre,
            email=datos.email,
            password=pwd_ctx.hash(datos.password),
            rol="paciente",
            aprobado=True,
            fecha_nacimiento=datos.fecha_nacimiento,
            pregunta_seguridad=datos.pregunta_seguridad,
            respuesta_seguridad=datos.respuesta_seguridad.strip().lower(),
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return nuevo


class MedicoCreator(UsuarioCreator):
    """
    Creator Concreto — crea usuarios con rol medico.
    Valida ReTHUS y deja aprobado=False hasta revision del admin.
    """

    def crear_usuario(self, datos, db: Session) -> Usuario:
        # Validar edad minima
        nac = datetime.strptime(datos.fecha_nacimiento, "%Y-%m-%d").date()
        hoy = date.today()
        edad = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
        if edad < 18:
            raise HTTPException(400, "Los medicos deben ser mayores de 18 anos")

        # Validar ReTHUS
        if not datos.numero_rethus:
            raise HTTPException(400, "Numero ReTHUS obligatorio para medicos")

        nuevo = Usuario(
            nombre=datos.nombre,
            email=datos.email,
            password=pwd_ctx.hash(datos.password),
            rol="medico",
            aprobado=False,
            fecha_nacimiento=datos.fecha_nacimiento,
            pregunta_seguridad=datos.pregunta_seguridad,
            respuesta_seguridad=datos.respuesta_seguridad.strip().lower(),
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)

        # Crear perfil medico
        perfil = MedicoPerfil(
            usuario_id=nuevo.id,
            especialidad_id=datos.especialidad_id,
            numero_rethus=datos.numero_rethus,
        )
        db.add(perfil)
        db.commit()
        return nuevo


# Registro de creators — extensible sin modificar codigo existente
CREATORS = {
    "paciente": PacienteCreator(),
    "medico": MedicoCreator(),
}


def get_creator(rol: str) -> UsuarioCreator:
    """
    Retorna el creator correspondiente al rol.
    Agregar nuevo rol = agregar entrada al diccionario.
    No requiere modificar este metodo.
    """
    creator = CREATORS.get(rol)
    if not creator:
        from fastapi import HTTPException
        raise HTTPException(400, f"Rol '{rol}' no valido")
    return creator
