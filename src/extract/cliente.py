"""Cliente HTTP comun: pausas entre pedidos, reintentos y cache en disco."""

import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
import yaml

RAIZ = Path(__file__).resolve().parents[2]
RUTA_FUENTES = RAIZ / "config" / "fuentes.yaml"
RUTA_RAW = RAIZ / "data" / "raw"


def cargar_fuentes(ruta=RUTA_FUENTES):
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


class ClienteCoes:
    """Hace pedidos al portal COES sin saturarlo.

    - Espera pausa_segundos entre un pedido y el siguiente
    - Reintenta con espera creciente si el servidor falla
    - Guarda cada respuesta en disco y no la vuelve a pedir, salvo que
      sea de dias recientes (el COES aun puede corregirlos)
    """

    def __init__(self, config_cliente, sesion=None, dormir=time.sleep, ahora=datetime.now):
        self.cfg = config_cliente
        self.sesion = sesion or requests.Session()
        self.sesion.headers["User-Agent"] = self.cfg["user_agent"]
        self.dormir = dormir
        self.ahora = ahora
        self._ultimo_pedido = None

    def _esperar_turno(self):
        if self._ultimo_pedido is None:
            return
        transcurrido = time.monotonic() - self._ultimo_pedido
        faltante = self.cfg["pausa_segundos"] - transcurrido
        if faltante > 0:
            self.dormir(faltante)

    def cache_vigente(self, ruta, fecha_fin):
        """True si el archivo existe y no hace falta volver a bajarlo."""
        ruta = Path(ruta)
        if not ruta.exists() or ruta.stat().st_size == 0:
            return False
        hoy = self.ahora().date()
        limite_provisional = hoy - timedelta(days=self.cfg["dias_provisionales"])
        if fecha_fin < limite_provisional:
            return True
        edad = self.ahora() - datetime.fromtimestamp(ruta.stat().st_mtime)
        return edad < timedelta(hours=self.cfg["horas_vigencia_reciente"])

    def pedir(self, metodo, url, params):
        """Devuelve el contenido en bytes. Lanza error si todos los intentos fallan."""
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
                if intento < self.cfg["reintentos"]:
                    self.dormir(self.cfg["pausa_segundos"] * 2 ** intento)
            finally:
                self._ultimo_pedido = time.monotonic()
        raise RuntimeError(f"No se pudo descargar {url} con {params}: {ultimo_error}")


def formato_coes(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")
