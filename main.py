"""
main.py — DESPUES de refactorizacion con 5 patrones GoF
Responsabilidad unica: configuracion y montaje de la aplicacion (SRP)

ANTES: 415 lineas mezclando auth + citas + admin + notificaciones + HTML
DESPUES: 68 lineas — solo configuracion, middleware y montaje de routers

Estructura refactorizada:
    routers/auth_router.py      — endpoints de autenticacion
    routers/citas_router.py     — endpoints de citas
    routers/admin_router.py     — endpoints de administracion
    routers/notif_router.py     — endpoints de notificaciones
    adapters/auth_adapter.py    — Patron 3: Adapter
    services/usuario_factory.py — Patron 1: Factory Method
    services/citas_facade.py    — Patron 2: Facade
    observers/cita_observers.py — Patron 4: Observer
    strategies/cost_strategy.py — Patron 5: Strategy
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import engine
from models import Base
from seed import run_seed
from routers import auth_router, citas_router, admin_router, notif_router

app = FastAPI(title="CitasMedicas API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """Inicializa la BD y ejecuta el seed de datos iniciales."""
    Base.metadata.create_all(bind=engine)
    run_seed()


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(citas_router.router, prefix="", tags=["Citas"])
app.include_router(admin_router.router, prefix="/admin", tags=["Admin"])
app.include_router(notif_router.router, prefix="/notificaciones", tags=["Notificaciones"])


@app.get("/")
def home(request: Request):
    """Renderiza la pagina de login con Jinja2."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/registro")
def reg(request: Request):
    """Renderiza la pagina de registro."""
    return templates.TemplateResponse("registro.html", {"request": request})


@app.get("/dashboard")
def dash(request: Request):
    """Renderiza el dashboard principal."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/mis-citas")
def citas_pg(request: Request):
    """Renderiza la pagina de citas."""
    return templates.TemplateResponse("citas.html", {"request": request})


@app.get("/olvide-password")
def olvide(request: Request):
    """Renderiza la pagina de recuperacion de contrasena."""
    return templates.TemplateResponse("olvide_password.html", {"request": request})


@app.get("/admin")
def admin_pg(request: Request):
    """Renderiza el panel de administracion."""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/404")
def not_found():
    """Renderiza la pagina 404."""
    return FileResponse("static/404.html")


@app.exception_handler(404)
async def custom_404(request: Request, _exc: Exception):
    """Maneja errores 404 — retorna JSON para API y HTML para paginas."""
    if request.url.path.startswith(("/auth/", "/admin/", "/citas", "/notificaciones",
                                    "/especialidades", "/medicos", "/disponibilidad")):
        return JSONResponse(status_code=404, content={"detail": "No encontrado"})
    return FileResponse("static/404.html", status_code=404)
