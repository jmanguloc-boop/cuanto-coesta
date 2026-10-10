"""Indicadores semanales: tablas procesadas -> ResumenSemanal."""

import json
from pathlib import Path

import pandas as pd

from src.analysis import indicadores as ind
from src.analysis.hechos import top_hechos
from src.analysis.modelo import Indicador, ResumenSemanal
from src.utils import config
from src.utils.datos import leer_tabla, semanas_disponibles
from src.utils.fechas import misma_semana_anio_anterior, rango_semana, semana_anterior, texto_semana
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)

# Totales de la semana: con dias faltantes no se pueden comparar contra semanas completas
ACUMULADOS = {"energia_semana", "horas_precio_bajo", "horas_precio_alto"}
INTERVALOS_DIA_COMPLETO = 46


def _datos_semana(semana, raiz=None):
    """Lee las tablas de una semana y arma las series base."""
    cmg = ind.serie_cmg_referencia(leer_tabla("costo_marginal", semana, raiz))
    dem = ind.serie_demanda(leer_tabla("demanda", semana, raiz))
    gen = ind.serie_generacion(leer_tabla("generacion", semana, raiz))
    emb = leer_tabla("embalses", semana, raiz)
    return cmg, dem, gen, emb


def metricas_semana(semana, raiz=None) -> dict:
    """Valores escalares de una semana (para comparar e historico)."""
    cmg, dem, gen, emb = _datos_semana(semana, raiz)
    umbrales = config.cargar_yaml("analisis")["umbrales_precio"]
    p, d, m = ind.precios(cmg, umbrales), ind.demanda(dem), ind.mix(gen)
    renov, renov_sin = ind.participacion_renovable(m) if m else (None, None)
    vol = ind.volumen_por_embalse(emb)
    return {
        "semana": semana,
        "cmg_promedio": p.get("cmg_promedio"),
        "cmg_maximo": p["cmg_maximo"][0] if p else None,
        "cmg_minimo": p["cmg_minimo"][0] if p else None,
        "horas_precio_bajo": p.get("horas_precio_bajo"),
        "horas_precio_alto": p.get("horas_precio_alto"),
        "demanda_maxima": d["demanda_maxima"][0] if d else None,
        "energia_semana": d.get("energia_semana"),
        "participacion_renovable": renov,
        "participacion_renovable_sin_hidro": renov_sin,
        "precio_capturado_solar": ind.precio_capturado(gen, cmg, "solar"),
        "precio_capturado_eolica": ind.precio_capturado(gen, cmg, "eolica"),
        "volumen_embalses": float(vol.sum()) if len(vol) else None,
        "_vol": vol,
        "_mix": m,
        "_perfil": ind.perfil_horario(cmg),
    }


def dias_completos(serie_dem) -> int:
    if serie_dem.empty:
        return 0
    conteo = serie_dem.groupby("fecha")["ejecutada"].count()
    return int((conteo >= INTERVALOS_DIA_COMPLETO).sum())


def _historico(semana, raiz=None, maximo=12):
    """Metricas de las semanas inmediatamente anteriores y consecutivas (para hablar de 'las ultimas N semanas')."""
    disponibles = set(semanas_disponibles("demanda", raiz))
    previas = []
    for i in range(1, maximo + 1):
        s = semana_anterior(semana, i)
        if s not in disponibles:
            break   # un hueco corta la racha: no se afirma un record sobre semanas salteadas
        previas.insert(0, s)
    filas = []
    for s in previas:
        m = metricas_semana(s, raiz)
        filas.append({k: v for k, v in m.items() if not k.startswith("_")})
    return pd.DataFrame(filas)


def calcular_resumen(semana, raiz=None) -> ResumenSemanal:
    desde, hasta = rango_semana(semana)
    sem_ant, sem_anio = semana_anterior(semana), misma_semana_anio_anterior(semana)
    cmg, dem, gen, emb = _datos_semana(semana, raiz)
    if dem.empty and cmg.empty and gen.empty:
        raise FileNotFoundError(f"No hay datos procesados para {semana}. Corre antes extract y transform.")
    umbrales = config.cargar_yaml("analisis")["umbrales_precio"]

    actual = metricas_semana(semana, raiz)
    ant = metricas_semana(sem_ant, raiz)
    anio = metricas_semana(sem_anio, raiz)
    p, d = ind.precios(cmg, umbrales), ind.demanda(dem)
    dias = dias_completos(dem)

    def nuevo(clave, unidad, momento=None, es_puntos=False):
        return Indicador(clave, actual.get(clave), unidad, ant.get(clave), anio.get(clave), momento, es_puntos,
                         comparable=not (clave in ACUMULADOS and dias < 7))

    indicadores = {
        "cmg_promedio": nuevo("cmg_promedio", "S/ por MWh"),
        "cmg_maximo": nuevo("cmg_maximo", "S/ por MWh", p["cmg_maximo"][1] if p else None),
        "cmg_minimo": nuevo("cmg_minimo", "S/ por MWh", p["cmg_minimo"][1] if p else None),
        "horas_precio_bajo": nuevo("horas_precio_bajo", "horas"),
        "horas_precio_alto": nuevo("horas_precio_alto", "horas"),
        "demanda_maxima": nuevo("demanda_maxima", "MW", d["demanda_maxima"][1] if d else None),
        "energia_semana": nuevo("energia_semana", "GWh"),
        "error_programa_diario": Indicador("error_programa_diario", d.get("error_programa_diario"), "%"),
        "participacion_renovable": nuevo("participacion_renovable", "%", es_puntos=True),
        "participacion_renovable_sin_hidro": nuevo("participacion_renovable_sin_hidro", "%", es_puntos=True),
        "precio_capturado_solar": nuevo("precio_capturado_solar", "S/ por MWh"),
        "precio_capturado_eolica": nuevo("precio_capturado_eolica", "S/ por MWh"),
    }
    # Embalses: variacion solo sobre embalses con dato en ambas semanas
    var_ant, ref_ant = ind.comparar_embalses(actual["_vol"], ant["_vol"])
    var_anio, ref_anio = ind.comparar_embalses(actual["_vol"], anio["_vol"])
    indicadores["volumen_embalses"] = Indicador(
        "volumen_embalses", actual["volumen_embalses"], "Hm3", ref_ant, ref_anio,
        var_anterior=var_ant, var_anio=var_anio)

    perfil = pd.DataFrame({"actual": actual["_perfil"], "anterior": ant["_perfil"]}).rename_axis("hora").reset_index()
    detalle_emb = pd.DataFrame({"actual": actual["_vol"], "anterior": ant["_vol"]}).rename_axis("entidad").reset_index()
    if not emb.empty:
        cuencas = emb.drop_duplicates("entidad").set_index("entidad")["cuenca"]
        detalle_emb["cuenca"] = detalle_emb["entidad"].map(cuencas)

    historico = _historico(semana, raiz)
    tablas_prelim = [leer_tabla(t, semana, raiz) for t in ("demanda", "generacion", "costo_marginal")]
    es_prelim = dias < 7 or any(not t.empty and t["es_preliminar"].any() for t in tablas_prelim)
    ruta_avisos = Path(raiz or config.DIR_PROCESSED) / "avisos" / f"avisos_{semana}.json"
    avisos = json.loads(ruta_avisos.read_text(encoding="utf-8")) if ruta_avisos.exists() else []

    return ResumenSemanal(
        semana=semana, texto_semana=texto_semana(semana), desde=desde, hasta=hasta,
        semana_anterior=sem_ant, semana_anio_anterior=sem_anio,
        es_preliminar=es_prelim, dias_con_datos=dias,
        barra_referencia=config.cargar_yaml("analisis")["barra_referencia"], umbrales_precio=umbrales,
        indicadores=indicadores, mix=actual["_mix"], mix_anterior=ant["_mix"],
        hechos=top_hechos(indicadores, actual["_mix"], historico, cmg),
        avisos=avisos, perfil_cmg=perfil, serie_cmg=cmg, serie_demanda=dem, serie_generacion=gen,
        serie_embalses=ind.serie_embalses(emb), embalses_detalle=detalle_emb, historico=historico,
    )
