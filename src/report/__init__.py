"""Informe semanal en PDF (opcional): A4 apaisado con la identidad editorial, fpdf2 sin HTML.

Paginas: portada con el pulso en cuatro cifras; 01 la senal (precios); 02 demanda y
generacion; 03 hidrologia y mapa; 04 lo que merece atencion; 05 metodo, fuentes y glosario.
"""

from pathlib import Path

from fpdf import FPDF

from src.analysis import calcular_resumen
from src.narrative import CATEGORIA_HECHO, en_simple, explicar_hecho, generar_narrativa, niveles, pulir
from src.utils import config, estado
from src.utils.estilo import registrar_fuentes_pdf
from src.utils.fechas import ahora_peru, dia_y_hora
from src.utils.formato import numero, porcentaje
from src.utils.logs import obtener_logger
from src.visual import graficos as G

log = obtener_logger(__name__)

ANCHO, ALTO, MARGEN = 297, 210, 14
UTIL = ANCHO - 2 * MARGEN


def _rgb(hexa):
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))


class InformePDF(FPDF):
    def __init__(self, resumen):
        super().__init__(orientation="L", format="A4")
        self.r = resumen
        self.proyecto = config.proyecto()
        self.p = self.proyecto["paleta"]
        self.f = registrar_fuentes_pdf(self)
        self.set_auto_page_break(True, margin=16)
        self.set_margins(MARGEN, 20, MARGEN)
        self.set_title(f"{self.proyecto['nombre']}: {resumen.texto_semana}")
        self.set_author(self.proyecto["nombre"])

    # ----- utilidades -----

    def color(self, clave):
        self.set_text_color(*_rgb(self.p[clave]))

    def relleno(self, clave):
        self.set_fill_color(*_rgb(self.p[clave]))

    def fuente(self, rol, tam, estilo=""):
        self.set_font(self.f[rol], estilo, tam)

    # ----- marco de pagina -----

    def header(self):
        self.relleno("papel")
        self.rect(0, 0, ANCHO, ALTO, style="F")
        self.relleno("tinta")
        self.rect(0, 0, ANCHO, 11, style="F")
        self.relleno("lima")
        self.ellipse(MARGEN, 3.5, 4, 4, style="F")
        self.set_xy(MARGEN + 7, 3)
        self.fuente("texto", 8.5, "B")
        self.set_text_color(255, 255, 255)
        self.cell(80, 5, self.proyecto["nombre"].upper())
        self.set_xy(ANCHO - MARGEN - 140, 3)
        self.fuente("mono", 6.5)
        self.color("gris")
        self.cell(140, 5, self.proyecto["tagline"].upper(), align="R")
        self.set_y(18)

    def footer(self):
        self.set_draw_color(*_rgb(self.p["linea"]))
        self.line(MARGEN, ALTO - 11, ANCHO - MARGEN, ALTO - 11)
        self.set_xy(MARGEN, ALTO - 10)
        self.fuente("mono", 6.5)
        self.color("gris")
        self.cell(200, 4, "OPEN SOURCE / NO AFILIADO AL COES / DATOS PÚBLICOS DE WWW.COES.ORG.PE")
        self.set_xy(ANCHO - MARGEN - 30, ALTO - 10)
        self.cell(30, 4, f"Página {self.page_no()} de {{nb}}", align="R")

    # ----- piezas -----

    def kicker(self, texto, clave_color="verde", y=None):
        if y is not None:
            self.set_y(y)
        self.fuente("mono", 7.5)
        self.color(clave_color)
        self.cell(0, 5, texto.upper(), new_x="LMARGIN", new_y="NEXT")

    def titular(self, texto, tam=22, ancho=0, clave_color="tinta"):
        self.fuente("titulares", tam, "B")
        self.color(clave_color)
        self.multi_cell(ancho, tam * 0.42, texto, new_x="LMARGIN", new_y="NEXT")

    def parrafo(self, texto, tam=9, ancho=0, clave_color="tinta", x=None, alto_linea=4.4):
        if x is not None:
            self.set_x(x)
        self.fuente("texto", tam)
        self.color(clave_color)
        self.multi_cell(ancho, alto_linea, pulir(texto), align="L", new_x="LMARGIN" if x is None else "LEFT", new_y="NEXT")

    def imagen(self, fig, x, y, w, h):
        self.image(G.a_png(fig), x=x, y=y, w=w, h=h)

    def celdas_cifras(self, celdas, y, alto=26):
        """Fila de cifras: etiqueta mono, valor condensado y pie (estilo 'el pulso en cuatro cifras')."""
        ancho = UTIL / len(celdas)
        self.set_draw_color(*_rgb(self.p["linea"]))
        for i, (etiqueta, valor, pie, color_pie) in enumerate(celdas):
            x = MARGEN + i * ancho
            self.relleno("blanco")
            self.rect(x, y, ancho, alto, style="DF")
            self.line(x, y + 7, x + ancho, y + 7)
            self.line(x, y + alto - 7, x + ancho, y + alto - 7)
            self.set_xy(x + 4, y + 1.5)
            self.fuente("mono", 6.5)
            self.color("gris")
            self.cell(ancho - 8, 4, etiqueta.upper())
            self.set_xy(x + 4, y + 9)
            self.fuente("titulares", 19, "B")
            self.color("tinta")
            self.cell(ancho - 8, 9, valor)
            self.set_xy(x + 4, y + alto - 5.8)
            self.fuente("mono", 6.5)
            self.set_text_color(*_rgb(color_pie))
            self.cell(ancho - 8, 4, pie)
        self.set_y(y + alto + 4)

    def caja_niveles(self, textos, x, y, w):
        """'Que significa esto' en tres niveles."""
        partes = [("LECTURA RÁPIDA", textos.get("rapida")), ("CON MÁS DETALLE", textos.get("intermedia")),
                  ("NOTA TÉCNICA", textos.get("tecnica"))]
        partes = [(e, t) for e, t in partes if t]
        self.fuente("texto", 8)
        alto = 10 + sum(5 + len(self.multi_cell(w - 8, 3.8, t, dry_run=True, output="LINES")) * 3.8 for _, t in partes)
        self.set_fill_color(231, 232, 224)
        self.set_draw_color(*_rgb(self.p["linea"]))
        self.rect(x, y, w, alto, style="DF")
        self.set_xy(x + 4, y + 3)
        self.fuente("mono", 7)
        self.color("verde")
        self.cell(w - 8, 4, "¿QUÉ SIGNIFICA ESTO?")
        cy = y + 8
        for etiqueta, texto in partes:
            self.set_xy(x + 4, cy)
            self.fuente("mono", 5.8)
            self.color("gris")
            self.cell(w - 8, 3.5, etiqueta)
            self.set_xy(x + 4, cy + 3.6)
            self.fuente("texto", 8)
            self.color("tinta" if etiqueta != "NOTA TÉCNICA" else "gris")
            self.multi_cell(w - 8, 3.8, texto, align="L")
            cy = self.get_y() + 1
        return y + alto


def _var(ind, p, invertir=False, puntos=False):
    if ind is None or ind.var_anterior is None:
        return "SIN COMPARACIÓN", p["gris"]
    v = ind.var_anterior
    unidad = " PP" if puntos else "%"
    texto = f"{'▲' if v > 0 else '▼'} {v * 100:+.1f}{unidad} VS. SEMANA PREVIA"
    bueno = (v < 0) if invertir else (v > 0)
    return texto, p["baja"] if bueno else p["sube"]


def _soles(v):
    return "s/d" if v is None else f"S/ {numero(v, 1)}"


# ---------- paginas ----------

def _portada(pdf, r, n):
    p = pdf.p
    pdf.add_page()
    pdf.set_xy(MARGEN, 18)
    nombre = pdf.proyecto["nombre"].split(" ", 1)
    pdf.fuente("titulares", 34, "B")
    pdf.color("tinta")
    pdf.cell(pdf.get_string_width(nombre[0] + " "), 14, nombre[0] + " ")
    pdf.color("verde")
    pdf.cell(0, 14, nombre[1] if len(nombre) > 1 else "", new_x="LMARGIN", new_y="NEXT")
    pdf.fuente("mono", 7)
    pdf.color("verde")
    pdf.cell(0, 4, pdf.proyecto["tagline"].upper(), new_x="LMARGIN", new_y="NEXT")

    y = pdf.get_y() + 3
    pdf.relleno("tinta")
    pdf.rect(MARGEN, y, UTIL, 62, style="F")
    pdf.set_xy(MARGEN + 8, y + 6)
    pdf.fuente("mono", 7.5)
    pdf.color("lima")
    estado_txt = "PRELIMINAR" if r.es_preliminar else "DATOS COMPLETOS"
    pdf.cell(0, 4, f"INFORME SEMANAL / {r.semana.replace('-W', ' · SEMANA ')} / {estado_txt}")
    pdf.set_xy(MARGEN + 8, y + 14)
    pdf.fuente("titulares", 30, "B")
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(UTIL - 100, 12, n.titulares[0] if n.titulares else r.texto_semana, align="L")
    pdf.set_x(MARGEN + 8)
    pdf.fuente("texto", 9)
    pdf.set_text_color(193, 199, 184)
    lead = f"{r.texto_semana}. Una lectura de precios, demanda y generación del SEIN con datos públicos del COES."
    if r.es_preliminar:
        lead += f" Reporte preliminar: {r.dias_con_datos} de 7 días con datos completos."
    pdf.multi_cell(UTIL - 100, 4.6, lead, align="L")
    prom = r.ind("cmg_promedio")
    pdf.set_xy(ANCHO - MARGEN - 88, y + 10)
    pdf.fuente("mono", 6.5)
    pdf.color("lima")
    pdf.cell(80, 4, "COSTO MARGINAL MEDIO / SANTA ROSA 220 KV", align="R")
    pdf.set_xy(ANCHO - MARGEN - 88, y + 17)
    pdf.fuente("titulares", 40, "B")
    pdf.set_text_color(241, 240, 232)
    pdf.cell(80, 18, _soles(prom.valor), align="R")
    pdf.set_xy(ANCHO - MARGEN - 88, y + 35)
    pdf.fuente("mono", 6.5)
    pdf.set_text_color(193, 199, 184)
    pdf.cell(80, 4, "POR MWH · PROMEDIO DE LA SEMANA", align="R")
    texto, _ = _var(prom, p, invertir=True)
    pdf.fuente("mono", 7)
    ancho_insignia = pdf.get_string_width(texto) + 6
    pdf.relleno("lima")
    pdf.rect(ANCHO - MARGEN - 8 - ancho_insignia, y + 42, ancho_insignia, 7, style="F")
    pdf.set_xy(ANCHO - MARGEN - 8 - ancho_insignia, y + 43.2)
    pdf.color("tinta")
    pdf.cell(ancho_insignia, 4.5, texto, align="C")

    pdf.kicker("El pulso en cuatro cifras", y=y + 68)
    dm, ren, emb = r.ind("demanda_maxima"), r.ind("participacion_renovable"), r.ind("volumen_embalses")
    pdf.celdas_cifras([
        ("Costo marginal medio", f"{_soles(prom.valor)} /MWh", *_var(prom, p, invertir=True)),
        ("Pico de demanda", f"{numero(dm.valor)} MW", *_var(dm, p)),
        ("Generación renovable*", porcentaje(ren.valor), *_var(ren, p, puntos=True)),
        ("Agua en embalses", f"{numero(emb.valor, 1)} Hm3" if emb.valor else "s/d", *_var(emb, p)),
    ], pdf.get_y() + 1)
    pdf.fuente("texto", 7.5)
    pdf.color("gris")
    sin = r.ind("participacion_renovable_sin_hidro")
    pdf.multi_cell(0, 3.8, f"*Incluye hidro; sin hidro: {porcentaje(sin.valor)}. Verde: cambio favorable para quien usa "
                           f"electricidad; rojo: desfavorable. Generado el {dia_y_hora(ahora_peru())} (hora de Perú). "
                           + " ".join(pdf.proyecto["aviso"].split()), align="L")
    dato = en_simple(r)
    if dato:
        y2 = pdf.get_y() + 3
        pdf.relleno("lima")
        pdf.rect(MARGEN, y2, UTIL, 22, style="F")
        pdf.set_xy(MARGEN + 6, y2 + 3)
        pdf.fuente("mono", 6.5)
        pdf.color("verde")
        pdf.cell(0, 4, "EN SIMPLE")
        pdf.set_xy(MARGEN + 6, y2 + 7.5)
        pdf.fuente("titulares", 13, "B")
        pdf.color("tinta")
        pdf.cell(0, 6, dato["titulo"].upper())
        pdf.set_xy(MARGEN + 6, y2 + 14)
        pdf.fuente("texto", 8)
        pdf.multi_cell(UTIL - 12, 3.8, " ".join(dato["texto"].split()), align="L")


def _pagina_precios(pdf, r, n):
    pdf.add_page()
    pdf.kicker("01 / La señal")
    pdf.titular("¿Qué movió el costo esta semana?", 22)
    pdf.parrafo(n.parrafos["precios"], 8.6, alto_linea=4.1)
    y = pdf.get_y() + 2
    mitad = (UTIL - 6) / 2
    if not r.serie_cmg.empty:
        pdf.imagen(G.precio_semana(r.serie_cmg, r.umbrales_precio, n.titulos_graficos["precios_serie"]),
                   MARGEN, y, mitad, mitad * 0.39)
    if "precios_perfil" in n.titulos_graficos:
        pdf.imagen(G.perfil_horario(r.perfil_cmg, n.titulos_graficos["precios_perfil"]),
                   MARGEN + mitad + 6, y, mitad, mitad * 0.39)
    pdf.caja_niveles(niveles(r, "cmg_promedio"), MARGEN, y + mitad * 0.39 + 4, UTIL)


def _pagina_demanda_generacion(pdf, r, n):
    pdf.add_page()
    pdf.kicker("02 / Demanda y generación")
    pdf.titular("Cuánto consumió el país y de dónde salió la energía", 22)
    mitad = (UTIL - 6) / 2
    y = pdf.get_y() + 2
    if not r.serie_demanda.empty:
        pdf.imagen(G.demanda(r.serie_demanda, n.titulos_graficos["demanda"]), MARGEN, y, mitad, mitad * 0.39)
    if r.mix:
        pdf.imagen(G.generacion(r.serie_generacion, n.titulos_graficos["generacion"]),
                   MARGEN + mitad + 6, y, mitad, mitad * 0.39)
    y += mitad * 0.39 + 3
    pdf.set_xy(MARGEN, y)
    pdf.parrafo(n.parrafos["demanda"], 8.4, ancho=mitad, alto_linea=4)
    y_izq = pdf.get_y()
    pdf.set_xy(MARGEN + mitad + 6, y)
    pdf.parrafo(n.parrafos["generacion"], 8.4, ancho=mitad, x=MARGEN + mitad + 6, alto_linea=4)
    y = max(y_izq, pdf.get_y()) + 3
    if y < ALTO - 60:
        pdf.caja_niveles(niveles(r, "precio_capturado_solar"), MARGEN, y, UTIL)


def _pagina_hidro_mapa(pdf, r, n):
    pdf.add_page()
    pdf.kicker("03 / Hidrología y el mapa del costo")
    izq = 168
    pdf.titular(n.titulos_graficos.get("embalses", "Hidrología"), 22, ancho=izq)
    y = pdf.get_y() + 2
    if not r.serie_embalses.empty:
        pdf.imagen(G.embalses(r.serie_embalses, n.titulos_graficos["embalses"]), MARGEN, y, izq, izq * 0.39)
    pdf.set_xy(MARGEN, y + izq * 0.39 + 3)
    pdf.parrafo(n.parrafos["hidrologia"], 8.4, ancho=izq, alto_linea=4)
    y_texto = pdf.get_y() + 3
    if not r.cmg_barras.empty and r.cmg_barras["latitud"].notna().any():
        ancho_mapa = UTIL - izq - 6
        alto_mapa = min(ancho_mapa * 5.6 / 4.6, ALTO - 36)
        pdf.imagen(G.mapa(r.cmg_barras, n.titulos_graficos.get("mapa", "")), MARGEN + izq + 6, 18,
                   alto_mapa * 4.6 / 5.6, alto_mapa)
    g = config.glosario()["indicadores"]["mapa_cmg"]
    textos = {"rapida": n.titulos_graficos.get("mapa", ""), "intermedia": " ".join(g["explicacion_simple"].split()),
              "tecnica": " ".join(g["nota_tecnica"].split())}
    pdf.caja_niveles(textos, MARGEN, y_texto, izq)


def _pagina_atencion(pdf, r, n):
    pdf.add_page()
    pdf.kicker("04 / Lo que merece atención")
    pdf.titular("Tres señales, con evidencia y sin inventar causalidad", 22)
    pdf.parrafo("Las reglas automáticas detectan cambios medibles y producen textos transparentes: qué cambió, contra qué "
                "se compara y qué limitación tiene la lectura.", 8.6)
    y = pdf.get_y() + 3
    for i, (h, titular) in enumerate(zip(r.hechos, n.titulares, strict=False), start=1):
        explicacion = explicar_hecho(h, r)
        pdf.fuente("texto", 8.4)
        lineas = len(pdf.multi_cell(UTIL - 40, 4, explicacion, dry_run=True, output="LINES"))
        alto = 15 + lineas * 4
        pdf.relleno("blanco")
        pdf.set_draw_color(*_rgb(pdf.p["linea"]))
        pdf.rect(MARGEN, y, UTIL, alto, style="DF")
        pdf.set_xy(MARGEN + 6, y + 4)
        pdf.fuente("mono", 14, "B")
        pdf.color("verde")
        pdf.cell(18, 7, f"{i:02d}")
        pdf.set_xy(MARGEN + 30, y + 3)
        pdf.fuente("mono", 6.5)
        pdf.cell(0, 4, CATEGORIA_HECHO.get(h.clave, "Sistema").upper())
        pdf.set_xy(MARGEN + 30, y + 7)
        pdf.fuente("texto", 10, "B")
        pdf.color("tinta")
        pdf.cell(0, 5, titular)
        pdf.set_xy(MARGEN + 30, y + 12.5)
        pdf.fuente("texto", 8.4)
        pdf.multi_cell(UTIL - 40, 4, explicacion, align="L")
        y += alto + 3
    pdf.set_y(y + 2)
    pdf.kicker("Rarezas y versiones del dato")
    rarezas = (f"El detector marcó {r.n_rarezas} medias horas que rompieron el rango de su misma hora en las 4 semanas "
               "previas. " + (f"La más llamativa: {dia_y_hora(r.rarezas[0]['fecha_hora'])}. {r.rarezas[0]['regla']}"
                              if r.rarezas else "Ninguna esta semana."))
    pdf.parrafo(rarezas, 8.4)
    if r.revision:
        rv = r.revision
        pdf.parrafo(f"Lo que el sistema creía: de {rv['intervalos']} medias horas con versión preliminar y confirmada, el "
                    f"COES cambió {rv['cambiados']}. En promedio el precio se movió {_soles(rv['diferencia_media_abs'])} por "
                    f"MWh ({porcentaje(rv['diferencia_media_pct'])}); el mayor cambio, {_soles(rv['max_abs'])}, fue el "
                    f"{dia_y_hora(rv['momento_max'])}".rstrip(".") + ".", 8.4)


def _pagina_metodo(pdf, r):
    pdf.add_page()
    pdf.kicker("05 / Método y fuentes")
    pdf.titular("La confianza también forma parte del diseño", 20)
    y = pdf.get_y() + 2
    fuentes = config.fuentes()
    est = estado.leer()
    filas = [(nombre, f) for nombre, f in fuentes["fuentes"].items() if nombre != "costo_marginal_tr"]
    filas += [(f"ahora_{nombre}", f) for nombre, f in fuentes["ahora"].items() if isinstance(f, dict)]
    columnas = [("FUENTE", 34), ("QUÉ TRAE", 105), ("FRECUENCIA", 24), ("RETRASO", 22), ("ESTADO", 26), ("ÚLTIMA EXTRACCIÓN OK", 58)]
    pdf.set_xy(MARGEN, y)
    pdf.relleno("tinta")
    pdf.fuente("mono", 6)
    pdf.set_text_color(255, 255, 255)
    for titulo, w in columnas:
        pdf.cell(w, 6, " " + titulo, fill=True)
    pdf.ln()
    pdf.fuente("texto", 7)
    pdf.color("tinta")
    pdf.relleno("blanco")
    pdf.set_draw_color(*_rgb(pdf.p["linea"]))
    for nombre, f in filas:
        exito = est.get(nombre, {}).get("ultima_extraccion_exitosa", "sin registro").replace("T", " ")[:16]
        valores = [nombre.replace("_", " "), f.get("descripcion", "")[:100], f.get("frecuencia_objetivo", ""),
                   f.get("retraso_esperado", ""), f.get("estado_dato", "").replace("_", " "), exito]
        pdf.set_x(MARGEN)
        for (_, w), v in zip(columnas, valores, strict=True):
            pdf.cell(w, 5.2, " " + v, border="B", fill=True)
        pdf.ln()
    ancho_col = (UTIL - 12) / 3
    y = pdf.get_y() + 4
    pdf.set_xy(MARGEN, y)
    pdf.kicker("Calidad de esta semana")
    texto = "; ".join(r.avisos) if r.avisos else "Sin avisos: no hubo duplicados, huecos ni valores fuera de rango."
    pdf.parrafo(texto[:500], 7.2, ancho=ancho_col, alto_linea=3.5)
    pdf.set_x(MARGEN)
    pdf.kicker("Reglas editoriales")
    pdf.parrafo("Nunca ocultar de dónde sale el dato. Mostrar los huecos en vez de rellenarlos. Comparar ventanas "
                "equivalentes. Describir la señal, no inventar la causa.", 7.2, ancho=ancho_col, alto_linea=3.5)
    y_ind = pdf.get_y() + 2
    pdf.relleno("lima")
    pdf.fuente("texto", 7.2)
    aviso = "Independencia: " + " ".join(pdf.proyecto["aviso"].split())
    lineas = len(pdf.multi_cell(ancho_col - 6, 3.5, aviso, dry_run=True, output="LINES"))
    pdf.rect(MARGEN, y_ind, ancho_col, lineas * 3.5 + 6, style="F")
    pdf.set_xy(MARGEN + 3, y_ind + 3)
    pdf.color("tinta")
    pdf.multi_cell(ancho_col - 6, 3.5, aviso, align="L")
    pdf.set_xy(MARGEN + ancho_col + 6, y)
    pdf.fuente("mono", 7.5)
    pdf.color("verde")
    pdf.cell(0, 5, "GLOSARIO")
    pdf.set_y(y + 6)
    glosario = config.glosario()
    with pdf.text_columns(ncols=2, gutter=6, text_align="L", line_height=1.05,
                          l_margin=MARGEN + ancho_col + 6, r_margin=MARGEN) as cols:
        for grupo in ("indicadores", "terminos"):
            for g in glosario[grupo].values():
                pdf.fuente("texto", 6.2, "B")
                pdf.color("tinta")
                cols.write(g["nombre"] + ". ")
                pdf.fuente("texto", 6.2)
                cols.write(" ".join(g["explicacion_simple"].split()))
                cols.ln()


def generar_pdf(semana, destino=None, raiz=None):
    """Arma el PDF de la semana (opcional) y devuelve su ruta."""
    r = calcular_resumen(semana, raiz)
    n = generar_narrativa(r)
    pdf = InformePDF(r)
    _portada(pdf, r, n)
    _pagina_precios(pdf, r, n)
    _pagina_demanda_generacion(pdf, r, n)
    _pagina_hidro_mapa(pdf, r, n)
    _pagina_atencion(pdf, r, n)
    _pagina_metodo(pdf, r)
    destino = Path(destino or config.DIR_REPORTS / f"{config.proyecto()['slug']}_{semana}.pdf")
    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(destino))
    log.info("PDF %s (%s paginas, %.0f KB)", destino.name, pdf.pages_count, destino.stat().st_size / 1024)
    return destino


def exportar_portada_png(ruta_pdf, destino, escala=2):
    """Renderiza la pagina 1 del PDF a PNG (requiere pypdfium2)."""
    import pypdfium2 as pdfium
    documento = pdfium.PdfDocument(str(ruta_pdf))
    documento[0].render(scale=escala).to_pil().save(destino)
    documento.close()
    return destino
