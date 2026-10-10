"""CLI: python -m src.transform [--semana AAAA-Www]"""

import argparse

from src.transform import transformar_semana
from src.utils.fechas import ultima_semana_completa
from src.utils.logs import configurar_logging, obtener_logger

log = obtener_logger("src.transform")


def main(argv=None):
    """Punto de entrada de la linea de comandos."""
    parser = argparse.ArgumentParser(description="Convierte los crudos de una semana a parquet")
    parser.add_argument("--semana", default=None, help="ej. 2026-W40 (por defecto la ultima completa)")
    args = parser.parse_args(argv)
    configurar_logging()
    semana = args.semana or ultima_semana_completa()
    filas, avisos = transformar_semana(semana)
    log.info("Semana %s: %s tablas, %s avisos", semana, len(filas), len(avisos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
