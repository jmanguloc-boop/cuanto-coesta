"""Piezas comunes de la transformacion: formato largo, fechas, validaciones."""

import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.utils import config
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)

COLUMNAS = ["fecha_hora", "fecha", "entidad", "variable", "valor", "unidad", "es_preliminar", "fuente"]


def clave_ascii(texto) -> str:
    """'BIOGÁS', 'BIOG\\ufffdS' -> 'BIOGS'. Sirve para mapear nombres con tildes rotas."""
    return re.sub(r"[^A-Z0-9]", "", str(texto).upper().encode("ascii", "ignore").decode())


def limpiar_texto(texto) -> str:
    """Quita el caracter de reemplazo U+FFFD y espacios sobrantes."""
    return re.sub(r"\s+", " ", str(texto).replace("�", "")).strip()


def fin_de_intervalo(momento) -> datetime:
    """El COES marca el ultimo intervalo como 23:59; se normaliza a 24:00 (00:00 del dia siguiente)."""
    momento = pd.Timestamp(momento).to_pydatetime().replace(second=0, microsecond=0)
    if momento.minute == 59:
        momento += timedelta(minutes=1)
    return momento


def dia_operativo(fecha_hora: pd.Series) -> pd.Series:
    """Intervalo que termina a las 00:00 pertenece al dia anterior."""
    return (fecha_hora - pd.Timedelta(minutes=1)).dt.date


def fechas_de_archivo(ruta: Path):
    """'demanda_20260928_20261004.xlsx' -> (date, date)."""
    fechas = re.findall(r"(\d{8})", ruta.stem)
    inicio = datetime.strptime(fechas[0], "%Y%m%d").date()
    fin = datetime.strptime(fechas[-1], "%Y%m%d").date()
    return inicio, fin


def archivos_del_rango(fuente, desde: date, hasta: date, raiz=None):
    """Archivos crudos de una fuente que se cruzan con [desde, hasta]."""
    carpeta = Path(raiz or config.DIR_RAW) / fuente
    salida = []
    for ruta in sorted(carpeta.glob(f"{fuente}_*")):
        inicio, fin = fechas_de_archivo(ruta)
        if inicio <= hasta and fin >= desde:
            salida.append(ruta)
    return salida


def dias_con_ieod(desde, hasta, raiz=None):
    """Dias que ya tienen IEOD publicado (evaluados por el COES)."""
    return {fechas_de_archivo(r)[0] for r in archivos_del_rango("ieod_anexo", desde, hasta, raiz)}


def armar(df, unidad, fuente, es_preliminar=False):
    """Completa columnas comunes y ordena."""
    df = df.copy()
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    if "fecha" not in df:
        df["fecha"] = dia_operativo(df["fecha_hora"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["unidad"] = unidad
    df["fuente"] = fuente
    if "es_preliminar" not in df:
        df["es_preliminar"] = es_preliminar
    extras = [c for c in df.columns if c not in COLUMNAS]
    return df[COLUMNAS + extras].dropna(subset=["valor"]).reset_index(drop=True)


def recortar(df, desde, hasta):
    """Filas cuyo dia operativo cae en el rango."""
    return df[(df["fecha"] >= desde) & (df["fecha"] <= hasta)].reset_index(drop=True)


def validar(df, tabla, por_dia=48, minimo=None, maximo=None, sin_minimo=()):
    """Devuelve avisos (no rompe): duplicados, intervalos faltantes, valores imposibles."""
    avisos = []
    if df.empty:
        return [f"{tabla}: sin datos"]
    clave = ["fecha_hora", "entidad", "variable"]
    duplicados = int(df.duplicated(clave).sum())
    if duplicados:
        avisos.append(f"{tabla}: {duplicados} filas duplicadas (se conserva la ultima)")
    if por_dia:
        conteo = df.groupby(["fecha", "entidad", "variable"]).size()
        incompletos = conteo[conteo < por_dia]
        if len(incompletos):
            peor = incompletos.sort_values().head(3)
            ejemplos = ", ".join(f"{e} {v} {f} ({n}/{por_dia})" for (f, e, v), n in peor.items())
            avisos.append(f"{tabla}: {len(incompletos)} series-dia con intervalos faltantes. Ej: {ejemplos}")
    if minimo is not None:
        n = int(((df["valor"] < minimo) & ~df["variable"].isin(sin_minimo)).sum())
        if n:
            avisos.append(f"{tabla}: {n} valores menores a {minimo}")
    if maximo is not None:
        n = int((df["valor"] > maximo).sum())
        if n:
            avisos.append(f"{tabla}: {n} valores mayores a {maximo}")
    for aviso in avisos:
        log.warning(aviso)
    return avisos


def sin_duplicados(df):
    """Quita duplicados por fecha_hora, entidad y variable (queda el ultimo)."""
    return df.drop_duplicates(["fecha_hora", "entidad", "variable"], keep="last").reset_index(drop=True)
