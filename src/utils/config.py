"""Lectura de los archivos de config/ (con cache en memoria)."""

from functools import lru_cache
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
DIR_CONFIG = RAIZ / "config"
DIR_DATA = RAIZ / "data"
DIR_RAW = DIR_DATA / "raw"
DIR_PROCESSED = DIR_DATA / "processed"
DIR_SAMPLES = DIR_DATA / "samples"
DIR_REPORTS = RAIZ / "reports"
DIR_CAPTURAS = RAIZ / "docs" / "capturas"


@lru_cache(maxsize=None)
def cargar_yaml(nombre):
    """Lee config/<nombre>.yaml."""
    with open(DIR_CONFIG / f"{nombre}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def proyecto():
    return cargar_yaml("proyecto")


def fuentes():
    return cargar_yaml("fuentes")


def glosario():
    return cargar_yaml("glosario")


def color_tecnologia(clave):
    techs = proyecto()["tecnologias"]
    return techs.get(clave, techs["otros"])["color"]


def nombre_tecnologia(clave):
    techs = proyecto()["tecnologias"]
    return techs.get(clave, techs["otros"])["nombre"]
