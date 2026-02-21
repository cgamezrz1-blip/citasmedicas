# 🏥 Gestión de Citas Médicas

API REST para gestión de citas médicas construida con FastAPI y SQLite.

## Stack

- **Backend:** FastAPI
- **Base de datos:** SQLite + SQLAlchemy
- **Autenticación:** JWT (python-jose) + bcrypt
- **Testing:** pytest + httpx

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/gestion-citas-medicas.git
cd gestion-citas-medicas

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Correr el servidor

```bash
uvicorn app.main:app --reload
```

La API estará disponible en: http://localhost:8000  
Documentación interactiva: http://localhost:8000/docs

## Correr los tests

```bash
pytest -v
```

## Endpoints

### Auth

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/login` | Login y obtención de JWT |

### Ejemplo de login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@ejemplo.com", "password": "mi_password"}'
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

## Estructura del proyecto

```
gestion-citas-medicas/
├── app/
│   ├── __init__.py
│   ├── main.py          # App principal FastAPI
│   ├── database.py      # Configuración SQLite
│   ├── models.py        # Modelos SQLAlchemy
│   ├── schemas.py       # Schemas Pydantic
│   ├── auth.py          # Lógica de autenticación JWT
│   └── routers/
│       ├── __init__.py
│       └── login.py     # Endpoint de login
├── tests/
│   ├── __init__.py
│   └── test_login.py    # Tests del login
├── requirements.txt
├── pyproject.toml
└── README.md
```
