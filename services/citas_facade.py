"""
Patron 2 — Facade
Archivo: services/citas_facade.py
Resuelve: SRP en main.py L1-L415 (archivo dios con 415 lineas)
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import Usuario, Cita, Notificacion, MedicoPerfil
from adapters.auth_adapter import AuthServicePort, JoseJWTAdapter
from observers.cita_observers import CitaEventPublisher, NotificacionObserver, LogObserver
from strategies.cost_strategy import CitaService, TarifaFijaStrategy


class AuthService:
    """
    Subsistema de autenticacion.
    Responsabilidad unica: gestionar login, registro y tokens.
    """

    def __init__(self, auth: AuthServicePort = None):
        self._auth = auth or JoseJWTAdapter()

    def login(self, email: str, password: str, db: Session) -> dict:
        """Autentica un usuario y retorna el token JWT."""
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario or not self._auth.verify_password(password, usuario.password):
            raise HTTPException(401, "Email o contrasena incorrectos")
        if not usuario.activo:
            raise HTTPException(403, "Usuario inactivo")
        if usuario.rol == "medico" and not usuario.aprobado:
            raise HTTPException(403, "Cuenta pendiente de aprobacion")
        token = self._auth.crear_token(usuario.email)
        return {"access_token": token, "token_type": "bearer",
                "usuario": {"id": usuario.id, "nombre": usuario.nombre,
                            "email": usuario.email, "rol": usuario.rol}}

    def verificar_token(self, token: str, db: Session) -> Usuario:
        """Verifica el token y retorna el usuario autenticado."""
        try:
            email = self._auth.verificar_token(token)
            usuario = db.query(Usuario).filter(Usuario.email == email).first()
            if not usuario or not usuario.activo:
                raise HTTPException(401, "Token invalido")
            return usuario
        except ValueError as exc:
            raise HTTPException(401, "Token invalido o expirado") from exc

    def hash_password(self, password: str) -> str:
        """Hashea una contrasena usando el adapter."""
        return self._auth.hash_password(password)


class CitaServiceFacade:
    """
    Subsistema de citas.
    Responsabilidad unica: gestionar CRUD de citas medicas.
    """

    def __init__(self):
        self._cost = CitaService(TarifaFijaStrategy())
        self._publisher = CitaEventPublisher()
        self._publisher.suscribir(NotificacionObserver())
        self._publisher.suscribir(LogObserver())

    def crear_cita(self, datos, usuario: Usuario, db: Session) -> dict:
        """Crea una cita y notifica via Observer."""
        medico = db.query(MedicoPerfil).filter(MedicoPerfil.id == datos.medico_id).first()
        if not medico:
            raise HTTPException(404, "Medico no encontrado")
        existente = db.query(Cita).filter(
            Cita.medico_id == datos.medico_id,
            Cita.fecha == datos.fecha,
            Cita.hora == datos.hora,
            Cita.estado != "cancelada"
        ).first()
        if existente:
            raise HTTPException(400, f"El medico ya tiene cita a las {datos.hora}")
        cita = Cita(
            paciente_id=usuario.id,
            medico_id=datos.medico_id,
            fecha=datos.fecha,
            hora=datos.hora,
            motivo=datos.motivo,
            costo=datos.costo,
            estado="pendiente"
        )
        db.add(cita)
        db.commit()
        db.refresh(cita)
        self._publisher.notificar(cita, usuario, db)
        return {"mensaje": "Cita creada", "cita_id": cita.id}

    def get_citas(self, usuario: Usuario, db: Session) -> dict:
        """Retorna las citas segun el rol del usuario."""
        query = db.query(Cita)
        if usuario.rol == "paciente":
            query = query.filter(Cita.paciente_id == usuario.id)
        elif usuario.rol == "medico":
            perfil = db.query(MedicoPerfil).filter(
                MedicoPerfil.usuario_id == usuario.id).first()
            if perfil:
                query = query.filter(Cita.medico_id == perfil.id)
        citas = query.order_by(Cita.fecha, Cita.hora).all()
        return {"citas": [{
            "id": c.id,
            "fecha": c.fecha,
            "hora": c.hora,
            "estado": c.estado,
            "motivo": c.motivo,
            "costo": c.costo,
            "medico_nombre": c.medico.usuario.nombre if c.medico and c.medico.usuario else "—",
            "paciente_nombre": c.paciente.nombre if c.paciente else "—",
            "especialidad": c.medico.get_especialidad() if c.medico else "—",
            "medico_id": c.medico_id,
            "paciente_id": c.paciente_id,
            "notas_medico": c.notas_medico or "",
        } for c in citas]}


class AdminService:
    """
    Subsistema de administracion.
    Responsabilidad unica: gestionar usuarios y estadisticas.
    """

    def get_usuarios(self, db: Session) -> list:
        """Retorna todos los usuarios del sistema."""
        return [{"id": u.id, "nombre": u.nombre, "email": u.email,
                 "rol": u.rol, "activo": u.activo, "aprobado": u.aprobado}
                for u in db.query(Usuario).all()]

    def aprobar_medico(self, uid: int, db: Session) -> dict:
        """Aprueba un medico pendiente."""
        usuario = db.query(Usuario).filter(Usuario.id == uid).first()
        if not usuario:
            raise HTTPException(404, "No encontrado")
        usuario.aprobado = True
        db.commit()
        return {"mensaje": f"{usuario.nombre} aprobado"}

    def get_estadisticas(self, db: Session) -> dict:
        """Retorna estadisticas generales del sistema."""
        return {
            "total_usuarios": db.query(Usuario).count(),
            "total_citas":    db.query(Cita).count(),
            "total_medicos":  db.query(Usuario).filter(Usuario.rol == "medico").count(),
        }


class NotificacionService:
    """
    Subsistema de notificaciones.
    Responsabilidad unica: gestionar notificaciones del sistema.
    """

    def get_notificaciones(self, usuario: Usuario, db: Session) -> list:
        """Retorna las notificaciones del usuario."""
        notifs = db.query(Notificacion).filter(
            Notificacion.usuario_id == usuario.id
        ).order_by(Notificacion.creado_en.desc()).limit(20).all()
        return [{"id": n.id, "mensaje": n.mensaje, "leida": n.leida,
                 "tipo": n.tipo,
                 "creado_en": n.creado_en.isoformat() if n.creado_en else None}
                for n in notifs]

    def marcar_leida(self, nid: int, usuario: Usuario, db: Session) -> dict:
        """Marca una notificacion como leida."""
        n = db.query(Notificacion).filter(
            Notificacion.id == nid,
            Notificacion.usuario_id == usuario.id
        ).first()
        if n:
            n.leida = True; db.commit()
        return {"mensaje": "Marcada como leida"}


class CitasMedicasFacade:
    """
    Fachada principal — punto unico de entrada al sistema.
    main.py solo conoce CitasMedicasFacade, no los subsistemas.
    Composicion: gestiona el ciclo de vida de los 4 subsistemas.
    """

    def __init__(self):
        self.auth  = AuthService()
        self.citas = CitaServiceFacade()
        self.admin = AdminService()
        self.notif = NotificacionService()

    def login(self, datos, db: Session) -> dict:
        """Delega el login al AuthService."""
        return self.auth.login(datos.email, datos.password, db)

    def agendar_cita(self, datos, usuario: Usuario, db: Session) -> dict:
        """Delega el agendamiento al CitaServiceFacade."""
        return self.citas.crear_cita(datos, usuario, db)

    def get_notificaciones(self, usuario: Usuario, db: Session) -> list:
        """Delega al NotificacionService."""
        return self.notif.get_notificaciones(usuario, db)

    def get_estadisticas(self, db: Session) -> dict:
        """Delega al AdminService."""
        return self.admin.get_estadisticas(db)


# Instancia global de la fachada
facade = CitasMedicasFacade()
