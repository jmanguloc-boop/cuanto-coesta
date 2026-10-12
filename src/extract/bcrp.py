"""Tipo de cambio del BCRP (S/ por US$, venta, sistema bancario SBS), API publica y gratuita.

Se guarda en data/tipo_cambio.csv y solo se piden los dias que faltan. El BCRP publica
dias habiles: fines de semana y feriados toman el ultimo valor conocido.
"""

import json
from datetime import date, timedelta

import pandas as pd

from src.extract.cliente import crear_sesion
from src.utils import config
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)

SERIE = "PD04640PD"
URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{serie}/json/{desde}/{hasta}"
MESES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Set": 9, "Sep": 9,
         "Oct": 10, "Nov": 11, "Dic": 12}


def ruta_cache():
    """Archivo local con el tipo de cambio ya descargado."""
    return config.DIR_DATA / "tipo_cambio.csv"


def leer_periodo(nombre):
    """'25.Set.26' -> date(2026, 9, 25)."""
    dia, mes, anio = nombre.split(".")
    return date(2000 + int(anio), MESES[mes[:3].title()], int(dia))


def interpretar(contenido: bytes) -> pd.DataFrame:
    """JSON del BCRP -> DataFrame fecha, tc (sin los dias 'n.d.')."""
    datos = json.loads(contenido.decode("utf-8-sig"))
    filas = []
    for periodo in datos.get("periods", []):
        valor = periodo["values"][0]
        try:
            filas.append({"fecha": leer_periodo(periodo["name"]), "tc": float(valor)})
        except (ValueError, KeyError):
            continue
    return pd.DataFrame(filas, columns=["fecha", "tc"])


def leer_cache():
    """Tipo de cambio guardado, o vacio."""
    ruta = ruta_cache()
    if not ruta.exists():
        return pd.DataFrame(columns=["fecha", "tc"])
    df = pd.read_csv(ruta)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    return df


def actualizar(desde: date, hasta: date, sesion=None):
    """Baja del BCRP lo que falta en el rango y devuelve la tabla completa."""
    cache = leer_cache()
    pedir_desde = desde
    if not cache.empty:
        conocidos = set(cache["fecha"])
        ultimo = max(conocidos)
        if min(conocidos) <= desde and ultimo >= hasta - timedelta(days=3):
            return cache    # al dia (los ultimos dias suelen ser 'n.d.' hasta que el BCRP publica)
        pedir_desde = max(desde, ultimo - timedelta(days=5)) if min(conocidos) <= desde else desde
    sesion = sesion or crear_sesion()
    sesion.headers["User-Agent"] = config.fuentes()["cliente"]["user_agent"]
    url = URL.format(serie=SERIE, desde=f"{pedir_desde:%Y-%m-%d}", hasta=f"{hasta:%Y-%m-%d}")
    try:
        resp = sesion.get(url, timeout=60)
        resp.raise_for_status()
        nuevos = interpretar(resp.content)
    except Exception as error:   # sin tipo de cambio la app sigue en soles
        log.warning("No se pudo bajar el tipo de cambio del BCRP: %s", error)
        return cache
    tabla = pd.concat([cache, nuevos]).drop_duplicates("fecha", keep="last").sort_values("fecha")
    ruta_cache().parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(ruta_cache(), index=False)
    log.info("Tipo de cambio: %s dias nuevos", len(nuevos))
    return tabla


def tc_para(fechas, tabla) -> pd.Series:
    """Tipo de cambio de cada fecha; dias sin dato toman el ultimo conocido (o el siguiente al inicio)."""
    if tabla.empty:
        return pd.Series([None] * len(fechas), index=range(len(fechas)), dtype=float)
    base = tabla.set_index(pd.to_datetime(tabla["fecha"]))["tc"].sort_index()
    objetivo = pd.to_datetime(pd.Series(fechas))
    rango = pd.date_range(min(base.index.min(), objetivo.min()), max(base.index.max(), objetivo.max()), freq="D")
    completo = base.reindex(rango).ffill().bfill()
    return objetivo.map(completo).reset_index(drop=True)
