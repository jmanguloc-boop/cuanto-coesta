"""Generacion por tipo de recurso y por central (portal COES, dia por dia)."""

from src.extract.base import descargar_por_tramos, obtener_portal

NOMBRE = "generacion"


def descargar(desde, hasta, cliente=None, raiz=None, forzar=False):
    """Baja la generacion por recurso, un pedido por dia."""
    return descargar_por_tramos(NOMBRE, desde, hasta, obtener_portal, cliente, raiz, forzar)
