"""Lectura de las tablas procesadas (parquet por semana)."""

from pathlib import Path

import pandas as pd

from src.utils import config


def ruta_tabla(tabla, semana, raiz=None):
    return Path(raiz or config.DIR_PROCESSED) / tabla / f"{tabla}_{semana}.parquet"


def leer_tabla(tabla, semana, raiz=None):
    """DataFrame de la tabla para la semana, o vacio si no existe."""
    ruta = ruta_tabla(tabla, semana, raiz)
    if not ruta.exists():
        return pd.DataFrame()
    return pd.read_parquet(ruta)


def semanas_disponibles(tabla="demanda", raiz=None):
    """Semanas con parquet de la tabla, ordenadas."""
    carpeta = Path(raiz or config.DIR_PROCESSED) / tabla
    return sorted(p.stem.replace(f"{tabla}_", "") for p in carpeta.glob(f"{tabla}_*.parquet"))
