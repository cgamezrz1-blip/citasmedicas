from fastapi import FastAPI, HTTPException, Depends
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
from database import Usuario, get_db, init_db

# ── Configuración ──────────────────────────────────────────────
SECRET_KEY = "clave-secreta-cambiala-en-produccion"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTOS = 60

app = FastAPI(title="CitasMédicas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Inicializar base de datos al arrancar ──────────────────────
@app.on_event("startup")
def startup():
    init_db()

# ── Servir archivos estáticos ──────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Utilidades ─────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ── Modelos de autenticación ───────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class RegistroRequest(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str = "paciente"

# ── Modelo de Cita (Pydantic) ──────────────────────────────────
class Cita(BaseModel):
    id: Optional[int] = None   # entero
    paciente_nombre: str        # string
    medico_nombre: str          # string
    fecha: str                  # string (formato: YYYY-MM-DD)
    hora: str                   # string (formato: HH:MM)
    motivo: str                 # string
    confirmada: bool = False    # booleano
    costo: float = 0.0          # float

# ── Base de datos temporal de citas ───────────────────────────
citas_db: list = []
contador_id: int = 1

# ── Funciones de autenticación ─────────────────────────────────
def crear_token(email: str) -> str:
    expira = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTOS)
    return jwt.encode({"sub": email, "exp": expira}, SECRET_KEY, algorithm=ALGORITHM)

async def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            raise HTTPException(status_code=401, detail="Token inválido")
        return usuario
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

# ── Rutas de páginas HTML ──────────────────────────────────────
@app.get("/")
def home():
    return FileResponse("static/login.html")

@app.get("/registro")
def pagina_registro():
    return FileResponse("static/registro.html")

@app.get("/dashboard")
def pagina_dashboard():
    return FileResponse("static/dashboard.html")

@app.get("/mis-citas")
def pagina_citas():
    return FileResponse("static/citas.html")

# ── Rutas de autenticación ─────────────────────────────────────
@app.post("/auth/login")
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario or not pwd_context.verify(datos.password, usuario.password):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    token = crear_token(usuario.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
        }
    }

@app.post("/auth/registro")
def registro(datos: RegistroRequest, db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    if datos.rol not in ["paciente", "medico"]:
        raise HTTPException(status_code=400, detail="Rol no válido")

    nuevo = Usuario(
        nombre=datos.nombre,
        email=datos.email,
        password=pwd_context.hash(datos.password),
        rol=datos.rol,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    token = crear_token(nuevo.email)
    return {
        "mensaje": "Usuario registrado exitosamente",
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": nuevo.id,
            "nombre": nuevo.nombre,
            "email": nuevo.email,
            "rol": nuevo.rol,
        }
    }

@app.get("/auth/me")
def mi_perfil(usuario=Depends(obtener_usuario_actual)):
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
    }

@app.get("/auth/usuarios")
def listar_usuarios(usuario=Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    usuarios = db.query(Usuario).all()
    return [
        {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol}
        for u in usuarios
    ]

# ── CRUD de Citas ──────────────────────────────────────────────

# 1. GET todos con filtros opcionales (Query Parameters)
@app.get("/citas")
def listar_citas(
    confirmada: Optional[bool] = None,
    medico_nombre: Optional[str] = None
):
    resultado = citas_db

    if confirmada is not None:
        resultado = [c for c in resultado if c["confirmada"] == confirmada]

    if medico_nombre:
        resultado = [c for c in resultado if medico_nombre.lower() in c["medico_nombre"].lower()]

    return {"citas": resultado, "total": len(resultado)}

# 2. POST crear cita (usa .dict() para guardar en la lista)
@app.post("/citas")
def crear_cita(cita: Cita):
    global contador_id
    cita.id = contador_id
    contador_id += 1
    citas_db.append(cita.dict())
    return {"mensaje": "Cita creada exitosamente", "cita": cita}

# 3. GET por ID (Path Parameter)
@app.get("/citas/{id}")
def obtener_cita(id: int):
    cita = next((c for c in citas_db if c["id"] == id), None)
    # 4. HTTPException 404 si no existe
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita

# PUT actualizar cita
@app.put("/citas/{id}")
def actualizar_cita(id: int, datos: Cita):
    for i, c in enumerate(citas_db):
        if c["id"] == id:
            datos.id = id
            citas_db[i] = datos.dict()
            return {"mensaje": "Cita actualizada", "cita": citas_db[i]}
    raise HTTPException(status_code=404, detail="Cita no encontrada")

# DELETE eliminar cita
@app.delete("/citas/{id}")
def eliminar_cita(id: int):
    for i, c in enumerate(citas_db):
        if c["id"] == id:
            citas_db.pop(i)
            return {"mensaje": "Cita eliminada exitosamente"}
    raise HTTPException(status_code=404, detail="Cita no encontrada")
