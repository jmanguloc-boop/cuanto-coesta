"""Diagnostico de conexion para la PC de la empresa (proxy, certificados, firewall).

Uso:  python -m src.utils.diagnostico     (o DiagnosticoConexion.bat)

Usa solo la biblioteca estandar, asi que corre ANTES de instalar nada. Prueba cada
fuente del COES, el BCRP y PyPI (para saber si pip podra instalar las librerias) y
deja el resultado en diagnostico_conexion.txt, junto al proyecto.
"""

import os
import platform
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "diagnostico_conexion.txt"
AGENTE = "CuantoCOESta/0.4 (diagnostico de conexion)"
PORTAL = "https://www.coes.org.pe/Portal"


def _pruebas():
    hoy = date.today()
    ayer = hoy - timedelta(days=3)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre",
             "Noviembre", "Diciembre"]
    ruta_ieod = (f"Post Operación/Reportes/IEOD/{ayer.year}/{ayer.month:02d}_{meses[ayer.month - 1]}/"
                 f"{ayer.day:02d}/AnexoA_{ayer:%d%m}.xlsx")
    f = hoy.strftime("%d/%m/%Y")
    return [
        ("Portal COES", "GET", f"{PORTAL}/", None),
        ("Demanda en vivo", "POST", f"{PORTAL}/portalinformacion/Demanda", {"fechaInicial": f, "fechaFinal": f}),
        ("Precio en vivo (procesos)", "POST", f"{PORTAL}/mercadomayorista/costosmarginales/listaproceso", {"fecha": f}),
        ("Generacion", "POST", f"{PORTAL}/portalinformacion/Generacion",
         {"fechaInicial": f, "fechaFinal": f, "indicador": 0}),
        ("Exportacion de demanda", "GET", f"{PORTAL}/portalinformacion/ExportarDemanda?fechaInicial={f}&fechaFinal={f}", None),
        ("Archivos IEOD", "GET", f"{PORTAL}/browser/download?url=" + urllib.parse.quote(ruta_ieod, safe="/"), None),
        ("Tipo de cambio BCRP", "GET",
         f"https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04640PD/json/{ayer:%Y-%m-%d}/{hoy:%Y-%m-%d}", None),
        ("PyPI (para instalar librerias)", "GET", "https://pypi.org/simple/requests/", None),
    ]


def _explicar(error):
    """Traduce un error de red a lenguaje simple y a una accion."""
    texto = str(error)
    if isinstance(error, ssl.SSLError) or "CERTIFICATE" in texto.upper():
        return ("Error de certificado: la red de la empresa revisa el trafico seguro. Solucion: dejar "
                "'certificados_sistema: true' en config/fuentes.yaml (ya viene asi) o pedir a TI el certificado raiz.")
    if "407" in texto or "Proxy" in texto:
        return ("El proxy pide usuario y clave. Solucion: pedir a TI la direccion del proxy y ponerla en "
                "config/fuentes.yaml (cliente.proxy).")
    if isinstance(error, (socket.timeout, TimeoutError)) or "timed out" in texto:
        return "Tiempo agotado: un firewall o proxy bloquea el sitio. Solucion: pedir a TI que habilite el dominio."
    if "getaddrinfo" in texto or "Name or service" in texto or "11001" in texto:
        return "No se encuentra el sitio (DNS). Puede ser falta de internet o un bloqueo de TI."
    if "403" in texto:
        return "Acceso prohibido (403): el sitio o el proxy rechazan el pedido."
    return texto[:200]


def _probar(nombre, metodo, url, datos, contexto):
    datos_bytes = urllib.parse.urlencode(datos).encode() if datos else None
    pedido = urllib.request.Request(url, data=datos_bytes, method=metodo, headers={"User-Agent": AGENTE})
    inicio = time.monotonic()
    try:
        with urllib.request.urlopen(pedido, timeout=40, context=contexto) as resp:
            cuerpo = resp.read()
            ms = (time.monotonic() - inicio) * 1000
            return True, f"OK  ({resp.status}, {len(cuerpo) / 1024:.0f} KB, {ms:.0f} ms)"
    except urllib.error.HTTPError as error:
        return False, f"FALLA  HTTP {error.code}. {_explicar(error)}"
    except Exception as error:   # se reporta cualquier falla de red, no se detiene
        motivo = getattr(error, "reason", error)
        return False, f"FALLA  {_explicar(motivo)}"


def diagnosticar(escribir=True):
    """Corre todas las pruebas y devuelve el informe como texto."""
    lineas = [
        "DIAGNOSTICO DE CONEXION - Cuanto COESta",
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        f"Equipo: {platform.node()} | {platform.system()} {platform.release()} | Python {sys.version.split()[0]}",
        f"Carpeta del proyecto: {RAIZ}",
        f"Proyecto en OneDrive/SharePoint: {'SI (los datos se guardaran fuera)' if 'onedrive' in str(RAIZ).lower() else 'no'}",
        f"Proxy detectado (sistema o variables): {urllib.request.getproxies() or 'ninguno'}",
        "",
    ]
    contextos = [("Certificados de Windows", ssl.create_default_context())]
    try:
        import certifi
        contextos.append(("Certificados de Python (certifi)", ssl.create_default_context(cafile=certifi.where())))
    except ImportError:
        pass
    resultados = {}
    for nombre_ctx, contexto in contextos:
        lineas.append(f"== Con {nombre_ctx}")
        for nombre, metodo, url, datos in _pruebas():
            ok, detalle = _probar(nombre, metodo, url, datos, contexto)
            resultados.setdefault(nombre_ctx, []).append(ok)
            lineas.append(f"  {'[OK]   ' if ok else '[FALLA]'} {nombre:<32} {detalle}")
            time.sleep(1.0)   # sin saturar al COES
        lineas.append("")
    windows = resultados.get("Certificados de Windows", [])
    certifi_ok = resultados.get("Certificados de Python (certifi)", [])
    lineas.append("== Conclusion")
    if windows and all(windows):
        lineas.append("  Todo responde. La app puede descargar datos desde esta PC.")
        if certifi_ok and not all(certifi_ok):
            lineas.append("  Ojo: con los certificados de Python falla. La app usa los de Windows (truststore), asi que esta bien.")
    elif windows and any(windows):
        lineas.append("  Algunas fuentes responden y otras no. Enviar este archivo para revisarlo.")
    else:
        lineas.append("  Nada responde: probablemente un proxy o firewall. Enviar este archivo a TI o para revisarlo.")
    informe = "\n".join(lineas)
    if escribir:
        SALIDA.write_text(informe, encoding="utf-8")
    return informe


if __name__ == "__main__":
    print(diagnosticar())
    print(f"\nInforme guardado en: {SALIDA}")
    if os.environ.get("CUANTO_COESTA_PAUSA"):
        try:
            input("\nPresiona Enter para cerrar...")
        except EOFError:
            pass
