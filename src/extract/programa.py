"""Programa Diario de Operacion del COES: costo marginal PROGRAMADO (lo que se espera).

El Anexo 1 (Despacho) trae, por media hora, el costo marginal que calcula el modelo
YUPANA del COES para Santa Rosa, Trujillo y Socabaya, en US$/MWh. El programa de
manana se publica en la tarde del dia anterior.
"""

from datetime import date, datetime, timedelta

import pandas as pd

from src.extract.cliente import ClienteCoes, NoPublicado
from src.utils import config
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)

RUTA_VISOR = ("Operación/Programa de Operación/Programa Diario/{anio}/{mes:02d}_{nombre_mes}/Día {dia:02d}/"
              "Anexo1_Despacho_{aaaammdd}.xlsx")
BARRAS = {"SANTA ROSA": "SANTA ROSA 220", "TRUJILLO": "TRUJILLO 220", "SOCABAYA": "SOCABAYA 220"}


def ruta_raw(fecha: date):
    """Archivo local del programa de un dia."""
    return config.DIR_RAW / "programa" / f"programa_{fecha:%Y%m%d}.xlsx"


def ruta_visor(fecha: date):
    """Ruta del archivo en el visor de documentos del COES."""
    meses = config.fuentes()["meses_ieod"]
    return RUTA_VISOR.format(anio=fecha.year, mes=fecha.month, nombre_mes=meses[fecha.month - 1].upper(),
                             dia=fecha.day, aaaammdd=f"{fecha:%Y%m%d}")


def descargar(fecha: date, cliente=None, forzar=False):
    """Baja el programa de un dia. Devuelve la ruta o None si aun no se publica."""
    ruta = ruta_raw(fecha)
    if ruta.exists() and not forzar:
        return ruta
    cliente = cliente or ClienteCoes()
    try:
        contenido = cliente.pedir_archivo_visor(ruta_visor(fecha))
    except NoPublicado:
        log.info("Programa del %s aun no publicado", fecha)
        return None
    if not contenido.startswith(b"PK"):
        log.warning("Programa del %s: el COES devolvio algo que no es Excel", fecha)
        return None
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)
    return ruta


def leer(ruta, fecha: date) -> pd.DataFrame:
    """Excel del programa -> fecha_hora (fin de intervalo), barra, cmg_usd."""
    crudo = pd.read_excel(ruta, header=None)
    fila_cab = crudo.index[crudo.iloc[:, 1].astype(str).str.strip().str.lower() == "día hora"]
    if not len(fila_cab):
        return pd.DataFrame(columns=["fecha_hora", "barra", "cmg_usd"])
    cab = crudo.iloc[fila_cab[0]]
    columnas = {j: str(v) for j, v in cab.items() if isinstance(v, str) and v.strip().upper().startswith("CMG ")}
    datos = crudo.iloc[fila_cab[0] + 1:]
    datos = datos[datos.iloc[:, 1].astype(str).str.match(r"^\d{1,2}:\d{2}$")]
    filas = []
    for _, fila in datos.iterrows():
        hora, minuto = (int(x) for x in str(fila.iloc[1]).split(":"))
        momento = datetime(fecha.year, fecha.month, fecha.day, hora, minuto)
        if minuto == 59:
            momento += timedelta(minutes=1)
        for j, nombre in columnas.items():
            clave = nombre.upper().replace("CMG ", "").split(" YUPANA")[0].strip()
            valor = pd.to_numeric(fila.iloc[j], errors="coerce")
            if valor == valor:
                filas.append({"fecha_hora": momento, "barra": BARRAS.get(clave, clave), "cmg_usd": float(valor)})
    return pd.DataFrame(filas)


def programa(fecha: date, barra=None, cliente=None, forzar=False) -> pd.DataFrame:
    """Costo marginal programado de un dia para una barra (vacio si no hay)."""
    barra = barra or config.fuentes()["barra_referencia"]
    ruta = descargar(fecha, cliente, forzar)
    if ruta is None:
        return pd.DataFrame(columns=["fecha_hora", "barra", "cmg_usd"])
    df = leer(ruta, fecha)
    return df[df["barra"] == barra].reset_index(drop=True)


def en_soles(df: pd.DataFrame, tabla_tc: pd.DataFrame) -> pd.DataFrame:
    """Agrega cmg_soles con el tipo de cambio del dia (o el ultimo conocido)."""
    from src.extract.bcrp import tc_para
    df = df.copy()
    if df.empty:
        df["cmg_soles"] = []
        return df
    tc = tc_para((df["fecha_hora"] - pd.Timedelta(minutes=1)).dt.date.tolist(), tabla_tc).values
    df["cmg_soles"] = df["cmg_usd"] * tc
    return df
