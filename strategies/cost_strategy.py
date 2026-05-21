"""
Patron 5 — Strategy
Archivo: strategies/cost_strategy.py
Resuelve: OCP y DIP en citas.html L310-L318 (TARIFAS hardcodeadas)
"""
from abc import ABC, abstractmethod


class CostStrategy(ABC):
    """
    Interfaz Strategy — define el contrato para calculo de costos.
    Permite intercambiar algoritmos de precios en tiempo de ejecucion.
    """

    @abstractmethod
    def calcular_costo(self, especialidad: str) -> float:
        """Calcula el costo de la consulta segun la especialidad."""


class BaseStrategy(CostStrategy):
    """
    Clase Abstracta Base — define las tarifas base del sistema.
    Las subclases pueden sobreescribir o extender el calculo.
    """

    TARIFAS: dict = {
        "Medicina General": 35000,
        "Pediatria":        55000,
        "Cardiologia":     120000,
        "Dermatologia":     90000,
        "Ginecologia":     100000,
        "Ortopedia":       110000,
    }

    @abstractmethod
    def calcular_costo(self, especialidad: str) -> float:
        """Metodo abstracto — implementado por cada strategy."""

    def get_tarifa_base(self, especialidad: str) -> float:
        """Retorna la tarifa base de la especialidad."""
        return self.TARIFAS.get(especialidad, 35000)


class TarifaFijaStrategy(BaseStrategy):
    """
    Strategy Concreta — calcula el costo con tarifas fijas.
    Retorna el precio estandar por especialidad.
    """

    def calcular_costo(self, especialidad: str) -> float:
        return self.get_tarifa_base(especialidad)


class TarifaConvenioStrategy(BaseStrategy):
    """
    Strategy Concreta — aplica un descuento sobre la tarifa base.
    Util para pacientes con convenio empresarial o EPS.
    """

    def __init__(self, descuento: float = 0.20):
        self._descuento = descuento
        self._base = TarifaFijaStrategy()

    def calcular_costo(self, especialidad: str) -> float:
        base = self._base.calcular_costo(especialidad)
        return base * (1 - self._descuento)


class CitaService:
    """
    Contexto — usa CostStrategy para calcular costos.
    Permite cambiar la estrategia en tiempo de ejecucion.
    Composicion: gestiona el ciclo de vida de la estrategia.
    """

    def __init__(self, strategy: CostStrategy = None):
        self._strategy = strategy or TarifaFijaStrategy()

    def set_strategy(self, strategy: CostStrategy) -> None:
        """Cambia la estrategia en tiempo de ejecucion."""
        self._strategy = strategy

    def calcular_costo_cita(self, especialidad: str) -> float:
        """
        Calcula el costo usando la estrategia configurada.
        El cliente no sabe cual estrategia se usa internamente.
        """
        return self._strategy.calcular_costo(especialidad)


# Instancia por defecto con tarifa fija
cita_service = CitaService(TarifaFijaStrategy())

# Para convenios: cita_service.set_strategy(TarifaConvenioStrategy(0.15))
