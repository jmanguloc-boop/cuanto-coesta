"""Costo marginal en tiempo real (portal COES). Respaldo: trae ~35 de 48 intervalos."""

from src.extract.base import descargar_por_tramos, obtener_portal

NOMBRE = "costo_marginal_tr"


def descargar(desde, hasta, cliente=None, raiz=None, forzar=False):
    """Baja el costo marginal en tiempo real (respaldo)."""
    return descargar_por_tramos(NOMBRE, desde, hasta, obtener_portal, cliente, raiz, forzar)
