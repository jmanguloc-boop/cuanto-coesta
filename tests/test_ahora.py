"""Tests de Cuanto COESta Ahora: versiones, lectura del COES, memoria del precio y rarezas."""

from datetime import date, datetime

import pandas as pd
import pytest

from src.ahora import db
from src.ahora.extractor import _momento, leer_tabla_proceso
from src.analysis.rarezas import evaluar, salto_brusco
from src.utils.config import DIR_SAMPLES


@pytest.fixture
def con(tmp_path):
    with db.conectar(tmp_path / "prueba.sqlite") as c:
        yield c


def fila(hora, valor, barra="SANTA ROSA 220"):
    return {"fecha_hora": hora, "barra": barra, "cmg_total": valor, "cmg_energia": valor,
            "cmg_congestion": 0.0, "correlativo": 1}


def test_versiones_solo_si_cambia(con):
    assert db.guardar_cmg(con, [fila("2026-10-10 10:00", 100.0)], "t1") == (1, 0)
    assert db.guardar_cmg(con, [fila("2026-10-10 10:00", 100.0)], "t2") == (0, 0)   # igual: no se duplica
    assert db.guardar_cmg(con, [fila("2026-10-10 10:00", 120.0)], "t3") == (0, 1)   # el COES lo corrigio
    vigente = db.cmg_vigente(con, "SANTA ROSA 220")
    assert vigente["cmg_total"].tolist() == [120.0]
    rev = db.revisiones(con)
    assert rev.iloc[0]["primero"] == 100.0 and rev.iloc[0]["ultimo"] == 120.0


def test_demanda_versionada(con):
    filas = [{"fecha_hora": "2026-10-10 10:00", "variable": "ejecutada", "valor": 8000.0},
             {"fecha_hora": "2026-10-10 10:00", "variable": "programa_diario", "valor": 8100.0}]
    assert db.guardar_demanda(con, filas, "t1") == (2, 0)
    ancho = db.demanda_vigente(con)
    assert ancho.loc[0, "ejecutada"] == 8000.0 and ancho.loc[0, "programa_diario"] == 8100.0


def test_lee_tabla_real_del_coes():
    html = (DIR_SAMPLES / "cmg_tiempo_real_proceso.html").read_text(encoding="utf-8")
    filas = leer_tabla_proceso(html, 504131, datetime(2026, 10, 10, 10, 0))
    assert len(filas) == 5
    sr = [f for f in filas if f["barra"] == "SANTA ROSA 220"]
    assert sr and sr[0]["cmg_total"] > 0 and sr[0]["fecha_hora"] == "2026-10-10 10:00"


def test_momento_fin_de_dia():
    assert _momento(date(2026, 10, 10), "23:59") == datetime(2026, 10, 11, 0, 0)
    assert _momento(date(2026, 10, 10), "10:30") == datetime(2026, 10, 10, 10, 30)


def historia_plana(valor=200.0, dias=20, hora="10:00"):
    indices = pd.to_datetime([f"2026-09-{d:02d} {hora}" for d in range(1, dias + 1)])
    ruido = [valor + (i % 5) * 4 for i in range(dias)]
    return pd.Series(ruido, index=indices)


def test_rareza_detecta_valor_inusual_para_su_hora():
    historia = historia_plana()
    ev = evaluar(800.0, "2026-09-25 10:00", historia)
    assert ev.es_rara and "por encima" in ev.regla
    assert not evaluar(205.0, "2026-09-25 10:00", historia).es_rara


def test_rareza_no_juzga_sin_historia():
    ev = evaluar(800.0, "2026-09-25 10:00", historia_plana(dias=3))
    assert not ev.es_rara and "Sin juicio" in ev.regla


def test_salto_brusco():
    assert salto_brusco(500.0, 200.0) is not None
    assert salto_brusco(230.0, 200.0) is None
    assert salto_brusco(500.0, None) is None
