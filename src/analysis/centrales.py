"""Vista de generadora: centrales, empresas e indisponibilidades (todo con datos publicos del IEOD).

El ingreso spot es una ESTIMACION: generacion de cada media hora por el costo marginal
de su barra (o de la barra de referencia si no se configuro). No incluye potencia,
contratos ni retiros: no es la valorizacion oficial de transferencias del COES.
"""

from datetime import timedelta

import pandas as pd

from src.utils import config
from src.utils.datos import leer_tabla


def participacion_empresas(centrales: pd.DataFrame, anterior: pd.DataFrame | None = None, n=10):
    """Energia (MWh) y cuota de cada empresa; con la cuota de la semana anterior si se da."""
    if centrales.empty:
        return pd.DataFrame(columns=["empresa", "energia_mwh", "cuota", "cuota_anterior"])
    energia = centrales.groupby("empresa")["valor"].sum().clip(lower=0) * 0.5
    tabla = pd.DataFrame({"energia_mwh": energia, "cuota": energia / energia.sum()})
    if anterior is not None and not anterior.empty:
        previa = anterior.groupby("empresa")["valor"].sum().clip(lower=0) * 0.5
        tabla["cuota_anterior"] = previa / previa.sum()
    else:
        tabla["cuota_anterior"] = None
    return tabla.sort_values("energia_mwh", ascending=False).head(n).rename_axis("empresa").reset_index()


def top_centrales(centrales: pd.DataFrame, n=12):
    """Las centrales que mas energia produjeron."""
    if centrales.empty:
        return pd.DataFrame(columns=["central", "empresa", "tecnologia", "energia_mwh", "mw_max"])
    g = centrales.groupby(["entidad", "empresa", "tecnologia"])
    tabla = pd.DataFrame({"energia_mwh": g["valor"].sum() * 0.5, "mw_max": g["valor"].max()}).reset_index()
    return tabla.rename(columns={"entidad": "central"}).sort_values("energia_mwh", ascending=False).head(n)


def lista_centrales(centrales: pd.DataFrame):
    """Nombres de centrales para el selector: primero las propias (config/interno.yaml)."""
    if centrales.empty:
        return []
    todas = sorted(centrales["entidad"].unique())
    propias = [c for c in config.interno().get("mis_centrales", []) if c in todas]
    return propias + [c for c in todas if c not in propias]


def barra_de(central):
    """Barra configurada para la central, o la de referencia (y si es aproximada)."""
    barras = config.interno().get("barras_de_centrales", {}) or {}
    if central in barras:
        return barras[central], False
    return config.cargar_yaml("analisis")["barra_referencia"], True


def detalle_central(centrales: pd.DataFrame, central: str, cmg: pd.DataFrame):
    """Generacion de una central y su ingreso spot estimado con el CMg dado (fecha_hora, total)."""
    g = centrales[centrales["entidad"] == central].groupby("fecha_hora", as_index=False)["valor"].sum()
    if g.empty:
        return None
    unido = g.merge(cmg[["fecha_hora", "total"]], on="fecha_hora", how="left")
    produce = unido["valor"].clip(lower=0)
    energia = float(produce.sum() * 0.5)
    con_precio = unido.dropna(subset=["total"])
    peso = con_precio["valor"].clip(lower=0)
    capturado = float((peso * con_precio["total"]).sum() / peso.sum()) if peso.sum() > 0 else None
    ingreso = float((peso * 0.5 * con_precio["total"]).sum()) if len(con_precio) else None
    info = centrales[centrales["entidad"] == central].iloc[0]
    return {
        "central": central, "empresa": info["empresa"], "tecnologia": info["tecnologia"], "area": info.get("area", ""),
        "serie": g, "energia_mwh": energia, "mw_max": float(produce.max()),
        "horas_generando": float((produce > 0.5).sum() * 0.5),
        "precio_capturado": capturado, "precio_promedio": float(cmg["total"].mean()) if len(cmg) else None,
        "ingreso_estimado": ingreso,
    }


# ---------- indisponibilidades ----------

def indisponible_por_dia(eventos: pd.DataFrame, desde, hasta):
    """MW de generacion fuera de servicio cada dia, separando programado y forzado.

    Un equipo cuenta en cada dia en que estuvo fuera al menos una parte del dia
    (se suma su MW maximo indisponible). Solo unidades de generacion con MW > 0.
    """
    dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
    gen = eventos[(eventos["clase"] == "G") & (eventos["mw"] > 0)] if not eventos.empty else eventos
    filas = []
    for dia in dias:
        activos = gen[(gen["inicio"].dt.date <= dia) & (gen["final"].dt.date >= dia)] if len(gen) else gen
        # El final 00:00 del dia siguiente no cuenta para ese dia
        if len(activos):
            activos = activos[~((activos["final"].dt.date == dia) & (activos["final"].dt.hour == 0)
                                & (activos["final"].dt.minute == 0) & (activos["inicio"].dt.date < dia))]
        filas.append({"fecha": dia,
                      "programado": float(activos.loc[activos["programado"], "mw"].sum()) if len(activos) else 0.0,
                      "forzado": float(activos.loc[~activos["programado"], "mw"].sum()) if len(activos) else 0.0})
    return pd.DataFrame(filas)


def precio_durante(cmg: pd.DataFrame, inicio, final):
    """Costo marginal promedio mientras duro un evento (descriptivo, no implica causa)."""
    if cmg.empty or pd.isna(inicio) or pd.isna(final):
        return None
    tramo = cmg[(cmg["fecha_hora"] > inicio) & (cmg["fecha_hora"] <= final + timedelta(minutes=29))]
    return float(tramo["total"].mean()) if len(tramo) else None


def eventos_semana(semana, raiz=None):
    """Tabla de eventos de la semana (vacia si no hay)."""
    return leer_tabla("eventos", semana, raiz)
