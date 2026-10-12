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


_CERTIFICADOS_SISTEMA = None


def usar_certificados_del_sistema():
    """En redes corporativas con inspeccion SSL, usa los certificados de Windows/macOS (truststore).

    Devuelve True si se activo. Se hace una sola vez por proceso.
    """
    global _CERTIFICADOS_SISTEMA
    if _CERTIFICADOS_SISTEMA is None:
        try:
            import truststore
            truststore.inject_into_ssl()
            _CERTIFICADOS_SISTEMA = True
        except Exception as error:   # sin truststore se usan los certificados de certifi
            log.debug("truststore no disponible: %s", error)
            _CERTIFICADOS_SISTEMA = False
    return _CERTIFICADOS_SISTEMA


def crear_sesion(cfg=None):
    """Sesion HTTP lista para redes corporativas.

    - Proxy del sistema: requests lo lee solo (en Windows, de la configuracion de Internet)
    - Proxy manual: cliente.proxy en config/fuentes.yaml, si TI lo pide
    - Certificados: los del sistema operativo si cliente.certificados_sistema es true
    """
    cfg = cfg or config.fuentes()["cliente"]
    if cfg.get("certificados_sistema", True):
        usar_certificados_del_sistema()
    sesion = requests.Session()
    proxy = cfg.get("proxy")
    if proxy:
        sesion.proxies.update({"http": proxy, "https": proxy})
    return sesion


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
        if sesion is None:
            sesion = crear_sesion(self.cfg)
        self.sesion = sesion
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
        """URL absoluta a partir de una ruta del portal."""
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
    """Fecha en el formato dd/mm/aaaa que pide el portal."""
    return fecha.strftime("%d/%m/%Y")
