"""Detector de rarezas: valores inusuales para su hora del dia, con la regla explicada.

No busca solo maximos: un precio de S/ 300 puede ser normal a las 7 p. m. y raro a
las 3 a. m. Se compara cada valor contra la mediana de esa misma hora en los dias
previos, usando la MAD (desviacion absoluta mediana), que no se deja arrastrar por picos.
"""

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from src.utils import config
from src.utils.datos import semanas_disponibles


@dataclass
class Evaluacion:
    valor: float
    mediana: float | None
    z: float | None
    n: int
    es_rara: bool
    regla: str            # texto que explica que regla se activo (o por que no se juzga)


def _cfg():
    return config.cargar_yaml("analisis")["rarezas"]


def historial_barra(barra, con_ahora=None, raiz=None):
    """Serie de CMg total de una barra: version post operacion (IEOD) + tiempo real donde falte.

    El IEOD tiene prioridad porque es el dato evaluado por el COES.
    """
    raiz = raiz or config.DIR_PROCESSED
    partes = []
    for semana in semanas_disponibles("costo_marginal", raiz):
        ruta = raiz / "costo_marginal" / f"costo_marginal_{semana}.parquet"
        df = pd.read_parquet(ruta, filters=[("entidad", "==", barra), ("variable", "==", "cmg_total")],
                             columns=["fecha_hora", "valor", "fuente"])
        partes.append(df)
    serie = pd.concat(partes) if partes else pd.DataFrame(columns=["fecha_hora", "valor", "fuente"])
    if con_ahora is not None:
        from src.ahora import db
        tr = db.cmg_vigente(con_ahora, barra)
        if not tr.empty:
            tr = tr.rename(columns={"cmg_total": "valor"})[["fecha_hora", "valor"]].assign(fuente="ahora_tiempo_real")
            serie = pd.concat([serie, tr])
    if serie.empty:
        return pd.Series(dtype=float)
    serie["prioridad"] = (serie["fuente"] != "ieod_cmg").astype(int)   # 0 = IEOD primero
    serie = serie.sort_values(["fecha_hora", "prioridad"]).drop_duplicates("fecha_hora", keep="first")
    return serie.set_index("fecha_hora")["valor"].sort_index()


def evaluar(valor, momento, historia: pd.Series, cfg=None) -> Evaluacion:
    """Compara un valor con la misma hora del dia en los dias previos a 'momento'."""
    cfg = cfg or _cfg()
    momento = pd.Timestamp(momento)
    inicio = momento - timedelta(days=cfg["dias_historia"])
    previos = historia[(historia.index < momento) & (historia.index >= inicio)]
    misma_hora = previos[(previos.index.hour == momento.hour) & (previos.index.minute == momento.minute)].dropna()
    n = len(misma_hora)
    if n < cfg["minimo_observaciones"]:
        return Evaluacion(valor, None, None, n, False,
                          f"Sin juicio: solo hay {n} días previos a esta hora (se piden {cfg['minimo_observaciones']}).")
    mediana = float(misma_hora.median())
    mad = float((misma_hora - mediana).abs().median()) * 1.4826
    escala = max(mad, 1.0)   # evita dividir por cero cuando el precio estuvo plano
    z = (valor - mediana) / escala
    diferencia = valor - mediana
    es_rara = abs(z) >= cfg["z_robusto"] and abs(diferencia) >= cfg["diferencia_minima"]
    sentido = "por encima" if diferencia > 0 else "por debajo"
    if es_rara:
        regla = (f"Raro para la hora: S/ {abs(diferencia):,.1f} {sentido} de lo habitual a esta hora "
                 f"(mediana de {n} días: S/ {mediana:,.1f}). Regla: alejarse {cfg['z_robusto']} veces la "
                 f"variación típica y al menos S/ {cfg['diferencia_minima']}.")
    else:
        regla = f"Dentro de lo habitual para esta hora (mediana de {n} días: S/ {mediana:,.1f})."
    return Evaluacion(valor, mediana, z, n, es_rara, regla)


def salto_brusco(valor, anterior, cfg=None):
    """Texto si el cambio frente a la media hora anterior es grande, o None."""
    cfg = cfg or _cfg()
    if anterior in (None, 0) or pd.isna(anterior):
        return None
    cambio = valor - anterior
    if abs(cambio) >= cfg["salto_intervalo_min"] and abs(cambio / anterior) >= cfg["salto_intervalo_pct"]:
        return (f"Salto brusco: {'subió' if cambio > 0 else 'bajó'} S/ {abs(cambio):,.1f} "
                f"({abs(cambio / anterior) * 100:.0f}%) en media hora. Regla: cambio de al menos "
                f"{cfg['salto_intervalo_pct'] * 100:.0f}% y S/ {cfg['salto_intervalo_min']}.")
    return None


def rarezas_de_semana(serie_semana: pd.DataFrame, historia: pd.Series, maximo=5):
    """Intervalos de la semana raros para su hora, ordenados por cuan raros son."""
    cfg = _cfg()
    encontradas = []
    for _, fila in serie_semana.iterrows():
        ev = evaluar(fila["valor"], fila["fecha_hora"], historia, cfg)
        if ev.es_rara:
            encontradas.append({"fecha_hora": fila["fecha_hora"], "valor": ev.valor, "mediana": ev.mediana,
                                "z": ev.z, "n": ev.n, "regla": ev.regla})
    encontradas.sort(key=lambda e: -abs(e["z"]))
    return encontradas[:maximo], len(encontradas)
