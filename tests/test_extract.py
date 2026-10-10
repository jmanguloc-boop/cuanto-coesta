"""Tests sin red: el servidor COES se simula."""

import os
import time
from datetime import date, datetime

import pytest

from src.extract.cliente import ClienteCoes, formato_coes
from src.extract.coes import descargar_fuente, partir_rango, validar_contenido
from src.extract.run import ultima_semana_completa

CFG_CLIENTE = {
    "user_agent": "test",
    "pausa_segundos": 2.0,
    "timeout_segundos": 5,
    "reintentos": 2,
    "dias_provisionales": 3,
    "horas_vigencia_reciente": 6,
}

CONFIG = {
    "cliente": CFG_CLIENTE,
    "fuentes": {
        "generacion": {
            "url": "http://falso/gen",
            "metodo": "POST",
            "formato": "json",
            "params": {"fechaInicial": "{desde}", "fechaFinal": "{hasta}", "indicador": 0},
            "max_dias_por_pedido": 1,
        }
    },
}


class RespuestaFalsa:
    def __init__(self, contenido):
        self.content = contenido

    def raise_for_status(self):
        pass


class SesionFalsa:
    def __init__(self, contenido=b'{"ok": 1}'):
        self.headers = {}
        self.pedidos = []
        self.contenido = contenido

    def post(self, url, data, timeout):
        self.pedidos.append(data)
        return RespuestaFalsa(self.contenido)

    get = None


def test_partir_rango_en_tramos():
    tramos = partir_rango(date(2026, 1, 1), date(2026, 2, 15), 30)
    assert tramos == [(date(2026, 1, 1), date(2026, 1, 30)), (date(2026, 1, 31), date(2026, 2, 15))]


def test_partir_rango_dia_por_dia():
    assert len(partir_rango(date(2026, 10, 1), date(2026, 10, 7), 1)) == 7


def test_partir_rango_invertido():
    with pytest.raises(ValueError):
        partir_rango(date(2026, 10, 2), date(2026, 10, 1), 1)


def test_formato_coes():
    assert formato_coes(date(2026, 10, 1)) == "01/10/2026"


def test_ultima_semana_completa():
    # jueves 9 oct 2026 -> semana del lunes 28 sep al domingo 4 oct
    assert ultima_semana_completa(date(2026, 10, 9)) == (date(2026, 9, 28), date(2026, 10, 4))


def test_validar_rechaza_html_como_excel():
    with pytest.raises(ValueError):
        validar_contenido(b"<html>Server Error</html>", "xlsx")
    validar_contenido(b"PK\x03\x04resto", "xlsx")


def test_descarga_dia_por_dia_y_usa_cache(tmp_path):
    sesion = SesionFalsa()
    ahora = lambda: datetime(2026, 10, 9, 12, 0)
    cliente = ClienteCoes(CFG_CLIENTE, sesion=sesion, dormir=lambda s: None, ahora=ahora)
    desde, hasta = date(2026, 9, 1), date(2026, 9, 3)

    archivos = descargar_fuente("generacion", desde, hasta, cliente=cliente, config=CONFIG, raiz=tmp_path)
    assert len(archivos) == 3
    assert sesion.pedidos[0] == {"fechaInicial": "01/09/2026", "fechaFinal": "01/09/2026", "indicador": "0"}

    # Segunda corrida: dias viejos ya en cache, no se pide nada
    descargar_fuente("generacion", desde, hasta, cliente=cliente, config=CONFIG, raiz=tmp_path)
    assert len(sesion.pedidos) == 3


def test_dias_recientes_se_refrescan(tmp_path):
    ruta = tmp_path / "x.json"
    ruta.write_bytes(b"{}")
    viejo = time.time() - 10 * 3600
    os.utime(ruta, (viejo, viejo))
    cliente = ClienteCoes(CFG_CLIENTE, sesion=SesionFalsa(), ahora=datetime.now)
    hoy = date.today()
    assert not cliente.cache_vigente(ruta, hoy)            # reciente y con 10 h: se rebaja
    assert cliente.cache_vigente(ruta, date(2020, 1, 1))   # viejo: cache para siempre


def test_pausa_entre_pedidos():
    esperas = []
    cliente = ClienteCoes(CFG_CLIENTE, sesion=SesionFalsa(), dormir=esperas.append)
    cliente.pedir("POST", "http://falso", {})
    cliente.pedir("POST", "http://falso", {})
    assert len(esperas) == 1 and esperas[0] > 1.5
