"""Tests del dashboard: tema sincronizado con la paleta y app que levanta con datos de muestra."""

import tomllib

import pytest

from src.utils import config


def test_tema_streamlit_coincide_con_paleta():
    tema = tomllib.loads((config.RAIZ / "app" / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
    paleta = config.proyecto()["paleta"]
    assert tema["primaryColor"] == paleta["primario"]
    assert tema["backgroundColor"] == paleta["fondo"]
    assert tema["secondaryBackgroundColor"] == paleta["fondo_suave"]
    assert tema["textColor"] == paleta["texto"]


def test_graficos_se_construyen(processed_muestra):
    import sys
    sys.path.insert(0, str(config.RAIZ / "app"))
    import graficos as G
    from src.analysis import calcular_resumen
    from tests.conftest import SEMANA_MUESTRA

    r = calcular_resumen(SEMANA_MUESTRA, processed_muestra[0])
    figuras = [
        G.grafico_precio_semana(r.serie_cmg, r.umbrales_precio, "t"),
        G.grafico_perfil_horario(r.perfil_cmg, "t"),
        G.grafico_demanda(r.serie_demanda, "t"),
        G.grafico_generacion(r.serie_generacion, "t"),
        G.grafico_mix(r.mix, r.mix_anterior, "t"),
        G.grafico_embalses(r.serie_embalses, "t"),
        G.grafico_embalses_detalle(r.embalses_detalle, "t"),
    ]
    for fig in figuras:
        assert fig.data, "grafico vacio"
        for traza in fig.data:
            if traza.hovertemplate:
                assert "<extra></extra>" in traza.hovertemplate
    colores = {t.name: t.fillcolor for t in figuras[3].data}
    assert colores["Hidroeléctrica"] == config.color_tecnologia("hidro")


@pytest.mark.skipif(not (config.DIR_PROCESSED / "demanda").exists(), reason="sin datos procesados locales")
def test_app_levanta_sin_errores():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(config.RAIZ / "app" / "streamlit_app.py"), default_timeout=180).run()
    assert not at.exception
    assert len(at.tabs) == 6
    assert len(at.metric) >= 4
