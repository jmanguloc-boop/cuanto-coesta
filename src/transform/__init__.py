"""Transformacion: crudos de data/raw -> parquet en formato largo en data/processed."""

import json
from pathlib import Path

from src.transform import tablas
from src.transform.comun import sin_duplicados, validar
from src.utils import config
from src.utils.datos import ruta_tabla
from src.utils.fechas import rango_semana
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)

# tabla -> (funcion, intervalos esperados por dia, minimo, maximo, variables sin chequeo de minimo)
# La congestion puede ser negativa legitimamente; el CMg total no deberia bajar de 0
TABLAS = {
    "demanda": (tablas.tabla_demanda, 48, 0, 20000, ()),
    "generacion": (tablas.tabla_generacion, 48, -5, 15000, ()),
    "costo_marginal": (tablas.tabla_costo_marginal, 48, 0, 10000, ("cmg_congestion",)),
    # El preliminar trae ~35 de 48 intervalos por diseno del COES: no se avisa por faltantes
    "cmg_preliminar": (tablas.tabla_cmg_preliminar, None, 0, 10000, ("cmg_congestion",)),
    "embalses": (tablas.tabla_embalses, None, 0, None, ()),
    "centrales": (tablas.tabla_centrales, 48, -5, 1500, ()),
}


def transformar_semana(semana, raiz_raw=None, raiz_processed=None):
    """Genera los parquet de una semana. Devuelve {tabla: filas} y la lista de avisos."""
    desde, hasta = rango_semana(semana)
    filas, avisos = {}, []
    for tabla, (funcion, por_dia, minimo, maximo, sin_minimo) in TABLAS.items():
        try:
            df = funcion(desde, hasta, raiz_raw)
        except Exception as error:  # una tabla rota no detiene a las demas
            log.error("No se pudo armar %s: %s", tabla, error)
            avisos.append(f"{tabla}: error al transformar ({error})")
            continue
        avisos += validar(df, tabla, por_dia, minimo, maximo, sin_minimo)
        if df.empty:
            continue
        df = sin_duplicados(df)
        dias = df["fecha"].nunique()
        if dias < 7:
            avisos.append(f"{tabla}: solo {dias} de 7 dias disponibles")
        destino = ruta_tabla(tabla, semana, raiz_processed)
        destino.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(destino, index=False)
        filas[tabla] = len(df)
        log.info("%s: %s filas -> %s", tabla, len(df), destino.name)
    ruta_avisos = Path(raiz_processed or config.DIR_PROCESSED) / "avisos" / f"avisos_{semana}.json"
    ruta_avisos.parent.mkdir(parents=True, exist_ok=True)
    ruta_avisos.write_text(json.dumps(avisos, ensure_ascii=False, indent=2), encoding="utf-8")
    return filas, avisos
