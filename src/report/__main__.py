"""CLI: python -m src.report [--semana AAAA-Www] [--png] -> reports/<slug>_AAAA-Www.pdf"""

import argparse

from src.report import exportar_portada_png, generar_pdf
from src.utils import config
from src.utils.fechas import ultima_semana_completa
from src.utils.logs import configurar_logging, obtener_logger

log = obtener_logger("src.report")


def main(argv=None):
    """Punto de entrada de la linea de comandos."""
    parser = argparse.ArgumentParser(description="Genera el PDF semanal")
    parser.add_argument("--semana", default=None)
    parser.add_argument("--png", action="store_true", help="exporta la portada a docs/capturas/")
    args = parser.parse_args(argv)
    configurar_logging()
    ruta = generar_pdf(args.semana or ultima_semana_completa())
    if args.png:
        destino = config.DIR_CAPTURAS / "pdf_portada.png"
        exportar_portada_png(ruta, destino)
        log.info("Portada exportada a %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
