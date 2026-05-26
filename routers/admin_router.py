"""
routers/admin_router.py
Responsabilidad unica: endpoints de administracion.
Usa Patron 2 (Facade) — AdminService.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario, Cita
from services.citas_facade import CitasMedicasFacade
from routers.deps import admin_only

router = APIRouter()
facade = CitasMedicasFacade()



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
    """Retorna estadisticas generales del sistema."""
    import datetime
    medicos_pendientes = db.query(Usuario).filter(Usuario.rol == "medico", Usuario.aprobado.is_(False)).count()
    return {
        "total_usuarios":    db.query(Usuario).count(),
        "total_citas":       db.query(Cita).count(),
        "total_medicos":     db.query(Usuario).filter(Usuario.rol == "medico").count(),
        "total_pacientes":   db.query(Usuario).filter(Usuario.rol == "paciente").count(),
        "total_admins":      db.query(Usuario).filter(Usuario.rol == "admin").count(),
        "medicos_pendientes": medicos_pendientes,
        "citas_pendientes":  db.query(Cita).filter(Cita.estado == "pendiente").count(),
        "citas_confirmadas": db.query(Cita).filter(Cita.estado == "confirmada").count(),
        "citas_canceladas":  db.query(Cita).filter(Cita.estado == "cancelada").count(),
        "citas_hoy":         db.query(Cita).filter(Cita.fecha == datetime.date.today().isoformat()).count(),
    }