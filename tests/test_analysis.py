"""Tests de indicadores con la semana de muestra (1 dia real) y casos sinteticos."""

import pandas as pd
import pytest

from src.analysis import calcular_resumen
from src.analysis.indicadores import comparar_embalses, hora_del_dia, precio_capturado
from src.analysis.modelo import Indicador
from src.utils import config
from tests.conftest import SEMANA_MUESTRA


@pytest.fixture(scope="module")
def resumen(processed_muestra):
    raiz, _, _ = processed_muestra
    return calcular_resumen(SEMANA_MUESTRA, raiz)


def test_resumen_basico(resumen):
    assert resumen.texto_semana == "Semana del 28 de septiembre al 4 de octubre de 2026"
    assert resumen.es_preliminar  # solo 1 de 7 dias
    assert resumen.dias_con_datos == 1
    assert 50 < resumen.ind("cmg_promedio").valor < 2000
    assert 5000 < resumen.ind("demanda_maxima").valor < 12000
    assert resumen.ind("demanda_maxima").momento is not None


def test_sin_semana_anterior_no_rompe(resumen):
    assert resumen.ind("cmg_promedio").anterior is None
    assert resumen.ind("cmg_promedio").var_anterior is None


def test_mix_suma_uno(resumen):
    assert abs(sum(resumen.mix.values()) - 1) < 1e-6
    renov = resumen.ind("participacion_renovable").valor
    sin_hidro = resumen.ind("participacion_renovable_sin_hidro").valor
    assert 0 < sin_hidro < renov < 1


def test_perfil_24_horas(resumen):
    assert resumen.perfil_cmg["hora"].tolist() == list(range(24))


def test_tres_hechos_aunque_no_haya_comparacion(resumen):
    assert len(resumen.hechos) == 3


def test_todo_indicador_tiene_glosario(resumen):
    glosario = config.glosario()["indicadores"]
    claves = set(resumen.indicadores) | {"mix_generacion", "perfil_horario"} | {h.clave for h in resumen.hechos}
    faltan = claves - set(glosario)
    assert not faltan, f"Indicadores sin glosario: {faltan}"
    for clave, entrada in glosario.items():
        assert {"nombre", "explicacion_simple", "por_que_importa", "unidad"} <= set(entrada), clave


def test_glosario_sin_guion_largo():
    texto = (config.DIR_CONFIG / "glosario.yaml").read_text(encoding="utf-8")
    assert "—" not in texto


def test_indicador_variaciones():
    assert Indicador("x", 110, "MW", anterior=100).var_anterior == pytest.approx(0.10)
    assert Indicador("x", 0.5, "%", anterior=0.45, es_puntos=True).var_anterior == pytest.approx(0.05)
    assert Indicador("x", 5, "h", anterior=0).var_anterior is None


def test_hora_del_dia():
    s = pd.Series(pd.to_datetime(["2026-10-01 00:30", "2026-10-01 01:00", "2026-10-02 00:00"]))
    assert hora_del_dia(s).tolist() == [0, 0, 23]


def test_precio_capturado_pondera_por_generacion():
    t = pd.to_datetime(["2026-10-01 01:00", "2026-10-01 13:00"])
    gen = pd.DataFrame({"fecha_hora": t, "tecnologia": "solar", "valor": [0, 100]})
    cmg = pd.DataFrame({"fecha_hora": t, "valor": [300.0, 100.0]})
    assert precio_capturado(gen, cmg, "solar") == pytest.approx(100.0)


def test_comparar_embalses_solo_comunes():
    actual = pd.Series({"A": 10.0, "B": 20.0, "C": 5.0})
    previa = pd.Series({"A": 8.0, "B": 20.0})
    var, ref = comparar_embalses(actual, previa)
    assert ref == 28.0 and var == pytest.approx(30 / 28 - 1)


def test_revision_preliminar_vs_revisado():
    from src.analysis.indicadores import revision_preliminar
    t = pd.to_datetime(["2026-10-01 10:00", "2026-10-01 10:30"])
    base = {"entidad": "B", "variable": "cmg_total"}
    pre = pd.DataFrame({"fecha_hora": t, "valor": [100.0, 200.0], **base})
    rev = pd.DataFrame({"fecha_hora": t, "valor": [100.0, 300.0], "fuente": "ieod_cmg", **base})
    r = revision_preliminar(pre, rev, "B")
    assert r["intervalos"] == 2 and r["cambiados"] == 1
    assert r["diferencia_media_pct"] == pytest.approx(50 / 200)


def test_cmg_por_barra_con_coordenadas():
    from src.analysis.indicadores import cmg_por_barra
    cmg = pd.DataFrame({"entidad": ["SANTA ROSA 220", "SANTA ROSA 220", "INVENTADA 1"],
                        "variable": "cmg_total", "valor": [100.0, 200.0, 50.0]})
    barras = cmg_por_barra(cmg).set_index("barra")
    assert barras.loc["SANTA ROSA 220", "cmg_promedio"] == 150.0
    assert barras.loc["SANTA ROSA 220", "latitud"] < 0          # Lima esta al sur del ecuador
    assert pd.isna(barras.loc["INVENTADA 1", "latitud"])


def test_tres_niveles(resumen):
    from src.narrative import niveles
    n = niveles(resumen, "cmg_promedio")
    assert n["rapida"].startswith("Costo marginal promedio")
    assert n["intermedia"] and "Santa Rosa" in n["tecnica"]
