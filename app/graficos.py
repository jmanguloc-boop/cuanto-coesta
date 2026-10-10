"""Graficos Plotly del dashboard. Colores y textos salen de config/ (nunca hardcodeados)."""

import pandas as pd
import plotly.graph_objects as go

from src.utils import config
from src.utils.fechas import dia_y_hora

FUENTE = "Inter, Segoe UI, Roboto, sans-serif"


def _paleta():
    return config.proyecto()["paleta"]


def _base(fig, titulo, alto=380, eje_y=""):
    p = _paleta()
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=17, color=p["texto"]), x=0, xanchor="left"),
        height=alto, margin=dict(l=10, r=10, t=60, b=10),
        font=dict(family=FUENTE, color=p["texto"], size=13),
        plot_bgcolor=p["fondo"], paper_bgcolor=p["fondo"],
        hoverlabel=dict(bgcolor="white", font_size=13, font_family=FUENTE),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="left", x=0),
        separators=".,",   # decimal con punto, miles con coma
    )
    fig.update_xaxes(showgrid=False, linecolor="#C9D1D9")
    fig.update_yaxes(gridcolor="#EEF1F4", title_text=eje_y, zeroline=False, tickformat=",")
    return fig


def _eje_dias(fig, fechas):
    """Marcas del eje X en espanol: 'lun 28/9' a medianoche de cada dia."""
    dias = (pd.to_datetime(pd.Series(fechas)) - pd.Timedelta(minutes=1)).dt.normalize().drop_duplicates().sort_values()
    abrev = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
    # Marca al mediodia: queda centrada en el dia y no se sale del rango (la serie arranca 00:30)
    fig.update_xaxes(tickvals=list(dias + pd.Timedelta(hours=12)), ticktext=[f"{abrev[d.weekday()]} {d.day}/{d.month}" for d in dias])
    return fig


def _textos_momento(serie):
    return [dia_y_hora(t) for t in serie]


def grafico_precio_semana(serie_cmg: pd.DataFrame, umbrales: dict, titulo: str):
    """Costo marginal de la semana con lineas de precio alto y bajo."""
    p = _paleta()
    fig = go.Figure(go.Scatter(
        x=serie_cmg["fecha_hora"], y=serie_cmg["valor"], mode="lines",
        line=dict(color=p["secundario"], width=2), name="Costo marginal",
        customdata=_textos_momento(serie_cmg["fecha_hora"]),
        hovertemplate="%{customdata}<br><b>S/ %{y:,.1f} por MWh</b><br>Lo que costó producir el último MWh<extra></extra>",
    ))
    for nivel, color, texto in ((umbrales["alto"], p["sube"], "precio alto"), (umbrales["bajo"], p["baja"], "precio bajo")):
        fig.add_hline(y=nivel, line=dict(color=color, dash="dot", width=1),
                      annotation_text=f"{texto} (S/ {nivel})", annotation_position="top left",
                      annotation_font=dict(color=color, size=11))
    _eje_dias(fig, serie_cmg["fecha_hora"])
    return _base(fig, titulo, eje_y="S/ por MWh")


def grafico_perfil_horario(perfil: pd.DataFrame, titulo: str):
    """Precio promedio por hora del dia, esta semana vs la anterior."""
    p = _paleta()
    fig = go.Figure()
    if perfil["anterior"].notna().any():
        fig.add_trace(go.Scatter(
            x=perfil["hora"], y=perfil["anterior"], mode="lines", name="Semana anterior",
            line=dict(color=p["texto_suave"], width=1.5, dash="dot"),
            hovertemplate="%{x}:00 h, semana anterior<br>S/ %{y:,.1f} por MWh<extra></extra>"))
    fig.add_trace(go.Bar(
        x=perfil["hora"], y=perfil["actual"], name="Esta semana", marker_color=p["secundario"],
        hovertemplate="%{x}:00 h<br><b>S/ %{y:,.1f} por MWh</b><br>Precio promedio a esta hora en la semana<extra></extra>"))
    fig.update_xaxes(dtick=3, ticksuffix=" h")
    return _base(fig, titulo, eje_y="S/ por MWh")


def grafico_demanda(serie_dem: pd.DataFrame, titulo: str):
    """Demanda real vs programada, con el pico marcado."""
    p = _paleta()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=serie_dem["fecha_hora"], y=serie_dem["prog_diaria"], mode="lines", name="Lo programado",
        line=dict(color=p["texto_suave"], width=1.2, dash="dot"),
        customdata=_textos_momento(serie_dem["fecha_hora"]),
        hovertemplate="%{customdata}<br>Programado: %{y:,.0f} MW<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=serie_dem["fecha_hora"], y=serie_dem["ejecutada"], mode="lines", name="Consumo real",
        line=dict(color=p["primario"], width=2.2),
        customdata=_textos_momento(serie_dem["fecha_hora"]),
        hovertemplate="%{customdata}<br><b>%{y:,.0f} MW</b><br>Electricidad que pedía el país en ese momento<extra></extra>"))
    imax = serie_dem["ejecutada"].idxmax()
    fig.add_annotation(x=serie_dem.loc[imax, "fecha_hora"], y=serie_dem.loc[imax, "ejecutada"],
                       text=f"Pico: {serie_dem.loc[imax, 'ejecutada']:,.0f} MW", showarrow=True, arrowhead=0,
                       ay=-30, font=dict(color=p["acento"], size=12))
    _eje_dias(fig, serie_dem["fecha_hora"])
    return _base(fig, titulo, eje_y="MW")


def grafico_generacion(serie_gen: pd.DataFrame, titulo: str):
    """Generacion apilada por tecnologia cada 30 min."""
    proyecto = config.proyecto()
    fig = go.Figure()
    for tec in proyecto["orden_tecnologias"]:
        parte = serie_gen[serie_gen["tecnologia"] == tec]
        if parte.empty or parte["valor"].sum() <= 0:
            continue
        nombre = config.nombre_tecnologia(tec)
        fig.add_trace(go.Scatter(
            x=parte["fecha_hora"], y=parte["valor"].clip(lower=0), mode="lines", stackgroup="uno", name=nombre,
            line=dict(width=0.5, color=config.color_tecnologia(tec)), fillcolor=config.color_tecnologia(tec),
            customdata=_textos_momento(parte["fecha_hora"]),
            hovertemplate=f"%{{customdata}}<br><b>{nombre}: %{{y:,.0f}} MW</b><extra></extra>"))
    _eje_dias(fig, serie_gen["fecha_hora"])
    return _base(fig, titulo, alto=420, eje_y="MW")


def grafico_mix(mix: dict, mix_anterior: dict, titulo: str):
    """Participacion de cada tecnologia, esta semana vs la anterior."""
    _paleta()
    tecs = [t for t in sorted(mix, key=mix.get) if mix[t] >= 0.001]
    nombres = [config.nombre_tecnologia(t) for t in tecs]
    fig = go.Figure()
    if mix_anterior:
        fig.add_trace(go.Bar(
            y=nombres, x=[mix_anterior.get(t, 0) * 100 for t in tecs], orientation="h", name="Semana anterior",
            marker_color="#D5DCE3", hovertemplate="%{y}, semana anterior: %{x:.1f}%<extra></extra>"))
    fig.add_trace(go.Bar(
        y=nombres, x=[mix[t] * 100 for t in tecs], orientation="h", name="Esta semana",
        marker_color=[config.color_tecnologia(t) for t in tecs],
        text=[f"{mix[t] * 100:.1f}%" for t in tecs], textposition="outside",
        hovertemplate="<b>%{y}: %{x:.1f}%</b><br>de toda la electricidad de la semana<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.25, showlegend=False)
    fig.update_xaxes(ticksuffix="%", range=[0, max(mix.values()) * 100 * 1.2])
    return _base(fig, titulo, alto=360)


def grafico_embalses(serie_emb: pd.DataFrame, titulo: str):
    """Volumen util total de los embalses al cierre de cada dia."""
    _paleta()
    textos = [f"{d.day}/{d.month}" for d in serie_emb["fecha"]]
    fig = go.Figure(go.Scatter(
        x=textos, y=serie_emb["valor"], mode="lines+markers", line=dict(color=config.color_tecnologia("hidro"), width=2.5),
        hovertemplate="%{x}<br><b>%{y:,.1f} Hm3</b><br>Agua útil guardada en los embalses (mil millones de litros cada Hm3)<extra></extra>"))
    return _base(fig, titulo, alto=320, eje_y="Hm3")


def grafico_embalses_detalle(detalle: pd.DataFrame, titulo: str, n=10):
    """Los n embalses con mas agua, esta semana vs la anterior."""
    _paleta()
    top = detalle.dropna(subset=["actual"]).nlargest(n, "actual").iloc[::-1]
    nombres = top["entidad"].str.title()
    fig = go.Figure()
    fig.add_trace(go.Bar(y=nombres, x=top["anterior"], orientation="h", name="Semana anterior", marker_color="#D5DCE3",
                         hovertemplate="%{y}, semana anterior: %{x:,.1f} Hm3<extra></extra>"))
    fig.add_trace(go.Bar(y=nombres, x=top["actual"], orientation="h", name="Esta semana",
                         marker_color=config.color_tecnologia("hidro"),
                         hovertemplate="<b>%{y}: %{x:,.1f} Hm3</b><extra></extra>"))
    fig.update_layout(barmode="group")
    return _base(fig, titulo, alto=440)
