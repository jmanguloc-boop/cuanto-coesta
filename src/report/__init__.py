"""PDF semanal con fpdf2 (sin HTML): portada, 4 secciones, glosario y nota metodologica."""

from pathlib import Path

import matplotlib
from fpdf import FPDF

from src.analysis import calcular_resumen
from src.narrative import generar_narrativa
from src.report import graficos as G
from src.utils import config
from src.utils.fechas import ahora_peru, dia_y_hora
from src.utils.formato import numero, porcentaje
from src.utils.logs import obtener_logger

log = obtener_logger(__name__)

DIR_FUENTES = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FUENTE = "DejaVu"


def _rgb(hexa):
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))


class ReportePDF(FPDF):
    def __init__(self, resumen):
        super().__init__(format="A4")
        self.r = resumen
        self.proyecto = config.proyecto()
        self.paleta = self.proyecto["paleta"]
        self.add_font(FUENTE, "", str(DIR_FUENTES / "DejaVuSans.ttf"))
        self.add_font(FUENTE, "B", str(DIR_FUENTES / "DejaVuSans-Bold.ttf"))
        self.add_font(FUENTE, "I", str(DIR_FUENTES / "DejaVuSans-Oblique.ttf"))
        self.set_auto_page_break(True, margin=18)
        self.set_margins(15, 15, 15)
        self.set_title(f"{self.proyecto['nombre']}: {resumen.texto_semana}")
        self.set_author(self.proyecto["nombre"])

    def color_texto(self, clave):
        """Color de texto de la paleta."""
        self.set_text_color(*_rgb(self.paleta[clave]))

    def header(self):
        """Encabezado de las paginas interiores."""
        if self.page_no() == 1:
            return
        self.set_font(FUENTE, "B", 9)
        self.color_texto("primario")
        self.cell(0, 6, self.proyecto["nombre"], new_x="LMARGIN", new_y="TOP")
        self.set_font(FUENTE, "", 8)
        self.color_texto("texto_suave")
        etiqueta = self.r.texto_semana + (" (preliminar)" if self.r.es_preliminar else "")
        self.cell(0, 6, etiqueta, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*_rgb(self.paleta["secundario"]))
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def footer(self):
        """Pie con fuente, aviso y numero de pagina."""
        self.set_y(-13)
        self.set_font(FUENTE, "", 7)
        self.color_texto("texto_suave")
        self.cell(0, 5, "Fuente: COES (www.coes.org.pe). Proyecto independiente, no afiliado al COES.", new_x="LMARGIN", new_y="TOP")
        self.cell(0, 5, f"Página {self.page_no()} de {{nb}}", align="R")

    # ---------- piezas ----------

    def titulo_seccion(self, texto):
        """Titulo grande de seccion."""
        self.set_font(FUENTE, "B", 16)
        self.color_texto("primario")
        self.cell(0, 9, texto, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def parrafo(self, texto, tam=9.5):
        """Parrafo de texto corrido."""
        self.set_font(FUENTE, "", tam)
        self.color_texto("texto")
        self.multi_cell(0, 5, texto, align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def imagen(self, png, alto):
        """Inserta un grafico a todo el ancho."""
        self.image(png, x=15, w=180, h=alto)
        self.ln(1)

    def cajita(self, claves):
        """Recuadro 'Que significa esto' con textos del glosario."""
        glosario = config.glosario()
        bloques = []
        for clave in claves:
            g = glosario["indicadores"].get(clave) or glosario["terminos"][clave]
            bloques.append((g["nombre"], " ".join(g["explicacion_simple"].split()), g["por_que_importa"]))
        textos = [f"**{n}.** {e} __Por qué importa:__ {p}" for n, e, p in bloques]
        self.set_font(FUENTE, "", 8.5)
        lineas = sum(len(self.multi_cell(172, 4.4, txt, markdown=True, align="L", dry_run=True, output="LINES"))
                     for txt in textos)
        alto = 12 + lineas * 4.4 + 1.5 * len(bloques)
        if self.get_y() + alto > self.h - 20:
            self.add_page()
        x, y = 15, self.get_y()
        self.set_fill_color(*_rgb(self.paleta["fondo_suave"]))
        self.set_draw_color(*_rgb(self.paleta["secundario"]))
        self.rect(x, y, 180, alto, style="DF")
        self.set_xy(x + 4, y + 3)
        self.set_font(FUENTE, "B", 9)
        self.color_texto("secundario")
        self.cell(0, 5, "¿Qué significa esto?", new_x="LMARGIN", new_y="NEXT")
        for texto in textos:
            self.set_x(x + 4)
            self.color_texto("texto")
            self.set_font(FUENTE, "", 8.5)
            self.multi_cell(172, 4.4, texto, markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
            self.ln(1.5)
        self.set_y(y + alto + 4)

    def tarjeta(self, x, y, ancho, etiqueta, valor, var_texto, color_var, tam_valor=14):
        """Tarjeta de indicador: etiqueta, valor y variacion."""
        self.set_fill_color(*_rgb(self.paleta["fondo_suave"]))
        self.rect(x, y, ancho, 30, style="F")
        self.set_xy(x + 3, y + 3)
        self.set_font(FUENTE, "", 8)
        self.color_texto("texto_suave")
        self.multi_cell(ancho - 6, 4, etiqueta, align="L", new_x="LEFT", new_y="NEXT")
        self.set_xy(x + 3, y + 12)
        self.set_font(FUENTE, "B", tam_valor)
        self.color_texto("texto")
        self.cell(ancho - 6, 8, valor, new_x="LEFT", new_y="NEXT")
        self.set_x(x + 3)
        self.set_font(FUENTE, "", 7.5)
        self.set_text_color(*_rgb(color_var))
        self.cell(ancho - 6, 5, var_texto)


def _var(ind, puntos=False, invertir=False, paleta=None):
    """('▲ 3.2% vs sem. ant.', color)."""
    if ind is None or ind.var_anterior is None:
        return "sin comparación", paleta["texto_suave"]
    v = ind.var_anterior
    flecha = "▲" if v > 0 else "▼"
    texto = f"{flecha} {abs(v) * 100:.1f} {'pp' if puntos else '%'} vs sem. ant.".replace(" %", "%")
    bueno = (v < 0) if invertir else (v > 0)
    return texto, paleta["baja"] if bueno else paleta["sube"]


def _portada(pdf, r, n):
    proyecto, p = pdf.proyecto, pdf.paleta
    pdf.add_page()
    pdf.set_fill_color(*_rgb(p["primario"]))
    pdf.rect(0, 0, 210, 62, style="F")
    pdf.set_xy(15, 16)
    pdf.set_font(FUENTE, "B", 28)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, proyecto["nombre"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FUENTE, "", 11)
    pdf.cell(0, 7, proyecto["tagline"], new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font(FUENTE, "B", 13)
    pdf.set_text_color(*_rgb(p["acento"]))
    pdf.cell(0, 8, r.texto_semana, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(72)
    if r.es_preliminar:
        pdf.set_font(FUENTE, "B", 9)
        pdf.set_text_color(*_rgb(p["acento"]))
        pdf.multi_cell(0, 5, f"REPORTE PRELIMINAR: {r.dias_con_datos} de 7 días con datos o días que el COES aún no "
                             "confirma. Los números pueden cambiar.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    pdf.set_font(FUENTE, "B", 11)
    pdf.color_texto("texto_suave")
    pdf.cell(0, 7, "Lo más importante de la semana", new_x="LMARGIN", new_y="NEXT")
    for titular in n.titulares:
        pdf.set_font(FUENTE, "B", 13)
        pdf.color_texto("texto")
        pdf.multi_cell(0, 7, f"•  {titular}", align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    pdf.ln(4)
    y = pdf.get_y()
    g = config.glosario()["indicadores"]
    tarjetas = [
        (g["cmg_promedio"]["nombre"] + " (S/ por MWh)", f"S/ {numero(r.ind('cmg_promedio').valor, 1)}", _var(r.ind("cmg_promedio"), invertir=True, paleta=p)),
        (g["demanda_maxima"]["nombre"], f"{numero(r.ind('demanda_maxima').valor)} MW", _var(r.ind("demanda_maxima"), paleta=p)),
        (g["participacion_renovable"]["nombre"], porcentaje(r.ind("participacion_renovable").valor), _var(r.ind("participacion_renovable"), puntos=True, paleta=p)),
        (g["volumen_embalses"]["nombre"], f"{numero(r.ind('volumen_embalses').valor, 1)} Hm3", _var(r.ind("volumen_embalses"), paleta=p)),
    ]
    ancho = 42.75
    for i, (etiqueta, valor, (var_texto, color)) in enumerate(tarjetas):
        pdf.tarjeta(15 + i * (ancho + 3), y, ancho, etiqueta, valor, var_texto, color)
    y += 34
    sol, prom = r.ind("precio_capturado_solar"), r.ind("cmg_promedio")
    segunda = [
        (g["energia_semana"]["nombre"], f"{numero(r.ind('energia_semana').valor)} GWh", _var(r.ind("energia_semana"), paleta=p)),
        (g["horas_precio_alto"]["nombre"], f"{numero(r.ind('horas_precio_alto').valor, 1)} h",
         _var(r.ind("horas_precio_alto"), invertir=True, paleta=p)),
        (g["participacion_renovable_sin_hidro"]["nombre"], porcentaje(r.ind("participacion_renovable_sin_hidro").valor),
         _var(r.ind("participacion_renovable_sin_hidro"), puntos=True, paleta=p)),
        (g["precio_capturado_solar"]["nombre"] + " (S/ por MWh)", f"S/ {numero(sol.valor, 1)}" if sol.valor else "s/d",
         (f"{abs(1 - sol.valor / prom.valor) * 100:.1f}% {'bajo' if sol.valor < prom.valor else 'sobre'} el promedio"
          if sol.valor and prom.valor else "", p["texto_suave"])),
    ]
    for i, (etiqueta, valor, (var_texto, color)) in enumerate(segunda):
        pdf.tarjeta(15 + i * (ancho + 3), y, ancho, etiqueta, valor, var_texto, color, tam_valor=12)
    pdf.set_y(y + 36)
    pdf.set_font(FUENTE, "I", 8)
    pdf.color_texto("texto_suave")
    pdf.multi_cell(0, 4.2, "Las variaciones comparan con la semana anterior. Verde: cambio favorable para quien usa "
                           "electricidad (por ejemplo, precio más bajo o más renovable). Rojo: cambio desfavorable.",
                   align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(-45)
    pdf.set_font(FUENTE, "", 8)
    pdf.multi_cell(0, 4.2, " ".join(proyecto["aviso"].split()) + f" Generado el {dia_y_hora(ahora_peru())} (hora de Perú).",
                   new_x="LMARGIN", new_y="NEXT")


def _glosario_y_metodologia(pdf, r):
    pdf.add_page()
    pdf.titulo_seccion("Nota metodológica")
    pdf.parrafo(
        "Fuentes: portal de información del COES (demanda y generación por tecnología) y el Informe de Evaluación "
        "de la Operación Diaria, IEOD (costo marginal y embalses). Si el IEOD de un día aún no se publica, el costo "
        f"marginal se toma del reporte en tiempo real y el día se marca como preliminar. El precio se sigue en la "
        f"barra {r.barra_referencia.title()} kV (Lima). Precio alto: más de S/ {r.umbrales_precio['alto']} por MWh; "
        f"precio bajo: menos de S/ {r.umbrales_precio['bajo']} por MWh. La variación de los embalses compara solo "
        "embalses con dato en ambas semanas. Los textos se generan con reglas fijas, sin inteligencia artificial. "
        + " ".join(pdf.proyecto["aviso"].split()), tam=8.5)
    pdf.titulo_seccion("Glosario")
    glosario = config.glosario()
    pdf.set_font(FUENTE, "", 7.0)
    pdf.color_texto("texto")
    with pdf.text_columns(ncols=2, gutter=6, text_align="L", line_height=1.1) as cols:
        for grupo in ("indicadores", "terminos"):
            for entrada in glosario[grupo].values():
                pdf.set_font(FUENTE, "B", 7.0)
                cols.write(entrada["nombre"] + ". ")
                pdf.set_font(FUENTE, "", 7.0)
                cols.write(" ".join(entrada["explicacion_simple"].split()))
                cols.ln()
                cols.ln()


def generar_pdf(semana, destino=None, raiz=None):
    """Arma el PDF de la semana y devuelve su ruta."""
    r = calcular_resumen(semana, raiz)
    n = generar_narrativa(r)
    t = n.titulos_graficos
    pdf = ReportePDF(r)

    _portada(pdf, r, n)

    pdf.add_page()
    pdf.titulo_seccion("Precios")
    pdf.imagen(G.precio_semana(r.serie_cmg, r.umbrales_precio, t["precios_serie"]), 62)
    if "precios_perfil" in t:
        pdf.imagen(G.perfil_horario(r.perfil_cmg, t["precios_perfil"]), 52)
    pdf.parrafo(n.parrafos["precios"])
    pdf.cajita(["cmg_promedio", "perfil_horario"])

    pdf.add_page()
    pdf.titulo_seccion("Demanda")
    if "demanda" in t:
        pdf.imagen(G.demanda(r.serie_demanda, t["demanda"]), 72)
    pdf.parrafo(n.parrafos["demanda"])
    pdf.cajita(["demanda_maxima", "energia_semana", "error_programa_diario"])

    pdf.add_page()
    pdf.titulo_seccion("Generación")
    if r.mix:
        pdf.imagen(G.generacion(r.serie_generacion, t["generacion"]), 72)
        pdf.imagen(G.mix(r.mix, r.mix_anterior, "Participación de cada fuente (en gris, la semana anterior)"), 52)
    pdf.parrafo(n.parrafos["generacion"])
    pdf.cajita(["participacion_renovable", "precio_capturado_solar"])

    pdf.add_page()
    pdf.titulo_seccion("Hidrología")
    if not r.serie_embalses.empty:
        pdf.imagen(G.embalses(r.serie_embalses, t["embalses"]), 60)
        pdf.imagen(G.embalses_detalle(r.embalses_detalle, "Los embalses con más agua, frente a la semana anterior"), 62)
    pdf.parrafo(n.parrafos["hidrologia"])
    pdf.cajita(["volumen_embalses"])

    _glosario_y_metodologia(pdf, r)

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
