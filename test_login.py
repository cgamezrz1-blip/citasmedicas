"""
Tests para la funcionalidad de Login
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Usuario
from app.auth import hash_password

# Base de datos en memoria solo para tests
DATABASE_TEST_URL = "sqlite:///./test.db"
engine_test = create_engine(DATABASE_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Sobreescribir la dependencia de BD para tests
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Crea y destruye las tablas antes y después de cada test."""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def usuario_en_db():
    """Crea un usuario de prueba en la base de datos."""
    db = TestingSessionLocal()
    usuario = Usuario(
        nombre="Juan Pérez",
        email="juan@ejemplo.com",
        hashed_password=hash_password("password123"),
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    db.close()
    return usuario


# ─────────────────────────────────────────────
# TESTS DE LOGIN EXITOSO
# ─────────────────────────────────────────────

class TestLoginExitoso:

    def test_login_retorna_token(self, client, usuario_en_db):
        """Login con credenciales correctas debe retornar un token JWT."""
        response = client.post("/auth/login", json={
            "email": "juan@ejemplo.com",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_token_no_vacio(self, client, usuario_en_db):
        """El token retornado no debe estar vacío."""
        response = client.post("/auth/login", json={
            "email": "juan@ejemplo.com",
            "password": "password123"
        })
        data = response.json()
        assert len(data["access_token"]) > 0


# ─────────────────────────────────────────────
# TESTS DE LOGIN FALLIDO
# ─────────────────────────────────────────────

class TestLoginFallido:

    def test_password_incorrecto(self, client, usuario_en_db):
        """Login con password incorrecto debe retornar 401."""
        response = client.post("/auth/login", json={
            "email": "juan@ejemplo.com",
            "password": "password_WRONG"
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Credenciales incorrectas"

    def test_email_no_existe(self, client):
        """Login con email que no existe debe retornar 401."""
        response = client.post("/auth/login", json={
            "email": "noexiste@ejemplo.com",
            "password": "cualquier_cosa"
        })
        assert response.status_code == 401

    def test_usuario_inactivo(self, client):
        """Login con usuario inactivo debe retornar 401."""
        db = TestingSessionLocal()
        usuario_inactivo = Usuario(
            nombre="Ana Inactiva",
            email="ana@ejemplo.com",
            hashed_password=hash_password("password123"),
            activo=False,
        )
        db.add(usuario_inactivo)
        db.commit()
        db.close()

        response = client.post("/auth/login", json={
            "email": "ana@ejemplo.com",
            "password": "password123"
        })
        assert response.status_code == 401

    def test_email_formato_invalido(self, client):
        """Email con formato inválido debe retornar 422."""
        response = client.post("/auth/login", json={
            "email": "esto-no-es-un-email",
            "password": "password123"
        })
        assert response.status_code == 422

    def test_campos_vacios(self, client):
        """Request sin campos debe retornar 422."""
        response = client.post("/auth/login", json={})
        assert response.status_code == 422


# ─────────────────────────────────────────────
# TESTS DEL TOKEN JWT
# ─────────────────────────────────────────────

class TestToken:

    def test_token_es_jwt_valido(self, client, usuario_en_db):
        """El token retornado debe ser un JWT decodificable."""
        from app.auth import verificar_token

        response = client.post("/auth/login", json={
            "email": "juan@ejemplo.com",
            "password": "password123"
        })
        token = response.json()["access_token"]
        payload = verificar_token(token)

        assert payload is not None
        assert payload["sub"] == "juan@ejemplo.com"

    def test_token_contiene_id_usuario(self, client, usuario_en_db):
        """El token debe contener el ID del usuario."""
        from app.auth import verificar_token

        response = client.post("/auth/login", json={
            "email": "juan@ejemplo.com",
            "password": "password123"
        })
        token = response.json()["access_token"]
        payload = verificar_token(token)

        assert "id" in payload
        assert payload["id"] == usuario_en_db.id
