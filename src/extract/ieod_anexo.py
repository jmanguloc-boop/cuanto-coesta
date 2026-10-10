"""Anexo A del IEOD (embalses, caudales, eventos, mantenimientos), un archivo por dia."""

from src.extract.base import descargar_por_tramos, ruta_ieod

NOMBRE = "ieod_anexo"


def _obtener(cliente, fuente, inicio, fin):
    return cliente.pedir_archivo_visor(ruta_ieod(fuente["ruta_ieod"], inicio))


def descargar(desde, hasta, cliente=None, raiz=None, forzar=False):
    return descargar_por_tramos(NOMBRE, desde, hasta, _obtener, cliente, raiz, forzar)
