from fastapi import FastAPI

from app.database import Base, engine
from app.routers import login

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gestión de Citas Médicas",
    description="API para gestionar citas médicas",
    version="0.1.0",
)

app.include_router(login.router)


@app.get("/")
def root():
    return {"mensaje": "API de Gestión de Citas Médicas"}
