"""
routers/notif_router.py
Responsabilidad unica: endpoints de notificaciones.
Usa Patron 2 (Facade) — NotificacionService.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Notificacion
from services.citas_facade import CitasMedicasFacade
from routers.deps import get_user

router = APIRouter()
facade = CitasMedicasFacade()



@router.get("")
def get_notifs(u=Depends(get_user), db: Session = Depends(get_db)):
    """Retorna notificaciones del usuario usando NotificacionService."""
    return facade.notif.get_notificaciones(u, db)

@router.put("/{nid}/leer")
def leer_notif(nid: int, u=Depends(get_user), db: Session = Depends(get_db)):
    """Marca una notificacion como leida."""
    return facade.notif.marcar_leida(nid, u, db)

@router.put("/leer-todas")
def leer_todas(u=Depends(get_user), db: Session = Depends(get_db)):
    """Marca todas las notificaciones del usuario como leidas."""
    db.query(Notificacion).filter(
        Notificacion.usuario_id == u.id,
        Notificacion.leida.is_(False)
    ).update({"leida": True})
    db.commit()
    return {"mensaje": "Todas marcadas como leidas"}
