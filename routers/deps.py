"""
routers/deps.py
Dependencias compartidas entre todos los routers.
Resuelve: R0801 (codigo duplicado de get_user en 4 routers).
"""
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from adapters.auth_adapter import auth_adapter

oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    """
    Dependencia compartida — verifica el token JWT.
    Patron 3 — Adapter: usa AuthServicePort, no jose.jwt directamente.
    """
    try:
        email = auth_adapter.verificar_token(token)
        u = db.query(Usuario).filter(Usuario.email == email).first()
        if not u or not u.activo:
            raise HTTPException(401, "Token invalido o usuario inactivo")
        return u
    except ValueError as exc:
        raise HTTPException(401, "Token invalido o expirado") from exc


def admin_only(u: Usuario = Depends(get_user)):
    """
    Dependencia de admin — verifica rol usando get_rol() polimorfco.
    Patron 1 — Factory Method: usa metodo de la interfaz, no strings.
    """
    if u.get_rol() != "admin":
        raise HTTPException(403, "Solo administradores")
    return u
