"""Dashboard Streamlit. Correr desde la raiz: streamlit run app/streamlit_app.py"""

import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

import graficos as G  # noqa: E402
from src.analysis import calcular_resumen  # noqa: E402
from src.narrative import generar_narrativa  # noqa: E402
from src.utils import config  # noqa: E402
from src.utils.datos import ruta_tabla, semanas_disponibles  # noqa: E402
from src.utils.fechas import HORA_PERU, dia_y_hora, texto_semana, ultima_semana_completa  # noqa: E402
from src.utils.formato import numero, porcentaje  # noqa: E402

PROYECTO = config.proyecto()
GLOSARIO = config.glosario()

st.set_page_config(page_title=PROYECTO["nombre"], page_icon="⚡", layout="wide")


# ---------- datos ----------

@st.cache_data(ttl=3600, show_spinner="Calculando la semana...")
def cargar(semana):
    """Resumen y narrativa de la semana (cacheado)."""
    resumen = calcular_resumen(semana)
    return resumen, generar_narrativa(resumen)


@st.cache_data(ttl=600)
def semanas():
    """Semanas con las tablas base disponibles."""
    # Solo semanas con las tablas base completas para analizar
    return [s for s in semanas_disponibles("demanda")
            if ruta_tabla("costo_marginal", s).exists() and ruta_tabla("generacion", s).exists()]


def ayuda(clave):
    """Texto para el parametro help de st.metric (tooltip)."""
    g = GLOSARIO["indicadores"][clave]
    return f"{g['explicacion_simple'].strip()}\n\n¿Por qué importa? {g['por_que_importa']}"


def que_significa(*claves):
    """Expander con las explicaciones del glosario."""
    with st.expander("¿Qué significa esto?"):
        for clave in claves:
            g = GLOSARIO["indicadores"].get(clave) or GLOSARIO["terminos"][clave]
            st.markdown(f"**{g['nombre']}.** {g['explicacion_simple'].strip()}")
            st.markdown(f"*Por qué importa:* {g['por_que_importa']}")
            if g.get("ejemplo_cotidiano"):
                st.markdown(f"*Para imaginarlo:* {g['ejemplo_cotidiano'].strip()}")


def delta(ind, puntos=False):
    """Texto de variacion para st.metric."""
    if ind is None or ind.var_anterior is None:
        return None
    if puntos:
        return f"{ind.var_anterior * 100:+.1f} pp vs semana anterior"
    return f"{ind.var_anterior * 100:+.1f}% vs semana anterior"


def metrica(col, ind, etiqueta_valor, clave, puntos=False, invertir=False):
    """st.metric con nombre y ayuda tomados del glosario."""
    col.metric(GLOSARIO["indicadores"][clave]["nombre"], etiqueta_valor, delta(ind, puntos),
               delta_color="inverse" if invertir else "normal", help=ayuda(clave))


def soles(v):
    """Monto en soles o s/d."""
    return "s/d" if v is None else f"S/ {numero(v, 1)}"


def grafico(fig):
    """Muestra un grafico Plotly a todo el ancho."""
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "locale": "es"})


# ---------- encabezado ----------

lista = semanas()
if not lista:
    st.title(PROYECTO["nombre"])
    st.error("Todavía no hay datos procesados. Corre `python run_weekly.py` para descargar la primera semana.")
    st.stop()

col_titulo, col_semana = st.columns([3, 2])
col_titulo.title(f"⚡ {PROYECTO['nombre']}")
col_titulo.caption(PROYECTO["tagline"])
opciones = lista[::-1]
# Por defecto la ultima semana completa; la semana en curso queda disponible como preliminar
inicial = opciones.index(ultima_semana_completa()) if ultima_semana_completa() in opciones else 0
semana = col_semana.selectbox("Semana", options=opciones, index=inicial, format_func=texto_semana)

resumen, narrativa = cargar(semana)
r, n = resumen, narrativa

if r.es_preliminar:
    st.warning(f"Datos preliminares: {r.dias_con_datos} de 7 días con datos o días que el COES aún no confirma. "
               "Los números pueden cambiar un poco.", icon="⏳")

# ---------- portada ----------

st.subheader(r.texto_semana)
for titular in n.titulares:
    st.markdown(f"##### • {titular}")

c1, c2, c3, c4 = st.columns(4)
metrica(c1, r.ind("cmg_promedio"), f"{soles(r.ind('cmg_promedio').valor)} por MWh", "cmg_promedio", invertir=True)
dm = r.ind("demanda_maxima")
metrica(c2, dm, f"{numero(dm.valor)} MW", "demanda_maxima")
ren = r.ind("participacion_renovable")
metrica(c3, ren, porcentaje(ren.valor), "participacion_renovable", puntos=True)
emb = r.ind("volumen_embalses")
metrica(c4, emb, f"{numero(emb.valor, 1)} Hm3" if emb.valor else "s/d", "volumen_embalses")

# PDF de la semana
slug = PROYECTO["slug"]
ruta_pdf = config.DIR_REPORTS / f"{slug}_{semana}.pdf"
if not ruta_pdf.exists():
    try:
        from src.report import generar_pdf
        if st.button("Generar el PDF de esta semana"):
            with st.spinner("Armando el PDF..."):
                generar_pdf(semana)
            st.rerun()
    except ImportError:
        pass
if ruta_pdf.exists():
    st.download_button("📄 Descargar el reporte en PDF", ruta_pdf.read_bytes(), file_name=ruta_pdf.name,
                       mime="application/pdf")

# ---------- pestanas ----------

t_precios, t_demanda, t_gen, t_hidro, t_glosario, t_sobre = st.tabs(
    ["Precios", "Demanda", "Generación", "Hidrología", "Glosario", "Sobre el proyecto"])

with t_precios:
    st.markdown(n.parrafos["precios"])
    a, b, c, d = st.columns(4)
    mx, mn = r.ind("cmg_maximo"), r.ind("cmg_minimo")
    a.metric(GLOSARIO["indicadores"]["cmg_maximo"]["nombre"], soles(mx.valor), help=ayuda("cmg_maximo"))
    a.caption(dia_y_hora(mx.momento) if mx.momento is not None else "")
    b.metric(GLOSARIO["indicadores"]["cmg_minimo"]["nombre"], soles(mn.valor), help=ayuda("cmg_minimo"))
    b.caption(dia_y_hora(mn.momento) if mn.momento is not None else "")
    metrica(c, r.ind("horas_precio_alto"), numero(r.ind("horas_precio_alto").valor, 1), "horas_precio_alto", invertir=True)
    metrica(d, r.ind("horas_precio_bajo"), numero(r.ind("horas_precio_bajo").valor, 1), "horas_precio_bajo")
    grafico(G.grafico_precio_semana(r.serie_cmg, r.umbrales_precio, n.titulos_graficos["precios_serie"]))
    que_significa("cmg_promedio", "barra_referencia", "horas_precio_alto")
    if "precios_perfil" in n.titulos_graficos:
        grafico(G.grafico_perfil_horario(r.perfil_cmg, n.titulos_graficos["precios_perfil"]))
        que_significa("perfil_horario")

with t_demanda:
    st.markdown(n.parrafos["demanda"])
    a, b = st.columns(2)
    ene = r.ind("energia_semana")
    metrica(a, ene, f"{numero(ene.valor)} GWh", "energia_semana")
    err = r.ind("error_programa_diario")
    b.metric(GLOSARIO["indicadores"]["error_programa_diario"]["nombre"], porcentaje(err.valor),
             help=ayuda("error_programa_diario"))
    if "demanda" in n.titulos_graficos:
        grafico(G.grafico_demanda(r.serie_demanda, n.titulos_graficos["demanda"]))
    que_significa("demanda_maxima", "energia_semana", "error_programa_diario")

with t_gen:
    st.markdown(n.parrafos["generacion"])
    a, b, c, d = st.columns(4)
    metrica(a, ren, porcentaje(ren.valor), "participacion_renovable", puntos=True)
    sin = r.ind("participacion_renovable_sin_hidro")
    metrica(b, sin, porcentaje(sin.valor), "participacion_renovable_sin_hidro", puntos=True)
    metrica(c, r.ind("precio_capturado_solar"), soles(r.ind("precio_capturado_solar").valor), "precio_capturado_solar")
    metrica(d, r.ind("precio_capturado_eolica"), soles(r.ind("precio_capturado_eolica").valor), "precio_capturado_eolica")
    if r.mix:
        grafico(G.grafico_generacion(r.serie_generacion, n.titulos_graficos["generacion"]))
        que_significa("mix_generacion", "participacion_renovable")
        grafico(G.grafico_mix(r.mix, r.mix_anterior, "Participación de cada fuente (en gris, la semana anterior)"))
        que_significa("participacion_renovable_sin_hidro", "precio_capturado_solar")

with t_hidro:
    st.markdown(n.parrafos["hidrologia"])
    if not r.serie_embalses.empty:
        grafico(G.grafico_embalses(r.serie_embalses, n.titulos_graficos["embalses"]))
        que_significa("volumen_embalses")
        grafico(G.grafico_embalses_detalle(r.embalses_detalle, "Los embalses con más agua, frente a la semana anterior"))
        st.caption("Se muestran los embalses que reportan volumen útil en el IEOD del COES. "
                   "Algunos solo reportan nivel (metros sobre el nivel del mar) y no entran en la suma.")

with t_glosario:
    st.markdown("Todo lo que ves en el sitio, explicado en simple.")
    for grupo in ("indicadores", "terminos"):
        for entrada in sorted(GLOSARIO[grupo].values(), key=lambda g: g["nombre"]):
            with st.expander(entrada["nombre"]):
                st.markdown(entrada["explicacion_simple"].strip())
                st.markdown(f"*Por qué importa:* {entrada['por_que_importa']}")
                if entrada.get("ejemplo_cotidiano"):
                    st.markdown(f"*Para imaginarlo:* {entrada['ejemplo_cotidiano'].strip()}")
                if entrada.get("unidad"):
                    st.caption(f"Unidad: {entrada['unidad']}")

with t_sobre:
    st.markdown(f"""
**{PROYECTO['nombre']}** es un proyecto open source que descarga cada semana los datos públicos del
COES, los ordena y los explica en lenguaje simple.

**De dónde salen los datos**
- Demanda y generación por tecnología: portal de información del COES.
- Costo marginal: archivo diario del IEOD (Informe de Evaluación de la Operación Diaria). Si un día aún no se
  publica, se usa el costo marginal en tiempo real y se marca como preliminar.
- Embalses: anexo del IEOD.

**Cómo se calcula**
- El precio se sigue en la barra **{r.barra_referencia.title()} kV** de Lima.
- Precio alto: más de S/ {r.umbrales_precio['alto']} por MWh. Precio bajo: menos de S/ {r.umbrales_precio['bajo']} por MWh.
- La variación de los embalses compara solo los embalses con dato en ambas semanas.
- Los textos se arman con reglas fijas, sin inteligencia artificial.

**Aviso.** {PROYECTO['aviso'].strip()}
""")
    if r.avisos:
        with st.expander(f"Avisos de calidad de datos de esta semana ({len(r.avisos)})"):
            for aviso in r.avisos:
                st.markdown(f"- {aviso}")

# ---------- pie ----------

actualizado = datetime.fromtimestamp(ruta_tabla("demanda", semana).stat().st_mtime, HORA_PERU)
st.divider()
st.caption(f"Fuente: COES, www.coes.org.pe. Datos actualizados el {dia_y_hora(actualizado)} (hora de Perú). "
           f"{PROYECTO['aviso'].strip()}")
