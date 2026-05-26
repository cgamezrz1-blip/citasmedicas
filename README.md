# 🏥 CitasMédicas

Sistema de gestión de citas médicas desarrollado con FastAPI, PostgreSQL y 5 patrones de diseño GoF.

**URL Producción:** https://medical-app-camilo-andres.azurewebsites.net  
**Repositorio:** https://github.com/cgamezrz1-blip/citasmedicas (rama: `azure_deploy`)

---

## 🚀 Setup del Entorno Virtual

### Requisitos previos
- Python 3.12+
- PostgreSQL 16 (local o remoto)
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/cgamezrz1-blip/citasmedicas.git
cd citasmedicas
git checkout azure_deploy
```

### 2. Crear y activar el entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar en Linux/Mac
source venv/bin/activate

# Activar en Windows
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar la base de datos

El archivo `database.py` ya tiene la URL de conexión a PostgreSQL configurada por defecto:

```
Host: citasmedicas-pg-2026.postgres.database.azure.com
DB:   citasmedicas
```

Para usar una BD local, edita `database.py` y cambia `DATABASE_URL`:

```python
DATABASE_URL = "postgresql://usuario:password@localhost:5432/citasmedicas"
```

### 5. Ejecutar la aplicación

```bash
uvicorn main:app --reload --port 8000
```

La aplicación estará disponible en: http://localhost:8000

---

## 👤 Credenciales de prueba

| Rol | Email | Contraseña |
|-----|-------|------------|
| Admin | admin@citasmedicas.com | Admin123! |
| Médico | d1@gmail.com | Test123! |
| Médico | d2@gmail.com | Test123! |
| Paciente | p1@gmail.com | Test123! |
| Paciente | p2@gmail.com | Test123! |

---

## 🧪 Ejecutar Pruebas

```bash
pytest tests/ -v
```

Resultado esperado: **6 passed**

---

## 📁 Estructura del Proyecto

```
citasmedicas/
├── main.py                     # Configuración y montaje (SRP)
├── database.py                 # Conexión PostgreSQL
├── models.py                   # Modelos ORM con UsuarioMixin
├── seed.py                     # Datos iniciales
├── requirements.txt            # Dependencias
├── routers/
│   ├── auth_router.py          # Endpoints de autenticación
│   ├── citas_router.py         # Endpoints de citas
│   ├── admin_router.py         # Endpoints de administración
│   ├── notif_router.py         # Endpoints de notificaciones
│   └── deps.py                 # Dependencias compartidas
├── adapters/
│   └── auth_adapter.py         # Patrón Adapter — JWT y bcrypt
├── services/
│   ├── usuario_factory.py      # Patrón Factory Method
│   └── citas_facade.py         # Patrón Facade
├── observers/
│   └── cita_observers.py       # Patrón Observer
├── strategies/
│   └── cost_strategy.py        # Patrón Strategy
├── static/
│   ├── login.html
│   ├── registro.html
│   ├── dashboard.html
│   ├── citas.html
│   └── admin.html
└── tests/
    └── test_citasmedicas.py    # Pruebas automatizadas Pytest
```

---

## 🎨 5 Patrones de Diseño GoF Implementados

| # | Patrón | Archivo | Resuelve |
|---|--------|---------|----------|
| 1 | Factory Method | `services/usuario_factory.py` | Creación de usuarios por rol sin if/else |
| 2 | Facade | `services/citas_facade.py` | Simplifica main.py de 415 → 60 líneas |
| 3 | Adapter | `adapters/auth_adapter.py` | JWT y bcrypt desacoplados |
| 4 | Observer | `observers/cita_observers.py` | Notificaciones al crear citas |
| 5 | Strategy | `strategies/cost_strategy.py` | Tarifas intercambiables por especialidad |

---

## 🔌 API Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /auth/login | Autenticación JWT |
| POST | /auth/registro | Registro de usuarios |
| GET | /citas | Listar citas del usuario |
| POST | /citas | Crear nueva cita |
| PUT | /citas/{id} | Actualizar cita |
| DELETE | /citas/{id} | Eliminar cita |
| GET | /especialidades | Listar especialidades |
| GET | /especialidades/{id}/tarifa | Tarifa por especialidad (Strategy) |
| GET | /admin/estadisticas | Estadísticas del sistema |
| GET | /notificaciones | Notificaciones del usuario |

Documentación interactiva disponible en: http://localhost:8000/docs

---

## ☁️ CI/CD y Despliegue

Cada `git push` a la rama `azure_deploy` dispara automáticamente GitHub Actions y despliega en **Azure App Service**.

- **Plataforma:** Microsoft Azure App Service
- **BD:** PostgreSQL 16 en Azure
- **CI/CD:** GitHub Actions (`.github/workflows/`)

---

## 📊 Resultados de Calidad

- **Pylint:** 9.74/10 (mejorado desde 5.98/10, +3.76 puntos)
- **SOLID:** 18 violaciones resueltas → 0
- **Pytest:** 6/6 pruebas passing
- **Producción:** 7/7 endpoints verificados en Azure
