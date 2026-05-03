from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional
import secrets, smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from database import Usuario, Especialidad, MedicoPerfil, Horario, Cita, Notificacion, get_db, init_db

SECRET_KEY           = os.getenv("SECRET_KEY", "clave-secreta-cambiala-en-produccion")
ALGORITHM            = "HS256"
TOKEN_EXPIRE_MINUTOS = 60
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
APP_URL       = os.getenv("APP_URL", "https://medical-app-camilo-andres.azurewebsites.net")

app = FastAPI(title="CitasMedicas API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

app.mount("/static", StaticFiles(directory="static"), name="static")

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def crear_token(email: str) -> str:
    expira = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTOS)
    return jwt.encode({"sub": email, "exp": expira}, SECRET_KEY, algorithm=ALGORITHM)

async def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email   = payload.get("sub")
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario or not usuario.activo:
            raise HTTPException(status_code=401, detail="Token invalido o usuario inactivo")
        return usuario
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")

def solo_admin(usuario=Depends(obtener_usuario_actual)):
    if usuario.rol != "admin":
        raise HTTPException(status_code=403, detail="Acceso solo para administradores")
    return usuario

def _usuario_dict(u):
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol}

def enviar_correo(destinatario: str, asunto: str, html: str):
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[EMAIL] Sin credenciales. No enviado a {destinatario}")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = f"CitasMedicas <{SMTP_USER}>"
        msg["To"]      = destinatario
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_USER, destinatario, msg.as_string())
    except Exception as e:
        print(f"[EMAIL] Error: {e}")

# ── Modelos Pydantic ───────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class RegistroRequest(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str = "paciente"
    especialidad_id: Optional[int] = None

class OlvidePasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    nueva_password: str

class CambiarPasswordRequest(BaseModel):
    password_actual: str
    nueva_password: str

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[str] = None

class EspecialidadCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class MedicoPerfilCreate(BaseModel):
    especialidad_id: Optional[int] = None
    registro_medico: Optional[str] = None
    consultorio: Optional[str] = None
    tarifa_consulta: float = 0.0

class HorarioCreate(BaseModel):
    dia_semana: int
    hora_inicio: str
    hora_fin: str
    activo: bool = True

class CitaCreate(BaseModel):
    medico_id: int
    fecha: str
    hora: str
    motivo: str
    costo: float = 0.0

class CitaUpdate(BaseModel):
    fecha: Optional[str] = None
    hora: Optional[str] = None
    motivo: Optional[str] = None
    estado: Optional[str] = None
    costo: Optional[float] = None
    notas_medico: Optional[str] = None

# ── Paginas HTML ───────────────────────────────────────────────
@app.get("/")
def home(): return FileResponse("static/login.html")

@app.get("/registro")
def pagina_registro(): return FileResponse("static/registro.html")

@app.get("/dashboard")
def pagina_dashboard(): return FileResponse("static/dashboard.html")

@app.get("/mis-citas")
def pagina_citas(): return FileResponse("static/citas.html")

@app.get("/olvide-password")
def pagina_olvide(): return FileResponse("static/olvide_password.html")

@app.get("/reset-password")
def pagina_reset(): return FileResponse("static/reset_password.html")

@app.get("/admin")
def pagina_admin(): return FileResponse("static/admin.html")

# ── Auth ───────────────────────────────────────────────────────
@app.post("/auth/login")
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario or not pwd_context.verify(datos.password, usuario.password):
        raise HTTPException(status_code=401, detail="Email o contrasena incorrectos")
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    return {"access_token": crear_token(usuario.email), "token_type": "bearer", "usuario": _usuario_dict(usuario)}

@app.post("/auth/registro")
def registro(datos: RegistroRequest, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(status_code=400, detail="Este email ya esta registrado")
    if datos.rol not in ["paciente", "medico"]:
        raise HTTPException(status_code=400, detail="Rol no valido")
    nuevo = Usuario(nombre=datos.nombre, email=datos.email, password=pwd_context.hash(datos.password), rol=datos.rol)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    if datos.rol == "medico":
        perfil = MedicoPerfil(usuario_id=nuevo.id, especialidad_id=datos.especialidad_id)
        db.add(perfil)
        db.commit()
    return {"mensaje": "Registrado", "access_token": crear_token(nuevo.email), "token_type": "bearer", "usuario": _usuario_dict(nuevo)}

@app.post("/auth/olvide-password")
def olvide_password(datos: OlvidePasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if usuario and usuario.activo:
        token = secrets.token_urlsafe(32)
        usuario.reset_token  = token
        usuario.reset_expira = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        enlace = f"{APP_URL}/reset-password?token={token}"
        html = f"<h2>CitasMedicas</h2><p>Hola {usuario.nombre},</p><p><a href='{enlace}'>Restablecer contrasena</a></p><p>Expira en 1 hora.</p>"
        background_tasks.add_task(enviar_correo, usuario.email, "Recuperacion de contrasena", html)
    return {"mensaje": "Si el correo existe, recibiras un enlace para restablecer tu contrasena"}

@app.post("/auth/reset-password")
def reset_password(datos: ResetPasswordRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.reset_token == datos.token).first()
    if not usuario or usuario.reset_expira < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token invalido o expirado")
    if len(datos.nueva_password) < 6:
        raise HTTPException(status_code=400, detail="Minimo 6 caracteres")
    usuario.password = pwd_context.hash(datos.nueva_password)
    usuario.reset_token = None
    usuario.reset_expira = None
    db.commit()
    return {"mensaje": "Contrasena actualizada exitosamente"}

@app.get("/auth/me")
def mi_perfil(usuario=Depends(obtener_usuario_actual)):
    return _usuario_dict(usuario)

@app.put("/auth/me")
def actualizar_perfil(datos: UsuarioUpdate, usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    if datos.nombre: usuario.nombre = datos.nombre
    if datos.telefono: usuario.telefono = datos.telefono
    if datos.fecha_nacimiento: usuario.fecha_nacimiento = datos.fecha_nacimiento
    db.commit()
    return {"mensaje": "Perfil actualizado", "usuario": _usuario_dict(usuario)}

@app.post("/auth/cambiar-password")
def cambiar_password(datos: CambiarPasswordRequest, usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    if not pwd_context.verify(datos.password_actual, usuario.password):
        raise HTTPException(status_code=400, detail="Contrasena actual incorrecta")
    if len(datos.nueva_password) < 6:
        raise HTTPException(status_code=400, detail="Minimo 6 caracteres")
    usuario.password = pwd_context.hash(datos.nueva_password)
    db.commit()
    return {"mensaje": "Contrasena cambiada exitosamente"}

# ── Especialidades ─────────────────────────────────────────────
@app.get("/especialidades")
def listar_especialidades(db: Session = Depends(get_db)):
    return [{"id": e.id, "nombre": e.nombre} for e in db.query(Especialidad).filter(Especialidad.activa == True).all()]

@app.post("/especialidades")
def crear_especialidad(datos: EspecialidadCreate, usuario=Depends(solo_admin), db: Session = Depends(get_db)):
    if db.query(Especialidad).filter(Especialidad.nombre == datos.nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe")
    e = Especialidad(nombre=datos.nombre, descripcion=datos.descripcion)
    db.add(e); db.commit(); db.refresh(e)
    return {"id": e.id, "nombre": e.nombre}

# ── Medicos ────────────────────────────────────────────────────
@app.get("/medicos")
def listar_medicos(db: Session = Depends(get_db)):
    medicos = db.query(MedicoPerfil).join(Usuario).filter(Usuario.activo == True).all()
    return [{
        "id": m.id,
        "nombre": m.usuario.nombre,
        "email": m.usuario.email,
        "especialidad": m.especialidad.nombre if m.especialidad else "Medicina General",
        "consultorio": m.consultorio,
        "tarifa_consulta": m.tarifa_consulta,
    } for m in medicos]

@app.put("/medicos/perfil")
def actualizar_perfil_medico(datos: MedicoPerfilCreate, usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    if usuario.rol != "medico":
        raise HTTPException(status_code=403, detail="Solo medicos")
    perfil = db.query(MedicoPerfil).filter(MedicoPerfil.usuario_id == usuario.id).first()
    if not perfil:
        perfil = MedicoPerfil(usuario_id=usuario.id)
        db.add(perfil)
    if datos.especialidad_id: perfil.especialidad_id = datos.especialidad_id
    if datos.registro_medico: perfil.registro_medico = datos.registro_medico
    if datos.consultorio:     perfil.consultorio = datos.consultorio
    if datos.tarifa_consulta is not None: perfil.tarifa_consulta = datos.tarifa_consulta
    db.commit()
    return {"mensaje": "Perfil medico actualizado"}

# ── Disponibilidad ─────────────────────────────────────────────
@app.get("/disponibilidad")
def verificar_disponibilidad(medico_id: int, fecha: str, db: Session = Depends(get_db)):
    citas = db.query(Cita).filter(Cita.medico_id == medico_id, Cita.fecha == fecha, Cita.estado != "cancelada").all()
    return {"horas_ocupadas": [c.hora for c in citas]}

# ── Citas ──────────────────────────────────────────────────────
@app.get("/citas")
def listar_citas(confirmada: Optional[bool] = None, medico_nombre: Optional[str] = None,
                 usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    query = db.query(Cita)
    if usuario.rol == "paciente":
        query = query.filter(Cita.paciente_id == usuario.id)
    elif usuario.rol == "medico":
        perfil = db.query(MedicoPerfil).filter(MedicoPerfil.usuario_id == usuario.id).first()
        if perfil: query = query.filter(Cita.medico_id == perfil.id)
    if confirmada is not None:
        query = query.filter(Cita.estado == ("confirmada" if confirmada else "pendiente"))
    citas = query.all()
    resultado = []
    for c in citas:
        item = {
            "id": c.id,
            "paciente_nombre": c.paciente.nombre if c.paciente else "—",
            "medico_nombre": c.medico.usuario.nombre if c.medico and c.medico.usuario else "—",
            "medico_id": c.medico_id,
            "fecha": c.fecha, "hora": c.hora, "motivo": c.motivo,
            "estado": c.estado, "confirmada": c.estado == "confirmada",
            "costo": c.costo, "notas_medico": c.notas_medico,
        }
        if medico_nombre and medico_nombre.lower() not in item["medico_nombre"].lower():
            continue
        resultado.append(item)
    return {"citas": resultado, "total": len(resultado)}

@app.post("/citas")
def crear_cita(datos: CitaCreate, usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    medico = db.query(MedicoPerfil).filter(MedicoPerfil.id == datos.medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Medico no encontrado")
    # Verificar disponibilidad
    existente = db.query(Cita).filter(
        Cita.medico_id == datos.medico_id,
        Cita.fecha == datos.fecha,
        Cita.hora == datos.hora,
        Cita.estado != "cancelada"
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"El medico ya tiene una cita a las {datos.hora}")
    cita = Cita(paciente_id=usuario.id, medico_id=datos.medico_id, fecha=datos.fecha,
                hora=datos.hora, motivo=datos.motivo, costo=datos.costo, estado="pendiente")
    db.add(cita); db.commit(); db.refresh(cita)
    notif = Notificacion(usuario_id=usuario.id, cita_id=cita.id, tipo="confirmacion",
                         mensaje=f"Cita agendada con {medico.usuario.nombre} el {datos.fecha} a las {datos.hora}")
    db.add(notif); db.commit()
    return {"mensaje": "Cita creada exitosamente", "cita_id": cita.id}

@app.get("/citas/{cita_id}")
def obtener_cita(cita_id: int, usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    cita = db.query(Cita).filter(Cita.id == cita_id).first()
    if not cita: raise HTTPException(status_code=404, detail="Cita no encontrada")
    return {"id": cita.id, "paciente_nombre": cita.paciente.nombre,
            "medico_nombre": cita.medico.usuario.nombre, "medico_id": cita.medico_id,
            "fecha": cita.fecha, "hora": cita.hora, "motivo": cita.motivo,
            "estado": cita.estado, "costo": cita.costo, "notas_medico": cita.notas_medico}

@app.put("/citas/{cita_id}")
def actualizar_cita(cita_id: int, datos: CitaUpdate, usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    cita = db.query(Cita).filter(Cita.id == cita_id).first()
    if not cita: raise HTTPException(status_code=404, detail="Cita no encontrada")
    if datos.fecha:  cita.fecha = datos.fecha
    if datos.hora:   cita.hora = datos.hora
    if datos.motivo: cita.motivo = datos.motivo
    if datos.estado: cita.estado = datos.estado
    if datos.costo is not None: cita.costo = datos.costo
    if datos.notas_medico: cita.notas_medico = datos.notas_medico
    if datos.estado == "cancelada": cita.cancelado_en = datetime.utcnow()
    db.commit()
    return {"mensaje": "Cita actualizada"}

@app.delete("/citas/{cita_id}")
def eliminar_cita(cita_id: int, usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    cita = db.query(Cita).filter(Cita.id == cita_id).first()
    if not cita: raise HTTPException(status_code=404, detail="Cita no encontrada")
    db.delete(cita); db.commit()
    return {"mensaje": "Cita eliminada"}

# ── Notificaciones ─────────────────────────────────────────────
@app.get("/notificaciones")
def mis_notificaciones(usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    notifs = db.query(Notificacion).filter(Notificacion.usuario_id == usuario.id).order_by(Notificacion.creado_en.desc()).limit(20).all()
    return [{"id": n.id, "tipo": n.tipo, "mensaje": n.mensaje, "leida": n.leida,
             "creado_en": n.creado_en.strftime("%Y-%m-%d %H:%M")} for n in notifs]

# ── Admin ──────────────────────────────────────────────────────
@app.get("/admin/usuarios")
def admin_listar_usuarios(usuario=Depends(solo_admin), db: Session = Depends(get_db)):
    return [{"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol,
             "activo": u.activo, "creado_en": u.creado_en.strftime("%Y-%m-%d")}
            for u in db.query(Usuario).all()]

@app.put("/admin/usuarios/{uid}/activar")
def admin_activar(uid: int, usuario=Depends(solo_admin), db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.id == uid).first()
    if not u: raise HTTPException(status_code=404, detail="No encontrado")
    u.activo = not u.activo; db.commit()
    return {"mensaje": f"Usuario {'activado' if u.activo else 'desactivado'}"}

@app.delete("/admin/usuarios/{uid}")
def admin_eliminar(uid: int, usuario=Depends(solo_admin), db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.id == uid).first()
    if not u: raise HTTPException(status_code=404, detail="No encontrado")
    if u.id == usuario.id: raise HTTPException(status_code=400, detail="No puedes eliminarte")
    db.delete(u); db.commit()
    return {"mensaje": "Usuario eliminado"}

@app.get("/admin/estadisticas")
def admin_estadisticas(usuario=Depends(solo_admin), db: Session = Depends(get_db)):
    return {
        "total_usuarios":    db.query(Usuario).count(),
        "total_pacientes":   db.query(Usuario).filter(Usuario.rol == "paciente").count(),
        "total_medicos":     db.query(Usuario).filter(Usuario.rol == "medico").count(),
        "total_citas":       db.query(Cita).count(),
        "citas_pendientes":  db.query(Cita).filter(Cita.estado == "pendiente").count(),
        "citas_confirmadas": db.query(Cita).filter(Cita.estado == "confirmada").count(),
        "citas_canceladas":  db.query(Cita).filter(Cita.estado == "cancelada").count(),
        "especialidades":    db.query(Especialidad).count(),
    }
