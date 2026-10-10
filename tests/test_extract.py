"""Tests del extractor sin red: el servidor COES se simula con archivos de data/samples."""

import io
import os
import time
import zipfile
from datetime import date, datetime

import pytest

from src.extract import costo_marginal, generacion, ieod_anexo
from src.extract.__main__ import descargar_todo
from src.extract.base import partir_rango, ruta_ieod, validar_contenido
from src.extract.cliente import ClienteCoes, formato_coes
from src.utils.config import DIR_SAMPLES

AHORA = lambda: datetime(2026, 10, 10, 12, 0)


class RespuestaFalsa:
    def __init__(self, contenido):
        self.content = contenido

    def raise_for_status(self):
        pass


class SesionFalsa:
    """Responde segun la URL pedida y registra cada pedido."""

    def __init__(self, respuestas):
        self.headers = {}
        self.pedidos = []
        self.respuestas = respuestas  # lista de (fragmento_url, bytes)

    def _responder(self, url, datos):
        self.pedidos.append((url, datos))
        for fragmento, contenido in self.respuestas:
            if fragmento in url:
                return RespuestaFalsa(contenido)
        return RespuestaFalsa(b"")

    def post(self, url, data, timeout):
        return self._responder(url, data)

    def get(self, url, params=None, timeout=None):
        return self._responder(url, params)


def cliente_falso(respuestas):
    return ClienteCoes(sesion=SesionFalsa(respuestas), dormir=lambda s: None, ahora=AHORA)


def zip_cmg_falso(carpeta="CMg20261001/"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(f"{carpeta}CMgCP0110.xlsx", (DIR_SAMPLES / "costo_marginal_20261001.xlsx").read_bytes())
        z.writestr("CMg20261001/PSSE_20261001.zip", b"no se usa")
    return buffer.getvalue()


def test_partir_rango_en_tramos():
    tramos = partir_rango(date(2026, 1, 1), date(2026, 2, 15), 30)
    assert tramos == [(date(2026, 1, 1), date(2026, 1, 30)), (date(2026, 1, 31), date(2026, 2, 15))]
    assert len(partir_rango(date(2026, 10, 1), date(2026, 10, 7), 1)) == 7
    with pytest.raises(ValueError):
        partir_rango(date(2026, 10, 2), date(2026, 10, 1), 1)


def test_formato_y_ruta_ieod():
    assert formato_coes(date(2026, 10, 1)) == "01/10/2026"
    ruta = ruta_ieod("Post Operación/Reportes/IEOD/{anio}/{mes_carpeta}/{dia}/AnexoA_{ddmm}.xlsx", date(2026, 9, 5))
    assert ruta == "Post Operación/Reportes/IEOD/2026/09_Setiembre/05/AnexoA_0509.xlsx"


def test_validar_rechaza_html_como_excel():
    with pytest.raises(ValueError):
        validar_contenido(b"<html>Server Error</html>", "xlsx")
    validar_contenido(b"PK\x03\x04resto", "xlsx")


def test_generacion_dia_por_dia_y_cache(tmp_path):
    muestra = (DIR_SAMPLES / "generacion_20261001.json").read_bytes()
    cliente = cliente_falso([("Generacion", muestra)])
    archivos = generacion.descargar(date(2026, 9, 1), date(2026, 9, 3), cliente=cliente, raiz=tmp_path)
    assert len(archivos) == 3
    url, datos = cliente.sesion.pedidos[0]
    assert datos == {"fechaInicial": "01/09/2026", "fechaFinal": "01/09/2026", "indicador": "0"}
    # Segunda corrida: dias viejos en cache, cero pedidos nuevos
    generacion.descargar(date(2026, 9, 1), date(2026, 9, 3), cliente=cliente, raiz=tmp_path)
    assert len(cliente.sesion.pedidos) == 3


def test_costo_marginal_extrae_excel_del_zip(tmp_path):
    cliente = cliente_falso([("CMg20261001.zip", zip_cmg_falso())])
    archivos = costo_marginal.descargar(date(2026, 10, 1), date(2026, 10, 1), cliente=cliente, raiz=tmp_path)
    assert len(archivos) == 1
    assert archivos[0].read_bytes() == (DIR_SAMPLES / "costo_marginal_20261001.xlsx").read_bytes()


def test_costo_marginal_zip_sin_carpeta(tmp_path):
    # Algunos dias el COES publica el zip sin la carpeta CMgAAAAMMDD/
    cliente = cliente_falso([("CMg20261001.zip", zip_cmg_falso(carpeta=""))])
    archivos = costo_marginal.descargar(date(2026, 10, 1), date(2026, 10, 1), cliente=cliente, raiz=tmp_path)
    assert [a.parent.name for a in archivos] == ["costo_marginal"]


def test_costo_marginal_usa_respaldo_si_ieod_no_publico(tmp_path):
    respaldo = (DIR_SAMPLES / "costo_marginal_tr_20261001.xlsx").read_bytes()
    cliente = cliente_falso([("ExportarMasivo", respaldo)])  # el visor responde vacio
    archivos = costo_marginal.descargar(date(2026, 10, 1), date(2026, 10, 1), cliente=cliente, raiz=tmp_path)
    assert [a.parent.name for a in archivos] == ["costo_marginal_tr"]


def test_ieod_no_publicado_no_rompe(tmp_path):
    cliente = cliente_falso([])
    assert ieod_anexo.descargar(date(2026, 10, 9), date(2026, 10, 9), cliente=cliente, raiz=tmp_path) == []


def test_una_fuente_caida_no_tumba_a_las_demas(monkeypatch):
    from src.extract import DESCARGADORES

    def falla(*a, **k):
        raise RuntimeError("servidor caido")

    monkeypatch.setitem(DESCARGADORES, "demanda", falla)
    monkeypatch.setitem(DESCARGADORES, "generacion", lambda *a, **k: ["ok"])
    resultado, errores = descargar_todo(date(2026, 10, 1), date(2026, 10, 1), ["demanda", "generacion"],
                                        cliente=cliente_falso([]))
    assert "demanda" in errores and resultado["generacion"] == ["ok"]


def test_dias_recientes_se_refrescan(tmp_path):
    ruta = tmp_path / "x.json"
    ruta.write_bytes(b"{}")
    viejo = time.time() - 10 * 3600
    os.utime(ruta, (viejo, viejo))
    cliente = ClienteCoes(sesion=SesionFalsa([]), ahora=datetime.now)
    assert not cliente.cache_vigente(ruta, date.today())
    assert cliente.cache_vigente(ruta, date(2020, 1, 1))


def test_pausa_entre_pedidos():
    esperas = []
    cliente = ClienteCoes(sesion=SesionFalsa([]), dormir=esperas.append)
    cliente.pedir("POST", "http://falso", {})
    cliente.pedir("POST", "http://falso", {})
    assert len(esperas) == 1 and esperas[0] > 1.5
