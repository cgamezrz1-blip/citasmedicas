"""
Patron 4 — Observer
Archivo: observers/cita_observers.py
Resuelve: SRP en POST /citas (main.py L281-L295)
"""
from abc import ABC, abstractmethod
from datetime import datetime
from sqlalchemy.orm import Session

from models import Notificacion, Cita, Usuario, MedicoPerfil


class CitaObserver(ABC):
    """
    Interfaz Observer — define el contrato para todos los observadores.
    Cada observador reacciona al evento de creacion de una cita.
    """

    @abstractmethod
    def actualizar(self, cita: Cita, usuario: Usuario, db: Session) -> None:
        """Ejecuta la accion correspondiente al evento de cita."""


class BaseObserver(CitaObserver):
    """
    Clase Abstracta Base — extiende CitaObserver.
    Permite agregar comportamiento comun a todos los observers.
    """

    @abstractmethod
    def actualizar(self, cita: Cita, usuario: Usuario, db: Session) -> None:
        """Metodo abstracto — implementado por cada observer."""


class NotificacionObserver(BaseObserver):
    """
    Observer Concreto — crea notificaciones en la BD.
    Notifica al paciente (confirmacion) y al medico (nueva cita asignada).
    Unica responsabilidad: persistir las notificaciones.
    """

    def actualizar(self, cita: Cita, usuario: Usuario, db: Session) -> None:
        ahora = datetime.utcnow()

        # Notificacion al paciente
        notif_paciente = Notificacion(
            usuario_id=usuario.id,
            cita_id=cita.id,
            tipo="confirmacion",
            mensaje=f"Cita agendada para el {cita.fecha} a las {cita.hora}",
            leida=False,
            creado_en=ahora,
        )
        db.add(notif_paciente)

        # Notificacion al medico
        medico_perfil = db.query(MedicoPerfil).filter(
            MedicoPerfil.id == cita.medico_id
        ).first()
        if medico_perfil:
            notif_medico = Notificacion(
                usuario_id=medico_perfil.usuario_id,
                cita_id=cita.id,
                tipo="nueva_cita",
                mensaje=(
                    f"Nueva cita agendada: paciente {usuario.nombre} "
                    f"el {cita.fecha} a las {cita.hora}"
                ),
                leida=False,
                creado_en=ahora,
            )
            db.add(notif_medico)

        db.commit()


class LogObserver(BaseObserver):
    """
    Observer Concreto — registra un log de auditoria.
    Unica responsabilidad: registrar el evento en logs.
    """

    def actualizar(self, cita: Cita, usuario: Usuario, db: Session) -> None:
        print(
            f"[AUDIT] {datetime.utcnow().isoformat()} | "
            f"Cita #{cita.id} creada por {usuario.email} | "
            f"Medico ID: {cita.medico_id} | "
            f"Fecha: {cita.fecha} {cita.hora}"
        )


class CitaEventPublisher:
    """
    Sujeto (Publisher) — mantiene la lista de observers y los notifica.
    Agregacion: los observers tienen ciclo de vida independiente.
    """

    def __init__(self):
        self._observadores: list[CitaObserver] = []

    def suscribir(self, observer: CitaObserver) -> None:
        """Agrega un observer a la lista."""
        self._observadores.append(observer)

    def desuscribir(self, observer: CitaObserver) -> None:
        """Elimina un observer de la lista."""
        self._observadores.remove(observer)

    def notificar(self, cita: Cita, usuario: Usuario, db: Session) -> None:
        """
        Notifica a todos los observers registrados.
        Agregar nueva accion = suscribir nuevo Observer.
        No requiere modificar este metodo ni el endpoint.
        """
        for observer in self._observadores:
            observer.actualizar(cita, usuario, db)


# Publisher global con observers configurados
publisher = CitaEventPublisher()
publisher.suscribir(NotificacionObserver())
publisher.suscribir(LogObserver())
# Para agregar email: publisher.suscribir(EmailObserver())
