from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional
import random, os

from database import Usuario, Especialidad, MedicoPerfil, Cita, Notificacion, get_db, init_db

SECRET_KEY = os.getenv("SECRET_KEY", "clave-secreta-cambiala-en-produccion")
ALGORITHM  = "HS256"
TOKEN_EXP  = 60

app = FastAPI(title="CitasMedicas API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): init_db()

app.mount("/static", StaticFiles(directory="static"), name="static")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2  = OAuth2PasswordBearer(tokenUrl="auth/login")

COLORES = ["#1a56db","#059669","#7c3aed","#d97706","#dc2626","#0891b2","#db2777","#65a30d"]

def crear_token(email):
    exp = datetime.utcnow() + timedelta(minutes=TOKEN_EXP)
    return jwt.encode({"sub": email, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

async def get_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        u = db.query(Usuario).filter(Usuario.email == payload.get("sub")).first()
        if not u or not u.activo: raise HTTPException(401, "Token invalido")
        return u
    except JWTError:
        raise HTTPException(401, "Token invalido o expirado")

def admin_only(u=Depends(get_user)):
    if u.rol != "admin": raise HTTPException(403, "Solo administradores")
    return u

def _u(u):
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol,
            "telefono": u.telefono or "", "fecha_nacimiento": u.fecha_nacimiento or "",
            "color_avatar": u.color_avatar or "#1a56db"}

def edad(fecha_str):
    try:
        nac = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        h = date.today()
        return h.year - nac.year - ((h.month, h.day) < (nac.month, nac.day))
    except: return 0

# ── Pydantic ───────────────────────────────────────────────────
class LoginReq(BaseModel):
    email: str; password: str

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

class CitaCreateReq(BaseModel):
    medico_id: int; fecha: str; hora: str; motivo: str; costo: float = 0.0

class CitaUpdateReq(BaseModel):
    fecha: Optional[str] = None; hora: Optional[str] = None
    motivo: Optional[str] = None; estado: Optional[str] = None
    costo: Optional[float] = None; notas_medico: Optional[str] = None

# ── Paginas ────────────────────────────────────────────────────
@app.get("/")         
def home():      return FileResponse("static/login.html")
@app.get("/registro") 
def reg():       return FileResponse("static/registro.html")
@app.get("/dashboard")
def dash():      return FileResponse("static/dashboard.html")
@app.get("/mis-citas")
def citas_pg():  return FileResponse("static/citas.html")
@app.get("/olvide-password")
def olvide():    return FileResponse("static/olvide_password.html")
@app.get("/admin")
def admin_pg():  return FileResponse("static/admin.html")

@app.get("/404")
def not_found(): return FileResponse("static/404.html")

@app.exception_handler(404)
async def custom_404(request, exc):
    return FileResponse("static/404.html", status_code=404)

# ── Auth ───────────────────────────────────────────────────────
@app.post("/auth/login")
def login(d: LoginReq, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.email == d.email).first()
    if not u or not pwd_ctx.verify(d.password, u.password):
        raise HTTPException(401, "Email o contrasena incorrectos")
    if not u.activo:
        raise HTTPException(403, "Usuario inactivo")
    if u.rol == "medico" and not u.aprobado:
        raise HTTPException(403, "Tu cuenta esta pendiente de aprobacion por el administrador")
    return {"access_token": crear_token(u.email), "token_type": "bearer", "usuario": _u(u)}

@app.post("/auth/registro")
def registro(d: RegistroReq, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == d.email).first():
        raise HTTPException(400, "Email ya registrado")
    if d.rol not in ["paciente", "medico"]:
        raise HTTPException(400, "Rol no valido")
    if not d.pregunta_seguridad or not d.respuesta_seguridad:
        raise HTTPException(400, "Pregunta y respuesta de seguridad obligatorias")
    if not d.fecha_nacimiento:
        raise HTTPException(400, "Fecha de nacimiento obligatoria")
    if d.rol == "medico":
        if edad(d.fecha_nacimiento) < 18:
            raise HTTPException(400, "Los medicos deben ser mayores de 18 anos")
        if not d.numero_rethus:
            raise HTTPException(400, "Numero ReTHUS obligatorio para medicos")

    color = random.choice(COLORES)
    nuevo = Usuario(
        nombre=d.nombre, email=d.email, password=pwd_ctx.hash(d.password),
        rol=d.rol, aprobado=d.rol != "medico", color_avatar=color,
        fecha_nacimiento=d.fecha_nacimiento,
        pregunta_seguridad=d.pregunta_seguridad,
        respuesta_seguridad=d.respuesta_seguridad.strip().lower(),
    )
    db.add(nuevo); db.commit(); db.refresh(nuevo)

    if d.rol == "medico":
        db.add(MedicoPerfil(usuario_id=nuevo.id, especialidad_id=d.especialidad_id,
                            numero_rethus=d.numero_rethus))
        db.commit()
        return {"mensaje": "Pendiente de aprobacion", "pendiente_aprobacion": True, "usuario": _u(nuevo)}

    return {"mensaje": "Registro exitoso", "access_token": crear_token(nuevo.email),
            "token_type": "bearer", "usuario": _u(nuevo)}

@app.get("/auth/pregunta-seguridad/{email}")
def get_pregunta(email: str, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.email == email).first()
    if not u or not u.pregunta_seguridad:
        raise HTTPException(404, "Email no encontrado")
    return {"pregunta": u.pregunta_seguridad}

@app.post("/auth/verificar-respuesta")
def verificar(d: VerifReq, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.email == d.email).first()
    if not u: raise HTTPException(404, "Email no encontrado")
    if u.respuesta_seguridad != d.respuesta.strip().lower():
        raise HTTPException(400, "Respuesta incorrecta")
    return {"puede_resetear": True}

@app.post("/auth/reset-con-pregunta")
def reset_pass(d: ResetReq, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.email == d.email).first()
    if not u: raise HTTPException(404, "Email no encontrado")
    if u.respuesta_seguridad != d.respuesta.strip().lower():
        raise HTTPException(400, "Respuesta incorrecta")
    if len(d.nueva_password) < 6:
        raise HTTPException(400, "Minimo 6 caracteres")
    u.password = pwd_ctx.hash(d.nueva_password); db.commit()
    return {"mensaje": "Contrasena actualizada"}

@app.get("/auth/me")
def me(u=Depends(get_user)): return _u(u)

@app.put("/auth/me")
def update_me(d: UpdatePerfilReq, u=Depends(get_user), db: Session = Depends(get_db)):
    if d.nombre:       u.nombre = d.nombre
    if d.telefono is not None: u.telefono = d.telefono
    if d.color_avatar: u.color_avatar = d.color_avatar
    db.commit()
    return {"mensaje": "Perfil actualizado", "usuario": _u(u)}

@app.post("/auth/cambiar-password")
def cambiar_pass(d: CambioPassReq, u=Depends(get_user), db: Session = Depends(get_db)):
    if not pwd_ctx.verify(d.password_actual, u.password):
        raise HTTPException(400, "Contrasena actual incorrecta")
    if len(d.nueva_password) < 6:
        raise HTTPException(400, "Minimo 6 caracteres")
    u.password = pwd_ctx.hash(d.nueva_password); db.commit()
    return {"mensaje": "Contrasena cambiada"}

# ── Especialidades ─────────────────────────────────────────────
@app.get("/especialidades")
def get_especialidades(db: Session = Depends(get_db)):
    return [{"id": e.id, "nombre": e.nombre}
            for e in db.query(Especialidad).filter(Especialidad.activa == True).all()]

# ── Medicos ────────────────────────────────────────────────────
@app.get("/medicos")
def get_medicos(especialidad_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(MedicoPerfil).join(Usuario).filter(Usuario.activo == True, Usuario.aprobado == True)
    if especialidad_id: q = q.filter(MedicoPerfil.especialidad_id == especialidad_id)
    return [{"id": m.id, "nombre": m.usuario.nombre, "email": m.usuario.email,
             "especialidad": m.especialidad.nombre if m.especialidad else "Medicina General",
             "especialidad_id": m.especialidad_id, "numero_rethus": m.numero_rethus or "",
             "tarifa_consulta": m.tarifa_consulta} for m in q.all()]

# ── Disponibilidad ─────────────────────────────────────────────
@app.get("/disponibilidad")
def disponibilidad(medico_id: int, fecha: str, db: Session = Depends(get_db)):
    citas = db.query(Cita).filter(Cita.medico_id == medico_id, Cita.fecha == fecha,
                                  Cita.estado != "cancelada").all()
    return {"horas_ocupadas": [c.hora for c in citas]}

# ── Citas ──────────────────────────────────────────────────────
@app.get("/citas")
def get_citas(confirmada: Optional[bool] = None, medico_nombre: Optional[str] = None,
              fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
              tipo: Optional[str] = None,
              u=Depends(get_user), db: Session = Depends(get_db)):
    q = db.query(Cita)
    if u.rol == "paciente":    q = q.filter(Cita.paciente_id == u.id)
    elif u.rol == "medico":
        p = db.query(MedicoPerfil).filter(MedicoPerfil.usuario_id == u.id).first()
        if p: q = q.filter(Cita.medico_id == p.id)
    if confirmada is not None:
        q = q.filter(Cita.estado == ("confirmada" if confirmada else "pendiente"))
    if fecha_desde: q = q.filter(Cita.fecha >= fecha_desde)
    if fecha_hasta: q = q.filter(Cita.fecha <= fecha_hasta)
    hoy = date.today().isoformat()
    if tipo == "proximas": q = q.filter(Cita.fecha >= hoy)
    elif tipo == "pasadas": q = q.filter(Cita.fecha < hoy)
    resultado = []
    for c in q.order_by(Cita.fecha, Cita.hora).all():
        resultado.append({
            "id": c.id, "paciente_nombre": c.paciente.nombre if c.paciente else "—",
            "medico_nombre": c.medico.usuario.nombre if c.medico and c.medico.usuario else "—",
            "medico_id": c.medico_id, "fecha": c.fecha, "hora": c.hora,
            "motivo": c.motivo, "estado": c.estado, "costo": c.costo,
            "notas_medico": c.notas_medico or "",
            "es_pasada": c.fecha < hoy,
        })
    return {"citas": resultado, "total": len(resultado)}

@app.get("/citas/proxima")
def proxima_cita(u=Depends(get_user), db: Session = Depends(get_db)):
    hoy = date.today().isoformat()
    q = db.query(Cita).filter(Cita.fecha >= hoy, Cita.estado != "cancelada")
    if u.rol == "paciente":
        q = q.filter(Cita.paciente_id == u.id)
    elif u.rol == "medico":
        p = db.query(MedicoPerfil).filter(MedicoPerfil.usuario_id == u.id).first()
        if p: q = q.filter(Cita.medico_id == p.id)
    cita = q.order_by(Cita.fecha, Cita.hora).first()
    if not cita: return {"proxima": None}
    return {"proxima": {
        "id": cita.id, "fecha": cita.fecha, "hora": cita.hora,
        "medico_nombre": cita.medico.usuario.nombre if cita.medico else "—",
        "paciente_nombre": cita.paciente.nombre if cita.paciente else "—",
        "motivo": cita.motivo, "estado": cita.estado,
    }}

@app.post("/citas")
def create_cita(d: CitaCreateReq, u=Depends(get_user), db: Session = Depends(get_db)):
    medico = db.query(MedicoPerfil).filter(MedicoPerfil.id == d.medico_id).first()
    if not medico: raise HTTPException(404, "Medico no encontrado")
    if db.query(Cita).filter(Cita.medico_id == d.medico_id, Cita.fecha == d.fecha,
                              Cita.hora == d.hora, Cita.estado != "cancelada").first():
        raise HTTPException(400, f"El medico ya tiene cita a las {d.hora}")
    cita = Cita(paciente_id=u.id, medico_id=d.medico_id, fecha=d.fecha, hora=d.hora,
                motivo=d.motivo, costo=d.costo, estado="pendiente")
    db.add(cita); db.commit(); db.refresh(cita)
    notif = Notificacion(usuario_id=u.id, cita_id=cita.id, tipo="confirmacion",
                         mensaje=f"Cita agendada con {medico.usuario.nombre} el {d.fecha} a las {d.hora}")
    db.add(notif); db.commit()
    return {"mensaje": "Cita creada", "cita_id": cita.id}

@app.get("/citas/{cita_id}")
def get_cita(cita_id: int, u=Depends(get_user), db: Session = Depends(get_db)):
    c = db.query(Cita).filter(Cita.id == cita_id).first()
    if not c: raise HTTPException(404, "Cita no encontrada")
    return {"id": c.id, "paciente_nombre": c.paciente.nombre,
            "medico_nombre": c.medico.usuario.nombre, "medico_id": c.medico_id,
            "fecha": c.fecha, "hora": c.hora, "motivo": c.motivo,
            "estado": c.estado, "costo": c.costo, "notas_medico": c.notas_medico or ""}

@app.put("/citas/{cita_id}")
def update_cita(cita_id: int, d: CitaUpdateReq, u=Depends(get_user), db: Session = Depends(get_db)):
    c = db.query(Cita).filter(Cita.id == cita_id).first()
    if not c: raise HTTPException(404, "Cita no encontrada")
    if d.fecha:  c.fecha = d.fecha
    if d.hora:   c.hora = d.hora
    if d.motivo: c.motivo = d.motivo
    if d.estado:
        c.estado = d.estado
        if d.estado == "cancelada": c.cancelado_en = datetime.utcnow()
        # Notificar al paciente si medico confirma/cancela
        if u.rol == "medico" and d.estado in ["confirmada", "cancelada"]:
            msg = f"Tu cita del {c.fecha} a las {c.hora} fue {d.estado} por el medico."
            db.add(Notificacion(usuario_id=c.paciente_id, cita_id=c.id, tipo=d.estado, mensaje=msg))
    if d.costo is not None: c.costo = d.costo
    if d.notas_medico is not None: c.notas_medico = d.notas_medico
    db.commit()
    return {"mensaje": "Cita actualizada"}

@app.delete("/citas/{cita_id}")
def delete_cita(cita_id: int, u=Depends(get_user), db: Session = Depends(get_db)):
    c = db.query(Cita).filter(Cita.id == cita_id).first()
    if not c: raise HTTPException(404, "Cita no encontrada")
    db.delete(c); db.commit()
    return {"mensaje": "Cita eliminada"}

# ── Notificaciones ─────────────────────────────────────────────
@app.get("/notificaciones")
def get_notifs(u=Depends(get_user), db: Session = Depends(get_db)):
    n = db.query(Notificacion).filter(Notificacion.usuario_id == u.id)\
        .order_by(Notificacion.creado_en.desc()).limit(20).all()
    return [{"id": x.id, "tipo": x.tipo, "mensaje": x.mensaje, "leida": x.leida,
             "creado_en": x.creado_en.strftime("%Y-%m-%d %H:%M")} for x in n]

@app.put("/notificaciones/{nid}/leer")
def leer_notif(nid: int, u=Depends(get_user), db: Session = Depends(get_db)):
    n = db.query(Notificacion).filter(Notificacion.id == nid, Notificacion.usuario_id == u.id).first()
    if n: n.leida = True; db.commit()
    return {"mensaje": "Marcada como leida"}

@app.put("/notificaciones/leer-todas")
def leer_todas(u=Depends(get_user), db: Session = Depends(get_db)):
    db.query(Notificacion).filter(Notificacion.usuario_id == u.id, Notificacion.leida == False)\
        .update({"leida": True}); db.commit()
    return {"mensaje": "Todas marcadas como leidas"}

# ── Admin ──────────────────────────────────────────────────────
@app.get("/admin/usuarios")
def admin_get_users(u=Depends(admin_only), db: Session = Depends(get_db)):
    return [{"id": x.id, "nombre": x.nombre, "email": x.email, "rol": x.rol,
             "activo": x.activo, "aprobado": x.aprobado,
             "numero_rethus": x.medico_perfil.numero_rethus if x.medico_perfil else "",
             "creado_en": x.creado_en.strftime("%Y-%m-%d")}
            for x in db.query(Usuario).all()]

@app.get("/admin/medicos-pendientes")
def admin_pendientes(u=Depends(admin_only), db: Session = Depends(get_db)):
    ps = db.query(Usuario).filter(Usuario.rol == "medico", Usuario.aprobado == False).all()
    return [{"id": x.id, "nombre": x.nombre, "email": x.email,
             "numero_rethus": x.medico_perfil.numero_rethus if x.medico_perfil else "",
             "especialidad": x.medico_perfil.especialidad.nombre if x.medico_perfil and x.medico_perfil.especialidad else "—",
             "fecha_nacimiento": x.fecha_nacimiento or "",
             "creado_en": x.creado_en.strftime("%Y-%m-%d")} for x in ps]

@app.put("/admin/usuarios/{uid}/aprobar")
def aprobar(uid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    x = db.query(Usuario).filter(Usuario.id == uid).first()
    if not x: raise HTTPException(404, "No encontrado")
    x.aprobado = True; db.commit()
    notif = Notificacion(usuario_id=uid, tipo="aprobacion",
                         mensaje="Tu cuenta de medico ha sido aprobada. Ya puedes iniciar sesion.")
    db.add(notif); db.commit()
    return {"mensaje": f"{x.nombre} aprobado"}

@app.put("/admin/usuarios/{uid}/rechazar")
def rechazar(uid: int, motivo: str = "No cumple los requisitos", u=Depends(admin_only), db: Session = Depends(get_db)):
    x = db.query(Usuario).filter(Usuario.id == uid).first()
    if not x: raise HTTPException(404, "No encontrado")
    db.delete(x); db.commit()
    return {"mensaje": f"Medico rechazado y eliminado"}

@app.put("/admin/usuarios/{uid}/activar")
def activar(uid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    x = db.query(Usuario).filter(Usuario.id == uid).first()
    if not x: raise HTTPException(404, "No encontrado")
    x.activo = not x.activo; db.commit()
    return {"mensaje": f"Usuario {'activado' if x.activo else 'desactivado'}"}

@app.delete("/admin/usuarios/{uid}")
def del_user(uid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    x = db.query(Usuario).filter(Usuario.id == uid).first()
    if not x: raise HTTPException(404, "No encontrado")
    if x.id == u.id: raise HTTPException(400, "No puedes eliminarte")
    db.delete(x); db.commit()
    return {"mensaje": "Eliminado"}

@app.get("/admin/estadisticas")
def admin_stats(u=Depends(admin_only), db: Session = Depends(get_db)):
    hoy = date.today().isoformat()
    return {
        "total_usuarios":    db.query(Usuario).count(),
        "total_pacientes":   db.query(Usuario).filter(Usuario.rol=="paciente").count(),
        "total_medicos":     db.query(Usuario).filter(Usuario.rol=="medico").count(),
        "medicos_pendientes":db.query(Usuario).filter(Usuario.rol=="medico", Usuario.aprobado==False).count(),
        "total_citas":       db.query(Cita).count(),
        "citas_hoy":         db.query(Cita).filter(Cita.fecha==hoy).count(),
        "citas_pendientes":  db.query(Cita).filter(Cita.estado=="pendiente").count(),
        "citas_confirmadas": db.query(Cita).filter(Cita.estado=="confirmada").count(),
        "citas_canceladas":  db.query(Cita).filter(Cita.estado=="cancelada").count(),
        "especialidades":    db.query(Especialidad).count(),
    }
