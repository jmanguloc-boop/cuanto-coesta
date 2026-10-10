"""Tests de la narrativa: forma, reglas de estilo y que no afirme causas sin respaldo."""

import re
from dataclasses import replace

import pytest

from src.analysis import calcular_resumen
from src.narrative import elegir, enumerar, generar_narrativa, parrafo_precios, pulir
from tests.conftest import SEMANA_MUESTRA

PALABRAS_CAUSALES = re.compile(r"\b(porque|debido a|a causa de|por culpa de|gracias a)\b", re.I)


@pytest.fixture(scope="module")
def resumen(processed_muestra):
    return calcular_resumen(SEMANA_MUESTRA, processed_muestra[0])


@pytest.fixture(scope="module")
def narrativa(resumen):
    return generar_narrativa(resumen)


def todos_los_textos(n):
    return n.titulares + list(n.parrafos.values()) + list(n.titulos_graficos.values())


def test_tres_titulares_y_cuatro_parrafos(narrativa):
    assert len(narrativa.titulares) == 3
    assert set(narrativa.parrafos) == {"precios", "demanda", "generacion", "hidrologia"}
    assert all(len(t) < 110 for t in narrativa.titulares)


def test_reglas_de_estilo(narrativa):
    for texto in todos_los_textos(narrativa):
        assert "—" not in texto, texto          # sin guion largo
        assert " de el " not in texto, texto
        assert ".." not in texto, texto
        assert "None" not in texto and "nan" not in texto, texto


def test_sin_causas_inventadas(narrativa):
    for texto in todos_los_textos(narrativa):
        assert not PALABRAS_CAUSALES.search(texto), texto


def test_relacion_hidro_solo_con_respaldo(resumen):
    # Sin semana anterior no se menciona relacion alguna con la hidro
    assert "coincidió" not in parrafo_precios(resumen)
    # Con precio +30% e hidro -5 pp si se menciona
    prom = replace(resumen.ind("cmg_promedio"), var_anterior=0.30)
    mix_ant = dict(resumen.mix, hidro=resumen.mix["hidro"] + 0.05)
    r2 = replace(resumen, indicadores=dict(resumen.indicadores, cmg_promedio=prom), mix_anterior=mix_ant)
    assert "coincidió con menos generación hidroeléctrica" in parrafo_precios(r2)


def test_eleccion_reproducible_y_variada():
    opciones = ["a", "b", "c"]
    assert elegir(opciones, "2026-W40", "x") == elegir(opciones, "2026-W40", "x")
    assert len({elegir(opciones, f"2026-W{s:02d}", "x") for s in range(1, 30)}) > 1


def test_helpers_de_texto():
    assert enumerar(["a", "b", "c"]) == "a, b y c"
    assert pulir("vino de el gas a las 6 p. m..") == "vino del gas a las 6 p. m."
