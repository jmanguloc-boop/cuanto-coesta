"""Detector de rarezas: valores inusuales para su hora del dia, con la regla explicada.

No busca solo maximos: un precio de S/ 300 puede ser normal a las 7 p. m. y raro a
las 3 a. m. Un valor es raro si rompe el rango visto a esa misma hora en las 4
semanas previas (por encima del maximo o por debajo del minimo, con margen).
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
    minimo: float | None
    maximo: float | None
    n: int
    es_rara: bool
    regla: str            # texto que explica que regla se activo (o por que no se juzga)
    intensidad: float = 0.0   # cuanto rompe el rango, relativo (para ordenar)


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
    serie["fecha_hora"] = pd.to_datetime(serie["fecha_hora"])   # sin parquet previo llega como texto
    serie["prioridad"] = (serie["fuente"] != "ieod_cmg").astype(int)   # 0 = IEOD primero
    serie = serie.sort_values(["fecha_hora", "prioridad"]).drop_duplicates("fecha_hora", keep="first")
    return serie.set_index("fecha_hora")["valor"].sort_index()


def evaluar(valor, momento, historia: pd.Series, cfg=None) -> Evaluacion:
    """Compara un valor con el rango de esa misma hora del dia en los dias previos a 'momento'."""
    cfg = cfg or _cfg()
    momento = pd.Timestamp(momento)
    inicio = momento - timedelta(days=cfg["dias_historia"])
    previos = historia[(historia.index < momento) & (historia.index >= inicio)]
    misma_hora = previos[(previos.index.hour == momento.hour) & (previos.index.minute == momento.minute)].dropna()
    n = len(misma_hora)
    hora = f"{momento.hour}:{momento.minute:02d}"
    if n < cfg["minimo_observaciones"]:
        return Evaluacion(valor, None, None, None, n, False,
                          f"Sin juicio: solo hay {n} días previos con dato a las {hora} "
                          f"(se piden {cfg['minimo_observaciones']}).")
    mediana, minimo, maximo = float(misma_hora.median()), float(misma_hora.min()), float(misma_hora.max())
    margen = cfg["margen_rango"]
    lejos = abs(valor - mediana) >= cfg["diferencia_minima"]
    semanas = round(cfg["dias_historia"] / 7)
    if valor > maximo * (1 + margen) and lejos:
        regla = (f"El precio más alto para las {hora} en {semanas} semanas: S/ {valor:,.1f}, cuando el máximo previo "
                 f"era S/ {maximo:,.1f} y lo habitual S/ {mediana:,.1f}. Regla: superar el máximo de {n} días "
                 f"en al menos {margen * 100:.0f}%.")
        return Evaluacion(valor, mediana, minimo, maximo, n, True, regla, valor / max(maximo, 1) - 1)
    if valor < minimo * (1 - margen) and lejos:
        regla = (f"El precio más bajo para las {hora} en {semanas} semanas: S/ {valor:,.1f}, cuando el mínimo previo "
                 f"era S/ {minimo:,.1f} y lo habitual S/ {mediana:,.1f}. Regla: bajar del mínimo de {n} días "
                 f"en al menos {margen * 100:.0f}%.")
        return Evaluacion(valor, mediana, minimo, maximo, n, True, regla, 1 - valor / max(minimo, 1))
    regla = (f"Dentro de lo visto a las {hora} en {semanas} semanas (entre S/ {minimo:,.1f} y S/ {maximo:,.1f}; "
             f"lo habitual, S/ {mediana:,.1f}).")
    return Evaluacion(valor, mediana, minimo, maximo, n, False, regla)


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
                                "intensidad": ev.intensidad, "n": ev.n, "regla": ev.regla})
    encontradas.sort(key=lambda e: -e["intensidad"])
    return encontradas[:maximo], len(encontradas)
