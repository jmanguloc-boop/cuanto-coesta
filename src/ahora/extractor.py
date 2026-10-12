"""Extractor ligero de "Cuanto COESta Ahora": solo costo marginal y demanda en tiempo real.

Pide unicamente los procesos que faltan en la base y vuelve a mirar los ultimos
(revisar_ultimos) para detectar si el COES corrigio algun valor.
"""

import html
import json
import re
from datetime import date, datetime, timedelta

from src.ahora import db
from src.extract.cliente import ClienteCoes, formato_coes
from src.transform.comun import limpiar_texto
from src.utils import config, estado
from src.utils.fechas import ahora_peru
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)

FILA_TABLA = re.compile(r"<tr>\s*" + r"\s*".join([r"<td>(.*?)</td>"] * 5) + r"\s*</tr>", re.S)


def _cfg():
    return config.fuentes()["ahora"]


def _momento(fecha: date, hora_texto: str) -> datetime:
    """'10:00' -> datetime; '23:59' es el fin del dia (00:00 del dia siguiente)."""
    hora, minuto = (int(x) for x in hora_texto.split(":"))
    momento = datetime(fecha.year, fecha.month, fecha.day, hora, minuto)
    if minuto == 59:
        momento += timedelta(minutes=1)
    return momento


def procesos_del_dia(cliente, fecha: date):
    """[(correlativo, fin_de_intervalo)] publicados por el COES para ese dia."""
    cfg = _cfg()["costo_marginal"]
    crudo = cliente.pedir("POST", cfg["url_procesos"], {"fecha": formato_coes(fecha)})
    procesos = json.loads(crudo.decode("utf-8-sig"))
    return sorted((p["Cmgncorrelativo"], _momento(fecha, p["FechaProceso"])) for p in procesos if p.get("FechaProceso"))


def leer_tabla_proceso(contenido: str, correlativo: int, momento: datetime):
    """HTML de la tabla del COES -> lista de dicts por barra."""
    filas = []
    for _hora, barra, energia, congestion, total in FILA_TABLA.findall(contenido):
        try:
            filas.append({
                "fecha_hora": momento.strftime("%Y-%m-%d %H:%M"),
                "barra": limpiar_texto(html.unescape(barra)),
                "cmg_energia": float(energia), "cmg_congestion": float(congestion), "cmg_total": float(total),
                "correlativo": correlativo,
            })
        except ValueError:
            continue
    return filas


def actualizar_cmg(con, cliente, dias):
    """Baja los procesos faltantes (y los ultimos, para ver revisiones). Devuelve (nuevos, revisados)."""
    cfg = _cfg()["costo_marginal"]
    barra_ref = config.fuentes()["barra_referencia"]
    ya = db.horas_con_cmg(con, barra_ref)
    procesos = []
    for dia in dias:
        procesos += procesos_del_dia(cliente, dia)
    procesos.sort(key=lambda p: p[1])
    recientes = {p[0] for p in procesos[-cfg["revisar_ultimos"]:]}
    pendientes = [p for p in procesos if p[1].strftime("%Y-%m-%d %H:%M") not in ya or p[0] in recientes]
    nuevos = revisados = 0
    extraido_en = ahora_peru().strftime("%Y-%m-%d %H:%M:%S")
    for correlativo, momento in pendientes:
        contenido = cliente.pedir("POST", cfg["url_lista"], {"correlativo": correlativo, "defecto": cfg["defecto"]})
        filas = leer_tabla_proceso(contenido.decode("utf-8", "replace"), correlativo, momento)
        if not filas:
            log.warning("Proceso %s (%s) vino sin filas", correlativo, momento)
            continue
        n, r = db.guardar_cmg(con, filas, extraido_en)
        nuevos, revisados = nuevos + n, revisados + r
    log.info("Costo marginal: %s procesos consultados, %s valores nuevos, %s revisados", len(pendientes), nuevos, revisados)
    return nuevos, revisados


def actualizar_demanda(con, cliente, dias):
    """Demanda ejecutada (solo intervalos ya ocurridos) y programa diario."""
    cfg = _cfg()["demanda"]
    extraido_en = ahora_peru().strftime("%Y-%m-%d %H:%M:%S")
    nuevos = revisados = 0
    for dia in dias:
        crudo = cliente.pedir("POST", cfg["url"], {"fechaInicial": formato_coes(dia), "fechaFinal": formato_coes(dia)})
        datos = json.loads(crudo.decode("utf-8-sig"))
        filas = []
        for serie in datos["Chart"]["Series"]:
            nombre = serie["Name"].lower()
            variable = "ejecutada" if nombre.startswith("ejecutado") else ("programa_diario" if "diaria" in nombre else None)
            if variable is None:
                continue
            for punto in serie["Data"]:
                if punto["Valor"] in (None, 0):
                    continue   # el COES rellena con 0/None los intervalos que aun no ocurren
                momento = datetime.strptime(punto["Nombre"], "%Y/%m/%d %H:%M:%S")
                filas.append({"fecha_hora": momento.strftime("%Y-%m-%d %H:%M"), "variable": variable, "valor": punto["Valor"]})
        n, r = db.guardar_demanda(con, filas, extraido_en)
        nuevos, revisados = nuevos + n, revisados + r
    log.info("Demanda: %s valores nuevos, %s revisados", nuevos, revisados)
    return nuevos, revisados


def dias_a_revisar(con, hoy, desde_ayer=False, maximo=7):
    """Dias que hay que consultar: desde el ultimo dato guardado hasta hoy (rellena huecos).

    Si la PC estuvo apagada, al abrir se completan los dias perdidos, hasta 'maximo' dias
    atras (lo mas antiguo llega confirmado con el IEOD en la descarga semanal).
    """
    barra = config.fuentes()["barra_referencia"]
    fila = con.execute("select max(fecha_hora) from cmg where barra = ?", (barra,)).fetchone()
    if not fila or not fila[0]:
        inicio = hoy - timedelta(days=1)
    else:
        ultimo = datetime.strptime(fila[0], "%Y-%m-%d %H:%M") - timedelta(minutes=1)
        inicio = ultimo.date()
    if desde_ayer:
        inicio = min(inicio, hoy - timedelta(days=1))
    inicio = max(inicio, hoy - timedelta(days=maximo - 1))
    return [inicio + timedelta(days=i) for i in range((hoy - inicio).days + 1)]


def actualizar(desde_ayer=False, cliente=None, ruta_db=None):
    """Una pasada completa. Si una fuente falla, se registra y sigue la otra. Devuelve un resumen."""
    cliente = cliente or ClienteCoes()
    hoy = ahora_peru().date()
    resumen = {}
    with db.conectar(ruta_db) as con:
        dias = dias_a_revisar(con, hoy, desde_ayer)
        if len(dias) > 1:
            log.info("Rellenando %s dias: %s a %s", len(dias), dias[0], dias[-1])
        for fuente, funcion in (("costo_marginal", actualizar_cmg), ("demanda", actualizar_demanda)):
            inicio = ahora_peru().isoformat(timespec="seconds")
            try:
                nuevos, revisados = funcion(con, cliente, dias)
                db.registrar_extraccion(con, fuente, inicio, ahora_peru().isoformat(timespec="seconds"), True,
                                        nuevos, revisados)
                estado.registrar(f"ahora_{fuente}", True, f"{nuevos} nuevos, {revisados} revisados")
                resumen[fuente] = {"ok": True, "nuevos": nuevos, "revisados": revisados}
            except Exception as error:   # el COES caido no debe romper la app
                log.error("Ahora %s fallo: %s", fuente, error)
                db.registrar_extraccion(con, fuente, inicio, ahora_peru().isoformat(timespec="seconds"), False,
                                        detalle=str(error))
                estado.registrar(f"ahora_{fuente}", False, str(error))
                resumen[fuente] = {"ok": False, "error": str(error)}
    return resumen
