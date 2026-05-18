"""
routers/__init__.py
Exporta todos los routers para importacion limpia en main.py.
"""
from routers import auth_router, citas_router, admin_router, notif_router

__all__ = ["auth_router", "citas_router", "admin_router", "notif_router"]
