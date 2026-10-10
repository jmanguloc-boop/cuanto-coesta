"""Cliente HTTP comun: pausas entre pedidos, reintentos y cache en disco."""

import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import requests

from src.utils import config
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)


class NoPublicado(Exception):
    """El COES todavia no publico el archivo pedido."""


class ClienteCoes:
    """Hace pedidos al portal COES sin saturarlo.

    - Espera pausa_segundos entre un pedido y el siguiente
    - Reintenta con espera exponencial si el servidor falla
    - cache_vigente() decide si un archivo en disco se puede reutilizar
    """

    def __init__(self, cfg_cliente=None, portal=None, sesion=None, dormir=time.sleep, ahora=datetime.now):
        fuentes = config.fuentes()
        self.cfg = cfg_cliente or fuentes["cliente"]
        self.portal = portal or fuentes["portal"]
        self.sesion = sesion or requests.Session()
        self.sesion.headers["User-Agent"] = self.cfg["user_agent"]
        self.dormir = dormir
        self.ahora = ahora
        self._ultimo_pedido = None

    def _esperar_turno(self):
        if self._ultimo_pedido is None:
            return
        faltante = self.cfg["pausa_segundos"] - (time.monotonic() - self._ultimo_pedido)
        if faltante > 0:
            self.dormir(faltante)

    def cache_vigente(self, ruta, fecha_fin: date):
        """True si el archivo existe y no hace falta volver a bajarlo."""
        ruta = Path(ruta)
        if not ruta.exists() or ruta.stat().st_size == 0:
            return False
        limite_provisional = self.ahora().date() - timedelta(days=self.cfg["dias_provisionales"])
        if fecha_fin < limite_provisional:
            return True
        edad = self.ahora() - datetime.fromtimestamp(ruta.stat().st_mtime)
        return edad < timedelta(hours=self.cfg["horas_vigencia_reciente"])

    def url(self, ruta):
        return ruta if ruta.startswith("http") else self.portal + ruta

    def pedir(self, metodo, url, params=None):
        """Devuelve el contenido en bytes. Lanza RuntimeError si todos los intentos fallan."""
        url = self.url(url)
        ultimo_error = None
        for intento in range(1, self.cfg["reintentos"] + 1):
            self._esperar_turno()
            try:
                if metodo == "POST":
                    resp = self.sesion.post(url, data=params, timeout=self.cfg["timeout_segundos"])
                else:
                    resp = self.sesion.get(url, params=params, timeout=self.cfg["timeout_segundos"])
                resp.raise_for_status()
                return resp.content
            except requests.RequestException as error:
                ultimo_error = error
                log.warning("Intento %s fallo para %s: %s", intento, url, error)
                if intento < self.cfg["reintentos"]:
                    self.dormir(self.cfg["pausa_segundos"] * 2 ** intento)
            finally:
                self._ultimo_pedido = time.monotonic()
        raise RuntimeError(f"No se pudo descargar {url}: {ultimo_error}")

    def pedir_archivo_visor(self, ruta_visor):
        """Baja un archivo del visor de documentos del COES (IEOD, etc.)."""
        contenido = self.pedir("GET", "/browser/download?url=" + quote(ruta_visor, safe="/"))
        if not contenido:
            raise NoPublicado(ruta_visor)
        return contenido


def formato_coes(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")
