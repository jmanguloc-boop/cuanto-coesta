"""Graficos editoriales (matplotlib) compartidos por la app de escritorio y el PDF.

Cada funcion devuelve una Figure. Ademas, fig.hover guarda las series que la app de
escritorio usa para mostrar el valor al pasar el mouse: lista de (x, y, formato).
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

ABREV = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
MILES = FuncFormatter(lambda v, _: f"{v:,.0f}")


def _fig(ancho=7.2, alto=2.8, oscuro=False):
    preparar_matplotlib()
    p = paleta()
    fig = Figure(figsize=(ancho, alto), dpi=110)
    ax = fig.add_subplot(111)
    fondo = p["tinta"] if oscuro else p["blanco"]
    fig.patch.set_facecolor(fondo)
    ax.set_facecolor(fondo)
    tick = "#9A9C92" if oscuro else p["gris"]
    ax.tick_params(colors=tick, labelsize=7.5, length=0)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(p["mineral"] if oscuro else p["linea"])
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.grid(axis="y", color=p["mineral"] if oscuro else "#E3E4DA", linewidth=0.6, linestyle=(0, (3, 4)))
    ax.set_axisbelow(True)
    for etiqueta in ax.get_xticklabels() + ax.get_yticklabels():
        etiqueta.set_fontfamily(fuente_mpl("mono")["family"])
    fig.hover = []
    return fig, ax


def _encabezado(fig, ax, titulo, kicker="", oscuro=False):
    """Kicker en mono (ej. 'PRECIO / HORA') y titular condensado que dice la conclusion."""
    p = paleta()
    # Titulos largos en dos lineas segun el ancho de la figura (~9 caracteres por pulgada)
    lineas = textwrap.wrap(titulo, width=max(int(fig.get_figwidth() * 9), 20))[:2]
    alto_linea = 0.30 / fig.get_figheight()          # alto de una linea del titular en coordenadas del eje
    ax.text(0, 1.06, "\n".join(lineas), transform=ax.transAxes, fontsize=13.5, va="bottom", linespacing=1.0,
            color=p["blanco"] if oscuro else p["tinta"], **fuente_mpl("titulares", weight="bold"))
    if kicker:
        ax.text(0, 1.08 + alto_linea * len(lineas), kicker.upper(), transform=ax.transAxes, fontsize=7.5, va="bottom",
                color=p["lima"] if oscuro else p["verde"], **fuente_mpl("mono"))
    fig.subplots_adjust(top=0.78 - 0.07 * (len(lineas) - 1), left=0.08, right=0.98, bottom=0.14)


def _leyenda(ax, oscuro=False, **extra):
    """Leyenda arriba a la derecha, fuera del area de datos (no tapa curvas)."""
    leyenda = ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.01), ncols=3, fontsize=7,
                        prop=fuente_mpl("mono") | {"size": 7}, handlelength=1.6, borderaxespad=0, **extra)
    if oscuro:
        for texto in leyenda.get_texts():
            texto.set_color("#C1C7B8")
    return leyenda


def _eje_dias(ax, fechas):
    dias = (pd.to_datetime(pd.Series(fechas)) - pd.Timedelta(minutes=1)).dt.normalize().drop_duplicates().sort_values()
    ax.set_xticks([d + pd.Timedelta(hours=12) for d in dias])
    ax.set_xticklabels([f"{ABREV[d.weekday()]} {d.day}/{d.month}" for d in dias])


def _fmt_soles(t, v):
    return f"{dia_y_hora(t)}\nS/ {v:,.1f} por MWh"


def _fmt_mw(t, v):
    return f"{dia_y_hora(t)}\n{v:,.0f} MW"


# ---------- precios ----------

def precio_semana(serie, umbrales, titulo, kicker="Costo marginal / Santa Rosa 220 kV"):
    """Costo marginal de la semana: linea verde sobre area lima, con umbrales."""
    p = paleta()
    fig, ax = _fig()
    x, y = serie["fecha_hora"], serie["valor"]
    ax.fill_between(x, y, color=p["lima"], alpha=0.45, linewidth=0)
    ax.plot(x, y, color=p["verde"], linewidth=1.6)
    for nivel, color, texto in ((umbrales["alto"], p["cobre"], "PRECIO ALTO"), (umbrales["bajo"], p["verde"], "PRECIO BAJO")):
        ax.axhline(nivel, color=color, linestyle=(0, (2, 3)), linewidth=0.9)
        ax.text(x.min(), nivel, f" {texto} · S/ {nivel}", color=color, fontsize=6.5, va="bottom", **fuente_mpl("mono"))
    imax = y.idxmax()
    ax.plot([x[imax]], [y[imax]], "o", color=p["cobre"], markersize=5)
    _eje_dias(ax, x)
    ax.yaxis.set_major_formatter(MILES)
    _encabezado(fig, ax, titulo, kicker)
    fig.hover.append((list(x), list(y), _fmt_soles))
    return fig


def perfil_horario(perfil, titulo, kicker="Un día, 24 señales · S/ por MWh"):
    """Precio promedio por hora: area lima + linea verde; la semana anterior punteada."""
    p = paleta()
    fig, ax = _fig()
    h, y = perfil["hora"], perfil["actual"]
    if perfil["anterior"].notna().any():
        ax.plot(h, perfil["anterior"], color=p["gris"], linewidth=1.1, linestyle=(0, (2, 2)), label="Semana anterior")
    ax.fill_between(h, y, color=p["lima"], alpha=0.45, linewidth=0)
    ax.plot(h, y, color=p["verde"], linewidth=2.2, label="Esta semana")
    imax = y.idxmax()
    ax.plot([h[imax]], [y[imax]], "o", color=p["cobre"], markersize=6)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f"{x:02d}" for x in range(0, 24, 3)])
    ax.set_xlim(0, 23)
    ax.yaxis.set_major_formatter(MILES)
    _leyenda(ax)
    _encabezado(fig, ax, titulo, kicker)
    fig.hover.append((list(h), list(y), lambda hh, v: f"{int(hh):02d}:00 h\nS/ {v:,.1f} por MWh (promedio)"))
    return fig


def ahora(serie_hoy, serie_ayer, titulo, umbrales=None, kicker="En vivo · tiempo real · preliminar"):
    """Instrumento oscuro: la curva de hoy (lima) frente a la de ayer (gris), en el mismo reloj."""
    p = paleta()
    fig, ax = _fig(oscuro=True)
    if len(serie_ayer):
        corrida = serie_ayer["fecha_hora"] + pd.Timedelta(days=1)
        ax.plot(corrida, serie_ayer["valor"], color="#8A8D82", linewidth=1.2, linestyle=(0, (2, 2)), label="Ayer")
    if len(serie_hoy):
        x, y = serie_hoy["fecha_hora"], serie_hoy["valor"]
        ax.plot(x, y, color=p["lima"], linewidth=2.2, label="Hoy")
        ax.plot([x.iloc[-1]], [y.iloc[-1]], "o", color=p["cobre"], markersize=7)
        fig.hover.append((list(x), list(y), _fmt_soles))
        dia = (x.iloc[-1] - pd.Timedelta(minutes=1)).normalize()
        ax.set_xlim(dia, dia + pd.Timedelta(days=1))
        ax.set_xticks([dia + pd.Timedelta(hours=h) for h in range(0, 25, 3)])
        ax.set_xticklabels([f"{h:02d}" for h in range(0, 25, 3)])
    if umbrales:
        ax.axhline(umbrales["alto"], color=p["cobre"], linestyle=(0, (2, 3)), linewidth=0.8)
    ax.yaxis.set_major_formatter(MILES)
    _leyenda(ax, oscuro=True)
    _encabezado(fig, ax, titulo, kicker, oscuro=True)
    return fig


def sparkline(serie, ancho=2.6, alto=0.8):
    """Mini curva lima sobre carbon para la caja de precio."""
    preparar_matplotlib()
    p = paleta()
    fig = Figure(figsize=(ancho, alto), dpi=110)
    fig.patch.set_facecolor(p["tinta"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(p["tinta"])
    ax.axis("off")
    if len(serie):
        ax.plot(range(len(serie)), list(serie), color=p["lima"], linewidth=1.8)
    fig.hover = []
    return fig


# ---------- demanda ----------

def demanda(serie, titulo, kicker="Demanda del SEIN · MW"):
    """Consumo real (carbon) frente a lo programado (gris punteado), con el pico marcado."""
    p = paleta()
    fig, ax = _fig()
    x = serie["fecha_hora"]
    ax.plot(x, serie["prog_diaria"], color=p["gris"], linewidth=1, linestyle=(0, (2, 2)), label="Lo programado")
    ax.plot(x, serie["ejecutada"], color=p["tinta"], linewidth=1.6, label="Consumo real")
    imax = serie["ejecutada"].idxmax()
    ax.plot([x[imax]], [serie.loc[imax, "ejecutada"]], "o", color=p["cobre"], markersize=6)
    ax.annotate(f"PICO {serie.loc[imax, 'ejecutada']:,.0f} MW", (x[imax], serie.loc[imax, "ejecutada"]),
                xytext=(0, 9), textcoords="offset points", ha="center", fontsize=7, color=p["cobre"], **fuente_mpl("mono"))
    _eje_dias(ax, x)
    ax.yaxis.set_major_formatter(MILES)
    _leyenda(ax)
    _encabezado(fig, ax, titulo, kicker)
    fig.hover.append((list(x), list(serie["ejecutada"]), _fmt_mw))
    return fig


# ---------- generacion ----------

def generacion(serie, titulo, kicker="Generación por tecnología · MW"):
    """Generacion apilada con un color fijo por tecnologia."""
    proyecto = config.proyecto()
    ancho = serie.pivot_table(index="fecha_hora", columns="tecnologia", values="valor", aggfunc="sum").fillna(0).clip(lower=0)
    tecs = [t for t in proyecto["orden_tecnologias"] if t in ancho and ancho[t].sum() > 0]
    fig, ax = _fig()
    ax.stackplot(ancho.index, *[ancho[t] for t in tecs], colors=[config.color_tecnologia(t) for t in tecs],
                 labels=[config.nombre_tecnologia(t) for t in tecs], linewidth=0)
    _eje_dias(ax, ancho.index)
    ax.yaxis.set_major_formatter(MILES)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncols=len(tecs), fontsize=7,
              prop=fuente_mpl("mono") | {"size": 7})
    _encabezado(fig, ax, titulo, kicker)
    fig.subplots_adjust(bottom=0.22)
    total = ancho.sum(axis=1)
    fig.hover.append((list(ancho.index), list(total), lambda t, v: f"{dia_y_hora(t)}\nTotal: {v:,.0f} MW"))
    return fig


def mix(participaciones, anterior, titulo, kicker="Mix · % de la energía"):
    """Barras horizontales tipo pista (como la maqueta): esta semana en color, la anterior en gris."""
    p = paleta()
    tecs = [t for t in sorted(participaciones, key=participaciones.get) if participaciones[t] >= 0.001]
    fig, ax = _fig(alto=2.6)
    y = np.arange(len(tecs))
    ax.barh(y, [100] * len(tecs), height=0.32, color="#E3E4DA")
    ax.barh(y, [participaciones[t] * 100 for t in tecs], height=0.32, color=[config.color_tecnologia(t) for t in tecs])
    if anterior:
        ax.scatter([anterior.get(t, 0) * 100 for t in tecs], y, marker="|", s=160, color=p["tinta"], zorder=3,
                   label="Semana anterior")
        _leyenda(ax)
    for i, t in enumerate(tecs):
        ax.text(101, i, f"{participaciones[t] * 100:.1f}%", va="center", fontsize=8, color=p["tinta"],
                **fuente_mpl("mono", weight="bold"))
    ax.set_yticks(y)
    ax.set_yticklabels([config.nombre_tecnologia(t) for t in tecs], fontsize=8)
    ax.set_xlim(0, 112)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    _encabezado(fig, ax, titulo, kicker)
    fig.subplots_adjust(left=0.2)
    return fig


# ---------- hidrologia ----------

def embalses(serie, titulo, kicker="Agua útil en embalses · Hm3"):
    """Volumen total por dia."""
    p = paleta()
    fig, ax = _fig()
    etiquetas = [f"{ABREV[d.weekday()]} {d.day}/{d.month}" for d in serie["fecha"]]
    x = np.arange(len(serie))
    ax.fill_between(x, serie["valor"], serie["valor"].min() * 0.98, color=config.color_tecnologia("hidro"), alpha=0.18)
    ax.plot(x, serie["valor"], color=config.color_tecnologia("hidro"), linewidth=2, marker="o", markersize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas)
    ax.yaxis.set_major_formatter(MILES)
    _encabezado(fig, ax, titulo, kicker)
    fig.hover.append((list(x), list(serie["valor"]), lambda i, v: f"{etiquetas[int(round(i))]}\n{v:,.1f} Hm3"))
    return fig


def embalses_detalle(detalle, titulo, n=8, kicker="Embalses con más agua · Hm3"):
    """Los n embalses con mas agua: esta semana (azul) y la anterior (marca)."""
    p = paleta()
    top = detalle.dropna(subset=["actual"]).nlargest(n, "actual").iloc[::-1]
    fig, ax = _fig(alto=3.0)
    y = np.arange(len(top))
    ax.barh(y, top["actual"], height=0.45, color=config.color_tecnologia("hidro"))
    ax.scatter(top["anterior"].fillna(0), y, marker="|", s=160, color=p["tinta"], zorder=3, label="Semana anterior")
    ax.set_yticks(y)
    ax.set_yticklabels(top["entidad"].str.title(), fontsize=7.5)
    ax.grid(axis="x", color="#E3E4DA", linewidth=0.6)
    ax.grid(axis="y", visible=False)
    _leyenda(ax)
    _encabezado(fig, ax, titulo, kicker)
    fig.subplots_adjust(left=0.28)
    return fig


# ---------- mapa ----------

def _contorno_peru():
    datos = json.loads((DIR_MAPAS / "peru.geo.json").read_text(encoding="utf-8"))
    geom = datos["features"][0]["geometry"]
    anillos = geom["coordinates"] if geom["type"] == "Polygon" else [r for poli in geom["coordinates"] for r in poli]
    return [np.array(anillo) for anillo in anillos]


def mapa(cmg_barras, titulo, kicker="El mapa del costo · promedio semanal por barra"):
    """Peru con cada barra coloreada por su costo marginal promedio (verde barato, cobre caro)."""
    p = paleta()
    fig, ax = _fig(ancho=4.6, alto=5.6)
    for anillo in _contorno_peru():
        ax.fill(anillo[:, 0], anillo[:, 1], color="#E7E6DC", zorder=1)
        ax.plot(anillo[:, 0], anillo[:, 1], color=p["gris"], linewidth=0.8, zorder=2)
    barras = cmg_barras.dropna(subset=["latitud", "longitud"])
    if len(barras):
        escala = LinearSegmentedColormap.from_list("cobre", [p["verde"], p["lima"], p["cobre"]])
        puntos = ax.scatter(barras["longitud"], barras["latitud"], c=barras["cmg_promedio"], cmap=escala, s=34,
                            edgecolors=p["tinta"], linewidths=0.4, zorder=3)
        barra_color = fig.colorbar(puntos, ax=ax, shrink=0.5, pad=0.02)
        barra_color.ax.tick_params(labelsize=6.5, colors=p["gris"])
        barra_color.set_label("S/ por MWh", fontsize=7, color=p["gris"])
        for _, fila in pd.concat([barras.nsmallest(1, "cmg_promedio"), barras.nlargest(2, "cmg_promedio")]).iterrows():
            ax.annotate(f"{fila['barra'].title()}\nS/ {fila['cmg_promedio']:,.0f}", (fila["longitud"], fila["latitud"]),
                        xytext=(6, 4), textcoords="offset points", fontsize=6.5, color=p["tinta"], **fuente_mpl("mono"))
        fig.hover.append((list(barras["longitud"]), list(barras["latitud"]),
                          None))  # el mapa usa su propio texto de hover
        fig.hover_mapa = barras.reset_index(drop=True)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for lado in ax.spines.values():
        lado.set_visible(False)
    _encabezado(fig, ax, titulo, kicker)
    fig.subplots_adjust(top=0.82, left=0.02, right=0.95, bottom=0.02)
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
