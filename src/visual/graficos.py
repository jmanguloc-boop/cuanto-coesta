"""Graficos (matplotlib) compartidos por la app de escritorio y el PDF.

Estilo limpio: fondo blanco, una serie principal en azul, el dato a mirar en naranja.
Cada funcion devuelve una Figure. Si se pasa titulo, se dibuja arriba (PDF); en la
app el titulo va en la tarjeta y se pasa titulo="". fig.hover guarda las series para
mostrar el valor al pasar el mouse: lista de (x, y, formato).
"""

import json
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from src.utils import config  # noqa: E402
from src.utils.estilo import DIR_MAPAS, fuente_mpl, paleta, preparar_matplotlib  # noqa: E402
from src.utils.fechas import dia_y_hora  # noqa: E402

ABREV = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MILES = FuncFormatter(lambda v, _: f"{v:,.0f}")
GRILLA = "#EEF2F7"
AYER = "#B9C7D6"


def _fig(ancho=7.2, alto=2.8):
    preparar_matplotlib()
    p = paleta()
    fig = Figure(figsize=(ancho, alto), dpi=110)
    ax = fig.add_subplot(111)
    fig.patch.set_facecolor(p["blanco"])
    ax.set_facecolor(p["blanco"])
    ax.tick_params(colors=p["gris"], labelsize=8, length=0)
    ax.spines["bottom"].set_color(p["linea"])
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.grid(axis="y", color=GRILLA, linewidth=1)
    ax.set_axisbelow(True)
    fig.hover = []
    fig.titulo = ""
    fig.subplots_adjust(top=0.95, left=0.08, right=0.98, bottom=0.14)
    return fig, ax


def _encabezado(fig, ax, titulo, kicker=""):
    """Titulo arriba del grafico (solo si se pide, para el PDF)."""
    fig.titulo = titulo
    if not titulo:
        return
    p = paleta()
    lineas = textwrap.wrap(titulo, width=max(int(fig.get_figwidth() * 10.5), 20))[:2]
    top = 0.80 - 0.07 * (len(lineas) - 1)
    fig.subplots_adjust(top=top, left=0.08, right=0.98, bottom=0.14)
    ax.text(0, 1.05, "\n".join(lineas), transform=ax.transAxes, fontsize=12, va="bottom", linespacing=1.05,
            color=p["tinta"], **fuente_mpl("titulares", weight="bold"))
    if kicker:
        alto_linea = 0.21 / max((top - 0.14) * fig.get_figheight(), 0.5)
        ax.text(0, 1.07 + alto_linea * len(lineas), kicker, transform=ax.transAxes, fontsize=8, va="bottom",
                color=p["azul"], **fuente_mpl("texto", weight="semibold"))


def _leyenda(ax, **extra):
    """Leyenda arriba a la derecha, fuera del area de datos (deja espacio arriba si no hay titulo)."""
    fig = ax.figure
    if not getattr(fig, "titulo", ""):
        fig.subplots_adjust(top=0.86)
    return ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.01), ncols=3, fontsize=8,
                     prop=fuente_mpl("texto") | {"size": 8}, handlelength=1.4, borderaxespad=0, frameon=False, **extra)


def _eje_dias(ax, fechas):
    dias = (pd.to_datetime(pd.Series(fechas)) - pd.Timedelta(minutes=1)).dt.normalize().drop_duplicates().sort_values()
    ax.set_xticks([d + pd.Timedelta(hours=12) for d in dias])
    ax.set_xticklabels([f"{ABREV[d.weekday()]} {d.day}" for d in dias])


def _fmt_soles(t, v):
    return f"{dia_y_hora(t)}\nS/ {v:,.1f} por MWh"


def _fmt_mw(t, v):
    return f"{dia_y_hora(t)}\n{v:,.0f} MW"


# ---------- precios ----------

def precio_semana(serie, umbrales, titulo="", kicker="Costo marginal · Santa Rosa 220 kV"):
    """Precio de la semana: linea azul sobre area celeste, el maximo en naranja."""
    p = paleta()
    fig, ax = _fig()
    x, y = serie["fecha_hora"], serie["valor"]
    ax.fill_between(x, y, color=p["celeste"], linewidth=0)
    ax.plot(x, y, color=p["azul"], linewidth=1.8)
    ax.axhline(umbrales["alto"], color=p["naranja"], linestyle=(0, (3, 3)), linewidth=1)
    ax.text(x.min(), umbrales["alto"], f" caro: más de S/ {umbrales['alto']}", color=p["naranja_texto"], fontsize=7.5,
            va="bottom", **fuente_mpl("texto"))
    imax = y.idxmax()
    ax.plot([x[imax]], [y[imax]], "o", color=p["naranja"], markersize=7, markeredgecolor="white", markeredgewidth=2)
    _eje_dias(ax, x)
    ax.yaxis.set_major_formatter(MILES)
    _encabezado(fig, ax, titulo, kicker)
    fig.hover.append((list(x), list(y), _fmt_soles))
    return fig


def perfil_horario(perfil, titulo="", kicker="Promedio por hora · S/ por MWh"):
    """Precio promedio por hora: barras celestes, la hora mas cara en naranja."""
    p = paleta()
    fig, ax = _fig()
    h, y = perfil["hora"], perfil["actual"]
    imax = int(y.idxmax())
    colores = [p["naranja"] if i == imax else p["azul_claro"] for i in range(len(y))]
    ax.bar(h, y, color=colores, width=0.72)
    if perfil["anterior"].notna().any():
        ax.plot(h, perfil["anterior"], color=p["tinta"], linewidth=1.2, linestyle=(0, (2, 2)), label="Semana anterior")
        _leyenda(ax)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f"{x} h" for x in range(0, 24, 3)])
    ax.set_xlim(-0.6, 23.6)
    ax.yaxis.set_major_formatter(MILES)
    _encabezado(fig, ax, titulo, kicker)
    fig.hover.append((list(h), list(y), lambda hh, v: f"{int(hh)}:00 h\nS/ {v:,.1f} por MWh"))
    return fig


def ahora(serie_hoy, serie_ayer, titulo="", umbrales=None, kicker="Tiempo real · preliminar"):
    """La curva de hoy (azul) frente a la de ayer (gris claro), en el mismo reloj."""
    p = paleta()
    fig, ax = _fig()
    if len(serie_ayer):
        corrida = serie_ayer["fecha_hora"] + pd.Timedelta(days=1)
        ax.plot(corrida, serie_ayer["valor"], color=AYER, linewidth=2, label="Ayer")
    if len(serie_hoy):
        x, y = serie_hoy["fecha_hora"], serie_hoy["valor"]
        ax.plot(x, y, color=p["azul"], linewidth=2.6, label="Hoy")
        ax.plot([x.iloc[-1]], [y.iloc[-1]], "o", color=p["naranja"], markersize=9, markeredgecolor="white",
                markeredgewidth=2.5)
        fig.hover.append((list(x), list(y), _fmt_soles))
        dia = (x.iloc[-1] - pd.Timedelta(minutes=1)).normalize()
        ax.set_xlim(dia, dia + pd.Timedelta(days=1))
        ax.set_xticks([dia + pd.Timedelta(hours=h) for h in range(0, 25, 6)])
        ax.set_xticklabels([f"{h} h" for h in range(0, 25, 6)])
    ax.yaxis.set_major_formatter(MILES)
    _leyenda(ax)
    _encabezado(fig, ax, titulo, kicker)
    del umbrales
    return fig


def sparkline(serie, ancho=2.6, alto=0.8):
    """Mini curva para tarjetas."""
    preparar_matplotlib()
    p = paleta()
    fig = Figure(figsize=(ancho, alto), dpi=110)
    fig.patch.set_facecolor(p["blanco"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    if len(serie):
        ax.plot(range(len(serie)), list(serie), color=p["azul"], linewidth=2)
    fig.hover = []
    fig.titulo = ""
    return fig


# ---------- demanda ----------

def demanda(serie, titulo="", kicker="Demanda del SEIN · MW"):
    """Consumo real (azul) frente a lo programado (gris), con el pico en naranja."""
    p = paleta()
    fig, ax = _fig()
    x = serie["fecha_hora"]
    ax.plot(x, serie["prog_diaria"], color=AYER, linewidth=1.6, label="Lo programado")
    ax.plot(x, serie["ejecutada"], color=p["azul"], linewidth=1.9, label="Consumo real")
    imax = serie["ejecutada"].idxmax()
    ax.plot([x[imax]], [serie.loc[imax, "ejecutada"]], "o", color=p["naranja"], markersize=7, markeredgecolor="white",
            markeredgewidth=2)
    _eje_dias(ax, x)
    ax.yaxis.set_major_formatter(MILES)
    _leyenda(ax)
    _encabezado(fig, ax, titulo, kicker)
    fig.hover.append((list(x), list(serie["ejecutada"]), _fmt_mw))
    return fig


# ---------- generacion ----------

def generacion(serie, titulo="", kicker="Generación por tecnología · MW"):
    """Generacion apilada con un color fijo por tecnologia."""
    proyecto = config.proyecto()
    ancho = serie.pivot_table(index="fecha_hora", columns="tecnologia", values="valor", aggfunc="sum").fillna(0).clip(lower=0)
    tecs = [t for t in proyecto["orden_tecnologias"] if t in ancho and ancho[t].sum() > 0]
    fig, ax = _fig()
    ax.stackplot(ancho.index, *[ancho[t] for t in tecs], colors=[config.color_tecnologia(t) for t in tecs],
                 labels=[config.nombre_tecnologia(t) for t in tecs], linewidth=0)
    _eje_dias(ax, ancho.index)
    ax.yaxis.set_major_formatter(MILES)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncols=len(tecs), fontsize=8, frameon=False,
              prop=fuente_mpl("texto") | {"size": 8})
    _encabezado(fig, ax, titulo, kicker)
    fig.subplots_adjust(bottom=0.22)
    total = ancho.sum(axis=1)
    fig.hover.append((list(ancho.index), list(total), lambda t, v: f"{dia_y_hora(t)}\nTotal: {v:,.0f} MW"))
    return fig


def mix(participaciones, anterior, titulo="", kicker="% de la energía de la semana"):
    """Barras horizontales: esta semana en color; la marca oscura es la semana anterior."""
    p = paleta()
    tecs = [t for t in sorted(participaciones, key=participaciones.get) if participaciones[t] >= 0.001]
    fig, ax = _fig(alto=2.6)
    y = np.arange(len(tecs))
    ax.barh(y, [100] * len(tecs), height=0.42, color=GRILLA)
    ax.barh(y, [participaciones[t] * 100 for t in tecs], height=0.42, color=[config.color_tecnologia(t) for t in tecs])
    if anterior:
        ax.scatter([anterior.get(t, 0) * 100 for t in tecs], y, marker="|", s=170, color=p["tinta"], zorder=3,
                   label="Semana anterior")
        _leyenda(ax)
    for i, t in enumerate(tecs):
        ax.text(101.5, i, f"{participaciones[t] * 100:.1f}%", va="center", fontsize=9, color=p["tinta"],
                **fuente_mpl("texto", weight="bold"))
    ax.set_yticks(y)
    ax.set_yticklabels([config.nombre_tecnologia(t) for t in tecs], fontsize=9)
    ax.set_xlim(0, 114)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    _encabezado(fig, ax, titulo, kicker)
    fig.subplots_adjust(left=0.22)
    return fig


# ---------- hidrologia ----------

def embalses(serie, titulo="", kicker="Agua útil en embalses · Hm3"):
    """Volumen total por dia."""
    hidro = config.color_tecnologia("hidro")
    fig, ax = _fig()
    etiquetas = [f"{ABREV[d.weekday()]} {d.day}" for d in serie["fecha"]]
    x = np.arange(len(serie))
    ax.fill_between(x, serie["valor"], serie["valor"].min() * 0.98, color=hidro, alpha=0.15, linewidth=0)
    ax.plot(x, serie["valor"], color=hidro, linewidth=2.4, marker="o", markersize=5, markeredgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    ax.yaxis.set_major_formatter(MILES)
    _encabezado(fig, ax, titulo, kicker)
    fig.hover.append((list(x), list(serie["valor"]), lambda i, v: f"{etiquetas[int(round(i))]}\n{v:,.1f} Hm3"))
    return fig


def embalses_detalle(detalle, titulo="", n=8, kicker="Embalses con más agua · Hm3"):
    """Los n embalses con mas agua: esta semana (azul) y la anterior (marca oscura)."""
    p = paleta()
    top = detalle.dropna(subset=["actual"]).nlargest(n, "actual").iloc[::-1]
    fig, ax = _fig(alto=3.0)
    y = np.arange(len(top))
    ax.barh(y, top["actual"], height=0.5, color=config.color_tecnologia("hidro"))
    ax.scatter(top["anterior"].fillna(0), y, marker="|", s=170, color=p["tinta"], zorder=3, label="Semana anterior")
    ax.set_yticks(y)
    ax.set_yticklabels(top["entidad"].str.title(), fontsize=8.5)
    ax.grid(axis="x", color=GRILLA, linewidth=1)
    ax.grid(axis="y", visible=False)
    _leyenda(ax)
    _encabezado(fig, ax, titulo, kicker)
    fig.subplots_adjust(left=0.3)
    return fig


# ---------- mapa ----------

def _contorno_peru():
    datos = json.loads((DIR_MAPAS / "peru.geo.json").read_text(encoding="utf-8"))
    geom = datos["features"][0]["geometry"]
    anillos = geom["coordinates"] if geom["type"] == "Polygon" else [r for poli in geom["coordinates"] for r in poli]
    return [np.array(anillo) for anillo in anillos]


def mapa(cmg_barras, titulo="", kicker="Precio promedio semanal por barra"):
    """Peru con cada barra coloreada por su costo marginal (azul barato, naranja caro)."""
    p = paleta()
    fig, ax = _fig(ancho=4.6, alto=5.6)
    for anillo in _contorno_peru():
        ax.fill(anillo[:, 0], anillo[:, 1], color="#EEF3F9", zorder=1)
        ax.plot(anillo[:, 0], anillo[:, 1], color=p["linea"], linewidth=1.2, zorder=2)
    barras = cmg_barras.dropna(subset=["latitud", "longitud"])
    if len(barras):
        escala = LinearSegmentedColormap.from_list("precio", [p["azul"], "#F5C518", p["naranja"]])
        puntos = ax.scatter(barras["longitud"], barras["latitud"], c=barras["cmg_promedio"], cmap=escala, s=42,
                            edgecolors="white", linewidths=0.8, zorder=3)
        barra_color = fig.colorbar(puntos, ax=ax, shrink=0.5, pad=0.02)
        barra_color.outline.set_visible(False)
        barra_color.ax.tick_params(labelsize=7, colors=p["gris"], length=0)
        barra_color.set_label("S/ por MWh", fontsize=8, color=p["gris"])
        for _, fila in pd.concat([barras.nsmallest(1, "cmg_promedio"), barras.nlargest(2, "cmg_promedio")]).iterrows():
            ax.annotate(f"{fila['barra'].title()}\nS/ {fila['cmg_promedio']:,.0f}", (fila["longitud"], fila["latitud"]),
                        xytext=(7, 4), textcoords="offset points", fontsize=7.5, color=p["tinta"],
                        **fuente_mpl("texto", weight="semibold"))
        fig.hover.append((list(barras["longitud"]), list(barras["latitud"]), None))
        fig.hover_mapa = barras.reset_index(drop=True)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for lado in ax.spines.values():
        lado.set_visible(False)
    _encabezado(fig, ax, titulo, kicker)
    fig.subplots_adjust(top=0.82 if titulo else 0.97, left=0.02, right=0.95, bottom=0.02)
    return fig


# ---------- utilidades ----------

def a_png(fig, dpi=200):
    """Figure -> BytesIO PNG (para el PDF)."""
    import io
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    plt.close("all")
    buffer.seek(0)
    return buffer


# ---------- evolucion (rango libre) ----------

def evolucion_diaria(dia, unidad="S/", titulo="", kicker=""):
    """Promedio diario (linea azul), banda entre minimo y maximo, punta (naranja) y promedio del periodo.

    Los dias sin datos quedan en blanco (no se unen con una linea). Los dias que no estan
    todos confirmados llevan un punto hueco.
    """
    p = paleta()
    fig, ax = _fig()
    if dia.empty:
        return fig
    completo = dia.set_index(pd.to_datetime(dia["fecha"])).reindex(
        pd.date_range(pd.to_datetime(dia["fecha"]).min(), pd.to_datetime(dia["fecha"]).max(), freq="D"))
    x = completo.index
    ax.fill_between(x, completo["minimo"], completo["maximo"], color=p["celeste"], linewidth=0, label="Mínimo a máximo")
    ax.plot(x, completo["punta"], color=p["naranja"], linewidth=1.4, label="Punta (6 a 11 p. m.)")
    ax.plot(x, completo["promedio"], color=p["azul"], linewidth=2.2, label="Promedio del día")
    prelim = completo[completo["confirmado"] == False]  # noqa: E712
    if len(prelim):
        ax.plot(prelim.index, prelim["promedio"], "o", markerfacecolor="white", markeredgecolor=p["azul"], markersize=5,
                label="Preliminar")
    media = dia["promedio"].mean()
    ax.axhline(media, color=p["tinta"], linestyle=(0, (3, 3)), linewidth=1)
    ax.text(x.max(), media, f" prom. {media:,.0f}", color=p["tinta"], fontsize=8, va="bottom", ha="right",
            **fuente_mpl("texto", weight="semibold"))
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{mdates.num2date(v).day}/{mdates.num2date(v).month}"))
    ax.yaxis.set_major_formatter(MILES)
    fig.subplots_adjust(top=0.86)
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.01), ncols=4, fontsize=8, frameon=False,
              prop=fuente_mpl("texto") | {"size": 8})
    _encabezado(fig, ax, titulo, kicker)
    validos = completo.dropna(subset=["promedio"])
    fig.hover.append((list(validos.index), list(validos["promedio"]),
                      lambda t, v: f"{pd.Timestamp(t):%d/%m/%Y}\nPromedio: {unidad} {v:,.1f} por MWh"))
    return fig


def mapa_calor(matriz, unidad="S/", titulo="", kicker=""):
    """Dias (filas) por media hora (columnas); color = precio. Muestra de un vistazo dias y horas caras."""
    p = paleta()
    alto = min(max(2.4, 0.11 * len(matriz) + 1.0), 7.5)
    fig, ax = _fig(alto=alto)
    if matriz.empty:
        return fig
    escala = LinearSegmentedColormap.from_list("calor", ["#EAF2FB", p["azul_claro"], "#F5C518", p["naranja"], "#B23A22"])
    imagen = ax.imshow(matriz.values, aspect="auto", cmap=escala, interpolation="nearest")
    ax.set_xticks([0, 12, 24, 36, 47])
    ax.set_xticklabels(["0 h", "6 h", "12 h", "18 h", "24 h"])
    paso = max(1, len(matriz) // 10)
    ax.set_yticks(range(0, len(matriz), paso))
    ax.set_yticklabels([f"{f.day}/{f.month}" for f in matriz.index[::paso]], fontsize=7.5)
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    barra = fig.colorbar(imagen, ax=ax, pad=0.01, fraction=0.035)
    barra.outline.set_visible(False)
    barra.ax.tick_params(labelsize=7, colors=p["gris"], length=0)
    barra.set_label(f"{unidad} por MWh", fontsize=8, color=p["gris"])
    _encabezado(fig, ax, titulo, kicker)
    fig.subplots_adjust(left=0.07, right=0.97, bottom=0.08)
    fig.hover = [("calor", None, None)]
    fig.hover_calor = matriz
    return fig


def mensual_barras(mes, unidad="S/", titulo="", kicker=""):
    """Promedio por mes (azul) y su punta (naranja)."""
    p = paleta()
    fig, ax = _fig(alto=2.6)
    if mes.empty:
        return fig
    x = np.arange(len(mes))
    nombres = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]
    etiquetas = [f"{nombres[m.month - 1]} {str(m.year)[2:]}" for m in mes["mes"]]
    ax.bar(x - 0.18, mes["promedio"], width=0.36, color=p["azul"], label="Promedio")
    ax.bar(x + 0.18, mes["punta"], width=0.36, color=p["naranja"], label="Punta")
    for i, v in enumerate(mes["promedio"]):
        ax.text(i - 0.18, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=7.5, color=p["tinta"],
                **fuente_mpl("texto", weight="semibold"))
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    ax.yaxis.set_major_formatter(MILES)
    _leyenda(ax)
    _encabezado(fig, ax, titulo, kicker)
    fig.hover.append((list(x), list(mes["promedio"]),
                      lambda i, v: f"{etiquetas[int(round(i))]}\nPromedio: {unidad} {v:,.1f} por MWh"))
    return fig
