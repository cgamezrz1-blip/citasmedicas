"""
routers/auth_router.py
Responsabilidad unica: endpoints de autenticacion y perfil de usuario.
Usa Patron 1 (Factory Method) y Patron 3 (Adapter).
"""
import random
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario, Notificacion
from adapters.auth_adapter import auth_adapter
from services.usuario_factory import get_creator
from routers.deps import get_user

router = APIRouter()
COLORES = ["#1a56db", "#059669", "#7c3aed", "#d97706", "#dc2626",
           "#0891b2", "#db2777", "#65a30d"]


class LoginReq(BaseModel):
    """Schema de solicitud de login."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_valido(cls, v):
        """Valida formato de email."""
        if not v or len(v) < 5:
            raise ValueError("Email debe tener al menos 5 caracteres")
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Email invalido")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_valido(cls, v):
        """Valida longitud de contrasena."""
        if not v or len(v) < 6:
            raise ValueError("Contrasena debe tener al menos 6 caracteres")
        return v


class RegistroReq(BaseModel):
    """Schema de solicitud de registro."""

    nombre: str
    email: str
    password: str
    rol: str = "paciente"
    especialidad_id: Optional[int] = None
    fecha_nacimiento: Optional[str] = None
    pregunta_seguridad: Optional[str] = None
    respuesta_seguridad: Optional[str] = None
    numero_rethus: Optional[str] = None

    @field_validator("nombre")
    @classmethod
    def nombre_valido(cls, v):
        """Valida nombre del usuario."""
        if not v or len(v) < 3:
            raise ValueError("Nombre debe tener al menos 3 caracteres")
        if len(v) > 100:
            raise ValueError("Nombre no puede exceder 100 caracteres")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", v):
            raise ValueError("Nombre solo puede contener letras y espacios")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_valido(cls, v):
        """Valida formato de email."""
        if not v or len(v) < 5:
            raise ValueError("Email debe tener al menos 5 caracteres")
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Email invalido")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_valido(cls, v):
        """Valida contrasena del usuario."""
        if not v or len(v) < 6:
            raise ValueError("Contrasena debe tener al menos 6 caracteres")
        if len(v) > 255:
            raise ValueError("Contrasena no puede exceder 255 caracteres")
        return v

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, v):
        """Valida que el rol sea paciente o medico."""
        if v not in ["paciente", "medico"]:
            raise ValueError("Rol debe ser paciente o medico")
        return v


class VerifReq(BaseModel):
    """Schema de verificacion de respuesta de seguridad."""

    email: str
    respuesta: str

    @field_validator("email")
    @classmethod
    def email_valido(cls, v):
        """Valida formato de email."""
        if not v or len(v) < 5:
            raise ValueError("Email debe tener al menos 5 caracteres")
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Email invalido")
        return v.lower()

    @field_validator("respuesta")
    @classmethod
    def respuesta_valida(cls, v):
        """Valida longitud de la respuesta."""
        if not v or len(v) < 2:
            raise ValueError("Respuesta debe tener al menos 2 caracteres")
        if len(v) > 255:
            raise ValueError("Respuesta no puede exceder 255 caracteres")
        return v.strip()


class ResetReq(BaseModel):
    """Schema de reset de contrasena."""

    email: str
    respuesta: str
    nueva_password: str

    @field_validator("email")
    @classmethod
    def email_valido(cls, v):
        """Valida formato de email."""
        if not v or len(v) < 5:
            raise ValueError("Email debe tener al menos 5 caracteres")
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Email invalido")
        return v.lower()

    @field_validator("respuesta")
    @classmethod
    def respuesta_valida(cls, v):
        """Valida longitud de la respuesta."""
        if not v or len(v) < 2:
            raise ValueError("Respuesta debe tener al menos 2 caracteres")
        return v.strip()

    @field_validator("nueva_password")
    @classmethod
    def password_valido(cls, v):
        """Valida nueva contrasena."""
        if not v or len(v) < 6:
            raise ValueError("Contrasena debe tener al menos 6 caracteres")
        if len(v) > 255:
            raise ValueError("Contrasena no puede exceder 255 caracteres")
        return v


class CambioPassReq(BaseModel):
    """Schema de cambio de contrasena."""

    password_actual: str
    nueva_password: str

    @field_validator("password_actual")
    @classmethod
    def password_actual_valido(cls, v):
        """Valida contrasena actual."""
        if not v or len(v) < 6:
            raise ValueError("Contrasena debe tener al menos 6 caracteres")
        return v

    @field_validator("nueva_password")
    @classmethod
    def nueva_password_valida(cls, v):
        """Valida nueva contrasena."""
        if not v or len(v) < 6:
            raise ValueError("Nueva contrasena debe tener al menos 6 caracteres")
        if len(v) > 255:
            raise ValueError("Contrasena no puede exceder 255 caracteres")
        return v


class UpdatePerfilReq(BaseModel):
    """Schema de actualizacion de perfil."""

    nombre: Optional[str] = None
    telefono: Optional[str] = None
    color_avatar: Optional[str] = None

    @field_validator("nombre")
    @classmethod
    def nombre_valido(cls, v):
        """Valida nombre del usuario."""
        if v is None:
            return v
        if len(v) < 3:
            raise ValueError("Nombre debe tener al menos 3 caracteres")
        if len(v) > 100:
            raise ValueError("Nombre no puede exceder 100 caracteres")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", v):
            raise ValueError("Nombre solo puede contener letras y espacios")
        return v.strip()

    @field_validator("telefono")
    @classmethod
    def telefono_valido(cls, v):
        """Valida formato de telefono."""
        if v is None or v.strip() == "":
            return None
        v = v.strip()
        if not re.match(r"^[0-9+\-\s()]{7,20}$", v):
            raise ValueError("Telefono invalido: solo numeros, +, -, espacios. Ej: 3001234567")
        return v

    @field_validator("color_avatar")
    @classmethod
    def color_avatar_valido(cls, v):
        """Valida formato hexadecimal del color."""
        if v is None:
            return v
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color debe ser un codigo hexadecimal valido (ej: #1a56db)")
        return v


def _u(u):
    """Serializa un usuario a dict."""
    return {
        "id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol,
        "telefono": u.telefono or "", "fecha_nacimiento": u.fecha_nacimiento or "",
        "color_avatar": u.color_avatar or "#1a56db",
    }


@router.post("/login")
def login(d: LoginReq, db: Session = Depends(get_db)):
    """Patron 3 — Adapter: verify_password via AuthServicePort."""
    u = db.query(Usuario).filter(Usuario.email == d.email).first()
    if not u or not auth_adapter.verify_password(d.password, u.password):
        raise HTTPException(401, "Email o contrasena incorrectos")
    if not u.activo:
        raise HTTPException(403, "Usuario inactivo")
    if u.get_rol() == "medico" and not u.esta_aprobado():
        raise HTTPException(403, "Cuenta pendiente de aprobacion")
    token = auth_adapter.crear_token(u.email)
    return {"access_token": token, "token_type": "bearer", "usuario": _u(u)}


@router.post("/registro")
def registro(d: RegistroReq, db: Session = Depends(get_db)):
    """
    Patron 1 — Factory Method.
    ANTES: if/else por rol en este endpoint (viola OCP).
    DESPUES: get_creator(rol).crear_usuario(datos, db)
    """
    if db.query(Usuario).filter(Usuario.email == d.email).first():
        raise HTTPException(400, "Email ya registrado")
    if not d.pregunta_seguridad or not d.respuesta_seguridad:
        raise HTTPException(400, "Pregunta y respuesta de seguridad obligatorias")
    if not d.fecha_nacimiento:
        raise HTTPException(400, "Fecha de nacimiento obligatoria")

    creator = get_creator(d.rol)
    usuario = creator.crear_usuario(d, db)
    usuario.color_avatar = random.choice(COLORES)
    db.commit()

    if d.rol == "medico":
        admins = db.query(Usuario).filter(
            Usuario.rol == "admin", Usuario.activo.is_(True)
        ).all()
        for admin in admins:
            db.add(Notificacion(
                usuario_id=admin.id,
                tipo="nuevo_medico",
                mensaje=f"Nuevo medico registrado: {usuario.nombre} — pendiente de aprobacion",
                leida=False,
                creado_en=datetime.utcnow(),
            ))
        db.commit()
        return {"mensaje": "Pendiente de aprobacion", "pendiente_aprobacion": True,
                "usuario": _u(usuario)}

    token = auth_adapter.crear_token(usuario.email)
    return {"mensaje": "Registro exitoso", "access_token": token,
            "token_type": "bearer", "usuario": _u(usuario)}


@router.get("/pregunta-seguridad/{email}")
def get_pregunta(email: str, db: Session = Depends(get_db)):
    """Retorna la pregunta de seguridad del usuario."""
    u = db.query(Usuario).filter(Usuario.email == email).first()
    if not u or not u.pregunta_seguridad:
        raise HTTPException(404, "Email no encontrado")
    return {"pregunta": u.pregunta_seguridad}


@router.post("/verificar-respuesta")
def verificar(d: VerifReq, db: Session = Depends(get_db)):
    """Verifica la respuesta de seguridad."""
    u = db.query(Usuario).filter(Usuario.email == d.email).first()
    if not u or u.respuesta_seguridad != d.respuesta.strip():
        raise HTTPException(400, "Respuesta incorrecta")
    return {"puede_resetear": True}


@router.post("/reset-con-pregunta")
def reset_pass(d: ResetReq, db: Session = Depends(get_db)):
    """Resetea la contrasena usando la pregunta de seguridad."""
    u = db.query(Usuario).filter(Usuario.email == d.email).first()
    if not u or u.respuesta_seguridad != d.respuesta.strip():
        raise HTTPException(400, "Respuesta incorrecta")
    if len(d.nueva_password) < 6:
        raise HTTPException(400, "Minimo 6 caracteres")
    u.password = auth_adapter.hash_password(d.nueva_password)
    db.commit()
    return {"mensaje": "Contrasena actualizada"}


@router.get("/me")
def me(u=Depends(get_user)):
    """Retorna el perfil del usuario autenticado."""
    return _u(u)


@router.put("/me")
def update_me(d: UpdatePerfilReq, u=Depends(get_user), db: Session = Depends(get_db)):
    """Actualiza el perfil del usuario autenticado."""
    if d.nombre:
        u.nombre = d.nombre
    if d.telefono is not None:
        if d.telefono:
            existe = db.query(Usuario).filter(
                Usuario.telefono == d.telefono,
                Usuario.id != u.id
            ).first()
            if existe:
                raise HTTPException(400, "Este numero de telefono ya esta registrado")
        u.telefono = d.telefono or None
    if d.color_avatar:
        u.color_avatar = d.color_avatar
    db.commit()
    return {"mensaje": "Perfil actualizado", "usuario": _u(u)}


@router.post("/cambiar-password")
def cambiar_pass(d: CambioPassReq, u=Depends(get_user), db: Session = Depends(get_db)):
    """Cambia la contrasena del usuario autenticado."""
    if not auth_adapter.verify_password(d.password_actual, u.password):
        raise HTTPException(400, "Contrasena actual incorrecta")
    if len(d.nueva_password) < 6:
        raise HTTPException(400, "Minimo 6 caracteres")
    u.password = auth_adapter.hash_password(d.nueva_password)
    db.commit()
    return {"mensaje": "Contrasena cambiada"}
