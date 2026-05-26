"""
routers/citas_router.py
Responsabilidad unica: endpoints de citas, especialidades y medicos.
Usa Patron 2 (Facade), Patron 4 (Observer) y Patron 5 (Strategy).
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Especialidad, MedicoPerfil, Cita, Notificacion
from services.citas_facade import CitasMedicasFacade
from routers.deps import get_user
from strategies.cost_strategy import cita_service

router = APIRouter()
facade = CitasMedicasFacade()


class CitaCreateReq(BaseModel):
    """Schema de creacion de cita."""

    medico_id: int
    fecha: str
    hora: str
    motivo: str
    costo: float = 0.0


class CitaUpdateReq(BaseModel):
    """Schema de actualizacion de cita."""

    fecha: Optional[str] = None
    hora: Optional[str] = None
    motivo: Optional[str] = None
    estado: Optional[str] = None
    costo: Optional[float] = None
    notas_medico: Optional[str] = None


@router.get("/especialidades")
def get_especialidades(db: Session = Depends(get_db)):
    """Retorna especialidades activas."""
    return [
        {"id": e.id, "nombre": e.nombre}
        for e in db.query(Especialidad).filter(Especialidad.activa.is_(True)).all()
    ]


@router.get("/especialidades/{esp_id}/tarifa")
def get_tarifa(esp_id: int, db: Session = Depends(get_db)):
    """
    Patron 5 — Strategy: tarifa calculada por TarifaFijaStrategy.
    ANTES: hardcodeada en citas.html.
    DESPUES: calculada en el backend, intercambiable en tiempo de ejecucion.
    """
    esp = db.query(Especialidad).filter(Especialidad.id == esp_id).first()
    if not esp:
        raise HTTPException(404, "Especialidad no encontrada")
    tarifa = cita_service.calcular_costo_cita(esp.nombre)
    return {"tarifa": tarifa, "especialidad": esp.nombre}


@router.get("/medicos")
def get_medicos(especialidad_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Retorna medicos activos y aprobados."""
    from models import Usuario
    query = db.query(MedicoPerfil).join(Usuario).filter(
        Usuario.activo.is_(True), Usuario.aprobado.is_(True)
    )
    if especialidad_id:
        query = query.filter(MedicoPerfil.especialidad_id == especialidad_id)
    return [
        {
            "id": m.id,
            "nombre": m.usuario.nombre,
            "email": m.usuario.email,
            "especialidad": m.get_especialidad(),
            "especialidad_id": m.especialidad_id,
            "numero_rethus": m.get_rethus(),
            "tarifa_consulta": cita_service.calcular_costo_cita(m.get_especialidad()),
        }
        for m in query.all()
    ]


@router.get("/disponibilidad")
def disponibilidad(medico_id: int, fecha: str, db: Session = Depends(get_db)):
    """Retorna horas ocupadas de un medico en una fecha."""
    citas = db.query(Cita).filter(
        Cita.medico_id == medico_id,
        Cita.fecha == fecha,
        Cita.estado != "cancelada",
    ).all()
    return {"horas_ocupadas": [c.hora for c in citas]}


@router.get("/citas")
def get_citas(
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    u=Depends(get_user),
    db: Session = Depends(get_db),
):
    """Patron 2 — Facade: delega a CitaServiceFacade."""
    resultado = facade.citas.get_citas(u, db)
    citas = resultado["citas"]
    hoy = date.today().isoformat()
    if tipo == "proximas":
        citas = [c for c in citas if c["fecha"] >= hoy]
    elif tipo == "pasadas":
        citas = [c for c in citas if c["fecha"] < hoy]
    if estado:
        citas = [c for c in citas if c["estado"] == estado]
    return {"citas": citas, "total": len(citas)}


@router.get("/citas/proxima")
def proxima_cita(u=Depends(get_user), db: Session = Depends(get_db)):
    """Retorna la proxima cita del usuario."""
    hoy = date.today().isoformat()
    query = db.query(Cita).filter(Cita.fecha >= hoy, Cita.estado != "cancelada")
    if u.get_rol() == "paciente":
        query = query.filter(Cita.paciente_id == u.id)
    elif u.get_rol() == "medico":
        perfil = db.query(MedicoPerfil).filter(MedicoPerfil.usuario_id == u.id).first()
        if perfil:
            query = query.filter(Cita.medico_id == perfil.id)
    cita = query.order_by(Cita.fecha, Cita.hora).first()
    if not cita:
        return {"proxima": None}
    return {
        "proxima": {
            "id": cita.id,
            "fecha": cita.fecha,
            "hora": cita.hora,
            "medico_nombre": cita.medico.usuario.nombre if cita.medico else "—",
            "paciente_nombre": cita.paciente.nombre if cita.paciente else "—",
            "motivo": cita.motivo,
            "estado": cita.get_estado(),
        }
    }


@router.post("/citas")
def crear_cita(d: CitaCreateReq, u=Depends(get_user), db: Session = Depends(get_db)):
    """
    Patron 2 — Facade + Patron 4 — Observer.
    ANTES: creacion + notificacion mezcladas en el endpoint.
    DESPUES: facade.citas.crear_cita() usa Observer internamente.
    """
    return facade.citas.crear_cita(d, u, db)


@router.get("/citas/{cita_id}")
def get_cita(cita_id: int, u=Depends(get_user), db: Session = Depends(get_db)):
    """Retorna una cita por ID."""
    _ = u
    c = db.query(Cita).filter(Cita.id == cita_id).first()
    if not c:
        raise HTTPException(404, "Cita no encontrada")
    return {
        "id": c.id,
        "paciente_nombre": c.paciente.nombre,
        "medico_nombre": c.medico.usuario.nombre,
        "fecha": c.fecha,
        "hora": c.hora,
        "motivo": c.motivo,
        "estado": c.get_estado(),
        "costo": c.costo,
        "notas_medico": c.notas_medico or "",
    }


@router.put("/citas/{cita_id}")
def update_cita(
    cita_id: int,
    d: CitaUpdateReq,
    u=Depends(get_user),
    db: Session = Depends(get_db),
):
    """Actualiza una cita existente."""
    c = db.query(Cita).filter(Cita.id == cita_id).first()
    if not c:
        raise HTTPException(404, "Cita no encontrada")
    if d.fecha:
        c.fecha = d.fecha
    if d.hora:
        c.hora = d.hora
    if d.motivo:
        c.motivo = d.motivo
    if d.estado:
        c.estado = d.estado
        if d.estado == "cancelada":
            c.cancelado_en = datetime.utcnow()
        if u.get_rol() == "medico" and d.estado in ["confirmada", "cancelada"]:
            db.add(Notificacion(
                usuario_id=c.paciente_id,
                cita_id=c.id,
                tipo=d.estado,
                mensaje=f"Tu cita del {c.fecha} fue {d.estado}",
                leida=False,
                creado_en=datetime.utcnow(),
            ))
    if d.costo is not None:
        c.costo = d.costo
    if d.notas_medico is not None:
        c.notas_medico = d.notas_medico
    db.commit()
    return {"mensaje": "Cita actualizada"}


@router.delete("/citas/{cita_id}")
def delete_cita(cita_id: int, u=Depends(get_user), db: Session = Depends(get_db)):
    """Elimina una cita."""
    _ = u
    c = db.query(Cita).filter(Cita.id == cita_id).first()
    if not c:
        raise HTTPException(404, "Cita no encontrada")
    db.delete(c)
    db.commit()
    return {"mensaje": "Cita eliminada"}
