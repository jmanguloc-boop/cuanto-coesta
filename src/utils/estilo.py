"""Identidad editorial: tipografias del proyecto y estilo comun para matplotlib, Tkinter y PDF.

Las fuentes viven en assets/fuentes (licencia OFL). No hace falta instalarlas:
- matplotlib y el PDF las leen directo del archivo
- en Windows, Tkinter las registra solo para este programa (AddFontResourceEx privado)
- si algo falla, se usan alternativas que traen los sistemas operativos
"""

import sys
from functools import lru_cache
from pathlib import Path

from src.utils import config
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)

DIR_FUENTES = config.RAIZ / "assets" / "fuentes"
DIR_MAPAS = config.RAIZ / "assets" / "mapas"

ARCHIVOS = {
    ("titulares", ""): "BarlowCondensed-SemiBold.ttf",
    ("titulares", "B"): "BarlowCondensed-Bold.ttf",
    ("texto", ""): "Barlow-Regular.ttf",
    ("texto", "B"): "Barlow-SemiBold.ttf",
    ("texto", "I"): "Barlow-Italic.ttf",
    ("texto", "M"): "Barlow-Medium.ttf",
    ("mono", ""): "IBMPlexMono-Regular.ttf",
    ("mono", "B"): "IBMPlexMono-Medium.ttf",
}

# Alternativas por sistema si las fuentes del proyecto no cargan
# matplotlib siempre trae DejaVu: es el respaldo seguro para graficos y PDF
RESPALDO_MPL = {"titulares": ["DejaVu Sans"], "texto": ["DejaVu Sans"], "mono": ["DejaVu Sans Mono"]}

RESPALDO = {
    "titulares": ["Bahnschrift SemiBold Condensed", "Arial Narrow", "Avenir Next Condensed", "DejaVu Sans Condensed"],
    "texto": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "mono": ["Consolas", "Menlo", "Courier New", "DejaVu Sans Mono"],
}


def paleta():
    """Colores del proyecto (config/proyecto.yaml)."""
    return config.proyecto()["paleta"]


def familia(rol):
    """Nombre de la familia tipografica de un rol: titulares, texto o mono."""
    return config.proyecto()["tipografia"][rol]


def ruta_fuente(rol, estilo=""):
    return DIR_FUENTES / ARCHIVOS[(rol, estilo)]


# ---------- matplotlib ----------

@lru_cache(maxsize=None)
def preparar_matplotlib():
    """Registra las fuentes en matplotlib y aplica el estilo editorial. Devuelve True si cargaron."""
    import logging

    import matplotlib
    from matplotlib import font_manager
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    cargadas = True
    for archivo in set(ARCHIVOS.values()):
        try:
            font_manager.fontManager.addfont(str(DIR_FUENTES / archivo))
        except Exception as error:  # fuente faltante o corrupta: se usa respaldo
            log.warning("No se pudo cargar %s: %s", archivo, error)
            cargadas = False
    p = paleta()
    matplotlib.rcParams.update({
        "font.family": [familia("texto")] + RESPALDO_MPL["texto"],
        "font.size": 8,
        "axes.facecolor": p["blanco"],
        "figure.facecolor": p["blanco"],
        "axes.edgecolor": p["linea"],
        "axes.labelcolor": p["gris"],
        "axes.titleweight": "bold",
        "xtick.color": p["gris"],
        "ytick.color": p["gris"],
        "grid.color": "#E3E4DA",
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "svg.fonttype": "none",
    })
    return cargadas


def fuente_mpl(rol, **extra):
    """Diccionario de fuente para textos de matplotlib (fontdict)."""
    preparar_matplotlib()
    return {"family": [familia(rol)] + RESPALDO_MPL[rol], **extra}


# ---------- Tkinter ----------

def registrar_fuentes_tk():
    """En Windows registra las TTF del proyecto solo para este proceso. Devuelve True si pudo."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        fr_private = 0x10
        agregar = ctypes.windll.gdi32.AddFontResourceExW
        return all(agregar(str(DIR_FUENTES / archivo), fr_private, 0) > 0 for archivo in set(ARCHIVOS.values()))
    except Exception as error:
        log.warning("No se pudieron registrar las fuentes en Windows: %s", error)
        return False


def familias_tk(raiz_tk):
    """{rol: familia disponible} eligiendo la del proyecto o su mejor respaldo."""
    from tkinter import font as tkfont
    disponibles = set(tkfont.families(raiz_tk))
    elegidas = {}
    for rol in ("titulares", "texto", "mono"):
        opciones = [familia(rol)] + RESPALDO[rol]
        if rol == "titulares":
            # En Windows la variante condensada se registra con su propio nombre
            opciones = ["Barlow Condensed SemiBold", "Barlow Condensed"] + opciones
        elegidas[rol] = next((f for f in opciones if f in disponibles), "TkDefaultFont")
    return elegidas


# ---------- PDF (fpdf2) ----------

def registrar_fuentes_pdf(pdf):
    """Agrega las fuentes del proyecto a un FPDF. Usa DejaVu de matplotlib si faltan archivos."""
    nombres = {"titulares": "Titular", "texto": "Texto", "mono": "Mono"}
    try:
        for (rol, estilo), archivo in ARCHIVOS.items():
            if estilo in ("", "B", "I"):
                pdf.add_font(nombres[rol], estilo, str(DIR_FUENTES / archivo))
        if ("mono", "I") not in ARCHIVOS:
            pdf.add_font("Mono", "I", str(DIR_FUENTES / ARCHIVOS[("mono", "")]))
        if ("titulares", "I") not in ARCHIVOS:
            pdf.add_font("Titular", "I", str(DIR_FUENTES / ARCHIVOS[("titulares", "")]))
    except Exception as error:
        import matplotlib
        log.warning("Fuentes del proyecto no disponibles para el PDF (%s); se usa DejaVu", error)
        base = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        for nombre in nombres.values():
            pdf.add_font(nombre, "", str(base / "DejaVuSans.ttf"))
            pdf.add_font(nombre, "B", str(base / "DejaVuSans-Bold.ttf"))
            pdf.add_font(nombre, "I", str(base / "DejaVuSans-Oblique.ttf"))
    return nombres
