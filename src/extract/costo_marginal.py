"""Costo marginal de corto plazo del IEOD (48 intervalos, todas las barras).

El COES lo publica dentro de un zip diario de ~5 MB; solo se guarda el Excel.
Los dias que el IEOD aun no publica se cubren con costo_marginal_tr.
"""

import io
import zipfile

from src.extract import costo_marginal_tr
from src.extract.base import descargar_por_tramos, ruta_ieod

NOMBRE = "costo_marginal"


def _obtener(cliente, fuente, inicio, fin):
    contenido = cliente.pedir_archivo_visor(ruta_ieod(fuente["ruta_ieod"], inicio))
    buscado = ruta_ieod(fuente["miembro_zip"], inicio).lower()
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        for nombre in z.namelist():
            if nombre.replace("\\", "/").split("/")[-1].lower() == buscado:
                return z.read(nombre)
    raise ValueError(f"El zip del IEOD no trae {buscado}")


def descargar(desde, hasta, cliente=None, raiz=None, forzar=False):
    archivos = descargar_por_tramos(NOMBRE, desde, hasta, _obtener, cliente, raiz, forzar)
    if len(archivos) < (hasta - desde).days + 1:
        # Faltan dias en el IEOD: bajar el respaldo en tiempo real para todo el rango
        archivos += costo_marginal_tr.descargar(desde, hasta, cliente, raiz, forzar)
    return archivos
