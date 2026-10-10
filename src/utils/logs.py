"""Configuracion comun de logging."""

import logging

FORMATO = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configurar_logging(nivel=logging.INFO):
    """Formato y nivel comun para todos los modulos."""
    logging.basicConfig(level=nivel, format=FORMATO, datefmt="%H:%M:%S")
    for ruidoso in ("urllib3", "matplotlib", "fontTools", "PIL"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)


def obtener_logger(nombre):
    """Logger con nombre."""
    return logging.getLogger(nombre)
