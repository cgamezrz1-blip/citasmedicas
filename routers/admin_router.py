"""
routers/admin_router.py
Responsabilidad unica: endpoints de administracion.
Usa Patron 2 (Facade) — AdminService.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario, Cita, Especialidad
from adapters.auth_adapter import auth_adapter
from services.citas_facade import CitasMedicasFacade

router = APIRouter()
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")
facade = CitasMedicasFacade()

async def get_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    try:
        email = auth_adapter.verificar_token(token)
        u = db.query(Usuario).filter(Usuario.email == email).first()
        if not u or not u.activo: raise HTTPException(401, "Token invalido")
        return u
    except ValueError as exc:
        raise HTTPException(401, "Token invalido") from exc

def admin_only(u=Depends(get_user)):
    """Usa get_rol() polimorfco — Patron 1 Factory Method (LSP)."""
    if u.get_rol() != "admin": raise HTTPException(403, "Solo administradores")
    return u

@router.get("/usuarios")
def get_usuarios(u=Depends(admin_only), db: Session = Depends(get_db)):
    """Patron 2 — Facade: delega a AdminService."""
    return facade.admin.get_usuarios(db)

@router.get("/medicos-pendientes")
def medicos_pendientes(u=Depends(admin_only), db: Session = Depends(get_db)):
    ps = db.query(Usuario).filter(Usuario.rol=="medico", Usuario.aprobado==False).all()
    return [{"id": x.id, "nombre": x.nombre, "email": x.email,
             "numero_rethus": x.medico_perfil.get_rethus() if x.medico_perfil else "",
             "especialidad": x.medico_perfil.get_especialidad() if x.medico_perfil else "—",
             "fecha_nacimiento": x.fecha_nacimiento or "",
             "creado_en": x.creado_en.strftime("%Y-%m-%d")} for x in ps]

@router.put("/usuarios/{uid}/aprobar")
def aprobar(uid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    return facade.admin.aprobar_medico(uid, db)

@router.put("/usuarios/{uid}/rechazar")
def rechazar(uid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    x = db.query(Usuario).filter(Usuario.id == uid).first()
    if not x: raise HTTPException(404, "No encontrado")
    db.delete(x); db.commit()
    return {"mensaje": "Medico rechazado y eliminado"}

@router.put("/usuarios/{uid}/activar")
def activar(uid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    x = db.query(Usuario).filter(Usuario.id == uid).first()
    if not x: raise HTTPException(404, "No encontrado")
    x.activo = not x.activo; db.commit()
    return {"mensaje": f"Usuario {'activado' if x.activo else 'desactivado'}"}

@router.delete("/usuarios/{uid}")
def del_user(uid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    x = db.query(Usuario).filter(Usuario.id == uid).first()
    if not x: raise HTTPException(404, "No encontrado")
    if x.id == u.id: raise HTTPException(400, "No puedes eliminarte")
    db.delete(x); db.commit()
    return {"mensaje": "Eliminado"}

@router.get("/estadisticas")
def estadisticas(u=Depends(admin_only), db: Session = Depends(get_db)):
    return facade.admin.get_estadisticas(db)
