"""
routers/auth_router.py
Responsabilidad unica: endpoints de autenticacion y perfil de usuario.
Usa Patron 1 (Factory Method) y Patron 3 (Adapter).
"""
import random
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from adapters.auth_adapter import auth_adapter
from services.usuario_factory import get_creator
from routers.deps import get_user

router = APIRouter()
COLORES = ["#1a56db","#059669","#7c3aed","#d97706","#dc2626","#0891b2","#db2777","#65a30d"]

class LoginReq(BaseModel):
    email: str
    password: str

class RegistroReq(BaseModel):
    nombre: str; email: str; password: str; rol: str = "paciente"
    especialidad_id: Optional[int] = None
    fecha_nacimiento: Optional[str] = None
    pregunta_seguridad: Optional[str] = None
    respuesta_seguridad: Optional[str] = None
    numero_rethus: Optional[str] = None

class VerifReq(BaseModel):
    email: str; respuesta: str

class ResetReq(BaseModel):
    email: str; respuesta: str; nueva_password: str

class CambioPassReq(BaseModel):
    password_actual: str; nueva_password: str

class UpdatePerfilReq(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    color_avatar: Optional[str] = None

def _u(u):
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol,
            "telefono": u.telefono or "", "fecha_nacimiento": u.fecha_nacimiento or "",
            "color_avatar": u.color_avatar or "#1a56db"}



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
        return {"mensaje": "Pendiente de aprobacion", "pendiente_aprobacion": True,
                "usuario": _u(usuario)}

    token = auth_adapter.crear_token(usuario.email)
    return {"mensaje": "Registro exitoso", "access_token": token,
            "token_type": "bearer", "usuario": _u(usuario)}

@router.get("/pregunta-seguridad/{email}")
def get_pregunta(email: str, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.email == email).first()
    if not u or not u.pregunta_seguridad:
        raise HTTPException(404, "Email no encontrado")
    return {"pregunta": u.pregunta_seguridad}

@router.post("/verificar-respuesta")
def verificar(d: VerifReq, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.email == d.email).first()
    if not u or u.respuesta_seguridad != d.respuesta.strip().lower():
        raise HTTPException(400, "Respuesta incorrecta")
    return {"puede_resetear": True}

@router.post("/reset-con-pregunta")
def reset_pass(d: ResetReq, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.email == d.email).first()
    if not u or u.respuesta_seguridad != d.respuesta.strip().lower():
        raise HTTPException(400, "Respuesta incorrecta")
    if len(d.nueva_password) < 6:
        raise HTTPException(400, "Minimo 6 caracteres")
    u.password = auth_adapter.hash_password(d.nueva_password)
    db.commit()
    return {"mensaje": "Contrasena actualizada"}

@router.get("/me")
def me(u=Depends(get_user)): return _u(u)

@router.put("/me")
def update_me(d: UpdatePerfilReq, u=Depends(get_user), db: Session = Depends(get_db)):
    if d.nombre: u.nombre = d.nombre
    if d.telefono is not None: u.telefono = d.telefono
    if d.color_avatar: u.color_avatar = d.color_avatar
    db.commit()
    return {"mensaje": "Perfil actualizado", "usuario": _u(u)}

@router.post("/cambiar-password")
def cambiar_pass(d: CambioPassReq, u=Depends(get_user), db: Session = Depends(get_db)):
    if not auth_adapter.verify_password(d.password_actual, u.password):
        raise HTTPException(400, "Contrasena actual incorrecta")
    if len(d.nueva_password) < 6:
        raise HTTPException(400, "Minimo 6 caracteres")
    u.password = auth_adapter.hash_password(d.nueva_password)
    db.commit()
    return {"mensaje": "Contrasena cambiada"}
