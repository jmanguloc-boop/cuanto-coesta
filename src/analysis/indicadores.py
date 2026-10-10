"""Calculo de indicadores de una semana a partir de las tablas procesadas."""

import pandas as pd

from src.utils import config


def hora_del_dia(fecha_hora: pd.Series) -> pd.Series:
    """El intervalo que termina 00:30 y el que termina 01:00 son la hora 0."""
    return (fecha_hora - pd.Timedelta(minutes=1)).dt.hour


# ---------- precios ----------

def serie_cmg_referencia(cmg: pd.DataFrame) -> pd.DataFrame:
    """Serie del costo marginal total en la barra de referencia."""
    if cmg.empty:
        return pd.DataFrame(columns=["fecha_hora", "valor"])
    barra = config.cargar_yaml("analisis")["barra_referencia"]
    sel = cmg[(cmg["entidad"] == barra) & (cmg["variable"] == "cmg_total")]
    return sel[["fecha_hora", "fecha", "valor"]].sort_values("fecha_hora").reset_index(drop=True)


def precios(serie: pd.DataFrame, umbrales: dict) -> dict:
    """Promedio, maximo, minimo y horas con precio alto o bajo."""
    if serie.empty:
        return {}
    imax, imin = serie["valor"].idxmax(), serie["valor"].idxmin()
    return {
        "cmg_promedio": serie["valor"].mean(),
        "cmg_maximo": (serie.loc[imax, "valor"], serie.loc[imax, "fecha_hora"]),
        "cmg_minimo": (serie.loc[imin, "valor"], serie.loc[imin, "fecha_hora"]),
        # cada intervalo dura media hora
        "horas_precio_bajo": (serie["valor"] < umbrales["bajo"]).sum() * 0.5,
        "horas_precio_alto": (serie["valor"] > umbrales["alto"]).sum() * 0.5,
    }


def perfil_horario(serie: pd.DataFrame) -> pd.Series:
    """Precio promedio por hora del dia (0 a 23)."""
    if serie.empty:
        return pd.Series(dtype=float)
    return serie.groupby(hora_del_dia(serie["fecha_hora"]))["valor"].mean()


# ---------- demanda ----------

def serie_demanda(dem: pd.DataFrame) -> pd.DataFrame:
    """Demanda en formato ancho: ejecutada, programa diario y semanal."""
    if dem.empty:
        return pd.DataFrame(columns=["fecha_hora", "fecha", "ejecutada", "prog_diaria"])
    ancho = dem.pivot_table(index=["fecha_hora", "fecha"], columns="variable", values="valor").reset_index()
    return ancho.rename(columns={"demanda_ejecutada": "ejecutada", "demanda_prog_diaria": "prog_diaria",
                                 "demanda_prog_semanal": "prog_semanal"})


def demanda(serie: pd.DataFrame) -> dict:
    """Demanda maxima, energia de la semana y error del programa diario."""
    if serie.empty:
        return {}
    imax = serie["ejecutada"].idxmax()
    error = (serie["ejecutada"] - serie["prog_diaria"]).abs().mean() / serie["ejecutada"].mean()
    return {
        "demanda_maxima": (serie.loc[imax, "ejecutada"], serie.loc[imax, "fecha_hora"]),
        "energia_semana": serie["ejecutada"].sum() * 0.5 / 1000,   # GWh
        "error_programa_diario": error,
    }


# ---------- generacion ----------

def serie_generacion(gen: pd.DataFrame) -> pd.DataFrame:
    """Generacion sumada por tecnologia e intervalo."""
    if gen.empty:
        return pd.DataFrame(columns=["fecha_hora", "tecnologia", "valor"])
    return gen.groupby(["fecha_hora", "fecha", "tecnologia"], as_index=False)["valor"].sum()


def mix(serie: pd.DataFrame) -> dict:
    """Participacion de cada tecnologia en la energia de la semana."""
    if serie.empty:
        return {}
    energia = serie.groupby("tecnologia")["valor"].sum().clip(lower=0)
    total = energia.sum()
    return (energia / total).sort_values(ascending=False).to_dict() if total else {}


def participacion_renovable(participaciones: dict) -> tuple:
    """Participacion renovable con y sin hidro."""
    mapeos = config.cargar_yaml("mapeos")
    con = sum(v for k, v in participaciones.items() if k in mapeos["renovables_con_hidro"])
    sin = sum(v for k, v in participaciones.items() if k in mapeos["renovables_sin_hidro"])
    return con, sin


def precio_capturado(serie_gen: pd.DataFrame, serie_cmg: pd.DataFrame, tecnologia: str):
    """Promedio del CMg ponderado por lo que produjo la tecnologia en cada intervalo."""
    if serie_gen.empty or serie_cmg.empty:
        return None
    g = serie_gen[serie_gen["tecnologia"] == tecnologia][["fecha_hora", "valor"]]
    unido = g.merge(serie_cmg[["fecha_hora", "valor"]], on="fecha_hora", suffixes=("_gen", "_cmg"))
    peso = unido["valor_gen"].clip(lower=0)
    if peso.sum() <= 0:
        return None
    return float((peso * unido["valor_cmg"]).sum() / peso.sum())


# ---------- hidrologia ----------

def volumen_por_embalse(emb: pd.DataFrame) -> pd.Series:
    """Ultima lectura valida de la semana de cada embalse (Hm3)."""
    if emb.empty:
        return pd.Series(dtype=float)
    vol = emb[emb["variable"] == "volumen_util"].sort_values("fecha_hora")
    return vol.groupby("entidad")["valor"].last()


def serie_embalses(emb: pd.DataFrame) -> pd.DataFrame:
    """Volumen util total al cierre de cada dia.

    Solo entran embalses con dato todos los dias: si no, un embalse sin lectura
    pareceria agua que desaparecio.
    """
    if emb.empty:
        return pd.DataFrame(columns=["fecha", "valor"])
    vol = emb[emb["variable"] == "volumen_util"].dropna(subset=["valor"]).sort_values("fecha_hora")
    cierre = vol.groupby(["fecha", "entidad"])["valor"].last().reset_index()
    dias = cierre["fecha"].nunique()
    completos = cierre.groupby("entidad")["fecha"].nunique()
    cierre = cierre[cierre["entidad"].isin(completos[completos == dias].index)]
    return cierre.groupby("fecha", as_index=False)["valor"].sum()


def comparar_embalses(actual: pd.Series, referencia: pd.Series):
    """Variacion usando solo embalses con dato en ambas semanas (no se compara manzanas con peras)."""
    comunes = actual.index.intersection(referencia.index)
    if len(comunes) == 0:
        return None, None
    a, r = actual[comunes].sum(), referencia[comunes].sum()
    return (a / r - 1 if r else None), r


# ---------- mapa: costo marginal por barra ----------

def coordenadas_barras():
    """Latitud y longitud de las barras (assets/mapas/barras_coordenadas.csv, tomado del mapa del COES)."""
    from src.utils.estilo import DIR_MAPAS
    ruta = DIR_MAPAS / "barras_coordenadas.csv"
    if not ruta.exists():
        return pd.DataFrame(columns=["barra", "latitud", "longitud"])
    return pd.read_csv(ruta)


def cmg_por_barra(cmg: pd.DataFrame) -> pd.DataFrame:
    """Promedio semanal del CMg total por barra, con coordenadas cuando se conocen."""
    if cmg.empty:
        return pd.DataFrame(columns=["barra", "cmg_promedio", "latitud", "longitud"])
    total = cmg[cmg["variable"] == "cmg_total"]
    prom = total.groupby("entidad", as_index=False)["valor"].mean().rename(
        columns={"entidad": "barra", "valor": "cmg_promedio"})
    return prom.merge(coordenadas_barras(), on="barra", how="left").sort_values("cmg_promedio")


# ---------- preliminar vs revisado ----------

def revision_preliminar(preliminar: pd.DataFrame, revisado: pd.DataFrame, barra: str) -> dict:
    """Cuanto cambio el CMg entre lo publicado en tiempo real y la version post operacion del IEOD."""
    if preliminar.empty or revisado.empty:
        return {}
    p = preliminar[(preliminar["entidad"] == barra) & (preliminar["variable"] == "cmg_total")][["fecha_hora", "valor"]]
    r = revisado[(revisado["entidad"] == barra) & (revisado["variable"] == "cmg_total")
                 & (revisado["fuente"] == "ieod_cmg")][["fecha_hora", "valor"]]
    unido = p.merge(r, on="fecha_hora", suffixes=("_preliminar", "_revisado"))
    if unido.empty:
        return {}
    dif = unido["valor_revisado"] - unido["valor_preliminar"]
    # Diferencia media sobre precio medio: evita que S/ 50 sobre un precio de S/ 90 pese como 55 %
    rel = dif.abs().mean() / max(unido["valor_revisado"].abs().mean(), 1)
    imax = dif.abs().idxmax()
    return {
        "intervalos": len(unido),
        "diferencia_media_abs": float(dif.abs().mean()),
        "diferencia_media_pct": float(rel),
        "max_abs": float(dif.abs().max()),
        "momento_max": unido.loc[imax, "fecha_hora"],
        "cambiados": int((dif.abs() > 0.5).sum()),
    }
