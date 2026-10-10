"""Cuanto COESta: aplicacion de escritorio (Tkinter, sin navegador).

Uso (desde la raiz del proyecto):  python app/escritorio.py

Pestanas: La senal, Ahora, Precios, Demanda, Generacion, Hidrologia, Mapa,
Metodo y fuentes, Glosario. El PDF semanal es opcional (boton).
"""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tk_ui as ui  # noqa: E402
from src.ahora.memoria import estado_precio  # noqa: E402
from src.analysis import calcular_resumen  # noqa: E402
from src.narrative import en_simple, explicar_hecho, generar_narrativa, niveles  # noqa: E402
from src.narrative import CATEGORIA_HECHO  # noqa: E402
from src.utils import config, estado  # noqa: E402
from src.utils.datos import ruta_tabla, semanas_disponibles  # noqa: E402
from src.utils.estilo import familias_tk, registrar_fuentes_tk  # noqa: E402
from src.utils.fechas import dia_y_hora, texto_semana, ultima_semana_completa  # noqa: E402
from src.utils.formato import numero, porcentaje  # noqa: E402
from src.utils.logs import configurar_logging, obtener_logger  # noqa: E402
from src.visual import graficos as G  # noqa: E402

log = obtener_logger("escritorio")
P = ui.P
PROYECTO = config.proyecto()
GLOSARIO = config.glosario()
ANCHO_TEXTO = 900


# ---------- formato ----------

def soles(v, unidad=True):
    """Monto en soles, con o sin la unidad por MWh."""
    if v is None:
        return "s/d"
    return f"S/ {numero(v, 1)}" + (" por MWh" if unidad else "")


def variacion(ind, invertir=False, puntos=False, texto_ref="vs semana anterior"):
    """('▲ +3.2% vs semana anterior', color). Verde = favorable para quien usa electricidad."""
    if ind is None or ind.var_anterior is None:
        return "sin comparación", P["gris"]
    v = ind.var_anterior
    flecha = "▲" if v > 0 else "▼"
    cifra = f"{v * 100:+.1f} pp" if puntos else f"{v * 100:+.1f}%"
    bueno = (v < 0) if invertir else (v > 0)
    return f"{flecha} {cifra} {texto_ref}", P["baja"] if bueno else P["sube"]


def ayuda(clave):
    """Texto del glosario para el tooltip de una cifra."""
    g = GLOSARIO["indicadores"].get(clave) or GLOSARIO["terminos"].get(clave)
    if not g:
        return ""
    return f"{' '.join(g['explicacion_simple'].split())}\n\n¿Por qué importa? {g['por_que_importa']}"


def semanas_completas():
    """Semanas con las tablas base para analizar."""
    return [s for s in semanas_disponibles("demanda")
            if ruta_tabla("costo_marginal", s).exists() and ruta_tabla("generacion", s).exists()]


def abrir_archivo(ruta):
    """Abre un archivo con el programa predeterminado del sistema."""
    if sys.platform == "win32":
        os.startfile(ruta)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.run(["open", str(ruta)], check=False)
    else:
        subprocess.run(["xdg-open", str(ruta)], check=False)


# ---------- aplicacion ----------

class App:
    def __init__(self):
        registrar_fuentes_tk()
        if sys.platform == "win32":
            # Nitido en pantallas con escala (125 %, 150 %): sin esto Windows estira la ventana como imagen
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except (AttributeError, OSError):
                pass
        self.raiz = tk.Tk()
        self.raiz.title(f"{PROYECTO['nombre']}: {PROYECTO['tagline']}")
        ancho = min(1400, int(self.raiz.winfo_screenwidth() * 0.9))
        alto = min(940, int(self.raiz.winfo_screenheight() * 0.88))
        self.raiz.geometry(f"{ancho}x{alto}+20+10")
        self.raiz.minsize(1050, 700)
        ui.configurar(self.raiz, familias_tk(self.raiz))
        self.cola = queue.Queue()
        self.ocupado = False
        self.pendientes = []       # tareas en espera: se ejecutan de a una, en orden
        self.r = self.n = self.e = None
        self.auto = tk.BooleanVar(value=True)
        self._construir_marco()
        self.raiz.after(150, self._revisar_cola)
        self.raiz.after(300, self.cargar_semana)
        self.raiz.after(400, self.cargar_ahora)
        self._programar_auto()

    # ----- estructura -----

    def _construir_marco(self):
        cab = tk.Frame(self.raiz, bg=P["papel"], padx=28, pady=14)
        cab.pack(fill="x")
        logo = tk.Frame(cab, bg=P["papel"])
        logo.pack(side="left")
        nombre = PROYECTO["nombre"].split(" ", 1)
        fila = tk.Frame(logo, bg=P["papel"])
        fila.pack(anchor="w")
        tk.Label(fila, text=nombre[0] + " ", font=(ui.F["titulares"], 30, "bold"), fg=P["tinta"], bg=P["papel"]).pack(side="left")
        if len(nombre) > 1:
            tk.Label(fila, text=nombre[1], font=(ui.F["titulares"], 30, "bold"), fg=P["verde"], bg=P["papel"]).pack(side="left")
        tk.Label(logo, text=PROYECTO["tagline"].upper(), font=(ui.F["mono"], 8), fg=P["tinta"], bg=P["papel"]).pack(anchor="w")

        derecha = tk.Frame(cab, bg=P["papel"])
        derecha.pack(side="right")
        self.meta = tk.Label(derecha, text="", font=(ui.F["mono"], 8), fg=P["gris"], bg=P["papel"], justify="right")
        self.meta.pack(anchor="e")
        controles = tk.Frame(derecha, bg=P["papel"])
        controles.pack(anchor="e", pady=(6, 0))
        tk.Label(controles, text="SEMANA", font=(ui.F["mono"], 8), fg=P["gris"], bg=P["papel"]).pack(side="left", padx=(0, 6))
        self.lista = semanas_completas()[::-1]
        self.combo = ttk.Combobox(controles, state="readonly", width=50, values=[texto_semana(s) for s in self.lista])
        self.combo.pack(side="left")
        if self.lista:
            inicial = ultima_semana_completa()
            self.combo.current(self.lista.index(inicial) if inicial in self.lista else 0)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.cargar_semana())
        self.botones = []
        for texto, accion, ayuda_txt in (
            ("↻ AHORA", self.actualizar_ahora, "Consulta al COES el último costo marginal y la demanda (tarda segundos)."),
            ("↓ DESCARGAR SEMANA", self.descargar_semana, "Baja y procesa la última semana completa (2 a 3 minutos)."),
            ("PDF", self.generar_pdf, "Genera el PDF de la semana elegida y lo abre. Es opcional."),
        ):
            b = tk.Label(controles, text=texto, font=(ui.F["mono"], 9, "bold"), bg=P["tinta"], fg=P["lima"], padx=10, pady=5,
                         cursor="hand2")
            b.pack(side="left", padx=(8, 0))
            b.bind("<Button-1>", lambda e, a=accion: a())
            ui.Tooltip(b, ayuda_txt, ancho=260)
            self.botones.append(b)

        ui.regla(self.raiz, 2, P["tinta"]).pack(fill="x", padx=28)
        self.libreta = ttk.Notebook(self.raiz)
        self.libreta.pack(fill="both", expand=True, padx=28, pady=(8, 0))
        self.paneles = {}
        for clave, titulo in (("senal", "LA SEÑAL"), ("ahora", "AHORA"), ("precios", "PRECIOS"), ("demanda", "DEMANDA"),
                              ("generacion", "GENERACIÓN"), ("hidro", "HIDROLOGÍA"), ("mapa", "MAPA"),
                              ("metodo", "MÉTODO Y FUENTES"), ("glosario", "GLOSARIO")):
            panel = ui.PanelScroll(self.libreta)
            self.libreta.add(panel, text=titulo)
            self.paneles[clave] = panel

        pie = tk.Frame(self.raiz, bg=P["papel"], padx=28, pady=6)
        pie.pack(fill="x")
        ui.regla(pie, 2, P["tinta"]).pack(fill="x", pady=(0, 6))
        self.estado = tk.Label(pie, text="Listo.", font=(ui.F["mono"], 8), fg=P["gris"], bg=P["papel"], anchor="w")
        self.estado.pack(side="left")
        tk.Label(pie, text="No es un producto oficial del COES · Datos públicos de www.coes.org.pe",
                 font=(ui.F["mono"], 8), fg="#7C4E32", bg=P["papel"]).pack(side="right")

    # ----- trabajo en segundo plano -----

    def _en_fondo(self, mensaje, tarea, al_terminar):
        if self.ocupado:
            if not any(m == mensaje for m, _, _ in self.pendientes):
                self.pendientes.append((mensaje, tarea, al_terminar))
            return
        self.ocupado = True
        self.avisar(mensaje + "...")
        for b in self.botones:
            b.configure(bg=P["gris"])

        def correr():
            try:
                self.cola.put((al_terminar, tarea(), None))
            except Exception as error:   # se muestra en la barra de estado, no se cae la app
                log.exception("Tarea fallida")
                self.cola.put((al_terminar, None, error))

        threading.Thread(target=correr, daemon=True).start()

    def _revisar_cola(self):
        try:
            while True:
                al_terminar, resultado, error = self.cola.get_nowait()
                self.ocupado = False
                for b in self.botones:
                    b.configure(bg=P["tinta"])
                if error:
                    self.avisar(f"Error: {error}")
                else:
                    al_terminar(resultado)
                if self.pendientes and not self.ocupado:
                    self._en_fondo(*self.pendientes.pop(0))
        except queue.Empty:
            pass
        self.raiz.after(150, self._revisar_cola)

    def avisar(self, texto):
        self.estado.configure(text=texto)

    def _programar_auto(self):
        minutos = config.fuentes()["ahora"]["cada_minutos"]

        def tic():
            if self.auto.get() and not self.ocupado:
                self.actualizar_ahora(silencioso=True)
            self.raiz.after(minutos * 60 * 1000, tic)

        self.raiz.after(minutos * 60 * 1000, tic)

    # ----- acciones -----

    def semana(self):
        return self.lista[self.combo.current()] if self.lista else None

    def cargar_semana(self):
        semana = self.semana()
        if not semana:
            self.vacio()
            return

        def tarea():
            r = calcular_resumen(semana)
            return r, generar_narrativa(r)

        self._en_fondo(f"Calculando {texto_semana(semana).lower()}", tarea, self._mostrar_semana)

    def _mostrar_semana(self, resultado):
        self.r, self.n = resultado
        estado_txt = "PRELIMINAR" if self.r.es_preliminar else "DATOS COMPLETOS"
        self.meta.configure(text=f"EDICIÓN {self.r.semana.replace('-W', ' / SEMANA ')} · {estado_txt}\nPERÚ / SEIN · "
                                 f"BARRA {self.r.barra_referencia}")
        for vista in (self.vista_senal, self.vista_precios, self.vista_demanda, self.vista_generacion,
                      self.vista_hidro, self.vista_mapa, self.vista_metodo, self.vista_glosario):
            vista()
        self.avisar(f"{self.r.texto_semana} cargada.")

    def cargar_ahora(self):
        self._en_fondo("Leyendo los últimos datos guardados", estado_precio, self._mostrar_ahora)

    def actualizar_ahora(self, silencioso=False):
        from src.ahora.extractor import actualizar

        def tarea():
            hay_base = (config.DIR_DATA / "ahora" / "ahora.sqlite").exists()
            actualizar(desde_ayer=not hay_base)
            return estado_precio()

        self._en_fondo("Consultando al COES (costo marginal y demanda)", tarea, self._mostrar_ahora)
        if not silencioso:
            self.libreta.select(self.paneles["ahora"])

    def _mostrar_ahora(self, e):
        self.e = e
        self.vista_ahora()
        if not e.sin_datos:
            self.avisar(f"Ahora: S/ {numero(e.valor, 1)} por MWh ({dia_y_hora(e.momento)}).")

    def descargar_semana(self):
        import run_weekly

        semana = ultima_semana_completa()

        def tarea():
            run_weekly.correr(semana, historico=1, descargar=True, pdf=False)
            return semana

        def listo(s):
            self.lista = semanas_completas()[::-1]
            self.combo.configure(values=[texto_semana(x) for x in self.lista])
            self.combo.current(self.lista.index(s) if s in self.lista else 0)
            self.cargar_semana()

        self._en_fondo(f"Descargando y procesando {texto_semana(semana).lower()} (2 a 3 minutos)", tarea, listo)

    def generar_pdf(self):
        from src.report import generar_pdf
        semana = self.semana()
        if not semana:
            return
        self._en_fondo("Generando el PDF", lambda: generar_pdf(semana),
                       lambda ruta: (abrir_archivo(ruta), self.avisar(f"PDF listo: {ruta}")))

    # ----- piezas de vista -----

    def _encabezado(self, cont, numero_sec, kicker, titulo, texto=None):
        ui.kicker(cont, f"{numero_sec} / {kicker}").pack(fill="x", pady=(18, 4))
        ui.titular(cont, titulo, tam=26, ancho=ANCHO_TEXTO + 200).pack(fill="x")
        if texto:
            ui.parrafo(cont, texto, ancho=ANCHO_TEXTO + 200).pack(fill="x", pady=(8, 4))

    def _cifras(self, cont, celdas):
        fila = tk.Frame(cont, bg=P["papel"])
        fila.pack(fill="x", pady=(12, 6))
        for i, (etiqueta, valor, pie, color, clave, unidad) in enumerate(celdas):
            ui.tarjeta_cifra(fila, etiqueta, valor, pie, color, ayuda(clave), unidad).grid(row=0, column=i, sticky="nsew",
                                                                                          padx=(0 if i == 0 else 6, 0))
            fila.columnconfigure(i, weight=1)

    def _grafico(self, cont, fig, clave=None, alto=None):
        ui.Grafico(cont, fig, alto).pack(fill="x", pady=(14, 4))
        if clave and self.r:
            if clave in self.r.indicadores:
                textos = niveles(self.r, clave)
            else:
                # Sin indicador propio: la lectura rapida es la conclusion que dice el titulo del grafico
                textos = self._niveles_glosario(clave)
                if getattr(fig, "titulo", ""):
                    textos["rapida"] = fig.titulo
            ui.QueSignifica(cont, textos, ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=(0, 6))

    @staticmethod
    def _niveles_glosario(clave):
        g = GLOSARIO["indicadores"].get(clave, {})
        return {"rapida": g.get("nombre", ""), "intermedia": " ".join(g.get("explicacion_simple", "").split()),
                "tecnica": " ".join(g.get("nota_tecnica", "").split())}

    def vacio(self):
        for panel in self.paneles.values():
            panel.limpiar()
            ui.titular(panel.interior, "Todavía no hay datos.", tam=26).pack(fill="x", pady=30)
            ui.parrafo(panel.interior, "Pulsa «↓ DESCARGAR SEMANA» para bajar la última semana del COES, o «↻ AHORA» "
                                       "para ver el precio en vivo.").pack(fill="x")

    # ----- pestanas -----

    def vista_senal(self):
        r, n = self.r, self.n
        panel = self.paneles["senal"]
        panel.limpiar()
        c = panel.interior
        heroe = tk.Frame(c, bg=P["papel"])
        heroe.pack(fill="x", pady=(10, 0))
        izq = tk.Frame(heroe, bg=P["papel"])
        izq.pack(side="left", fill="both", expand=True, padx=(0, 22))
        ui.kicker(izq, "01 / La señal de la semana").pack(fill="x", pady=(16, 6))
        ui.titular(izq, n.titulares[0] if n.titulares else r.texto_semana, tam=40, ancho=640).pack(fill="x")
        ui.parrafo(izq, f"{r.texto_semana}. Precios, demanda y generación del SEIN con datos públicos, método visible "
                        "y contexto." + (" Datos preliminares: pueden cambiar." if r.es_preliminar else ""),
                   ancho=620).pack(fill="x", pady=(12, 0))

        caja = ui.caja_oscura(heroe)
        caja.pack(side="right", fill="y")
        prom = r.ind("cmg_promedio")
        ui.kicker(caja, f"Costo marginal promedio / {r.barra_referencia.title()} kV", color=P["lima"]).pack(fill="x")
        tk.Label(caja, text=soles(prom.valor, False), font=(ui.F["titulares"], 52, "bold"), fg=P["papel"],
                 bg=P["tinta"]).pack(anchor="w", pady=(10, 0))
        tk.Label(caja, text="por MWh · promedio de la semana", font=(ui.F["mono"], 8), fg="#C1C7B8", bg=P["tinta"]).pack(anchor="w")
        texto, _ = variacion(prom, invertir=True)
        ui.insignia(caja, texto.upper()).pack(anchor="w", pady=(12, 8))
        if not r.serie_cmg.empty:
            diario = r.serie_cmg.groupby("fecha")["valor"].mean()
            ui.Grafico(caja, G.sparkline(diario), alto=70, borde=False).pack(fill="x")

        ui.seccion(c, "El pulso en cuatro cifras", r.texto_semana).pack(fill="x", pady=(26, 0))
        dm, ren, emb = r.ind("demanda_maxima"), r.ind("participacion_renovable"), r.ind("volumen_embalses")
        self._cifras(c, [
            ("Costo marginal medio", numero(prom.valor, 1), *variacion(prom, invertir=True), "cmg_promedio", "S/MWh"),
            ("Pico de demanda", numero(dm.valor), *variacion(dm), "demanda_maxima", "MW"),
            ("Generación renovable*", porcentaje(ren.valor), *variacion(ren, puntos=True), "participacion_renovable", ""),
            ("Agua en embalses", numero(emb.valor, 1) if emb.valor else "s/d", *variacion(emb), "volumen_embalses", "Hm3"),
        ])
        ui.parrafo(c, "*Incluye hidro. Sin hidro: " + porcentaje(r.ind("participacion_renovable_sin_hidro").valor)
                   + ". Pasa el mouse por cada cifra para ver qué significa.", tam=9, color=P["gris"]).pack(fill="x")

        ui.seccion(c, "Lo que merece atención", "Hechos detectados por reglas").pack(fill="x", pady=(26, 8))
        fila = tk.Frame(c, bg=P["papel"])
        fila.pack(fill="x")
        for i, (h, titular) in enumerate(zip(r.hechos, n.titulares, strict=False)):
            tarjeta = tk.Frame(fila, bg=P["papel"])
            tarjeta.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 14, 0))
            fila.columnconfigure(i, weight=1, uniform="hechos")
            ui.regla(tarjeta, 3, P["tinta"]).pack(fill="x")
            ui.kicker(tarjeta, f"Señal {i + 1:02d} / {CATEGORIA_HECHO.get(h.clave, 'Sistema')}").pack(fill="x", pady=(8, 4))
            tk.Label(tarjeta, text=titular, font=(ui.F["texto"], 12, "bold"), fg=P["tinta"], bg=P["papel"], anchor="w",
                     justify="left", wraplength=360).pack(fill="x")
            ui.parrafo(tarjeta, explicar_hecho(h, r), tam=9, color="#55584F", ancho=360).pack(fill="x", pady=(6, 0))

        dato = en_simple(r)
        if dato:
            caja = tk.Frame(c, bg=P["lima"], padx=18, pady=16)
            caja.pack(fill="x", pady=(26, 10))
            ui.kicker(caja, "En simple", color=P["verde"], bg=P["lima"]).pack(fill="x")
            ui.titular(caja, dato["titulo"].upper(), tam=20, bg=P["lima"], ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=(6, 4))
            ui.parrafo(caja, " ".join(dato["texto"].split()), color=P["tinta"], bg=P["lima"], ancho=ANCHO_TEXTO + 150).pack(fill="x")

    def vista_ahora(self):
        e = self.e
        panel = self.paneles["ahora"]
        panel.limpiar()
        c = panel.interior
        ui.kicker(c, "02 / Cuánto COESta ahora").pack(fill="x", pady=(18, 4))
        ui.titular(c, "El precio en este momento, con memoria.", tam=26).pack(fill="x")
        fila_auto = tk.Frame(c, bg=P["papel"])
        fila_auto.pack(fill="x", pady=(6, 0))
        tk.Checkbutton(fila_auto, text="Consultar al COES cada 30 minutos mientras la app esté abierta", variable=self.auto,
                       font=(ui.F["mono"], 8), bg=P["papel"], fg=P["gris"], activebackground=P["papel"],
                       selectcolor=P["blanco"]).pack(side="left")
        if e is None or e.sin_datos:
            ui.parrafo(c, "Todavía no hay datos en vivo. Pulsa «↻ AHORA»: la primera vez baja ayer y hoy (unos 2 minutos).",
                       ancho=ANCHO_TEXTO).pack(fill="x", pady=20)
            return

        caja = ui.caja_oscura(c)
        caja.pack(fill="x", pady=(12, 0))
        izq = tk.Frame(caja, bg=P["tinta"])
        izq.pack(side="left", fill="y")
        ui.kicker(izq, f"Costo marginal en vivo / {e.barra.title()} kV · preliminar", color=P["lima"]).pack(fill="x")
        tk.Label(izq, text=soles(e.valor, False), font=(ui.F["titulares"], 60, "bold"), fg=P["papel"], bg=P["tinta"]).pack(anchor="w")
        tk.Label(izq, text=f"por MWh · intervalo que terminó el {dia_y_hora(e.momento)}", font=(ui.F["mono"], 8),
                 fg="#C1C7B8", bg=P["tinta"]).pack(anchor="w")
        antig = e.antiguedad_min or 0
        if antig > 90:
            texto, fondo = f"SIN DATOS NUEVOS DEL COES HACE {antig / 60:.1f} H · SE MUESTRA EL ÚLTIMO", P["cobre"]
        else:
            texto, fondo = f"PUBLICADO HACE {antig:.0f} MIN", P["lima"]
        ui.insignia(izq, texto, fondo=fondo).pack(anchor="w", pady=(10, 0))
        ult = e.ultima_extraccion
        if ult:
            tk.Label(izq, text=f"Última consulta al COES: {ult['fin'][11:16]} · {ult['nuevos']} valores nuevos, "
                               f"{ult['revisados']} revisados", font=(ui.F["mono"], 8), fg="#9A9C92", bg=P["tinta"]).pack(anchor="w", pady=(8, 0))

        der = tk.Frame(caja, bg=P["tinta"])
        der.pack(side="right", padx=(30, 0))
        for ref in e.referencias:
            bloque = tk.Frame(der, bg=P["tinta"])
            bloque.pack(anchor="e", pady=4)
            tk.Label(bloque, text=f"VS {ref.nombre.upper()}", font=(ui.F["mono"], 8), fg="#9A9C92", bg=P["tinta"]).pack(anchor="e")
            if ref.var is None:
                txt, color = "s/d", "#9A9C92"
            else:
                txt = f"{'▲' if ref.var > 0 else '▼'} {abs(ref.var) * 100:.1f}%  ({soles(ref.valor, False)})"
                color = P["cobre"] if ref.var > 0 else P["lima"]
            tk.Label(bloque, text=txt, font=(ui.F["titulares"], 18, "bold"), fg=color, bg=P["tinta"]).pack(anchor="e")

        ui.seccion(c, "Alertas", "Reglas transparentes").pack(fill="x", pady=(22, 6))
        if e.alertas:
            for alerta in e.alertas:
                marco = tk.Frame(c, bg=P["blanco"], highlightthickness=2, highlightbackground=P["cobre"], padx=12, pady=8)
                marco.pack(fill="x", pady=3)
                ui.parrafo(marco, "⚠ " + alerta, bg=P["blanco"], color=P["tinta"], ancho=ANCHO_TEXTO + 150).pack(fill="x")
        else:
            ui.parrafo(c, "Sin alertas. " + (e.evaluacion.regla if e.evaluacion else ""), ancho=ANCHO_TEXTO + 150).pack(fill="x")

        umbrales = config.cargar_yaml("analisis")["umbrales_precio"]
        titulo = "La curva de hoy frente a la de ayer"
        if e.referencias[1].var is not None:
            titulo = (f"Hoy el precio va {abs(e.referencias[1].var) * 100:.0f}% "
                      f"{'por encima' if e.referencias[1].var > 0 else 'por debajo'} de ayer a esta hora")
        self._grafico(c, G.ahora(e.serie_hoy, e.serie_ayer, titulo, umbrales), "precio_ahora")

        if e.demanda:
            d = e.demanda
            ui.seccion(c, "Demanda ahora", "MW · preliminar").pack(fill="x", pady=(16, 0))
            desvio = "s/d" if d["desvio"] is None else f"{d['desvio'] * 100:+.1f}% vs lo programado"
            ayer = "s/d" if not d["ayer"] else f"{(d['valor'] / d['ayer'] - 1) * 100:+.1f}% vs ayer a esta hora"
            self._cifras(c, [
                ("Demanda del SEIN", numero(d["valor"]), dia_y_hora(d["momento"]), P["gris"], "demanda_maxima", "MW"),
                ("Frente al programa del COES", desvio.split(" ")[0], " ".join(desvio.split(" ")[1:]), P["gris"],
                 "error_programa_diario", ""),
                ("Frente a ayer", ayer.split(" ")[0], " ".join(ayer.split(" ")[1:]), P["gris"], "demanda_maxima", ""),
            ])
        ui.parrafo(c, f"Historial de versiones: el COES corrigió {e.revisiones} valores de {e.barra.title()} después de "
                      "publicarlos. Se guardan todas las versiones para medir cuánto cambia el dato preliminar.",
                   tam=9, color=P["gris"], ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=(10, 20))

    def vista_precios(self):
        r, n = self.r, self.n
        panel = self.paneles["precios"]
        panel.limpiar()
        c = panel.interior
        self._encabezado(c, "03", "Precios", n.titulos_graficos.get("precios_serie", "Precios"), n.parrafos["precios"])
        mx, mn, alto, bajo = r.ind("cmg_maximo"), r.ind("cmg_minimo"), r.ind("horas_precio_alto"), r.ind("horas_precio_bajo")
        self._cifras(c, [
            ("Precio más alto", numero(mx.valor, 1), dia_y_hora(mx.momento) if mx.momento is not None else "", P["gris"],
             "cmg_maximo", "S/MWh"),
            ("Precio más bajo", numero(mn.valor, 1), dia_y_hora(mn.momento) if mn.momento is not None else "", P["gris"],
             "cmg_minimo", "S/MWh"),
            ("Horas con precio alto", numero(alto.valor, 1), *variacion(alto, invertir=True), "horas_precio_alto", "h"),
            ("Horas con precio bajo", numero(bajo.valor, 1), *variacion(bajo), "horas_precio_bajo", "h"),
        ])
        if not r.serie_cmg.empty:
            self._grafico(c, G.precio_semana(r.serie_cmg, r.umbrales_precio, n.titulos_graficos["precios_serie"]), "cmg_promedio")
        if "precios_perfil" in n.titulos_graficos:
            self._grafico(c, G.perfil_horario(r.perfil_cmg, n.titulos_graficos["precios_perfil"]), "perfil_horario")
        ui.seccion(c, "Rarezas de la semana", f"{r.n_rarezas} detectadas").pack(fill="x", pady=(18, 6))
        if r.rarezas:
            for rz in r.rarezas:
                ui.parrafo(c, f"• {dia_y_hora(rz['fecha_hora'])}: {rz['regla']}", ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=2)
        else:
            ui.parrafo(c, "Ninguna media hora rompió el rango visto a su misma hora en las 4 semanas previas.",
                       ancho=ANCHO_TEXTO + 150).pack(fill="x")
        ui.QueSignifica(c, self._niveles_glosario("rarezas"), ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=(4, 0))
        if r.revision:
            rv = r.revision
            ui.seccion(c, "Lo que el sistema creía", "Preliminar vs confirmado").pack(fill="x", pady=(18, 6))
            ui.parrafo(c, f"De {rv['intervalos']} medias horas con ambas versiones, el COES cambió {rv['cambiados']} al "
                          f"confirmar el dato. En promedio el precio se movió {soles(rv['diferencia_media_abs'])} "
                          f"({porcentaje(rv['diferencia_media_pct'])}); el mayor cambio fue de {soles(rv['max_abs'])}, "
                          f"el {dia_y_hora(rv['momento_max'])}.", ancho=ANCHO_TEXTO + 150).pack(fill="x")
            ui.QueSignifica(c, niveles(r, "revision_cmg"), ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=(4, 20))

    def vista_demanda(self):
        r, n = self.r, self.n
        panel = self.paneles["demanda"]
        panel.limpiar()
        c = panel.interior
        self._encabezado(c, "04", "Demanda", n.titulos_graficos.get("demanda", "Demanda"), n.parrafos["demanda"])
        dm, ene, err = r.ind("demanda_maxima"), r.ind("energia_semana"), r.ind("error_programa_diario")
        self._cifras(c, [
            ("Demanda máxima", numero(dm.valor), *variacion(dm), "demanda_maxima", "MW"),
            ("Energía de la semana", numero(ene.valor), *variacion(ene), "energia_semana", "GWh"),
            ("Diferencia con lo programado", porcentaje(err.valor), "promedio de la semana", P["gris"], "error_programa_diario", ""),
        ])
        if not r.serie_demanda.empty:
            self._grafico(c, G.demanda(r.serie_demanda, n.titulos_graficos["demanda"]), "demanda_maxima")
        ui.QueSignifica(c, niveles(r, "energia_semana"), "Energía de la semana: ¿qué significa?",
                        ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=(0, 20))

    def vista_generacion(self):
        r, n = self.r, self.n
        panel = self.paneles["generacion"]
        panel.limpiar()
        c = panel.interior
        self._encabezado(c, "05", "Generación", n.titulos_graficos.get("generacion", "Generación"), n.parrafos["generacion"])
        ren, sin = r.ind("participacion_renovable"), r.ind("participacion_renovable_sin_hidro")
        sol, eol = r.ind("precio_capturado_solar"), r.ind("precio_capturado_eolica")
        self._cifras(c, [
            ("Renovable con hidro", porcentaje(ren.valor), *variacion(ren, puntos=True), "participacion_renovable", ""),
            ("Renovable sin hidro", porcentaje(sin.valor), *variacion(sin, puntos=True), "participacion_renovable_sin_hidro", ""),
            ("Precio capturado solar", numero(sol.valor, 1) if sol.valor else "s/d", *variacion(sol), "precio_capturado_solar", "S/MWh"),
            ("Precio capturado eólica", numero(eol.valor, 1) if eol.valor else "s/d", *variacion(eol), "precio_capturado_eolica", "S/MWh"),
        ])
        if r.mix:
            self._grafico(c, G.generacion(r.serie_generacion, n.titulos_graficos["generacion"]), "mix_generacion")
            self._grafico(c, G.mix(r.mix, r.mix_anterior, "Participación de cada fuente"), "participacion_renovable")
        ui.QueSignifica(c, niveles(r, "precio_capturado_solar"), "Precio capturado: ¿qué significa?",
                        ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=(0, 20))

    def vista_hidro(self):
        r, n = self.r, self.n
        panel = self.paneles["hidro"]
        panel.limpiar()
        c = panel.interior
        self._encabezado(c, "06", "Hidrología", n.titulos_graficos.get("embalses", "Hidrología"), n.parrafos["hidrologia"])
        if not r.serie_embalses.empty:
            self._grafico(c, G.embalses(r.serie_embalses, n.titulos_graficos["embalses"]), "volumen_embalses")
            self._grafico(c, G.embalses_detalle(r.embalses_detalle, "Los embalses con más agua"))
        ui.parrafo(c, "Se suman los embalses que reportan volumen útil en el IEOD. Algunos solo reportan nivel (metros sobre "
                      "el nivel del mar) y no entran en la suma.", tam=9, color=P["gris"]).pack(fill="x", pady=(4, 20))

    def vista_mapa(self):
        r, n = self.r, self.n
        panel = self.paneles["mapa"]
        panel.limpiar()
        c = panel.interior
        barras = r.cmg_barras.dropna(subset=["latitud"]) if not r.cmg_barras.empty else r.cmg_barras
        self._encabezado(c, "07", "El mapa del costo eléctrico", n.titulos_graficos.get("mapa", "Mapa"),
                         "Precio promedio de la semana en cada barra del sistema. Pasa el mouse por un punto para ver su nombre.")
        if barras.empty:
            ui.parrafo(c, "No hay datos por barra para esta semana.").pack(fill="x")
            return
        fila = tk.Frame(c, bg=P["papel"])
        fila.pack(fill="x", pady=(10, 0))
        ui.Grafico(fila, G.mapa(r.cmg_barras, n.titulos_graficos.get("mapa", ""))).pack(side="left")
        lado = tk.Frame(fila, bg=P["papel"])
        lado.pack(side="left", fill="both", expand=True, padx=(24, 0))
        for titulo, datos in (("Las 5 más caras", barras.nlargest(5, "cmg_promedio")),
                              ("Las 5 más baratas", barras.nsmallest(5, "cmg_promedio"))):
            ui.seccion(lado, titulo).pack(fill="x", pady=(8, 4))
            for _, f in datos.iterrows():
                linea = tk.Frame(lado, bg=P["papel"])
                linea.pack(fill="x")
                tk.Label(linea, text=f["barra"].title(), font=(ui.F["texto"], 10), bg=P["papel"]).pack(side="left")
                tk.Label(linea, text=soles(f["cmg_promedio"]), font=(ui.F["mono"], 9), fg=P["verde"],
                         bg=P["papel"]).pack(side="right")
                ui.regla(lado).pack(fill="x")
        diferencia = barras["cmg_promedio"].max() - barras["cmg_promedio"].min()
        ui.parrafo(lado, f"Entre la barra más cara y la más barata hubo {soles(diferencia)} de diferencia en promedio. "
                         f"Se muestran {len(barras)} barras con coordenadas públicas de {len(r.cmg_barras)} con precio.",
                   tam=9, color=P["gris"], ancho=380).pack(fill="x", pady=(10, 0))
        ui.QueSignifica(c, self._niveles_glosario("mapa_cmg"), ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=(10, 20))

    def vista_metodo(self):
        r = self.r
        panel = self.paneles["metodo"]
        panel.limpiar()
        c = panel.interior
        self._encabezado(c, "08", "Método y fuentes", "La confianza también forma parte del diseño",
                         "De dónde sale cada dato, cada cuánto se actualiza y en qué estado está. Los huecos se muestran, "
                         "no se rellenan en silencio.")
        fuentes = config.fuentes()
        est = estado.leer()
        # costo_marginal_tr se baja dentro de costo_marginal: no tiene registro propio
        filas = [(n, f) for n, f in fuentes["fuentes"].items() if n != "costo_marginal_tr"]
        filas += [(f"ahora_{n}", f) for n, f in fuentes["ahora"].items() if isinstance(f, dict)]
        tabla = tk.Frame(c, bg=P["linea"])
        tabla.pack(fill="x", pady=(14, 0))
        cabecera = ("Fuente", "Qué trae", "Frecuencia", "Retraso", "Estado del dato", "Última extracción OK")
        anchos = (16, 46, 12, 12, 14, 22)
        for j, peso in enumerate((2, 6, 2, 2, 2, 3)):
            tabla.columnconfigure(j, weight=peso)
        for j, (texto, ancho) in enumerate(zip(cabecera, anchos, strict=True)):
            tk.Label(tabla, text=texto.upper(), font=(ui.F["mono"], 8), bg=P["tinta"], fg=P["papel"], anchor="w",
                     width=ancho, padx=6, pady=6).grid(row=0, column=j, sticky="nsew", padx=(0, 1), pady=(0, 1))
        for i, (nombre, f) in enumerate(filas, start=1):
            ult = est.get(nombre, {})
            exito = ult.get("ultima_extraccion_exitosa", "sin registro")
            exito = exito.replace("T", " ")[:16] if exito != "sin registro" else exito
            if ult.get("ultimo_error"):
                exito += "  ⚠ último intento falló"
            valores = (nombre.replace("_", " "), f.get("descripcion", ""), f.get("frecuencia_objetivo", ""),
                       f.get("retraso_esperado", ""), f.get("estado_dato", "").replace("_", " "), exito)
            for j, (v, ancho) in enumerate(zip(valores, anchos, strict=True)):
                tk.Label(tabla, text=v, font=(ui.F["texto"], 9), bg=P["blanco"], fg=P["tinta"], anchor="nw", justify="left",
                         width=ancho, wraplength=ancho * 7, padx=6, pady=6).grid(row=i, column=j, sticky="nsew",
                                                                                 padx=(0, 1), pady=(0, 1))
        ui.parrafo(c, "Páginas públicas para verificar: " + " · ".join(sorted({f.get('url_fuente', '') for _, f in filas
                                                                               if f.get('url_fuente')})),
                   tam=8, color=P["gris"], ancho=ANCHO_TEXTO + 200).pack(fill="x", pady=(6, 0))

        ui.seccion(c, "Calidad de esta semana", f"{len(r.avisos)} avisos").pack(fill="x", pady=(22, 6))
        if r.avisos:
            for aviso in r.avisos:
                ui.parrafo(c, "• " + aviso, tam=9, ancho=ANCHO_TEXTO + 150).pack(fill="x")
        else:
            ui.parrafo(c, "Sin avisos: no hubo duplicados, huecos ni valores fuera de rango.").pack(fill="x")

        ui.seccion(c, "Reglas editoriales").pack(fill="x", pady=(22, 6))
        reglas = [("Fuente", "Nombre de publicación, URL, fecha de extracción y periodo cubierto.", "Nunca ocultar de dónde sale el dato."),
                  ("Calidad", "Última observación, faltantes, duplicados y estado preliminar o revisado.",
                   "Mostrar los huecos en vez de rellenarlos silenciosamente."),
                  ("Comparación", "Periodo actual y periodo de referencia exactos.", "Comparar ventanas equivalentes."),
                  ("Narrativa", "Regla que disparó el hecho y variables utilizadas.", "Describir la señal, no inventar la causa.")]
        tabla = tk.Frame(c, bg=P["linea"])
        tabla.pack(fill="x")
        for j, texto in enumerate(("Capa", "Qué mostrar", "Regla editorial")):
            tk.Label(tabla, text=texto.upper(), font=(ui.F["mono"], 8), bg=P["tinta"], fg=P["papel"], anchor="w", padx=8,
                     pady=6).grid(row=0, column=j, sticky="nsew", padx=(0, 1), pady=(0, 1))
        for i, fila in enumerate(reglas, start=1):
            for j, texto in enumerate(fila):
                tk.Label(tabla, text=texto, font=(ui.F["texto"], 9), bg=P["blanco"], anchor="w", justify="left",
                         wraplength=420, padx=8, pady=6).grid(row=i, column=j, sticky="nsew", padx=(0, 1), pady=(0, 1))
        for j, peso in enumerate((1, 3, 3)):
            tabla.columnconfigure(j, weight=peso)
        caja = tk.Frame(c, bg=P["lima"], padx=16, pady=12)
        caja.pack(fill="x", pady=(22, 20))
        ui.parrafo(caja, "Independencia: " + " ".join(PROYECTO["aviso"].split()) + " Las cifras citan fuentes públicas, "
                         "muestran la fecha de extracción y distinguen datos preliminares de revisados.",
                   color=P["tinta"], bg=P["lima"], ancho=ANCHO_TEXTO + 150).pack(fill="x")

    def vista_glosario(self):
        panel = self.paneles["glosario"]
        panel.limpiar()
        c = panel.interior
        self._encabezado(c, "09", "Glosario", "Todo lo que ves, explicado en tres niveles",
                         "Lectura rápida, explicación sencilla y nota técnica. Es la misma fuente que usa el PDF.")
        for grupo in ("indicadores", "terminos"):
            ui.seccion(c, "Indicadores" if grupo == "indicadores" else "Términos").pack(fill="x", pady=(18, 4))
            for g in sorted(GLOSARIO[grupo].values(), key=lambda x: x["nombre"]):
                bloque = tk.Frame(c, bg=P["papel"])
                bloque.pack(fill="x", pady=(8, 0))
                ui.regla(bloque).pack(fill="x", pady=(0, 6))
                tk.Label(bloque, text=g["nombre"].upper(), font=(ui.F["titulares"], 15, "bold"), bg=P["papel"],
                         anchor="w").pack(fill="x")
                ui.parrafo(bloque, " ".join(g["explicacion_simple"].split()), ancho=ANCHO_TEXTO + 150).pack(fill="x")
                ui.parrafo(bloque, "Por qué importa: " + g["por_que_importa"], tam=9, color=P["verde"],
                           ancho=ANCHO_TEXTO + 150).pack(fill="x", pady=(2, 0))
                if g.get("nota_tecnica"):
                    tk.Label(bloque, text="NOTA TÉCNICA · " + " ".join(g["nota_tecnica"].split()), font=(ui.F["mono"], 8),
                             fg=P["gris"], bg=P["papel"], anchor="w", justify="left",
                             wraplength=ANCHO_TEXTO + 150).pack(fill="x", pady=(2, 0))
        tk.Frame(c, height=20, bg=P["papel"]).pack()

    def correr(self):
        self.raiz.mainloop()


def main():
    """Abre la app de escritorio."""
    configurar_logging()
    App().correr()


if __name__ == "__main__":
    main()
