"""Componentes Tkinter con la identidad editorial de Cuanto COESta.

Solo usa la biblioteca estandar (tkinter) mas matplotlib, que ya es dependencia del proyecto.
"""

import tkinter as tk
from tkinter import ttk

import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src.utils.estilo import paleta

P = paleta()
F = {"titulares": "TkDefaultFont", "texto": "TkDefaultFont", "mono": "TkFixedFont"}   # se completa en configurar()


def configurar(raiz, familias):
    """Guarda las familias tipograficas elegidas y define los estilos ttk."""
    F.update(familias)
    raiz.configure(bg=P["papel"])
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    estilo.configure(".", background=P["papel"], foreground=P["tinta"], font=(F["texto"], 10))
    estilo.configure("TNotebook", background=P["papel"], borderwidth=0, tabmargins=(0, 6, 0, 0))
    estilo.configure("TNotebook.Tab", background=P["papel"], foreground=P["gris"], padding=(12, 7),
                     font=(F["mono"], 9), borderwidth=0)
    estilo.map("TNotebook.Tab", background=[("selected", P["tinta"])], foreground=[("selected", P["lima"])])
    estilo.configure("TCombobox", fieldbackground=P["blanco"], background=P["blanco"], arrowcolor=P["tinta"],
                     bordercolor=P["linea"], lightcolor=P["blanco"], darkcolor=P["blanco"])
    estilo.configure("Vertical.TScrollbar", background=P["linea"], troughcolor=P["papel"], borderwidth=0,
                     arrowcolor=P["gris"])
    raiz.option_add("*TCombobox*Listbox.font", (F["texto"], 10))


# ---------- textos ----------

def kicker(padre, texto, color=None, bg=None):
    """Etiqueta en mono mayuscula: '01 / LA SENAL DE LA SEMANA'."""
    return tk.Label(padre, text=texto.upper(), font=(F["mono"], 8), fg=color or P["verde"], bg=bg or padre["bg"],
                    anchor="w", justify="left")


def titular(padre, texto, tam=30, color=None, bg=None, ancho=760):
    """Titular condensado grande."""
    return tk.Label(padre, text=texto, font=(F["titulares"], tam, "bold"), fg=color or P["tinta"], bg=bg or padre["bg"],
                    anchor="w", justify="left", wraplength=ancho)


def parrafo(padre, texto, tam=10, color=None, bg=None, ancho=760):
    """Texto corrido."""
    return tk.Label(padre, text=texto, font=(F["texto"], tam), fg=color or "#484B43", bg=bg or padre["bg"],
                    anchor="w", justify="left", wraplength=ancho)


def regla(padre, grosor=1, color=None):
    """Linea horizontal (filete editorial)."""
    return tk.Frame(padre, height=grosor, bg=color or P["linea"])


def seccion(padre, titulo, nota=""):
    """Encabezado de seccion: titular condensado a la izquierda, nota en mono a la derecha."""
    marco = tk.Frame(padre, bg=padre["bg"])
    tk.Label(marco, text=titulo.upper(), font=(F["titulares"], 17, "bold"), fg=P["tinta"], bg=padre["bg"]).pack(side="left")
    if nota:
        tk.Label(marco, text=nota.upper(), font=(F["mono"], 7), fg=P["gris"], bg=padre["bg"]).pack(side="right", pady=(6, 0))
    return marco


# ---------- tooltip ----------

class Tooltip:
    """Explicacion al pasar el mouse por un widget."""

    def __init__(self, widget, texto_fn, ancho=420):
        self.widget, self.texto_fn, self.ancho, self.ventana = widget, texto_fn, ancho, None
        widget.bind("<Enter>", self.mostrar, add="+")
        widget.bind("<Leave>", self.ocultar, add="+")

    def mostrar(self, _evento=None):
        texto = self.texto_fn() if callable(self.texto_fn) else self.texto_fn
        if not texto or self.ventana:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.ventana = tk.Toplevel(self.widget)
        self.ventana.wm_overrideredirect(True)
        self.ventana.wm_geometry(f"+{x}+{y}")
        tk.Label(self.ventana, text=texto, justify="left", wraplength=self.ancho, bg=P["tinta"], fg=P["papel"],
                 font=(F["texto"], 9), padx=10, pady=8).pack()

    def ocultar(self, _evento=None):
        if self.ventana:
            self.ventana.destroy()
            self.ventana = None


# ---------- contenedor con scroll ----------

class PanelScroll(tk.Frame):
    """Marco con barra de desplazamiento vertical y rueda del mouse."""

    def __init__(self, padre, **kw):
        super().__init__(padre, bg=P["papel"], **kw)
        self.lienzo = tk.Canvas(self, bg=P["papel"], highlightthickness=0, bd=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.lienzo.yview)
        self.interior = tk.Frame(self.lienzo, bg=P["papel"])
        self.interior.bind("<Configure>", lambda e: self.lienzo.configure(scrollregion=self.lienzo.bbox("all")))
        self._ventana = self.lienzo.create_window((0, 0), window=self.interior, anchor="nw")
        self.lienzo.bind("<Configure>", lambda e: self.lienzo.itemconfigure(self._ventana, width=e.width))
        self.lienzo.configure(yscrollcommand=barra.set)
        self.lienzo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.bind_all("<MouseWheel>", self._rueda, add="+")
        self.bind_all("<Button-4>", lambda e: self._mover(-1), add="+")   # Linux
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


# ---------- tarjetas ----------

def tarjeta_cifra(padre, etiqueta, valor, pie="", color_pie=None, ayuda=None, unidad=""):
    """Celda de cifra: etiqueta mono, numero condensado grande y pie con la variacion."""
    celda = tk.Frame(padre, bg=P["blanco"], padx=16, pady=12, highlightthickness=1, highlightbackground=P["linea"])
    tk.Label(celda, text=etiqueta.upper(), font=(F["mono"], 8), fg=P["gris"], bg=P["blanco"], anchor="w").pack(fill="x")
    fila = tk.Frame(celda, bg=P["blanco"])
    fila.pack(fill="x", pady=(8, 2))
    numero = tk.Label(fila, text=valor, font=(F["titulares"], 28, "bold"), fg=P["tinta"], bg=P["blanco"])
    numero.pack(side="left")
    if unidad:
        tk.Label(fila, text=unidad, font=(F["mono"], 9), fg=P["gris"], bg=P["blanco"]).pack(side="left", padx=(5, 0), pady=(12, 0))
    if pie:
        tk.Label(celda, text=pie, font=(F["mono"], 8), fg=color_pie or P["gris"], bg=P["blanco"], anchor="w").pack(fill="x")
    if ayuda:
        for w in (celda, numero):
            Tooltip(w, ayuda)
    return celda


def caja_oscura(padre):
    """Bloque carbon para instrumentos (precio en vivo)."""
    return tk.Frame(padre, bg=P["tinta"], padx=20, pady=18)


def insignia(padre, texto, fondo=None, color=None):
    """Etiqueta resaltada (lima sobre carbon por defecto)."""
    return tk.Label(padre, text=texto, font=(F["mono"], 9, "bold"), bg=fondo or P["lima"], fg=color or P["tinta"],
                    padx=8, pady=5)


class QueSignifica(tk.Frame):
    """'Que significa esto?' plegable con la explicacion en tres niveles."""

    def __init__(self, padre, niveles: dict, titulo="¿Qué significa esto?", ancho=880):
        super().__init__(padre, bg=P["papel"])
        self.abierto = False
        self.boton = tk.Label(self, text=f"+  {titulo}", font=(F["mono"], 9), fg=P["verde"], bg=P["papel"], cursor="hand2",
                              anchor="w")
        self.boton.pack(fill="x")
        self.boton.bind("<Button-1>", self.alternar)
        self.cuerpo = tk.Frame(self, bg=P["blanco"], padx=14, pady=10, highlightthickness=1, highlightbackground=P["linea"])
        for etiqueta, clave in (("Lectura rápida", "rapida"), ("Con más detalle", "intermedia"), ("Nota técnica", "tecnica")):
            texto = niveles.get(clave)
            if not texto:
                continue
            tk.Label(self.cuerpo, text=etiqueta.upper(), font=(F["mono"], 7), fg=P["verde"], bg=P["blanco"], anchor="w").pack(fill="x", pady=(4, 0))
            tk.Label(self.cuerpo, text=texto, font=(F["texto"], 10 if clave != "tecnica" else 9),
                     fg=P["tinta"] if clave != "tecnica" else P["gris"], bg=P["blanco"], anchor="w", justify="left",
                     wraplength=ancho).pack(fill="x")

    def alternar(self, _evento=None):
        self.abierto = not self.abierto
        self.boton.configure(text=self.boton.cget("text").replace("+  " if self.abierto else "−  ",
                                                                  "−  " if self.abierto else "+  ", 1))
        if self.abierto:
            self.cuerpo.pack(fill="x", pady=(4, 0))
        else:
            self.cuerpo.pack_forget()


# ---------- graficos ----------

class Grafico(tk.Frame):
    """Figura matplotlib embebida, con el valor al pasar el mouse (usa fig.hover)."""

    def __init__(self, padre, fig, alto=None, borde=True):
        super().__init__(padre, bg=P["blanco"], highlightthickness=1 if borde else 0,
                         highlightbackground=P["linea"])
        self.fig = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        widget = self.canvas.get_tk_widget()
        widget.configure(bg=padre["bg"], highlightthickness=0)
        if alto:
            widget.configure(height=alto)
        widget.pack(fill="both", expand=True)
        self.ax = fig.axes[0]
        self.nota = self.ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points", fontsize=8,
                                     bbox={"boxstyle": "square,pad=0.5", "fc": P["tinta"], "ec": P["tinta"]},
                                     color=P["papel"], zorder=10)
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

    def _mostrar(self, x, y, texto):
        self.nota.xy = (x, y)
        self.nota.set_text(texto)
        # Si el punto esta en la mitad derecha, el recuadro se abre hacia la izquierda
        x0, x1 = self.ax.get_xlim()
        derecha = (self._a_numero(x) - x0) / max(x1 - x0, 1e-9) > 0.6
        self.nota.set_position((-120 if derecha else 10, 10))
        self.nota.set_visible(True)
        self.canvas.draw_idle()
