"""Lectores de archivos crudos -> tablas en formato largo (una funcion por tabla)."""

import json

import pandas as pd

from src.transform.comun import (
    archivos_del_rango, armar, clave_ascii, dias_con_ieod, fin_de_intervalo, limpiar_texto, recortar,
)
from src.utils import config
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)


def _marcar_preliminar(df, dias_evaluados):
    df["es_preliminar"] = ~df["fecha"].isin(dias_evaluados)
    return df


# ---------- demanda ----------

def leer_demanda_xlsx(ruta):
    """Excel de demanda del portal a formato largo."""
    crudo = pd.read_excel(ruta, header=None, skiprows=4)
    crudo = crudo.iloc[:, :4]
    crudo.columns = ["fecha_hora", "demanda_ejecutada", "demanda_prog_diaria", "demanda_prog_semanal"]
    crudo["fecha_hora"] = pd.to_datetime(crudo["fecha_hora"], format="%d/%m/%Y %H:%M", errors="coerce")
    crudo = crudo.dropna(subset=["fecha_hora"])
    largo = crudo.melt(id_vars="fecha_hora", var_name="variable", value_name="valor")
    largo["entidad"] = "SEIN"
    return largo


def tabla_demanda(desde, hasta, raiz=None):
    """Tabla de demanda de la semana."""
    partes = [leer_demanda_xlsx(r) for r in archivos_del_rango("demanda", desde, hasta, raiz)]
    if not partes:
        return pd.DataFrame()
    df = recortar(armar(pd.concat(partes), "MW", "portal_demanda"), desde, hasta)
    return _marcar_preliminar(df, dias_con_ieod(desde, hasta, raiz))


# ---------- generacion por tecnologia ----------

def _valores_nocturnos(serie):
    """Promedio de la serie entre 00:30 y 04:30 (el sol no produce)."""
    noche = [p["Valor"] or 0 for p in serie["Data"] if p["Nombre"][11:13] in ("00", "01", "02", "03", "04")]
    return sum(noche) / max(len(noche), 1)


def corregir_solar_bagazo(series, nombre_archivo=""):
    """El portal publica las series SOLAR y BAGAZO con las etiquetas cruzadas.

    Verificado contra el IEOD (hoja TIPO_RECURSO y despacho por central): la serie
    'BAGAZO' tiene forma solar (cero de noche) y 'SOLAR' es plana. Se detecta por
    la forma, asi que si el COES corrige el error esta funcion deja de actuar.
    """
    por_clave = {clave_ascii(s["Name"]): s for s in series}
    solar, bagazo = por_clave.get("SOLAR"), por_clave.get("BAGAZO")
    if not solar or not bagazo:
        return {}
    pico = lambda s: max((p["Valor"] or 0) for p in s["Data"])
    if _valores_nocturnos(solar) > 1 and _valores_nocturnos(bagazo) < 1 and pico(bagazo) > pico(solar):
        log.info("Generacion %s: etiquetas SOLAR y BAGAZO cruzadas en el portal, se corrigen", nombre_archivo)
        return {"SOLAR": "BAGAZO", "BAGAZO": "SOLAR"}
    return {}


def leer_generacion_json(ruta):
    """JSON de generacion a formato largo, con tecnologia."""
    datos = json.loads(ruta.read_bytes().decode("utf-8-sig"))
    mapeo = config.cargar_yaml("mapeos")["recursos"]
    series = datos["GraficoTipoCombustible"]["Series"]
    cruce = corregir_solar_bagazo(series, ruta.name)
    filas = []
    for serie in series:
        clave = clave_ascii(serie["Name"])
        clave = cruce.get(clave, clave)
        info = mapeo.get(clave)
        if info is None:
            log.warning("Recurso desconocido en %s: %r (se cuenta como 'otros')", ruta.name, serie["Name"])
            info = {"nombre": limpiar_texto(serie["Name"]).title(), "tecnologia": "otros"}
        for punto in serie["Data"]:
            filas.append({
                "fecha_hora": pd.to_datetime(punto["Nombre"], format="%Y/%m/%d %H:%M:%S"),
                "entidad": info["nombre"],
                "tecnologia": info["tecnologia"],
                "variable": "generacion",
                "valor": punto["Valor"],
            })
    return pd.DataFrame(filas)


def tabla_generacion(desde, hasta, raiz=None):
    """Tabla de generacion por tecnologia de la semana."""
    partes = [leer_generacion_json(r) for r in archivos_del_rango("generacion", desde, hasta, raiz)]
    if not partes:
        return pd.DataFrame()
    df = recortar(armar(pd.concat(partes), "MW", "portal_generacion"), desde, hasta)
    return _marcar_preliminar(df, dias_con_ieod(desde, hasta, raiz))


# ---------- costo marginal ----------

HOJAS_CMG = {"Cmg_Barra": "cmg_total", "Cmg_Ener": "cmg_energia", "Cmg_Cong": "cmg_congestion"}


def leer_cmg_ieod(ruta):
    """CMgCP del IEOD (total, energia, congestion) a formato largo."""
    partes = []
    for hoja, variable in HOJAS_CMG.items():
        crudo = pd.read_excel(ruta, sheet_name=hoja, header=None)
        barras = crudo.iloc[2, 2:].tolist()
        datos = crudo.iloc[3:, 1:]
        datos = datos[pd.to_datetime(datos.iloc[:, 0], errors="coerce").notna()]
        datos.columns = ["fecha_hora"] + barras
        largo = datos.melt(id_vars="fecha_hora", var_name="entidad", value_name="valor")
        largo["variable"] = variable
        partes.append(largo)
    df = pd.concat(partes)
    df["fecha_hora"] = df["fecha_hora"].map(fin_de_intervalo)
    df["entidad"] = df["entidad"].map(limpiar_texto)
    return df


def leer_cmg_tr(ruta):
    """Exportacion de CMg en tiempo real a formato largo."""
    crudo = pd.read_excel(ruta, header=None, skiprows=5).iloc[:, 1:7]
    crudo.columns = ["fecha_hora", "nodo", "entidad", "cmg_energia", "cmg_congestion", "cmg_total"]
    crudo["fecha_hora"] = pd.to_datetime(crudo["fecha_hora"], format="%d/%m/%Y %H:%M", errors="coerce")
    crudo = crudo.dropna(subset=["fecha_hora"])
    crudo["fecha_hora"] = crudo["fecha_hora"].map(fin_de_intervalo)
    crudo["entidad"] = crudo["entidad"].map(limpiar_texto)
    return crudo.drop(columns="nodo").melt(id_vars=["fecha_hora", "entidad"], var_name="variable", value_name="valor")


def tabla_costo_marginal(desde, hasta, raiz=None):
    """IEOD donde exista; tiempo real (preliminar) para los dias que faltan."""
    partes = [armar(leer_cmg_ieod(r), "S/ por MWh", "ieod_cmg", False)
              for r in archivos_del_rango("costo_marginal", desde, hasta, raiz)]
    df = recortar(pd.concat(partes), desde, hasta) if partes else pd.DataFrame(columns=["fecha"])
    dias_ieod = set(df["fecha"])
    tr = [armar(leer_cmg_tr(r), "S/ por MWh", "portal_cmg_tiempo_real", True)
          for r in archivos_del_rango("costo_marginal_tr", desde, hasta, raiz)]
    if tr:
        respaldo = recortar(pd.concat(tr), desde, hasta)
        respaldo = respaldo[~respaldo["fecha"].isin(dias_ieod)]
        if not respaldo.empty:
            log.info("Costo marginal: %s dias con respaldo en tiempo real", respaldo["fecha"].nunique())
            df = pd.concat([df, respaldo]) if len(df) else respaldo
    return df.reset_index(drop=True)


def tabla_cmg_preliminar(desde, hasta, raiz=None):
    """CMg en tiempo real tal como se publico (preliminar), para compararlo con el IEOD."""
    partes = [armar(leer_cmg_tr(r), "S/ por MWh", "portal_cmg_tiempo_real", True)
              for r in archivos_del_rango("costo_marginal_tr", desde, hasta, raiz)]
    if not partes:
        return pd.DataFrame()
    return recortar(pd.concat(partes), desde, hasta)


# ---------- embalses (IEOD, hoja PRINCIP_VOLUMENES) ----------

def _hoja(ruta, prefijo):
    hojas = pd.ExcelFile(ruta).sheet_names
    return next(h for h in hojas if clave_ascii(h).startswith(prefijo))


def leer_embalses(ruta, fecha):
    """Hoja de volumenes del IEOD a formato largo."""
    crudo = pd.read_excel(ruta, sheet_name=_hoja(ruta, "PRINCIPVOL"), header=None)
    meta = crudo.iloc[4:10, 1:].T
    meta.columns = ["empresa", "cuenca", "instalacion", "equipo", "tipo", "unidad"]
    datos = crudo.iloc[10:, :]
    datos = datos[datos.iloc[:, 0].astype(str).str.match(r"^\d{1,2}:\d{2}")]
    filas = []
    for col, info in meta.iterrows():
        if pd.isna(info["equipo"]):
            continue
        variable = "volumen_util" if "VOLUMEN" in clave_ascii(info["tipo"]) else "nivel"
        serie = pd.to_numeric(datos[col], errors="coerce")
        for hora, valor in zip(datos.iloc[:, 0], serie, strict=True):
            filas.append({
                "fecha_hora": pd.Timestamp(f"{fecha} {hora}"),
                "fecha": fecha,
                "entidad": limpiar_texto(info["equipo"]).replace("_", " "),
                "cuenca": limpiar_texto(info["cuenca"]),
                "empresa": limpiar_texto(info["empresa"]),
                "variable": variable,
                "valor": valor,
                "unidad_original": info["unidad"],
            })
    return pd.DataFrame(filas)


def tabla_embalses(desde, hasta, raiz=None):
    """Tabla de embalses de la semana."""
    from src.transform.comun import fechas_de_archivo
    partes = [leer_embalses(r, fechas_de_archivo(r)[0]) for r in archivos_del_rango("ieod_anexo", desde, hasta, raiz)]
    if not partes:
        return pd.DataFrame()
    df = pd.concat(partes)
    # Mismo equipo puede aparecer dos veces (p.ej. EMBALSE MALPASO como nivel y volumen):
    # se distingue por variable; si se repite igual, se agrega la cuenca al nombre
    repetidos = df.groupby(["fecha_hora", "entidad", "variable"])["cuenca"].transform("nunique") > 1
    df.loc[repetidos, "entidad"] = df.loc[repetidos, "entidad"] + " (" + df.loc[repetidos, "cuenca"] + ")"
    df = df.drop(columns="unidad_original")
    salida = [armar(df[df["variable"] == variable], unidad, "ieod_anexo")
              for variable, unidad in (("volumen_util", "Hm3"), ("nivel", "msnm"))]
    return recortar(pd.concat(salida), desde, hasta)


# ---------- generacion por central (IEOD, hoja DESPACHO_EJECUTADO) ----------

def leer_centrales(ruta):
    """Hoja DESPACHO_EJECUTADO del IEOD a formato largo."""
    crudo = pd.read_excel(ruta, sheet_name="DESPACHO_EJECUTADO", header=None)
    mapeo = config.cargar_yaml("mapeos")["tipos_central"]
    meta = crudo.iloc[5:10, 2:].T
    meta.columns = ["codigo", "area", "tipo", "empresa", "central"]
    datos = crudo.iloc[10:, :]
    datos = datos[datos.iloc[:, 1].astype(str).str.match(r"^\d{1,2}:\d{2}")]
    momentos = pd.to_datetime(datos.iloc[:, 0].astype(str) + " " + datos.iloc[:, 1].astype(str), format="%d/%m/%Y %H:%M")
    partes = []
    for col, info in meta.iterrows():
        if pd.isna(info["central"]) or pd.isna(info["tipo"]):
            continue
        partes.append(pd.DataFrame({
            "fecha_hora": momentos.values,
            "entidad": limpiar_texto(info["central"]),
            "empresa": limpiar_texto(info["empresa"]),
            "area": limpiar_texto(info["area"]),
            "tecnologia": mapeo.get(clave_ascii(info["tipo"]), "otros"),
            "variable": "generacion",
            "valor": pd.to_numeric(datos[col], errors="coerce").fillna(0).values,
        }))
    return pd.concat(partes)


def tabla_centrales(desde, hasta, raiz=None):
    """Tabla de generacion por central de la semana."""
    partes = [leer_centrales(r) for r in archivos_del_rango("ieod_anexo", desde, hasta, raiz)]
    if not partes:
        return pd.DataFrame()
    # Varias unidades pueden compartir nombre de central: se suman
    df = pd.concat(partes).groupby(
        ["fecha_hora", "entidad", "empresa", "area", "tecnologia", "variable"], as_index=False)["valor"].sum()
    return recortar(armar(df, "MW", "ieod_despacho"), desde, hasta)


# ---------- eventos, mantenimientos e indisponibilidades (IEOD Anexo A) ----------

HOJAS_EVENTOS = {"INDISP": "indisponibilidad", "MANTENIMIENTO EJECUTADOS": "mantenimiento", "EVENTOS": "evento"}
PRIORIDAD_ORIGEN = {"indisponibilidad": 0, "mantenimiento": 1, "evento": 2}


def _sin_tildes(texto):
    import unicodedata
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().upper().strip()


def _leer_hoja_eventos(ruta, hoja, origen):
    crudo = pd.read_excel(ruta, sheet_name=hoja, header=None)
    marca = "TIPO DE EVENTO" if origen == "evento" else "Empresa"
    filas_cab = crudo.index[crudo.iloc[:, 1].astype(str).str.strip() == marca]
    if not len(filas_cab):
        return pd.DataFrame()
    cab = [limpiar_texto(c) if isinstance(c, str) else c for c in crudo.iloc[filas_cab[0]].tolist()]
    datos = crudo.iloc[filas_cab[0] + 1:].copy()
    datos.columns = cab
    datos = datos.dropna(subset=[c for c in cab if isinstance(c, str) and c.upper().startswith("INICIO")])
    claves = {clave_ascii(c): c for c in cab if isinstance(c, str)}

    def col(*nombres):
        for n in nombres:
            if n in claves:
                return datos[claves[n]]
        return pd.Series([None] * len(datos), index=datos.index)

    salida = pd.DataFrame({
        "origen": origen,
        "empresa": col("EMPRESA").map(lambda v: limpiar_texto(v) if isinstance(v, str) else v),
        "ubicacion": col("UBICACIN").map(lambda v: limpiar_texto(v) if isinstance(v, str) else v),
        "equipo": col("EQUIPO").map(lambda v: limpiar_texto(str(v)) if v == v and v is not None else ""),
        "inicio": pd.to_datetime(col("INICIO"), dayfirst=True, errors="coerce"),
        "final": pd.to_datetime(col("FINAL"), dayfirst=True, errors="coerce"),
        "descripcion": col("DESCRIPCIN").map(lambda v: limpiar_texto(v) if isinstance(v, str) else ""),
        "mw": pd.to_numeric(col("MWINDISP"), errors="coerce"),
        "programado": col("PROG").astype(str).str.strip().eq("P") if origen != "evento" else False,
        "tipo": col("TIPO", "TIPODEEVENTO").astype(str).str.strip().str.rstrip("."),
        "clase": col("TIPOEQOSINERG").astype(str).str.strip() if origen != "evento" else
        col("TIPODEEQUIPO").map(lambda v: "G" if isinstance(v, str) and "GENERADOR" in v.upper() else "T"),
    })
    return salida.dropna(subset=["inicio"])


def leer_eventos(ruta):
    """Indisponibilidades, mantenimientos ejecutados y eventos de un dia del IEOD."""
    hojas = pd.ExcelFile(ruta).sheet_names
    partes = [_leer_hoja_eventos(ruta, h, o) for h, o in HOJAS_EVENTOS.items() if h in hojas]
    partes = [p for p in partes if not p.empty]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def tabla_eventos(desde, hasta, raiz=None):
    """Lista de la semana sin duplicados: un mantenimiento de varios dias queda en una sola fila."""
    partes = [leer_eventos(r) for r in archivos_del_rango("ieod_anexo", desde, hasta, raiz)]
    partes = [p for p in partes if not p.empty]
    if not partes:
        return pd.DataFrame()
    df = pd.concat(partes, ignore_index=True)
    df["prioridad"] = df["origen"].map(PRIORIDAD_ORIGEN)
    # La misma salida aparece en varias hojas, a veces con y sin tildes: se compara sin ellas
    for col in ("empresa", "ubicacion", "equipo"):
        df[col + "_clave"] = df[col].fillna("").map(_sin_tildes)
    df = df.sort_values("prioridad").drop_duplicates(["empresa_clave", "ubicacion_clave", "equipo_clave", "inicio"],
                                                     keep="first")
    df = df.drop(columns=["empresa_clave", "ubicacion_clave", "equipo_clave"])
    clave = ["origen", "empresa", "ubicacion", "equipo", "descripcion", "programado", "tipo", "clase"]
    df[clave] = df[clave].fillna("")
    agrupado = df.groupby(clave, as_index=False).agg(inicio=("inicio", "min"), final=("final", "max"),
                                                     mw=("mw", "max"), dias=("inicio", "count"))
    agrupado["fecha"] = (agrupado["inicio"]).dt.date
    agrupado = agrupado[(agrupado["final"].dt.date >= desde) & (agrupado["inicio"].dt.date <= hasta)]
    return agrupado.sort_values(["mw", "inicio"], ascending=[False, True]).reset_index(drop=True)
