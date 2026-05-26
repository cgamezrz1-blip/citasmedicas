from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_login_fallido_credenciales():
    res = client.post("/auth/login", json={"email": "noexiste@gmail.com", "password": "wrongpass"})
    assert res.status_code == 401

def test_login_password_corta():
    res = client.post("/auth/login", json={"email": "test@test.com", "password": "abc"})
    assert res.status_code == 422

def test_get_especialidades():
    res = client.get("/especialidades")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_get_tarifa_strategy():
    res = client.get("/especialidades/1/tarifa")
    assert res.status_code == 200
    assert "tarifa" in res.json()

def test_registro_email_duplicado():
    res = client.post("/auth/registro", json={
        "nombre": "Test", "email": "p1@gmail.com", "password": "Test123!",
        "rol": "paciente", "fecha_nacimiento": "2000-01-01",
        "pregunta_seguridad": "mascota", "respuesta_seguridad": "test"
    })
    assert res.status_code == 400

def test_especialidad_no_existe():
    res = client.get("/especialidades/9999/tarifa")
    assert res.status_code == 404
