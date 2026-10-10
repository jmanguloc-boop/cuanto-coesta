"""Piezas comunes de los descargadores: tramos de fechas, rutas, validacion."""

import json
from datetime import date, timedelta
from pathlib import Path

from src.extract.cliente import ClienteCoes, NoPublicado, formato_coes
from src.utils import config
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)


def partir_rango(desde: date, hasta: date, max_dias: int):
    """Divide [desde, hasta] en tramos de a lo mas max_dias dias."""
    if hasta < desde:
        raise ValueError("La fecha final es anterior a la inicial")
    tramos = []
    inicio = desde
    while inicio <= hasta:
        fin = min(inicio + timedelta(days=max_dias - 1), hasta)
        tramos.append((inicio, fin))
        inicio = fin + timedelta(days=1)
    return tramos


def validar_contenido(contenido: bytes, formato: str):
    """El COES a veces responde 200 con una pagina de error en HTML."""
    if formato in ("xlsx", "zip") and not contenido.startswith(b"PK"):
        raise ValueError("Se esperaba un archivo Office/zip y llego: " + contenido[:120].decode("utf-8", "replace"))
    if formato == "json":
        datos = json.loads(contenido.decode("utf-8-sig"))
        if not isinstance(datos, (dict, list)):
            raise ValueError("JSON inesperado")


def ruta_archivo(nombre_fuente, desde, hasta, formato, raiz=None):
    """Ruta en data/raw para un tramo de fechas de una fuente."""
    raiz = Path(raiz or config.DIR_RAW)
    if desde == hasta:
        nombre = f"{nombre_fuente}_{desde:%Y%m%d}.{formato}"
    else:
        nombre = f"{nombre_fuente}_{desde:%Y%m%d}_{hasta:%Y%m%d}.{formato}"
    return raiz / nombre_fuente / nombre


def ruta_ieod(plantilla, fecha: date):
    """Arma la ruta del visor IEOD para una fecha."""
    meses = config.fuentes()["meses_ieod"]
    return plantilla.format(
        anio=fecha.year,
        mes_carpeta=f"{fecha.month:02d}_{meses[fecha.month - 1]}",
        dia=f"{fecha.day:02d}",
        ddmm=f"{fecha:%d%m}",
        aaaammdd=f"{fecha:%Y%m%d}",
    )


def descargar_por_tramos(nombre_fuente, desde, hasta, obtener, cliente=None, raiz=None, forzar=False):
    """Esqueleto comun: recorre tramos, usa cache y guarda lo bajado.

    obtener(cliente, fuente_cfg, inicio, fin) -> bytes. Puede lanzar NoPublicado.
    """
    fuente = config.fuentes()["fuentes"][nombre_fuente]
    cliente = cliente or ClienteCoes()
    archivos = []
    for inicio, fin in partir_rango(desde, hasta, fuente["max_dias_por_pedido"]):
        ruta = ruta_archivo(nombre_fuente, inicio, fin, fuente["formato"], raiz)
        if not forzar and cliente.cache_vigente(ruta, fin):
            log.debug("cache %s", ruta.name)
            archivos.append(ruta)
            continue
        try:
            contenido = obtener(cliente, fuente, inicio, fin)
            validar_contenido(contenido, fuente["formato"])
        except NoPublicado:
            log.info("%s: %s aun no publicado", nombre_fuente, inicio)
            continue
        except (ValueError, KeyError) as error:
            # Archivo con formato inesperado: se salta ese tramo y se sigue con los demas
            log.error("%s: %s a %s con formato inesperado (%s)", nombre_fuente, inicio, fin, error)
            continue
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
        log.info("nuevo %s (%.0f KB)", ruta.name, len(contenido) / 1024)
        archivos.append(ruta)
    return archivos


def obtener_portal(cliente, fuente, inicio, fin):
    """Pedido simple al portal con los params de fuentes.yaml."""
    params = {
        clave: str(valor).format(desde=formato_coes(inicio), hasta=formato_coes(fin))
        for clave, valor in fuente["params"].items()
    }
    return cliente.pedir(fuente["metodo"], fuente["url"], params)
