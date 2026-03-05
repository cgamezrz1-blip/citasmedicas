from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from typing import Optional

# ── Configuración ──────────────────────────────────────────────
SECRET_KEY = "clave-secreta-cambiala-en-produccion"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTOS = 30

app = FastAPI(title="CitasMédicas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Servir archivos estáticos ──────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Utilidades ─────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ── Usuarios en memoria ────────────────────────────────────────
usuarios_db = {
    "doctor@citasmedicas.com": {
        "id": 1,
        "nombre": "Dr. Carlos García",
        "email": "doctor@citasmedicas.com",
        "rol": "medico",
        "password": pwd_context.hash("password123"),
    },
    "paciente@citasmedicas.com": {
        "id": 2,
        "nombre": "María López",
        "email": "paciente@citasmedicas.com",
        "rol": "paciente",
        "password": pwd_context.hash("password123"),
    },
}

# ── Modelos ────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class RegistroRequest(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str = "paciente"

# ── Funciones de autenticación ─────────────────────────────────
def autenticar_usuario(email: str, password: str):
    usuario = usuarios_db.get(email)
    if not usuario:
        return None
    if not pwd_context.verify(password, usuario["password"]):
        return None
    return usuario

def crear_token(email: str) -> str:
    expira = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTOS)
    return jwt.encode({"sub": email, "exp": expira}, SECRET_KEY, algorithm=ALGORITHM)

async def obtener_usuario_actual(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        usuario = usuarios_db.get(email)
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

# ── Rutas de autenticación ─────────────────────────────────────
@app.post("/auth/login")
def login(datos: LoginRequest):
    usuario = autenticar_usuario(datos.email, datos.password)
    if not usuario:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    token = crear_token(usuario["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario["id"],
            "nombre": usuario["nombre"],
            "email": usuario["email"],
            "rol": usuario["rol"],
        }
    }

@app.post("/auth/registro")
def registro(datos: RegistroRequest):
    if datos.email in usuarios_db:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    roles_permitidos = ["paciente", "medico"]
    if datos.rol not in roles_permitidos:
        raise HTTPException(status_code=400, detail="Rol no válido")

    nuevo_id = len(usuarios_db) + 1
    usuarios_db[datos.email] = {
        "id": nuevo_id,
        "nombre": datos.nombre,
        "email": datos.email,
        "rol": datos.rol,
        "password": pwd_context.hash(datos.password),
    }

    token = crear_token(datos.email)
    return {
        "mensaje": "Usuario registrado exitosamente",
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": nuevo_id,
            "nombre": datos.nombre,
            "email": datos.email,
            "rol": datos.rol,
        }
    }

@app.get("/auth/me")
def mi_perfil(usuario=Depends(obtener_usuario_actual)):
    return {
        "id": usuario["id"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "rol": usuario["rol"],
    }

@app.get("/auth/usuarios")
def listar_usuarios(usuario=Depends(obtener_usuario_actual)):
    return [
        {"id": u["id"], "nombre": u["nombre"], "email": u["email"], "rol": u["rol"]}
        for u in usuarios_db.values()
    ]