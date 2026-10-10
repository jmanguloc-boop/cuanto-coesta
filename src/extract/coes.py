"""Descargadores del portal COES. Cada fuente se define en config/fuentes.yaml."""

import json
from datetime import date, timedelta
from pathlib import Path

from src.extract.cliente import RUTA_RAW, ClienteCoes, cargar_fuentes, formato_coes


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
    if formato == "xlsx" and not contenido.startswith(b"PK"):
        raise ValueError("Se esperaba un Excel y llego otra cosa: " + contenido[:120].decode("utf-8", "replace"))
    if formato == "json":
        datos = json.loads(contenido.decode("utf-8-sig"))
        if not isinstance(datos, (dict, list)):
            raise ValueError("JSON inesperado")


def ruta_archivo(nombre_fuente, desde, hasta, formato, raiz=RUTA_RAW):
    if desde == hasta:
        nombre = f"{nombre_fuente}_{desde:%Y%m%d}.{formato}"
    else:
        nombre = f"{nombre_fuente}_{desde:%Y%m%d}_{hasta:%Y%m%d}.{formato}"
    return Path(raiz) / nombre_fuente / nombre


def descargar_fuente(nombre_fuente, desde, hasta, cliente=None, config=None, raiz=RUTA_RAW, forzar=False):
    """Baja una fuente para el rango pedido. Devuelve la lista de archivos."""
    config = config or cargar_fuentes()
    fuente = config["fuentes"][nombre_fuente]
    cliente = cliente or ClienteCoes(config["cliente"])
    archivos = []
    for inicio, fin in partir_rango(desde, hasta, fuente["max_dias_por_pedido"]):
        ruta = ruta_archivo(nombre_fuente, inicio, fin, fuente["formato"], raiz)
        if not forzar and cliente.cache_vigente(ruta, fin):
            print(f"  [cache] {ruta.name}")
            archivos.append(ruta)
            continue
        params = {
            clave: str(valor).format(desde=formato_coes(inicio), hasta=formato_coes(fin))
            for clave, valor in fuente["params"].items()
        }
        contenido = cliente.pedir(fuente["metodo"], fuente["url"], params)
        validar_contenido(contenido, fuente["formato"])
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
        print(f"  [nuevo] {ruta.name} ({len(contenido) / 1024:.0f} KB)")
        archivos.append(ruta)
    return archivos


def descargar_todo(desde, hasta, forzar=False):
    config = cargar_fuentes()
    cliente = ClienteCoes(config["cliente"])
    resultado = {}
    for nombre in config["fuentes"]:
        print(f"{nombre}: {desde} a {hasta}")
        resultado[nombre] = descargar_fuente(nombre, desde, hasta, cliente=cliente, config=config, forzar=forzar)
    return resultado
