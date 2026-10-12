"""Tests de transformacion con las muestras reales de 1 dia."""

from datetime import date, datetime

import duckdb
import pandas as pd

from src.transform.comun import clave_ascii, fin_de_intervalo, validar
from src.transform.tablas import corregir_solar_bagazo
from tests.conftest import SEMANA_MUESTRA


def leer(raiz, tabla):
    return pd.read_parquet(raiz / tabla / f"{tabla}_{SEMANA_MUESTRA}.parquet")


def test_clave_ascii_iguala_tildes_rotas():
    assert clave_ascii("BIOGÁS") == clave_ascii("BIOG�S") == "BIOGS"
    assert clave_ascii("NAFTA & GAS REFINERÍA") == "NAFTAGASREFINERA"


def test_fin_de_intervalo_2359_es_medianoche():
    assert fin_de_intervalo(datetime(2026, 10, 1, 23, 59)) == datetime(2026, 10, 2, 0, 0)
    assert fin_de_intervalo(datetime(2026, 10, 1, 12, 30)) == datetime(2026, 10, 1, 12, 30)


def test_se_generan_las_cinco_tablas(processed_muestra):
    _, filas, avisos = processed_muestra
    assert set(filas) == {"demanda", "generacion", "costo_marginal", "cmg_preliminar", "embalses", "centrales", "eventos"}
    assert any("1 de 7 dias" in a for a in avisos)  # la muestra es de un solo dia


def test_columnas_formato_largo(processed_muestra):
    raiz, _, _ = processed_muestra
    for tabla in ("demanda", "generacion", "costo_marginal", "embalses", "centrales"):
        df = leer(raiz, tabla)
        assert {"fecha_hora", "entidad", "variable", "valor", "unidad", "es_preliminar"} <= set(df.columns)


def test_demanda_48_intervalos_y_no_preliminar(processed_muestra):
    raiz, _, _ = processed_muestra
    df = leer(raiz, "demanda")
    ejecutada = df[df["variable"] == "demanda_ejecutada"]
    assert len(ejecutada) == 48
    assert ejecutada["fecha"].unique().tolist() == [date(2026, 10, 1)]
    assert not ejecutada["es_preliminar"].any()  # hay IEOD de ese dia


def test_generacion_cuadra_con_demanda(processed_muestra):
    raiz, _, _ = processed_muestra
    gen = leer(raiz, "generacion")["valor"].sum()
    dem = leer(raiz, "demanda").query("variable == 'demanda_ejecutada'")["valor"].sum()
    assert abs(gen / dem - 1) < 0.001


def test_solar_no_produce_de_noche(processed_muestra):
    raiz, _, _ = processed_muestra
    gen = leer(raiz, "generacion")
    solar = gen[gen["tecnologia"] == "solar"]
    noche = solar[solar["fecha_hora"].dt.hour.between(1, 4)]
    assert noche["valor"].max() < 1
    assert solar["valor"].max() > 500


def test_corregir_solar_bagazo_no_toca_series_correctas():
    plano = [{"Nombre": f"2026/10/01 {h:02d}:00:00", "Valor": 60} for h in range(24)]
    campana = [{"Nombre": f"2026/10/01 {h:02d}:00:00", "Valor": 1000 if 8 <= h <= 16 else 0} for h in range(24)]
    correctas = [{"Name": "SOLAR", "Data": campana}, {"Name": "BAGAZO", "Data": plano}]
    cruzadas = [{"Name": "SOLAR", "Data": plano}, {"Name": "BAGAZO", "Data": campana}]
    assert corregir_solar_bagazo(correctas) == {}
    assert corregir_solar_bagazo(cruzadas) == {"SOLAR": "BAGAZO", "BAGAZO": "SOLAR"}


def test_costo_marginal_ieod_completo(processed_muestra):
    raiz, _, _ = processed_muestra
    df = leer(raiz, "costo_marginal")
    sr = df[(df["entidad"] == "SANTA ROSA 220") & (df["variable"] == "cmg_total")]
    assert len(sr) == 48
    assert sr["fecha_hora"].max() == pd.Timestamp("2026-10-02 00:00")
    assert set(df["fuente"]) == {"ieod_cmg"}  # el respaldo no se usa si hay IEOD


def test_embalses_volumen_y_nivel(processed_muestra):
    raiz, _, _ = processed_muestra
    df = leer(raiz, "embalses")
    assert set(df["unidad"]) == {"Hm3", "msnm"}
    assert df.query("variable == 'volumen_util'")["entidad"].nunique() >= 20


def test_consultable_con_duckdb(processed_muestra):
    raiz, _, _ = processed_muestra
    ruta = (raiz / "centrales" / "*.parquet").as_posix()
    n = duckdb.sql(f"select count(distinct entidad) from '{ruta}'").fetchone()[0]
    assert n > 100


def test_validar_detecta_problemas():
    df = pd.DataFrame({
        "fecha_hora": pd.to_datetime(["2026-10-01 00:30"] * 2),
        "fecha": [date(2026, 10, 1)] * 2,
        "entidad": ["X", "X"], "variable": ["v", "v"], "valor": [-3.0, -3.0],
    })
    avisos = validar(df, "prueba", por_dia=48, minimo=0)
    assert len(avisos) == 3  # duplicados, faltantes, valores imposibles
