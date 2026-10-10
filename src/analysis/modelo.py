"""Estructuras del resumen semanal."""

from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from src.utils.formato import variacion


@dataclass
class Indicador:
    """Un numero de la semana con sus comparaciones. clave = entrada del glosario."""

    clave: str
    valor: float | None
    unidad: str
    anterior: float | None = None          # semana anterior
    anio_anterior: float | None = None     # misma semana del anio pasado
    momento: datetime | None = None        # cuando ocurrio (maximos y minimos)
    es_puntos: bool = False                # variaciones en puntos porcentuales (para shares)
    var_anterior: float | None = None
    var_anio: float | None = None
    comparable: bool = True                # False: total de una semana incompleta, no se compara

    def __post_init__(self):
        if not self.comparable:
            self.var_anterior = self.var_anio = None
            return
        if self.var_anterior is None:
            self.var_anterior = self._var(self.anterior)
        if self.var_anio is None:
            self.var_anio = self._var(self.anio_anterior)

    def _var(self, referencia):
        if self.valor is None or referencia is None:
            return None
        return self.valor - referencia if self.es_puntos else variacion(self.valor, referencia)


@dataclass
class Hecho:
    """Un hecho destacado de la semana, detectado por reglas."""

    tipo: str            # variacion, record, anomalia, dato
    clave: str           # indicador relacionado
    puntaje: float       # mayor = mas relevante
    datos: dict = field(default_factory=dict)


@dataclass
class ResumenSemanal:
    semana: str
    texto_semana: str
    desde: date
    hasta: date
    semana_anterior: str
    semana_anio_anterior: str
    es_preliminar: bool
    dias_con_datos: int                        # dias completos (>= 46 de 48 intervalos de demanda)
    barra_referencia: str
    umbrales_precio: dict
    indicadores: dict[str, Indicador]
    mix: dict[str, float]                      # tecnologia -> participacion (0 a 1)
    mix_anterior: dict[str, float]
    hechos: list[Hecho]
    avisos: list[str]
    # Series para graficos (no se imprimen)
    perfil_cmg: pd.DataFrame                   # hora, actual, anterior
    serie_cmg: pd.DataFrame                    # fecha_hora, valor
    serie_demanda: pd.DataFrame                # fecha_hora, ejecutada, prog_diaria
    serie_generacion: pd.DataFrame             # fecha_hora, tecnologia, valor
    serie_embalses: pd.DataFrame               # fecha, valor (Hm3 total diario)
    embalses_detalle: pd.DataFrame             # entidad, cuenca, actual, anterior
    historico: pd.DataFrame = field(default_factory=pd.DataFrame)  # metricas de semanas previas
    rarezas: list = field(default_factory=list)                    # intervalos raros para su hora (top 5)
    n_rarezas: int = 0
    cmg_barras: pd.DataFrame = field(default_factory=pd.DataFrame) # promedio por barra con coordenadas
    revision: dict = field(default_factory=dict)                   # preliminar vs post operacion

    def ind(self, clave):
        """Indicador por clave o None."""
        return self.indicadores.get(clave)
