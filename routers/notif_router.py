"""
routers/notif_router.py
Responsabilidad unica: endpoints de notificaciones.
Usa Patron 2 (Facade) — NotificacionService.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario, Notificacion
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

@router.get("")
def get_notifs(u=Depends(get_user), db: Session = Depends(get_db)):
    """Patron 2 — Facade: delega a NotificacionService."""
    return facade.notif.get_notificaciones(u, db)

@router.put("/{nid}/leer")
def leer_notif(nid: int, u=Depends(get_user), db: Session = Depends(get_db)):
    return facade.notif.marcar_leida(nid, u, db)

@router.put("/leer-todas")
def leer_todas(u=Depends(get_user), db: Session = Depends(get_db)):
    db.query(Notificacion).filter(
        Notificacion.usuario_id == u.id,
        Notificacion.leida == False
    ).update({"leida": True})
    db.commit()
    return {"mensaje": "Todas marcadas como leidas"}
