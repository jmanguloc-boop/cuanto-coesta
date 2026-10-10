"""Fixtures compartidas: arma un data/raw falso con las muestras de 1 dia (01/10/2026)."""

import shutil

import pytest

from src.utils.config import DIR_SAMPLES

SEMANA_MUESTRA = "2026-W40"
MUESTRAS = {
    "demanda": "demanda_20261001.xlsx",
    "generacion": "generacion_20261001.json",
    "costo_marginal": "costo_marginal_20261001.xlsx",
    "costo_marginal_tr": "costo_marginal_tr_20261001.xlsx",
    "ieod_anexo": "ieod_anexo_20261001.xlsx",
}


@pytest.fixture(scope="session")
def raw_muestra(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("raw")
    for fuente, archivo in MUESTRAS.items():
        (raiz / fuente).mkdir()
        shutil.copy(DIR_SAMPLES / archivo, raiz / fuente / archivo)
    return raiz


@pytest.fixture(scope="session")
def processed_muestra(raw_muestra, tmp_path_factory):
    from src.transform import transformar_semana
    raiz = tmp_path_factory.mktemp("processed")
    filas, avisos = transformar_semana(SEMANA_MUESTRA, raw_muestra, raiz)
    return raiz, filas, avisos
