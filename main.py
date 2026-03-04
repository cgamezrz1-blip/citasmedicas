from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
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

# ── Utilidades ─────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ── Usuarios en memoria (sin base de datos) ────────────────────
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

class Token(BaseModel):
    access_token: str
    token_type: str
    usuario: dict

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

# ── Rutas ──────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"mensaje": "CitasMédicas API - v1.0.0"}

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

@app.get("/auth/me")
def mi_perfil(usuario=Depends(obtener_usuario_actual)):
    return {
        "id": usuario["id"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "rol": usuario["rol"],
    }

@app.get("/prueba")
def evento_prueba():
    return {"eventos": ["city js", "devops day", "epam talks"]}