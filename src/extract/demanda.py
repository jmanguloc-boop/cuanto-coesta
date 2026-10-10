"""Demanda del SEIN cada 30 min (portal COES)."""

from src.extract.base import descargar_por_tramos, obtener_portal

NOMBRE = "demanda"


def descargar(desde, hasta, cliente=None, raiz=None, forzar=False):
    return descargar_por_tramos(NOMBRE, desde, hasta, obtener_portal, cliente, raiz, forzar)
