"""Graficos matplotlib para el PDF, con la misma paleta y colores por tecnologia que el dashboard."""

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from src.utils import config  # noqa: E402

ABREV = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MILES = FuncFormatter(lambda v, _: f"{v:,.0f}")


def _paleta():
    return config.proyecto()["paleta"]


def _figura(ancho_mm=180, alto_mm=70):
    p = _paleta()
    fig, ax = plt.subplots(figsize=(ancho_mm / 25.4, alto_mm / 25.4), dpi=200)
    fig.patch.set_facecolor(p["fondo"])
    ax.set_facecolor(p["fondo"])
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#C9D1D9")
    ax.tick_params(colors=p["texto_suave"], labelsize=7)
    ax.grid(axis="y", color="#EEF1F4", linewidth=0.6)
    ax.set_axisbelow(True)
    return fig, ax


def _titulo(ax, texto):
    ax.set_title(texto, loc="left", fontsize=10, fontweight="bold", color=_paleta()["texto"], pad=8)


def _eje_dias(ax, fechas):
    # La medianoche que cierra el ultimo dia no es un dia nuevo
    dias = (pd.to_datetime(pd.Series(fechas)) - pd.Timedelta(minutes=1)).dt.normalize().drop_duplicates().sort_values()
    ax.set_xticks(list(dias))
    ax.set_xticklabels([f"{ABREV[d.weekday()]} {d.day}/{d.month}" for d in dias])


def _png(fig):
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    buffer.seek(0)
    return buffer


def precio_semana(serie, umbrales, titulo):
    """PNG del costo marginal de la semana."""
    p = _paleta()
    fig, ax = _figura(alto_mm=62)
    ax.plot(serie["fecha_hora"], serie["valor"], color=p["secundario"], linewidth=1.2)
    for nivel, color, texto in ((umbrales["alto"], p["sube"], "precio alto"), (umbrales["bajo"], p["baja"], "precio bajo")):
        ax.axhline(nivel, color=color, linestyle=":", linewidth=0.8)
        ax.text(serie["fecha_hora"].min(), nivel, f" {texto} (S/ {nivel})", color=color, fontsize=6, va="bottom")
    _eje_dias(ax, serie["fecha_hora"])
    ax.yaxis.set_major_formatter(MILES)
    ax.set_ylabel("S/ por MWh", fontsize=7, color=p["texto_suave"])
    _titulo(ax, titulo)
    return _png(fig)


def perfil_horario(perfil, titulo):
    """PNG del precio por hora."""
    p = _paleta()
    fig, ax = _figura(alto_mm=52)
    ax.bar(perfil["hora"], perfil["actual"], color=p["secundario"], width=0.75, label="Esta semana")
    if perfil["anterior"].notna().any():
        ax.plot(perfil["hora"], perfil["anterior"], color=p["texto_suave"], linestyle=":", linewidth=1.2,
                label="Semana anterior")
        ax.legend(fontsize=6.5, frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0), ncols=2)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f"{h} h" for h in range(0, 24, 3)])
    ax.yaxis.set_major_formatter(MILES)
    ax.set_ylabel("S/ por MWh", fontsize=7, color=p["texto_suave"])
    _titulo(ax, titulo)
    return _png(fig)


def demanda(serie, titulo):
    """PNG de demanda real vs programada."""
    p = _paleta()
    fig, ax = _figura(alto_mm=72)
    ax.plot(serie["fecha_hora"], serie["prog_diaria"], color=p["texto_suave"], linestyle=":", linewidth=0.9,
            label="Lo programado")
    ax.plot(serie["fecha_hora"], serie["ejecutada"], color=p["primario"], linewidth=1.4, label="Consumo real")
    imax = serie["ejecutada"].idxmax()
    ax.annotate(f"Pico: {serie.loc[imax, 'ejecutada']:,.0f} MW", (serie.loc[imax, "fecha_hora"], serie.loc[imax, "ejecutada"]),
                xytext=(0, 8), textcoords="offset points", ha="center", fontsize=7, color=p["acento"], fontweight="bold")
    _eje_dias(ax, serie["fecha_hora"])
    ax.yaxis.set_major_formatter(MILES)
    ax.set_ylabel("MW", fontsize=7, color=p["texto_suave"])
    ax.legend(fontsize=6.5, frameon=False, loc="lower left", ncols=2)
    _titulo(ax, titulo)
    return _png(fig)


def generacion(serie, titulo):
    """PNG de generacion por tecnologia."""
    p = _paleta()
    proyecto = config.proyecto()
    ancho = serie.pivot_table(index="fecha_hora", columns="tecnologia", values="valor", aggfunc="sum").fillna(0).clip(lower=0)
    tecs = [t for t in proyecto["orden_tecnologias"] if t in ancho and ancho[t].sum() > 0]
    fig, ax = _figura(alto_mm=72)
    ax.stackplot(ancho.index, *[ancho[t] for t in tecs], colors=[config.color_tecnologia(t) for t in tecs],
                 labels=[config.nombre_tecnologia(t) for t in tecs], linewidth=0)
    _eje_dias(ax, ancho.index)
    ax.yaxis.set_major_formatter(MILES)
    ax.set_ylabel("MW", fontsize=7, color=p["texto_suave"])
    ax.legend(fontsize=6.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncols=len(tecs))
    _titulo(ax, titulo)
    return _png(fig)


def mix(participaciones, anterior, titulo):
    """PNG de participacion por tecnologia."""
    p = _paleta()
    tecs = [t for t in sorted(participaciones, key=participaciones.get) if participaciones[t] >= 0.001]
    fig, ax = _figura(alto_mm=52)
    y = range(len(tecs))
    if anterior:
        ax.barh([i - 0.2 for i in y], [anterior.get(t, 0) * 100 for t in tecs], height=0.35, color="#D5DCE3")
    barras = ax.barh([i + 0.15 for i in y], [participaciones[t] * 100 for t in tecs], height=0.35,
                     color=[config.color_tecnologia(t) for t in tecs])
    for barra, t in zip(barras, tecs, strict=True):
        ax.text(barra.get_width() + 0.5, barra.get_y() + barra.get_height() / 2, f"{participaciones[t] * 100:.1f}%",
                va="center", fontsize=6.5, color=p["texto"])
    ax.set_yticks(list(y))
    ax.set_yticklabels([config.nombre_tecnologia(t) for t in tecs])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.grid(axis="x", color="#EEF1F4", linewidth=0.6)
    ax.grid(axis="y", visible=False)
    _titulo(ax, titulo)
    return _png(fig)


def embalses(serie, titulo):
    """PNG del volumen de embalses por dia."""
    p = _paleta()
    fig, ax = _figura(alto_mm=60)
    etiquetas = [f"{ABREV[d.weekday()]} {d.day}/{d.month}" for d in serie["fecha"]]
    ax.plot(etiquetas, serie["valor"], color=config.color_tecnologia("hidro"), linewidth=1.6, marker="o", markersize=3)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_ylabel("Hm3", fontsize=7, color=p["texto_suave"])
    _titulo(ax, titulo)
    return _png(fig)


def embalses_detalle(detalle, titulo, n=8):
    """PNG de los embalses con mas agua."""
    top = detalle.dropna(subset=["actual"]).nlargest(n, "actual").iloc[::-1]
    fig, ax = _figura(alto_mm=62)
    y = range(len(top))
    ax.barh([i - 0.2 for i in y], top["anterior"].fillna(0), height=0.35, color="#D5DCE3", label="Semana anterior")
    ax.barh([i + 0.15 for i in y], top["actual"], height=0.35, color=config.color_tecnologia("hidro"), label="Esta semana")
    ax.set_yticks(list(y))
    ax.set_yticklabels(top["entidad"].str.title())
    ax.grid(axis="x", color="#EEF1F4", linewidth=0.6)
    ax.grid(axis="y", visible=False)
    ax.legend(fontsize=6.5, frameon=False, loc="lower right")
    _titulo(ax, titulo)
    return _png(fig)
