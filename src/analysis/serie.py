"""Serie continua del costo marginal: cualquier rango de fechas, no solo semanas.

Une todo lo descargado y, para cada media hora, usa la mejor version disponible:
1. confirmado: CMg del IEOD (post operacion)
2. preliminar: CMg en tiempo real del portal (respaldo semanal o tabla cmg_preliminar)
3. en vivo: base de Cuanto COESta Ahora (SQLite)
Las semanas pasan a ser solo un filtro.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from src.utils import config
from src.utils.datos import ruta_tabla, semanas_disponibles
from src.utils.fechas import rango_semana

ESTADOS = {"ieod_cmg": "confirmado", "portal_cmg_tiempo_real": "preliminar", "ahora": "en vivo"}
PRIORIDAD = {"confirmado": 0, "preliminar": 1, "en vivo": 2}
VARIABLES = {"cmg_total": "total", "cmg_energia": "energia", "cmg_congestion": "congestion"}


def _semanas_en_rango(tabla, desde, hasta, raiz=None):
    salida = []
    for s in semanas_disponibles(tabla, raiz):
        lunes, domingo = rango_semana(s)
        if lunes <= hasta and domingo >= desde:
            salida.append(s)
    return salida


def _leer_parquet(tabla, barra, desde, hasta, raiz=None):
    partes = []
    for s in _semanas_en_rango(tabla, desde, hasta, raiz):
        df = pd.read_parquet(ruta_tabla(tabla, s, raiz), filters=[("entidad", "==", barra)],
                             columns=["fecha_hora", "fecha", "variable", "valor", "fuente"])
        partes.append(df)
    if not partes:
        return pd.DataFrame()
    largo = pd.concat(partes)
    largo = largo[largo["variable"].isin(VARIABLES)]
    ancho = largo.pivot_table(index=["fecha_hora", "fecha", "fuente"], columns="variable", values="valor").reset_index()
    ancho = ancho.rename(columns=VARIABLES)
    ancho["estado"] = ancho["fuente"].map(ESTADOS).fillna("preliminar")
    return ancho.drop(columns="fuente")


def _leer_ahora(barra, desde, ruta_db=None):
    from src.ahora import db
    ruta = ruta_db or db.RUTA
    if not ruta.exists():
        return pd.DataFrame()
    with db.conectar(ruta) as con:
        df = db.cmg_vigente(con, barra, desde=f"{desde:%Y-%m-%d}")
    if df.empty:
        return df
    df = df.rename(columns={"cmg_total": "total", "cmg_energia": "energia", "cmg_congestion": "congestion"})
    df["fecha"] = (df["fecha_hora"] - pd.Timedelta(minutes=1)).dt.date
    df["estado"] = "en vivo"
    return df[["fecha_hora", "fecha", "total", "energia", "congestion", "estado"]]


def cmg_rango(desde: date, hasta: date, barra=None, raiz=None, ruta_db=None) -> pd.DataFrame:
    """CMg de una barra cada 30 min en [desde, hasta]: fecha_hora, fecha, total, energia, congestion, estado."""
    barra = barra or config.cargar_yaml("analisis")["barra_referencia"]
    partes = [_leer_parquet("costo_marginal", barra, desde, hasta, raiz),
              _leer_parquet("cmg_preliminar", barra, desde, hasta, raiz),
              _leer_ahora(barra, desde, ruta_db)]
    partes = [p for p in partes if not p.empty]
    if not partes:
        return pd.DataFrame(columns=["fecha_hora", "fecha", "total", "energia", "congestion", "estado"])
    serie = pd.concat(partes, ignore_index=True)
    serie = serie[(serie["fecha"] >= desde) & (serie["fecha"] <= hasta)].copy()
    serie["prioridad"] = serie["estado"].map(PRIORIDAD)
    serie = serie.sort_values(["fecha_hora", "prioridad"]).drop_duplicates("fecha_hora", keep="first")
    return serie.drop(columns="prioridad").reset_index(drop=True)


def barras_disponibles(raiz=None):
    """Barras con CMg en la ultima semana descargada (para elegir en la app)."""
    semanas = semanas_disponibles("costo_marginal", raiz)
    if not semanas:
        return []
    df = pd.read_parquet(ruta_tabla("costo_marginal", semanas[-1], raiz), columns=["entidad", "variable"])
    return sorted(df.loc[df["variable"] == "cmg_total", "entidad"].unique())


def primera_fecha(raiz=None):
    """Primer dia con datos de costo marginal."""
    semanas = semanas_disponibles("costo_marginal", raiz)
    return rango_semana(semanas[0])[0] if semanas else None


# ---------- moneda ----------

def en_dolares(serie: pd.DataFrame, tabla_tc: pd.DataFrame) -> pd.DataFrame:
    """Convierte total, energia y congestion a USD por MWh con el tipo de cambio de cada dia."""
    from src.extract.bcrp import tc_para
    df = serie.copy()
    if df.empty:
        return df
    tc = tc_para(df["fecha"].tolist(), tabla_tc).values
    for col in ("total", "energia", "congestion"):
        df[col] = df[col] / tc
    df["tc"] = tc
    return df


# ---------- resumenes ----------

def hora_inicio(fecha_hora: pd.Series) -> pd.Series:
    """Hora en que empieza el intervalo (el que termina 00:30 empieza a las 00:00)."""
    return (fecha_hora - pd.Timedelta(minutes=30)).dt.hour


def es_punta(fecha_hora: pd.Series) -> pd.Series:
    b = config.cargar_yaml("analisis")["bloques"]
    h = hora_inicio(fecha_hora)
    return (h >= b["punta_desde"]) & (h < b["punta_hasta"])


@dataclass
class ResumenRango:
    desde: date
    hasta: date
    barra: str
    moneda: str
    base: float | None = None
    punta: float | None = None
    fuera_punta: float | None = None
    maximo: float | None = None
    momento_max: object = None
    minimo: float | None = None
    momento_min: object = None
    congestion_media: float | None = None
    cobertura: float = 0.0          # medias horas con dato / esperadas
    dias: int = 0
    dias_preliminares: int = 0
    estados: dict = field(default_factory=dict)


def resumir(serie: pd.DataFrame, desde, hasta, barra, moneda="S/") -> ResumenRango:
    """Promedios base / punta / fuera de punta, extremos y calidad del rango."""
    r = ResumenRango(desde, hasta, barra, moneda)
    if serie.empty:
        return r
    punta = es_punta(serie["fecha_hora"])
    r.base = float(serie["total"].mean())
    r.punta = float(serie.loc[punta, "total"].mean()) if punta.any() else None
    r.fuera_punta = float(serie.loc[~punta, "total"].mean()) if (~punta).any() else None
    imax, imin = serie["total"].idxmax(), serie["total"].idxmin()
    r.maximo, r.momento_max = float(serie.loc[imax, "total"]), serie.loc[imax, "fecha_hora"]
    r.minimo, r.momento_min = float(serie.loc[imin, "total"]), serie.loc[imin, "fecha_hora"]
    r.congestion_media = float(serie["congestion"].mean()) if "congestion" in serie else None
    esperadas = ((hasta - desde).days + 1) * 48
    r.cobertura = len(serie) / esperadas if esperadas else 0
    r.dias = serie["fecha"].nunique()
    por_dia = serie.groupby("fecha")["estado"].apply(lambda e: (e != "confirmado").any())
    r.dias_preliminares = int(por_dia.sum())
    r.estados = serie["estado"].value_counts().to_dict()
    return r


def diario(serie: pd.DataFrame) -> pd.DataFrame:
    """Por dia: promedio, minimo, maximo, punta y si todo el dia esta confirmado."""
    if serie.empty:
        return pd.DataFrame(columns=["fecha", "promedio", "minimo", "maximo", "punta", "medias_horas", "confirmado"])
    df = serie.assign(es_punta=es_punta(serie["fecha_hora"]))
    g = df.groupby("fecha")
    salida = pd.DataFrame({
        "promedio": g["total"].mean(), "minimo": g["total"].min(), "maximo": g["total"].max(),
        "punta": df[df["es_punta"]].groupby("fecha")["total"].mean(),
        "medias_horas": g["total"].count(),
        "confirmado": g["estado"].apply(lambda e: (e == "confirmado").all()),
    }).reset_index()
    return salida


def mensual(serie: pd.DataFrame) -> pd.DataFrame:
    """Promedio por mes calendario (base y punta)."""
    if serie.empty:
        return pd.DataFrame(columns=["mes", "promedio", "punta", "dias"])
    df = serie.assign(mes=pd.to_datetime(serie["fecha"]).dt.to_period("M"), es_punta=es_punta(serie["fecha_hora"]))
    g = df.groupby("mes")
    return pd.DataFrame({
        "promedio": g["total"].mean(),
        "punta": df[df["es_punta"]].groupby("mes")["total"].mean(),
        "dias": g["fecha"].nunique(),
    }).reset_index()


def matriz_calor(serie: pd.DataFrame) -> pd.DataFrame:
    """Filas = dias, columnas = media hora del dia (0 a 47), valor = precio."""
    if serie.empty:
        return pd.DataFrame()
    inicio = serie["fecha_hora"] - pd.Timedelta(minutes=30)
    columna = inicio.dt.hour * 2 + inicio.dt.minute // 30
    return serie.assign(col=columna).pivot_table(index="fecha", columns="col", values="total").reindex(
        columns=range(48))


# ---------- atajos de rango ----------

def rango_atajo(atajo, hoy: date, primera: date | None):
    """'7d', '30d', 'mes', 'hidro', 'anio', 'todo' -> (desde, hasta)."""
    if atajo == "7d":
        return hoy - timedelta(days=6), hoy
    if atajo == "30d":
        return hoy - timedelta(days=29), hoy
    if atajo == "mes":
        return hoy.replace(day=1), hoy
    if atajo == "hidro":
        mes = config.cargar_yaml("analisis")["mes_inicio_ano_hidrologico"]
        anio = hoy.year if hoy.month >= mes else hoy.year - 1
        return date(anio, mes, 1), hoy
    if atajo == "anio":
        return date(hoy.year, 1, 1), hoy
    return (primera or hoy - timedelta(days=29)), hoy


def exportar_excel(serie: pd.DataFrame, ruta, barra, moneda="S/"):
    """Excel con las medias horas, el resumen diario y una nota de fuentes."""
    unidad = f"{moneda} por MWh"
    detalle = serie.rename(columns={"fecha_hora": "fecha_hora_fin_intervalo", "total": f"cmg_total ({unidad})",
                                    "energia": f"cmg_energia ({unidad})", "congestion": f"cmg_congestion ({unidad})"})
    dia = diario(serie)
    nota = pd.DataFrame({"Campo": ["Barra", "Unidad", "Estados", "Fuente", "Aviso"], "Detalle": [
        barra, unidad,
        "confirmado = IEOD del COES; preliminar = tiempo real del portal; en vivo = consulta cada 30 min",
        "Datos publicos de www.coes.org.pe" + ("; tipo de cambio BCRP (venta SBS)" if moneda != "S/" else ""),
        " ".join(config.proyecto()["aviso"].split()),
    ]})
    with pd.ExcelWriter(ruta, engine="openpyxl") as escritor:
        detalle.to_excel(escritor, sheet_name="medias_horas", index=False)
        dia.to_excel(escritor, sheet_name="diario", index=False)
        nota.to_excel(escritor, sheet_name="nota", index=False)
    return ruta
