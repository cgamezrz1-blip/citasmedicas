"""
Patron 3 — Adapter
Archivo: adapters/auth_adapter.py
Resuelve: DIP en main.py L33-L36 (CryptContext y jwt instanciados directamente)
"""
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext


class AuthServicePort(ABC):
    """
    Interfaz (Puerto) — define el contrato de autenticacion.
    La aplicacion depende de esta abstraccion, no de librerias concretas.
    Cambiar de python-jose a PyJWT = crear nuevo Adapter, sin tocar main.py.
    """

    @abstractmethod
    def crear_token(self, email: str) -> str:
        """Crea un token JWT para el email dado."""

    @abstractmethod
    def verificar_token(self, token: str) -> str:
        """Verifica el token y retorna el email. Lanza excepcion si invalido."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hashea una contrasena usando bcrypt."""

    @abstractmethod
    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verifica si la contrasena plana coincide con el hash."""


class BaseAdapter(ABC):
    """
    Clase Abstracta Base — inicializa las librerias externas.
    Sirve como punto de extension para otros adapters.
    """

    @abstractmethod
    def _init_libs(self) -> None:
        """Inicializa las librerias externas necesarias."""

    @abstractmethod
    def crear_token(self, email: str) -> str:
        """Crear token JWT."""

    @abstractmethod
    def verificar_token(self, token: str) -> str:
        """Verificar token JWT."""


class JoseJWTAdapter(BaseAdapter, AuthServicePort):
    """
    Adapter Concreto — adapta python-jose y passlib a AuthServicePort.
    Si se cambia la libreria, solo se crea un nuevo Adapter.
    main.py no necesita modificarse.
    """

    def __init__(self):
        self._secret = os.getenv("SECRET_KEY", "clave-secreta-cambiala-en-produccion")
        self._algorithm = "HS256"
        self._expire_minutes = 60
        self._pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._init_libs()

    def _init_libs(self) -> None:
        """Verifica que las librerias esten disponibles."""
        _ = jwt
        _ = CryptContext

    def crear_token(self, email: str) -> str:
        """Crea token JWT usando python-jose."""
        expira = datetime.utcnow() + timedelta(minutes=self._expire_minutes)
        return jwt.encode(
            {"sub": email, "exp": expira},
            self._secret,
            algorithm=self._algorithm
        )

    def verificar_token(self, token: str) -> str:
        """Verifica token JWT usando python-jose."""
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            email = payload.get("sub")
            if not email:
                raise ValueError("Token sin email")
            return email
        except JWTError as exc:
            raise ValueError("Token invalido o expirado") from exc

    def hash_password(self, password: str) -> str:
        """Hashea contrasena usando passlib/bcrypt."""
        return self._pwd_ctx.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verifica contrasena usando passlib/bcrypt."""
        return self._pwd_ctx.verify(plain, hashed)


# Instancia global — inyectable como dependencia
auth_adapter: AuthServicePort = JoseJWTAdapter()
