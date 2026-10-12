"""Lectura de los archivos de config/ (con cache en memoria).

Donde viven los datos descargados:
1. La carpeta de la variable de entorno CUANTO_COESTA_DATOS, si existe.
2. Si el proyecto esta dentro de OneDrive o SharePoint: %LOCALAPPDATA%/CuantoCOESta/data
   (la sincronizacion corrompe bases SQLite abiertas).
3. Si no: <proyecto>/data.
"""

import os
from functools import lru_cache
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
DIR_CONFIG = RAIZ / "config"


def _carpeta_datos():
    if os.environ.get("CUANTO_COESTA_DATOS"):
        return Path(os.environ["CUANTO_COESTA_DATOS"])
    ruta = str(RAIZ).lower()
    if ("onedrive" in ruta or "sharepoint" in ruta) and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "CuantoCOESta" / "data"
    return RAIZ / "data"


DIR_DATA = _carpeta_datos()
DIR_RAW = DIR_DATA / "raw"
DIR_PROCESSED = DIR_DATA / "processed"
DIR_SAMPLES = RAIZ / "data" / "samples"     # muestras del repositorio, siempre junto al codigo
DIR_REPORTS = RAIZ / "reports"
DIR_CAPTURAS = RAIZ / "docs" / "capturas"


@lru_cache(maxsize=None)
def cargar_yaml(nombre):
    """Lee config/<nombre>.yaml."""
    with open(DIR_CONFIG / f"{nombre}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def proyecto():
    """Contenido de config/proyecto.yaml."""
    return cargar_yaml("proyecto")


def fuentes():
    """Contenido de config/fuentes.yaml."""
    return cargar_yaml("fuentes")


def glosario():
    """Contenido de config/glosario.yaml."""
    return cargar_yaml("glosario")


def color_tecnologia(clave):
    """Color fijo de una tecnologia."""
    techs = proyecto()["tecnologias"]
    return techs.get(clave, techs["otros"])["color"]


def nombre_tecnologia(clave):
    """Nombre visible de una tecnologia."""
    techs = proyecto()["tecnologias"]
    return techs.get(clave, techs["otros"])["nombre"]
