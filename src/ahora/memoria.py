"""El precio tiene memoria: ultimo dato vs tres referencias, antiguedad y alertas.

Referencias de cada precio: la media hora anterior, la misma hora de ayer y la misma
hora de hace una semana. Si el COES no publico nada nuevo, se muestra el ultimo dato
con su antiguedad: nunca se finge una actualizacion.
"""

from dataclasses import dataclass, field
from datetime import timedelta

import pandas as pd

from src.ahora import db
from src.analysis.rarezas import evaluar, historial_barra, salto_brusco
from src.utils import config
from src.utils.fechas import ahora_peru
from src.utils.formato import variacion


@dataclass
class Referencia:
    nombre: str              # "media hora antes", "ayer a esta hora", "hace una semana"
    valor: float | None
    var: float | None        # variacion relativa del ultimo dato frente a esta referencia


@dataclass
class EstadoAhora:
    barra: str
    valor: float | None
    momento: pd.Timestamp | None           # fin del intervalo del ultimo dato
    extraido_en: str | None
    antiguedad_min: float | None           # minutos entre el intervalo y ahora
    referencias: list[Referencia]
    evaluacion: object | None              # rarezas.Evaluacion
    alertas: list[str]
    demanda: dict = field(default_factory=dict)
    serie_hoy: pd.DataFrame = field(default_factory=pd.DataFrame)      # fecha_hora, valor
    serie_ayer: pd.DataFrame = field(default_factory=pd.DataFrame)     # misma curva un dia antes
    revisiones: int = 0
    ultima_extraccion: dict | None = None
    sin_datos: bool = False


def _valor_en(historia, momento):
    try:
        return float(historia.loc[momento])
    except KeyError:
        return None


def estado_precio(barra=None, ruta_db=None, ahora=None) -> EstadoAhora:
    """Arma todo lo que muestra la pestana Ahora para una barra (por defecto la de referencia)."""
    barra = barra or config.fuentes()["barra_referencia"]
    ahora = pd.Timestamp(ahora or ahora_peru().replace(tzinfo=None))
    with db.conectar(ruta_db) as con:
        tr = db.cmg_vigente(con, barra)
        historia = historial_barra(barra, con_ahora=con)
        demanda = db.demanda_vigente(con)
        revs = db.revisiones(con, barra)
        ultima = db.ultima_extraccion(con, "costo_marginal")
    if tr.empty:
        return EstadoAhora(barra, None, None, None, None, [], None, ["Aún no hay datos. Pulsa Actualizar."],
                           ultima_extraccion=ultima, sin_datos=True)

    ultimo = tr.iloc[-1]
    momento = pd.Timestamp(ultimo["fecha_hora"])
    valor = float(ultimo["cmg_total"])
    referencias = []
    for nombre, delta in (("media hora antes", timedelta(minutes=30)), ("ayer a esta hora", timedelta(days=1)),
                          ("hace una semana", timedelta(days=7))):
        ref = _valor_en(historia, momento - delta)
        referencias.append(Referencia(nombre, ref, variacion(valor, ref)))

    ev = evaluar(valor, momento, historia)
    alertas = []
    salto = salto_brusco(valor, referencias[0].valor)
    if salto:
        alertas.append(salto)
    if ev.es_rara:
        alertas.append(ev.regla)

    hoy = momento.normalize()
    serie_hoy = historia[(historia.index > hoy) & (historia.index <= hoy + timedelta(days=1))]
    serie_ayer = historia[(historia.index > hoy - timedelta(days=1)) & (historia.index <= hoy)]
    return EstadoAhora(
        barra=barra, valor=valor, momento=momento, extraido_en=ultimo["extraido_en"],
        antiguedad_min=(ahora - momento).total_seconds() / 60,
        referencias=referencias, evaluacion=ev, alertas=alertas,
        demanda=estado_demanda(demanda),
        serie_hoy=serie_hoy.rename("valor").reset_index(),
        serie_ayer=serie_ayer.rename("valor").reset_index(),
        revisiones=len(revs), ultima_extraccion=ultima,
    )


def estado_demanda(demanda: pd.DataFrame) -> dict:
    """Ultima demanda ejecutada, lo programado para ese intervalo y la misma hora de ayer."""
    if demanda.empty or "ejecutada" not in demanda or demanda["ejecutada"].dropna().empty:
        return {}
    ejec = demanda.dropna(subset=["ejecutada"])
    ultimo = ejec.iloc[-1]
    momento = ultimo["fecha_hora"]
    programado = ultimo.get("programa_diario")
    ayer = ejec[ejec["fecha_hora"] == momento - timedelta(days=1)]["ejecutada"]
    return {
        "valor": float(ultimo["ejecutada"]),
        "momento": momento,
        "programado": None if pd.isna(programado) else float(programado),
        "desvio": variacion(float(ultimo["ejecutada"]), None if pd.isna(programado) else float(programado)),
        "ayer": float(ayer.iloc[0]) if len(ayer) else None,
        "serie": demanda,
    }
