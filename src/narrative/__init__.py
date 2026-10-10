"""Narrativa automatica por reglas: ResumenSemanal -> titulares, parrafos y titulos de graficos.

Sin APIs de IA: plantillas elegidas de forma reproducible (misma semana = mismo texto).
"""

import hashlib
from dataclasses import dataclass

from src.narrative import plantillas as P
from src.utils import config
from src.utils.fechas import DIAS, MESES, dia_y_hora
from src.utils.formato import numero, porcentaje

# Para afirmar una relacion entre precio e hidro hace falta un cambio claro en ambos
UMBRAL_PRECIO = 0.10      # 10 %
UMBRAL_HIDRO_PP = 0.02    # 2 puntos porcentuales


@dataclass
class Narrativa:
    titulares: list[str]
    parrafos: dict[str, str]          # precios, demanda, generacion, hidrologia
    titulos_graficos: dict[str, str]


# ---------- formato ----------

def elegir(opciones, *semilla):
    """Variante estable para una misma semana y caso."""
    h = int(hashlib.md5("|".join(map(str, semilla)).encode()).hexdigest(), 16)
    return opciones[h % len(opciones)]


def soles(v):
    return f"S/ {numero(v, 1)} por MWh"


def pct(v):
    return f"{abs(v) * 100:.1f}%"


def pp(v):
    return f"{abs(v) * 100:.1f} puntos"


def dia_texto(fecha):
    return f"{DIAS[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]}"


def hora_texto(hora):
    sufijo = "a. m." if hora < 12 else "p. m."
    return f"{hora % 12 or 12} {sufijo}"


def nombre_tec(clave):
    return config.nombre_tecnologia(clave)


def nombre_tec_min(clave):
    """Nombre en minuscula para usar a mitad de oracion ('la energia hidroelectrica')."""
    especiales = {"hidro": "las hidroeléctricas", "gas": "el gas natural", "solar": "el sol",
                  "eolica": "el viento", "diesel": "el diésel", "carbon": "el carbón", "biomasa": "la biomasa"}
    return especiales.get(clave, nombre_tec(clave).lower())


def capitalizar(texto):
    return texto[:1].upper() + texto[1:]


def sube_baja(v, sube="subió", baja="bajó"):
    return sube if v > 0 else baja


def horas(v):
    return numero(v) if float(v).is_integer() else numero(v, 1)


def enumerar(items):
    """['a', 'b', 'c'] -> 'a, b y c'."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]


def pulir(texto):
    """Contracciones y puntuacion: 'de el' -> 'del', 'a. m..' -> 'a. m.'."""
    for malo, bueno in ((" de el ", " del "), (" a el ", " al "), ("m..", "m."), ("..", "."), (" ,", ",")):
        texto = texto.replace(malo, bueno)
    return texto


# ---------- titulares ----------

def _titular(hecho, r):
    d, sem = hecho.datos, r.semana
    glosario = config.glosario()["indicadores"]
    if hecho.tipo == "variacion":
        sentido = "sube" if d["var"] > 0 else "baja"
        ind = r.ind(hecho.clave)
        valor = _valor_ind(ind)
        var = pp(d["var"]) if d["es_puntos"] else pct(d["var"])
        return elegir(P.TITULARES[("variacion", hecho.clave, sentido)], sem, hecho.clave).format(var=var, valor=valor)
    if hecho.tipo == "record":
        nombre = glosario[hecho.clave]["nombre"]
        return elegir(P.TITULARES[("record", d["sentido"])], sem, hecho.clave).format(nombre=nombre, semanas=d["semanas"])
    if hecho.tipo == "anomalia":
        sentido = "sube" if d["razon"] > 1 else "baja"
        return elegir(P.TITULARES[("anomalia", sentido)], sem).format(
            dia=dia_texto(d["fecha"]), veces=f"{d['razon']:.1f} veces".replace(".0 veces", " veces"), valor=soles(d["valor"]))
    if hecho.tipo == "dato":
        plantilla = elegir(P.TITULARES[("dato", hecho.clave)], sem, hecho.clave)
        if hecho.clave == "mix_generacion":
            return capitalizar(plantilla.format(tecnologia=nombre_tec(d["tecnologia"]),
                                                tecnologia_min=nombre_tec_min(d["tecnologia"]),
                                                participacion=porcentaje(d["participacion"])))
        if hecho.clave == "precio_capturado_solar":
            debajo = d["razon"] < 1
            comparacion = f"{pct(1 - d['razon'])} {'debajo de' if debajo else 'encima de'}"
            return plantilla.format(valor=soles(d["valor"]), comparacion=comparacion,
                                    calidad="baratas" if debajo else "caras")
        valor = soles(d["valor"]) if hecho.clave == "cmg_minimo" else f"{numero(d['valor'])} MW"
        return plantilla.format(valor=valor, momento=dia_y_hora(d["momento"]))
    return ""


def _valor_ind(ind):
    if ind is None or ind.valor is None:
        return "s/d"
    if ind.unidad == "%":
        return porcentaje(ind.valor)
    if ind.unidad == "S/ por MWh":
        return soles(ind.valor)
    return f"{numero(ind.valor)} {ind.unidad}"


def titulares(r):
    return [pulir(_titular(h, r)) for h in r.hechos]


# ---------- parrafos ----------

def _comparaciones(ind, nombre_anio, puntos=False):
    """'12.3% más que la semana anterior y 4.0% menos que en la misma semana de 2025'."""
    partes = []
    fmt = pp if puntos else pct
    if ind.var_anterior is not None:
        partes.append(f"{fmt(ind.var_anterior)} {sube_baja(ind.var_anterior, 'más', 'menos')} que la semana anterior")
    if ind.var_anio is not None:
        partes.append(f"{fmt(ind.var_anio)} {sube_baja(ind.var_anio, 'más', 'menos')} que en la misma semana de {nombre_anio}")
    return " y ".join(partes)


def _cambio_hidro(r):
    if "hidro" not in r.mix or "hidro" not in r.mix_anterior:
        return None
    return r.mix["hidro"] - r.mix_anterior["hidro"]


def parrafo_precios(r):
    prom, maxi, mini = r.ind("cmg_promedio"), r.ind("cmg_maximo"), r.ind("cmg_minimo")
    if prom is None or prom.valor is None:
        return "Esta semana no hay datos de precios disponibles."
    anio = r.desde.year - 1
    texto = elegir(P.APERTURA_PRECIOS, r.semana, "precios").format(valor=soles(prom.valor))
    comp = _comparaciones(prom, anio)
    texto += f", {comp}." if comp else "."
    # Relacion con la hidro: solo si ambos cambios son claros y van en sentidos opuestos
    dh = _cambio_hidro(r)
    if prom.var_anterior is not None and dh is not None and abs(prom.var_anterior) >= UMBRAL_PRECIO \
            and abs(dh) >= UMBRAL_HIDRO_PP and (prom.var_anterior > 0) != (dh > 0):
        texto += (f" El cambio coincidió con {'menos' if dh < 0 else 'más'} generación hidroeléctrica: "
                  f"{porcentaje(r.mix['hidro'])} del total frente a {porcentaje(r.mix_anterior['hidro'])} la semana previa.")
    texto += (f" La media hora más cara fue el {dia_y_hora(maxi.momento)} ({soles(maxi.valor)}) y la más barata "
              f"el {dia_y_hora(mini.momento)} ({soles(mini.valor)}).")
    if not r.perfil_cmg.empty and r.perfil_cmg["actual"].notna().any():
        hora_cara = int(r.perfil_cmg.loc[r.perfil_cmg["actual"].idxmax(), "hora"])
        texto += f" En promedio, la hora más cara del día fue la de las {hora_texto(hora_cara)}."
    alto, bajo = r.ind("horas_precio_alto"), r.ind("horas_precio_bajo")
    u = r.umbrales_precio
    texto += (f" Hubo {horas(alto.valor)} horas con precio alto (más de S/ {u['alto']}) y "
              f"{horas(bajo.valor)} con precio bajo (menos de S/ {u['bajo']}).")
    return texto


def parrafo_demanda(r):
    ene, pico, err = r.ind("energia_semana"), r.ind("demanda_maxima"), r.ind("error_programa_diario")
    if ene is None or ene.valor is None:
        return "Esta semana no hay datos de demanda disponibles."
    texto = elegir(P.APERTURA_DEMANDA, r.semana, "demanda").format(energia=f"{numero(ene.valor)} GWh")
    comp = _comparaciones(ene, r.desde.year - 1)
    texto += f", {comp}." if comp else "."
    texto += f" El momento de mayor consumo fue el {dia_y_hora(pico.momento)}, con {numero(pico.valor)} MW"
    texto += f" ({pct(pico.var_anterior)} {sube_baja(pico.var_anterior, 'más', 'menos')} que el pico de la semana anterior)." \
        if pico.var_anterior is not None else "."
    if err and err.valor is not None:
        calidad = "muy preciso" if err.valor < 0.02 else ("bastante preciso" if err.valor < 0.04 else "menos preciso de lo habitual")
        texto += (f" El pronóstico que el COES hace el día anterior se desvió en promedio {porcentaje(err.valor)}"
                  f" del consumo real: un cálculo {calidad}.")
    return texto


def parrafo_generacion(r):
    if not r.mix:
        return "Esta semana no hay datos de generación disponibles."
    lider = max(r.mix, key=r.mix.get)
    texto = capitalizar(elegir(P.APERTURA_GENERACION, r.semana, "gen").format(
        lider=nombre_tec(lider), lider_min=nombre_tec_min(lider), part_lider=porcentaje(r.mix[lider])))
    otras = [t for t in sorted(r.mix, key=r.mix.get, reverse=True) if t != lider and r.mix[t] >= 0.01][:3]
    if otras:
        texto += ", seguida de " + enumerar([f"{nombre_tec_min(t)} ({porcentaje(r.mix[t])})" for t in otras])
    texto += "."
    ren, sin = r.ind("participacion_renovable"), r.ind("participacion_renovable_sin_hidro")
    texto += f" Las fuentes renovables sumaron {porcentaje(ren.valor)}"
    if ren.var_anterior is not None and abs(ren.var_anterior) >= 0.001:
        texto += f" ({pp(ren.var_anterior)} {sube_baja(ren.var_anterior, 'más', 'menos')} que la semana anterior)"
    texto += f"; sin contar las hidroeléctricas, sol, viento y biomasa aportaron {porcentaje(sin.valor)}."
    sol, prom = r.ind("precio_capturado_solar"), r.ind("cmg_promedio")
    if sol and sol.valor and prom and prom.valor:
        razon = sol.valor / prom.valor
        if razon < 0.97:
            texto += (f" La energía solar se pagó en promedio a {soles(sol.valor)}, {pct(1 - razon)} por debajo del "
                      f"promedio de la semana: produjo sobre todo en horas más baratas que el resto.")
        elif razon > 1.03:
            texto += (f" La energía solar se pagó en promedio a {soles(sol.valor)}, {pct(razon - 1)} por encima del "
                      f"promedio de la semana: produjo en horas más caras que el resto.")
        else:
            texto += f" La energía solar se pagó a {soles(sol.valor)}, casi igual al promedio de la semana."
    return texto


def parrafo_hidrologia(r):
    vol = r.ind("volumen_embalses")
    if vol is None or vol.valor is None:
        return "Esta semana no hay datos de embalses disponibles."
    texto = elegir(P.APERTURA_HIDRO, r.semana, "hidro").format(valor=f"{numero(vol.valor, 1)} Hm3")
    texto += " (millones de metros cúbicos)."
    if vol.var_anterior is not None:
        if abs(vol.var_anterior) < 0.005:
            texto += " El nivel se mantuvo casi igual que la semana anterior"
        else:
            texto += f" Comparando los mismos embalses, el agua {sube_baja(vol.var_anterior, 'aumentó', 'disminuyó')} {pct(vol.var_anterior)} frente a la semana anterior"
        if vol.var_anio is not None:
            texto += f" y está {pct(vol.var_anio)} {sube_baja(vol.var_anio, 'por encima', 'por debajo')} de la misma semana de {r.desde.year - 1}"
        texto += "."
    det = r.embalses_detalle.dropna(subset=["actual", "anterior"])
    if len(det):
        det = det.assign(cambio=det["actual"] - det["anterior"])
        mayor = det.loc[det["cambio"].abs().idxmax()]
        if abs(mayor["cambio"]) >= 0.5:
            texto += (f" El mayor cambio fue en {mayor['entidad'].title()}, que {sube_baja(mayor['cambio'], 'ganó', 'perdió')} "
                      f"{numero(abs(mayor['cambio']), 1)} Hm3.")
    return texto


# ---------- titulos de graficos (dicen la conclusion) ----------

def titulos_graficos(r):
    t = {}
    if not r.perfil_cmg.empty and r.perfil_cmg["actual"].notna().any():
        hora = int(r.perfil_cmg.loc[r.perfil_cmg["actual"].idxmax(), "hora"])
        t["precios_perfil"] = f"El precio fue más alto alrededor de las {hora_texto(hora)}"
    prom = r.ind("cmg_promedio")
    if prom and prom.var_anterior is not None:
        t["precios_serie"] = f"El precio {sube_baja(prom.var_anterior)} {pct(prom.var_anterior)} frente a la semana pasada"
    else:
        t["precios_serie"] = "Así se movió el precio durante la semana"
    pico = r.ind("demanda_maxima")
    if pico and pico.momento is not None:
        t["demanda"] = f"El pico de consumo llegó el {dia_y_hora(pico.momento)}"
    if r.mix:
        lider = max(r.mix, key=r.mix.get)
        t["generacion"] = f"{nombre_tec(lider)} aportó {porcentaje(r.mix[lider])} de la electricidad"
    vol = r.ind("volumen_embalses")
    if vol and vol.var_anterior is not None:
        t["embalses"] = ("Los embalses se mantuvieron estables" if abs(vol.var_anterior) < 0.005 else
                         f"Los embalses {sube_baja(vol.var_anterior, 'ganaron', 'perdieron')} {pct(vol.var_anterior)} de agua")
    else:
        t["embalses"] = "Agua guardada en los embalses"
    return t


def generar_narrativa(r) -> Narrativa:
    return Narrativa(
        titulares=titulares(r),
        parrafos={
            "precios": pulir(parrafo_precios(r)),
            "demanda": pulir(parrafo_demanda(r)),
            "generacion": pulir(parrafo_generacion(r)),
            "hidrologia": pulir(parrafo_hidrologia(r)),
        },
        titulos_graficos={k: pulir(v) for k, v in titulos_graficos(r).items()},
    )
