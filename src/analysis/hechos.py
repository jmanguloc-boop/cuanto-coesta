"""Deteccion por reglas de los hechos mas relevantes de la semana."""

import pandas as pd

from src.analysis.modelo import Hecho
from src.utils import config

# Indicador -> nombre de la columna en el historico
CLAVES_HISTORICO = ["cmg_promedio", "demanda_maxima", "energia_semana", "participacion_renovable", "volumen_embalses"]
ES_PUNTOS = {"participacion_renovable"}


def hechos_por_variacion(indicadores):
    relevancia = config.cargar_yaml("analisis")["relevancia"]
    hechos = []
    for clave, umbral in relevancia.items():
        ind = indicadores.get(clave)
        if ind is None or ind.var_anterior is None:
            continue
        puntaje = abs(ind.var_anterior) / umbral
        if puntaje >= 1:
            hechos.append(Hecho("variacion", clave, puntaje, {
                "var": ind.var_anterior, "valor": ind.valor, "anterior": ind.anterior, "es_puntos": ind.es_puntos,
            }))
    return hechos


def hechos_por_record(indicadores, historico: pd.DataFrame):
    """Maximo o minimo del periodo disponible (solo si hay historia suficiente)."""
    minimo = config.cargar_yaml("analisis")["semanas_minimas_para_record"]
    if historico.empty or len(historico) < minimo:
        return []
    hechos = []
    for clave in CLAVES_HISTORICO:
        ind = indicadores.get(clave)
        if ind is None or ind.valor is None or clave not in historico:
            continue
        previos = historico[clave].dropna()
        if len(previos) < minimo:
            continue
        if ind.valor > previos.max():
            hechos.append(Hecho("record", clave, 2.5, {"sentido": "max", "semanas": len(previos) + 1, "valor": ind.valor}))
        elif ind.valor < previos.min():
            hechos.append(Hecho("record", clave, 2.5, {"sentido": "min", "semanas": len(previos) + 1, "valor": ind.valor}))
    return hechos


def hechos_por_anomalia(serie_cmg: pd.DataFrame):
    """Un dia con precio promedio muy distinto al del resto de la semana."""
    if serie_cmg.empty or serie_cmg["fecha"].nunique() < 4:
        return []
    diario = serie_cmg.groupby("fecha")["valor"].mean()
    hechos = []
    for fecha, valor in diario.items():
        resto = diario.drop(fecha).mean()
        if not resto:
            continue
        razon = valor / resto
        if razon >= 1.5 or razon <= 0.6:
            puntaje = razon if razon >= 1 else 1 / razon
            hechos.append(Hecho("anomalia", "cmg_promedio", puntaje,
                                {"fecha": fecha, "valor": valor, "resto": resto, "razon": razon}))
    return sorted(hechos, key=lambda h: -h.puntaje)[:1]


def hechos_de_respaldo(indicadores, mix):
    """Datos siempre disponibles para completar 3 hechos aunque la semana sea tranquila."""
    hechos = []
    ind = indicadores.get("demanda_maxima")
    if ind and ind.valor:
        hechos.append(Hecho("dato", "demanda_maxima", 0.5, {"valor": ind.valor, "momento": ind.momento}))
    if mix:
        lider = max(mix, key=mix.get)
        hechos.append(Hecho("dato", "mix_generacion", 0.4, {"tecnologia": lider, "participacion": mix[lider]}))
    ind = indicadores.get("cmg_minimo")
    if ind and ind.valor is not None:
        hechos.append(Hecho("dato", "cmg_minimo", 0.3, {"valor": ind.valor, "momento": ind.momento}))
    ind = indicadores.get("precio_capturado_solar")
    prom = indicadores.get("cmg_promedio")
    if ind and ind.valor and prom and prom.valor:
        hechos.append(Hecho("dato", "precio_capturado_solar", 0.35,
                            {"valor": ind.valor, "promedio": prom.valor, "razon": ind.valor / prom.valor}))
    return hechos


def top_hechos(indicadores, mix, historico, serie_cmg, n=3):
    candidatos = (hechos_por_record(indicadores, historico) + hechos_por_variacion(indicadores)
                  + hechos_por_anomalia(serie_cmg) + hechos_de_respaldo(indicadores, mix))
    elegidos, usados = [], set()
    for hecho in sorted(candidatos, key=lambda h: -h.puntaje):
        if hecho.clave in usados:   # un hecho por indicador
            continue
        elegidos.append(hecho)
        usados.add(hecho.clave)
        if len(elegidos) == n:
            break
    return elegidos
