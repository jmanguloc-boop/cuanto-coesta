"""CLI: python -m src.extract --desde AAAA-MM-DD --hasta AAAA-MM-DD [--fuente nombre] [--forzar]

Sin fechas baja la ultima semana completa (lunes a domingo).
"""

import argparse
from datetime import date

from src.extract import DESCARGADORES
from src.extract.cliente import ClienteCoes
from src.utils.fechas import rango_semana, ultima_semana_completa
from src.utils.logs import configurar_logging, obtener_logger

log = obtener_logger("src.extract")


def descargar_todo(desde, hasta, fuentes=None, forzar=False, cliente=None):
    """Corre cada descargador; si uno falla, registra el error y sigue."""
    cliente = cliente or ClienteCoes()
    resultado, errores = {}, {}
    for nombre in fuentes or DESCARGADORES:
        log.info("Descargando %s de %s a %s", nombre, desde, hasta)
        try:
            resultado[nombre] = DESCARGADORES[nombre](desde, hasta, cliente=cliente, forzar=forzar)
        except Exception as error:  # una fuente caida no debe tumbar a las demas
            log.error("Fallo %s: %s", nombre, error)
            errores[nombre] = str(error)
    return resultado, errores


def main(argv=None):
    parser = argparse.ArgumentParser(description="Descarga data publica del COES")
    parser.add_argument("--desde", type=date.fromisoformat)
    parser.add_argument("--hasta", type=date.fromisoformat)
    parser.add_argument("--fuente", choices=sorted(DESCARGADORES), action="append")
    parser.add_argument("--forzar", action="store_true", help="ignora la cache")
    args = parser.parse_args(argv)
    configurar_logging()

    desde, hasta = rango_semana(ultima_semana_completa())
    resultado, errores = descargar_todo(args.desde or desde, args.hasta or hasta, args.fuente, args.forzar)
    for nombre, archivos in resultado.items():
        log.info("%s: %s archivos", nombre, len(archivos))
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
