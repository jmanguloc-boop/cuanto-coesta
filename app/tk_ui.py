"""Componentes Tkinter de Cuanto COESta: tarjetas blancas, etiquetas de cambio y menu lateral.

Solo usa la biblioteca estandar (tkinter) mas matplotlib, que ya es dependencia del proyecto.
"""

import tkinter as tk
from tkinter import ttk

import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src.narrative import pulir
from src.utils.estilo import paleta

P = paleta()
F = {"texto": "TkDefaultFont", "fuerte": "TkDefaultFont"}   # se completa en configurar()

# Estados de una etiqueta de cambio: (fondo, texto)
TONOS = {
    "bueno": ("#E6F4EC", "#1E7A50"),
    "malo": ("#FBE7E3", "#B23A22"),
    "neutro": ("#EEF2F7", "#41536A"),
    "alerta": (P["naranja"], P["marino"]),
    "info": (P["celeste"], P["azul"]),
}


def configurar(raiz, familias):
    """Elige las familias tipograficas y define los estilos ttk."""
    from tkinter import font as tkfont
    disponibles = set(tkfont.families(raiz))
    F["texto"] = familias["texto"]
    F["fuerte"] = "Plus Jakarta Sans ExtraBold" if "Plus Jakarta Sans ExtraBold" in disponibles else familias["texto"]
    raiz.configure(bg=P["papel"])
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    estilo.configure(".", background=P["papel"], foreground=P["marino"], font=(F["texto"], 10))
    estilo.configure("TCombobox", fieldbackground="#FFFFFF", background="#FFFFFF", arrowcolor=P["marino"],
                     bordercolor=P["linea"], lightcolor="#FFFFFF", darkcolor="#FFFFFF", padding=6)
    estilo.configure("Vertical.TScrollbar", background=P["linea"], troughcolor=P["papel"], borderwidth=0,
                     arrowcolor=P["gris"])
    raiz.option_add("*TCombobox*Listbox.font", (F["texto"], 10))


def fuente(tam, peso="normal"):
    """Tupla de fuente: peso 'normal', 'bold' o 'xbold' (cifras grandes)."""
    if peso == "xbold":
        return (F["fuerte"], tam) if F["fuerte"] != F["texto"] else (F["texto"], tam, "bold")
    return (F["texto"], tam, "bold") if peso == "bold" else (F["texto"], tam)


# ---------- textos ----------

def texto(padre, contenido, tam=10, color=None, peso="normal", bg=None, ancho=0):
    """Etiqueta de texto (envuelve si se da ancho en px)."""
    return tk.Label(padre, text=pulir(contenido), font=fuente(tam, peso), fg=color or P["marino"],
                    bg=bg or padre["bg"], anchor="w", justify="left", wraplength=ancho)


def etiqueta_cambio(padre, contenido, tono="neutro"):
    """Pildora de color con el cambio (▲ 3.2%)."""
    fondo, color = TONOS[tono]
    return tk.Label(padre, text=contenido, font=fuente(9, "bold"), bg=fondo, fg=color, padx=10, pady=3)


# ---------- tooltip ----------

class Tooltip:
    """Explicacion corta al pasar el mouse."""

    def __init__(self, widget, contenido, ancho=320):
        self.widget, self.contenido, self.ancho, self.ventana = widget, contenido, ancho, None
        widget.bind("<Enter>", self.mostrar, add="+")
        widget.bind("<Leave>", self.ocultar, add="+")

    def mostrar(self, _evento=None):
        contenido = self.contenido() if callable(self.contenido) else self.contenido
        if not contenido or self.ventana:
            return
        x = self.widget.winfo_rootx() - 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.ventana = tk.Toplevel(self.widget)
        self.ventana.wm_overrideredirect(True)
        self.ventana.wm_geometry(f"+{x}+{y}")
        tk.Label(self.ventana, text=contenido, justify="left", wraplength=self.ancho, bg=P["marino"], fg="#FFFFFF",
                 font=fuente(9), padx=12, pady=9).pack()

    def ocultar(self, _evento=None):
        if self.ventana:
            self.ventana.destroy()
            self.ventana = None


def boton_info(padre, explicacion, bg=None):
    """Boton redondo 'i': la explicacion aparece al pasar el mouse."""
    b = tk.Label(padre, text="i", font=fuente(9, "bold"), fg=P["gris"], bg=bg or padre["bg"], width=2,
                 highlightthickness=1, highlightbackground=P["linea"], cursor="question_arrow")
    Tooltip(b, explicacion)
    return b


# ---------- botones ----------

def boton(padre, contenido, accion, primario=True, ayuda=None):
    """Boton plano: azul (primario) o blanco con borde (secundario)."""
    fondo, color, hover = (P["azul"], "#FFFFFF", "#0F4F99") if primario else ("#FFFFFF", P["marino"], P["celeste"])
    b = tk.Label(padre, text=contenido, font=fuente(10, "bold"), bg=fondo, fg=color, padx=16, pady=8, cursor="hand2",
                 highlightthickness=0 if primario else 1, highlightbackground=P["linea"])
    b.bind("<Button-1>", lambda e: accion())
    b.bind("<Enter>", lambda e: b.configure(bg=hover))
    b.bind("<Leave>", lambda e: b.configure(bg=fondo))
    b.tono_base = fondo
    if ayuda:
        Tooltip(b, ayuda, ancho=260)
    return b


# ---------- contenedores ----------

def tarjeta(padre, padx=22, pady=18):
    """Tarjeta blanca con borde suave."""
    return tk.Frame(padre, bg="#FFFFFF", padx=padx, pady=pady, highlightthickness=1, highlightbackground="#E3EAF2")


def tarjeta_cifra(padre, etiqueta, valor, unidad="", cambio="", tono="neutro", explicacion="", detalle=""):
    """Tarjeta de una cifra: nombre, numero grande, unidad y etiqueta de cambio."""
    t = tarjeta(padre, 20, 16)
    cabecera = tk.Frame(t, bg="#FFFFFF")
    cabecera.pack(fill="x")
    texto(cabecera, etiqueta, 10, P["gris"], "bold").pack(side="left")
    if explicacion:
        boton_info(cabecera, explicacion).pack(side="right")
    fila = tk.Frame(t, bg="#FFFFFF")
    fila.pack(fill="x", pady=(8, 6))
    tk.Label(fila, text=valor, font=fuente(26, "xbold"), fg=P["marino"], bg="#FFFFFF").pack(side="left")
    if unidad:
        tk.Label(fila, text=unidad, font=fuente(10, "bold"), fg=P["gris"], bg="#FFFFFF").pack(side="left", padx=(6, 0),
                                                                                             pady=(10, 0))
    if cambio:
        etiqueta_cambio(t, cambio, tono).pack(anchor="w")
    if detalle:
        texto(t, detalle, 9, P["gris"]).pack(anchor="w", pady=(4, 0))
    return t


class PanelScroll(tk.Frame):
    """Marco con desplazamiento vertical y rueda del mouse."""

    def __init__(self, padre, **kw):
        super().__init__(padre, bg=P["papel"], **kw)
        self.lienzo = tk.Canvas(self, bg=P["papel"], highlightthickness=0, bd=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.lienzo.yview)
        self.interior = tk.Frame(self.lienzo, bg=P["papel"], padx=36, pady=28)
        self.interior.bind("<Configure>", lambda e: self.lienzo.configure(scrollregion=self.lienzo.bbox("all")))
        self._ventana = self.lienzo.create_window((0, 0), window=self.interior, anchor="nw")
        self.lienzo.bind("<Configure>", lambda e: self.lienzo.itemconfigure(self._ventana, width=e.width))
        self.lienzo.configure(yscrollcommand=barra.set)
        self.lienzo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.bind_all("<MouseWheel>", self._rueda, add="+")
        self.bind_all("<Button-4>", lambda e: self._mover(-1), add="+")
        self.bind_all("<Button-5>", lambda e: self._mover(1), add="+")

    def _visible(self):
        return self.winfo_ismapped() and self.winfo_viewable()

    def _rueda(self, evento):
        if self._visible():
            self._mover(-1 if evento.delta > 0 else 1)

    def _mover(self, pasos):
        if self._visible():
            self.lienzo.yview_scroll(pasos * 3, "units")

    def limpiar(self):
        for hijo in self.interior.winfo_children():
            hijo.destroy()
        self.lienzo.yview_moveto(0)


class MenuLateral(tk.Frame):
    """Menu azul marino con las secciones; marca la activa."""

    def __init__(self, padre, nombre, secciones, al_elegir):
        super().__init__(padre, bg=P["marino"], width=236, padx=16, pady=24)
        self.pack_propagate(False)
        self.items, self.al_elegir, self.activa = {}, al_elegir, None
        logo = tk.Frame(self, bg=P["marino"])
        logo.pack(fill="x", pady=(0, 26))
        tk.Label(logo, text="⚡", font=fuente(14, "bold"), bg=P["naranja"], fg=P["marino"], width=2).pack(side="left")
        partes = nombre.split(" ", 1)
        tk.Label(logo, text=" " + partes[0], font=fuente(15, "xbold"), bg=P["marino"], fg="#FFFFFF").pack(side="left")
        if len(partes) > 1:
            tk.Label(logo, text=" " + partes[1], font=fuente(15, "xbold"), bg=P["marino"], fg=P["azul_claro"]).pack(side="left")
        for clave, etiqueta, icono in secciones:
            item = tk.Label(self, text=f"  {icono}   {etiqueta}", font=fuente(11), bg=P["marino"], fg="#C9D8EA",
                            anchor="w", padx=10, pady=7, cursor="hand2")
            item.pack(fill="x", pady=1)
            item.bind("<Button-1>", lambda e, c=clave: self.al_elegir(c))
            item.bind("<Enter>", lambda e, w=item, c=clave: w.configure(bg="#16375A") if c != self.activa else None)
            item.bind("<Leave>", lambda e, w=item, c=clave: w.configure(bg=P["marino"]) if c != self.activa else None)
            self.items[clave] = item
        from src.utils import config
        version = config.proyecto().get("version", "")
        pie = tk.Label(self, text=f"Datos públicos del COES.\nProyecto independiente · v{version}", font=fuente(8), bg="#16375A",
                       fg="#C9D8EA", justify="left", anchor="w", padx=12, pady=10)
        pie.pack(side="bottom", fill="x")

    def marcar(self, clave):
        """Resalta la seccion activa."""
        for c, item in self.items.items():
            activo = c == clave
            item.configure(bg=P["azul"] if activo else P["marino"], fg="#FFFFFF" if activo else "#C9D8EA",
                           font=fuente(11, "bold") if activo else fuente(11))
        self.activa = clave


# ---------- graficos ----------

class Grafico(tk.Frame):
    """Figura matplotlib embebida, con el valor al pasar el mouse (usa fig.hover)."""

    def __init__(self, padre, fig, alto=None):
        super().__init__(padre, bg="#FFFFFF")
        self.fig = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        widget = self.canvas.get_tk_widget()
        widget.configure(bg="#FFFFFF", highlightthickness=0)
        if alto:
            widget.configure(height=alto)
        widget.pack(fill="both", expand=True)
        self.ax = fig.axes[0]
        self.nota = self.ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points", fontsize=8.5,
                                     bbox={"boxstyle": "round,pad=0.5", "fc": P["marino"], "ec": P["marino"]},
                                     color="#FFFFFF", zorder=10)
        self.nota.set_visible(False)
        self.canvas.mpl_connect("motion_notify_event", self._mover)
        self.canvas.draw()

    def _mover(self, evento):
        series = getattr(self.fig, "hover", [])
        if evento.inaxes != self.ax or not series:
            if self.nota.get_visible():
                self.nota.set_visible(False)
                self.canvas.draw_idle()
            return
        calor = getattr(self.fig, "hover_calor", None)
        if calor is not None:
            fila, col = int(round(evento.ydata)), int(round(evento.xdata))
            if 0 <= fila < len(calor) and 0 <= col < 48:
                valor = calor.iloc[fila, col]
                if valor == valor:   # no es NaN
                    dia = calor.index[fila]
                    self._mostrar(col, fila, f"{dia.day}/{dia.month}  {col // 2}:{(col % 2) * 30:02d} h\n"
                                             f"{valor:,.1f} por MWh")
                    return
            self.nota.set_visible(False)
            self.canvas.draw_idle()
            return
        mapa = getattr(self.fig, "hover_mapa", None)
        if mapa is not None:
            d = (mapa["longitud"] - evento.xdata) ** 2 + (mapa["latitud"] - evento.ydata) ** 2
            i = int(d.idxmin())
            if d[i] > 0.6:
                self.nota.set_visible(False)
                self.canvas.draw_idle()
                return
            fila = mapa.loc[i]
            self._mostrar(fila["longitud"], fila["latitud"], f"{fila['barra'].title()}\nS/ {fila['cmg_promedio']:,.1f} por MWh")
            return
        xs, ys, fmt = series[0]
        if not xs or fmt is None:
            return
        x_num = np.array([self._a_numero(x) for x in xs])
        i = int(np.abs(x_num - evento.xdata).argmin())
        self._mostrar(xs[i], ys[i], fmt(xs[i], ys[i]))

    @staticmethod
    def _a_numero(x):
        if isinstance(x, (pd.Timestamp, np.datetime64)) or hasattr(x, "to_pydatetime"):
            import matplotlib.dates as mdates
            return mdates.date2num(pd.Timestamp(x).to_pydatetime())
        return float(x)

    def _mostrar(self, x, y, contenido):
        self.nota.xy = (x, y)
        self.nota.set_text(contenido)
        x0, x1 = self.ax.get_xlim()
        derecha = (self._a_numero(x) - x0) / max(x1 - x0, 1e-9) > 0.6
        self.nota.set_position((-130 if derecha else 10, 10))
        self.nota.set_visible(True)
        self.canvas.draw_idle()
