"""Tests de las mejoras del analisis gerencial: serie continua, USD, relleno de huecos, red corporativa."""

import json
from datetime import date

import pandas as pd
import pytest

from src.ahora import db
from src.ahora.extractor import dias_a_revisar
from src.analysis import serie as S
from src.extract import bcrp
from src.extract.cliente import crear_sesion


@pytest.fixture(scope="module")
def serie_muestra(processed_muestra):
    raiz, _, _ = processed_muestra
    return S.cmg_rango(date(2026, 10, 1), date(2026, 10, 1), "SANTA ROSA 220", raiz=raiz, ruta_db=raiz / "no_existe.sqlite")


def test_serie_continua_usa_el_confirmado(serie_muestra):
    assert len(serie_muestra) == 48
    assert set(serie_muestra["estado"]) == {"confirmado"}
    assert {"total", "energia", "congestion"} <= set(serie_muestra.columns)


def test_resumen_base_punta_fuera_punta(serie_muestra):
    r = S.resumir(serie_muestra, date(2026, 10, 1), date(2026, 10, 1), "SANTA ROSA 220")
    assert r.cobertura == pytest.approx(1.0)
    punta = S.es_punta(serie_muestra["fecha_hora"])
    assert punta.sum() == 10    # de 18:00 a 23:00 son 10 medias horas
    assert r.base == pytest.approx(serie_muestra["total"].mean())


def test_diario_mensual_y_calor(serie_muestra):
    assert len(S.diario(serie_muestra)) == 1
    assert len(S.mensual(serie_muestra)) == 1
    assert S.matriz_calor(serie_muestra).shape == (1, 48)


def test_prioridad_confirmado_sobre_preliminar():
    t = pd.to_datetime(["2026-10-01 10:00"] * 2)
    partes = pd.DataFrame({"fecha_hora": t, "fecha": [date(2026, 10, 1)] * 2, "total": [100.0, 150.0],
                           "energia": [100.0, 150.0], "congestion": [0.0, 0.0], "estado": ["preliminar", "confirmado"]})
    partes["prioridad"] = partes["estado"].map(S.PRIORIDAD)
    elegido = partes.sort_values(["fecha_hora", "prioridad"]).drop_duplicates("fecha_hora", keep="first")
    assert elegido["total"].tolist() == [150.0]


def test_atajos_de_rango():
    hoy = date(2026, 10, 12)
    assert S.rango_atajo("7d", hoy, None) == (date(2026, 10, 6), hoy)
    assert S.rango_atajo("mes", hoy, None) == (date(2026, 10, 1), hoy)
    assert S.rango_atajo("hidro", hoy, None) == (date(2025, 11, 1), hoy)   # ano hidrologico nov a oct
    assert S.rango_atajo("hidro", date(2026, 11, 5), None) == (date(2026, 11, 1), date(2026, 11, 5))


def test_exportar_excel(serie_muestra, tmp_path):
    ruta = S.exportar_excel(serie_muestra, tmp_path / "cmg.xlsx", "SANTA ROSA 220")
    hojas = pd.read_excel(ruta, sheet_name=None)
    assert set(hojas) == {"medias_horas", "diario", "nota"}
    assert len(hojas["medias_horas"]) == 48


def test_bcrp_interpreta_y_rellena_fines_de_semana():
    crudo = json.dumps({"periods": [{"name": "25.Set.26", "values": ["3.425"]}, {"name": "28.Set.26", "values": ["3.44"]},
                                    {"name": "08.Oct.26", "values": ["n.d."]}]}).encode()
    tabla = bcrp.interpretar(crudo)
    assert tabla["fecha"].tolist() == [date(2026, 9, 25), date(2026, 9, 28)]
    tc = bcrp.tc_para([date(2026, 9, 27), date(2026, 9, 28)], tabla)   # domingo toma el viernes
    assert tc.tolist() == [3.425, 3.44]


def test_en_dolares_divide_por_tipo_de_cambio(serie_muestra):
    tabla = pd.DataFrame({"fecha": [date(2026, 10, 1)], "tc": [4.0]})
    usd = S.en_dolares(serie_muestra, tabla)
    assert usd["total"].iloc[0] == pytest.approx(serie_muestra["total"].iloc[0] / 4.0)


def test_relleno_de_huecos(tmp_path):
    with db.conectar(tmp_path / "a.sqlite") as con:
        hoy = date(2026, 10, 12)
        assert dias_a_revisar(con, hoy) == [date(2026, 10, 11), hoy]          # base vacia: ayer y hoy
        db.guardar_cmg(con, [{"fecha_hora": "2026-10-09 15:00", "barra": "SANTA ROSA 220", "cmg_total": 1.0,
                              "cmg_energia": 1.0, "cmg_congestion": 0.0, "correlativo": 1}], "t")
        assert dias_a_revisar(con, hoy)[0] == date(2026, 10, 9)               # rellena desde el ultimo dato
        assert len(dias_a_revisar(con, date(2026, 10, 30))) == 7               # nunca mas de 7 dias


def test_sesion_con_proxy_manual():
    sesion = crear_sesion({"proxy": "http://proxy.empresa:8080", "certificados_sistema": False})
    assert sesion.proxies["https"] == "http://proxy.empresa:8080"


def test_diagnostico_explica_errores():
    from src.utils.diagnostico import _explicar
    assert "certificado" in _explicar(Exception("CERTIFICATE_VERIFY_FAILED")).lower()
    assert "proxy" in _explicar(Exception("407 Proxy Authentication Required")).lower()


def test_eventos_del_ieod(processed_muestra):
    from src.analysis import centrales as C
    raiz, filas, _ = processed_muestra
    assert filas.get("eventos", 0) > 0
    ev = C.eventos_semana("2026-W40", raiz)
    assert {"origen", "empresa", "inicio", "final", "mw", "programado", "clase"} <= set(ev.columns)
    assert set(ev["origen"]) <= {"indisponibilidad", "mantenimiento", "evento"}
    dia = C.indisponible_por_dia(ev, date(2026, 9, 28), date(2026, 10, 4))
    assert len(dia) == 7 and dia.loc[3, "programado"] + dia.loc[3, "forzado"] > 0   # el 01/10 es el dia con datos


def test_centrales_y_empresas(processed_muestra):
    from src.analysis import centrales as C
    from src.utils.datos import leer_tabla
    raiz, _, _ = processed_muestra
    cen = leer_tabla("centrales", "2026-W40", raiz)
    emp = C.participacion_empresas(cen)
    assert emp["cuota"].sum() <= 1.0001 and len(emp) == 10
    top = C.top_centrales(cen, 3)
    cmg = pd.DataFrame({"fecha_hora": cen["fecha_hora"].unique()})
    cmg["total"] = 100.0
    d = C.detalle_central(cen, top["central"].iloc[0], cmg)
    assert d["precio_capturado"] == pytest.approx(100.0)                       # precio plano: capturado = precio
    assert d["ingreso_estimado"] == pytest.approx(d["energia_mwh"] * 100.0, rel=1e-6)
