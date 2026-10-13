"""Cuanto COESta: aplicacion de escritorio (Tkinter, sin navegador).

Uso (desde la raiz del proyecto):  python app/escritorio.py

Menu lateral con: Resumen, Ahora, Precios, Demanda, Generacion, Embalses, Mapa,
Fuentes y Glosario. Informacion puntual en tarjetas; las explicaciones van en el
boton "i" de cada cifra. El PDF semanal es opcional (boton).
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
from src.ahora.memoria import estado_precio, programa_ahora  # noqa: E402
from src.analysis import calcular_resumen  # noqa: E402
from src.narrative import generar_narrativa  # noqa: E402
from src.utils import config, estado  # noqa: E402
from src.utils.datos import leer_tabla, ruta_tabla, semanas_disponibles  # noqa: E402
from src.utils.estilo import familias_tk, registrar_fuentes_tk  # noqa: E402
from src.analysis import centrales, serie  # noqa: E402
from src.utils.fechas import dia_y_hora, hoy_peru, texto_semana, ultima_semana_completa  # noqa: E402
from src.utils.formato import numero, porcentaje  # noqa: E402
from src.utils.logs import configurar_logging, obtener_logger  # noqa: E402
from src.visual import graficos as G  # noqa: E402

log = obtener_logger("escritorio")
P = ui.P
PROYECTO = config.proyecto()
GLOSARIO = config.glosario()

SECCIONES = [
    ("resumen", "Resumen", "▦"), ("ahora", "Ahora", "◷"), ("evolucion", "Evolución", "≋"), ("precios", "Precios", "↗"),
    ("demanda", "Demanda", "∿"), ("generacion", "Generación", "☀"), ("embalses", "Embalses", "◍"),
    ("eventos", "Eventos", "⚠"), ("centrales", "Centrales", "⌁"), ("mapa", "Mapa", "⌖"), ("fuentes", "Fuentes", "≡"), ("glosario", "Glosario", "?"),
]


# ---------- formato ----------

def soles(v):
    """Monto en soles o s/d."""
    return "s/d" if v is None else f"S/ {numero(v, 1)}"


def cambio(ind, invertir=False, puntos=False, neutral=False):
    """(texto, tono) de la variacion vs la semana anterior."""
    if ind is None or ind.var_anterior is None:
        return "sin comparación", "neutro"
    v = ind.var_anterior
    cifra = f"{abs(v) * 100:.1f} pp" if puntos else f"{abs(v) * 100:.1f}%"
    texto = f"{'▲' if v > 0 else '▼'} {cifra} vs semana pasada"
    if neutral or abs(v) < 0.001:
        return texto, "neutro"
    bueno = (v < 0) if invertir else (v > 0)
    return texto, "bueno" if bueno else "malo"


def explicacion(clave):
    """Una o dos lineas del glosario para el boton i."""
    g = GLOSARIO["indicadores"].get(clave) or GLOSARIO["terminos"].get(clave)
    return " ".join(g["explicacion_simple"].split()) if g else ""


def rango_corto(semana):
    """'28 de setiembre al 4 de octubre de 2026'."""
    return texto_semana(semana).replace("Semana del ", "")


def hora_corta(momento):
    """'11:00 a. m.'."""
    hora = momento.hour % 12 or 12
    return f"{hora}:{momento.minute:02d} {'a. m.' if momento.hour < 12 else 'p. m.'}"


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
            # Nitido en pantallas con escala (125 %, 150 %)
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except (AttributeError, OSError):
                pass
        self.raiz = tk.Tk()
        self.raiz.title(PROYECTO["nombre"])
        ancho = min(1440, int(self.raiz.winfo_screenwidth() * 0.9))
        alto = min(940, int(self.raiz.winfo_screenheight() * 0.88))
        self.raiz.geometry(f"{ancho}x{alto}+20+10")
        self.raiz.minsize(1100, 700)
        ui.configurar(self.raiz, familias_tk(self.raiz))
        self.cola = queue.Queue()
        self.ocupado = False
        self.pendientes = []
        self.r = self.n = self.e = None
        self.prog = {}
        self.auto = tk.BooleanVar(value=True)
        self.descarga_inicial_hecha = False
        # Estado de la seccion Evolucion
        self.ev_datos = None
        self.ev_barra = config.cargar_yaml("analisis")["barra_referencia"]
        self.ev_moneda = "S/"
        self.ev_desde, self.ev_hasta = serie.rango_atajo("30d", hoy_peru(), None)
        self.lista = semanas_completas()[::-1]
        self.indice_semana = 0
        if self.lista and ultima_semana_completa() in self.lista:
            self.indice_semana = self.lista.index(ultima_semana_completa())
        self._construir()
        self.raiz.after(150, self._revisar_cola)
        self.raiz.after(300, self.cargar_semana)
        self.raiz.after(400, self.cargar_ahora)
        self._programar_auto()

    # ----- estructura -----

    def _construir(self):
        self.menu = ui.MenuLateral(self.raiz, PROYECTO["nombre"], SECCIONES, self.ir_a)
        self.menu.pack(side="left", fill="y")
        # Actualizar ahora y sello de frescura, visibles desde cualquier seccion
        vivo = tk.Frame(self.menu, bg=P["marino"])
        vivo.pack(side="bottom", fill="x", pady=(0, 12))
        self.sello = tk.Label(vivo, text="Sin datos en vivo", font=ui.fuente(9), bg=P["marino"], fg="#C9D8EA",
                              justify="left", anchor="w")
        self.sello.pack(fill="x", pady=(0, 8))
        ui.boton(vivo, "↻  Actualizar ahora", self.actualizar_ahora,
                 ayuda="Trae el último precio y la demanda del COES (segundos). Si la PC estuvo apagada, "
                       "rellena los días que faltan.").pack(fill="x")
        derecha = tk.Frame(self.raiz, bg=P["papel"])
        derecha.pack(side="left", fill="both", expand=True)
        self.paneles = {}
        for clave, _, _ in SECCIONES:
            self.paneles[clave] = ui.PanelScroll(derecha)
        barra = tk.Frame(derecha, bg=P["papel"], padx=36, pady=6)
        barra.pack(side="bottom", fill="x")
        self.estado = tk.Label(barra, text="Listo.", font=ui.fuente(9), fg=P["gris"], bg=P["papel"], anchor="w")
        self.estado.pack(side="left")
        tk.Label(barra, text="No afiliado al COES", font=ui.fuente(9), fg=P["gris"], bg=P["papel"]).pack(side="right")
        self.botones = []
        self.ir_a("resumen")

    def ir_a(self, clave):
        for panel in self.paneles.values():
            panel.pack_forget()
        self.paneles[clave].pack(side="top", fill="both", expand=True)
        self.menu.marcar(clave)

    # ----- trabajo en segundo plano -----

    def _en_fondo(self, mensaje, tarea, al_terminar):
        if self.ocupado:
            if not any(m == mensaje for m, _, _ in self.pendientes):
                self.pendientes.append((mensaje, tarea, al_terminar))
            return
        self.ocupado = True
        self.avisar(mensaje + "...")

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
                if error:
                    self.avisar(f"No se pudo completar: {error}")
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
                self.actualizar_ahora()
            self.raiz.after(minutos * 60 * 1000, tic)

        self.raiz.after(minutos * 60 * 1000, tic)

    # ----- acciones -----

    def semana(self):
        return self.lista[self.indice_semana] if self.lista else None

    def cargar_semana(self):
        semana = self.semana()
        if not semana:
            # Primera vez (por ejemplo, recien descargado de GitHub): baja la ultima semana sola, una vez
            primera = not self.descarga_inicial_hecha
            mensaje = ("Primera vez: bajando la última semana del COES (2 a 3 minutos)..." if primera
                       else "Todavía no hay datos. Pulsa «Actualizar» en Resumen.")
            for panel in self.paneles.values():
                panel.limpiar()
                ui.texto(panel.interior, mensaje, 14, peso="bold").pack(anchor="w")
            self.vista_resumen_vacia(mensaje)
            if primera:
                self.descarga_inicial_hecha = True
                self.descargar_semana()
            return

        def tarea():
            r = calcular_resumen(semana)
            return r, generar_narrativa(r)

        self._en_fondo("Cargando la semana", tarea, self._mostrar_semana)

    def _mostrar_semana(self, resultado):
        self.r, self.n = resultado
        for vista in (self.vista_resumen, self.vista_precios, self.vista_demanda, self.vista_generacion,
                      self.vista_embalses, self.vista_eventos, self.vista_centrales, self.vista_mapa,
                      self.vista_fuentes, self.vista_glosario):
            vista()
        if self.ev_datos is None:
            self.cargar_evolucion()
        self.avisar("Semana cargada.")

    def cargar_ahora(self):
        """Al abrir: muestra lo guardado y, si tiene mas de 40 min (o hay huecos), consulta al COES."""
        def listo(resultado):
            self._mostrar_ahora(resultado)
            e = resultado[0]
            if e.sin_datos or (e.antiguedad_min or 0) > 40:
                self.actualizar_ahora()

        self._en_fondo("Leyendo el último precio", lambda: (estado_precio(), programa_ahora()), listo)

    def actualizar_ahora(self):
        from src.ahora.extractor import actualizar

        def tarea():
            hay_base = (config.DIR_DATA / "ahora" / "ahora.sqlite").exists()
            actualizar(desde_ayer=not hay_base)
            return estado_precio(), programa_ahora()

        self._en_fondo("Consultando al COES", tarea, self._mostrar_ahora)

    def _mostrar_ahora(self, resultado):
        e, self.prog = resultado
        self.e = e
        self.vista_ahora()
        self._frescura()
        if not e.sin_datos:
            self.avisar(f"Precio ahora: {soles(e.valor)} por MWh.")

    def _frescura(self):
        """Sello del menu lateral: hora del ultimo dato, antiguedad y estado."""
        e = self.e
        if e is None or e.sin_datos:
            self.sello.configure(text="Sin datos en vivo", fg="#C9D8EA")
            return
        antig = e.antiguedad_min or 0
        viejo = antig > 60
        cuando = f"hace {antig:.0f} min" if antig < 120 else f"hace {antig / 60:.0f} h"
        self.sello.configure(text=f"● Último dato {hora_corta(e.momento)}\n   {cuando} · preliminar",
                             fg=P["naranja"] if viejo else "#9BE0B8")

    def descargar_semana(self):
        import run_weekly
        semana = ultima_semana_completa()

        def tarea():
            run_weekly.correr(semana, historico=1, descargar=True, pdf=False)
            return semana

        def listo(s):
            self.lista = semanas_completas()[::-1]
            self.indice_semana = self.lista.index(s) if s in self.lista else 0
            self.cargar_semana()

        self._en_fondo("Descargando la última semana (2 a 3 minutos)", tarea, listo)

    def generar_pdf(self):
        from src.report import generar_pdf
        semana = self.semana()
        if semana:
            self._en_fondo("Generando el PDF", lambda: generar_pdf(semana),
                           lambda ruta: (abrir_archivo(ruta), self.avisar("PDF listo.")))

    def elegir_semana(self, _evento=None):
        self.indice_semana = self.combo.current()
        self.cargar_semana()

    # ----- piezas -----

    def _cabecera(self, cont, titulo, subtitulo, con_controles=False):
        fila = tk.Frame(cont, bg=P["papel"])
        fila.pack(fill="x", pady=(0, 20))
        izq = tk.Frame(fila, bg=P["papel"])
        izq.pack(side="left")
        ui.texto(izq, titulo, 22, peso="xbold").pack(anchor="w")
        ui.texto(izq, subtitulo, 11, P["gris"]).pack(anchor="w", pady=(2, 0))
        if con_controles:
            der = tk.Frame(cont, bg=P["papel"])
            der.pack(fill="x", pady=(0, 18))
            ui.texto(der, "Semana", 9, P["gris"], "bold").pack(side="left", padx=(0, 8))
            self.combo = ttk.Combobox(der, state="readonly", width=28,
                                      values=[rango_corto(s) for s in self.lista], font=ui.fuente(10))
            if self.lista:
                self.combo.current(self.indice_semana)
            self.combo.bind("<<ComboboxSelected>>", self.elegir_semana)
            self.combo.pack(side="left")
            ui.boton(der, "↻  Actualizar", self.descargar_semana,
                     ayuda="Baja la última semana del COES (2 a 3 minutos).").pack(side="left", padx=(10, 0))
            ui.boton(der, "Descargar PDF", self.generar_pdf, primario=False,
                     ayuda="Genera el informe de esta semana y lo abre.").pack(side="left", padx=(8, 0))

    def _fila(self, cont, columnas, pady=(0, 16), uniforme=True):
        fila = tk.Frame(cont, bg=P["papel"])
        fila.pack(fill="x", pady=pady)
        for i, peso in enumerate(columnas):
            fila.columnconfigure(i, weight=peso, uniform="c" if uniforme else None)
        return fila

    def _cifras(self, cont, celdas):
        fila = self._fila(cont, [1] * len(celdas))
        tam = 26 if len(celdas) <= 4 else 20     # con 5 tarjetas por fila, cifras mas chicas para que no se corten
        for i, c in enumerate(celdas):
            ui.tarjeta_cifra(fila, tam=c.pop("tam", tam), **c).grid(row=0, column=i, sticky="nsew",
                                                                    padx=(0 if i == 0 else 14, 0))

    def _tarjeta_grafico(self, padre, titulo, fig, nota="", alto=None):
        t = ui.tarjeta(padre)
        cab = tk.Frame(t, bg="#FFFFFF")
        cab.pack(fill="x")
        ui.texto(cab, titulo, 13, peso="bold").pack(side="left")
        if nota:
            ui.texto(cab, nota, 9, P["gris"]).pack(side="right")
        ui.Grafico(t, fig, alto).pack(fill="both", expand=True, pady=(10, 0))
        return t

    # ----- pantallas -----

    def vista_resumen_vacia(self, mensaje=None):
        panel = self.paneles["resumen"]
        panel.limpiar()
        self._cabecera(panel.interior, "Resumen de la semana", "Sin datos todavía", con_controles=True)
        if mensaje:
            ui.texto(panel.interior, mensaje, 14, peso="bold").pack(anchor="w")

    def vista_resumen(self):
        r, n = self.r, self.n
        panel = self.paneles["resumen"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Resumen de la semana", rango_corto(r.semana) + ("  ·  preliminar" if r.es_preliminar else ""),
                       con_controles=True)

        banda = tk.Frame(c, bg=P["celeste"], padx=18, pady=14)
        banda.pack(fill="x", pady=(0, 18))
        prom = r.ind("cmg_promedio")
        primero = r.hechos[0] if r.hechos else None
        if primero is not None and primero.tipo == "variacion":
            icono = "▲" if primero.datos["var"] > 0 else "▼"
        else:
            icono = "★" if primero is not None and primero.tipo == "record" else "●"
        tk.Label(banda, text=icono, font=ui.fuente(14, "bold"), bg=P["azul"], fg="#FFFFFF", width=3, pady=4).pack(side="left")
        ui.texto(banda, n.titulares[0] if n.titulares else r.texto_semana, 14, peso="bold", bg=P["celeste"]).pack(
            side="left", padx=(14, 0))

        dm, ren, emb = r.ind("demanda_maxima"), r.ind("participacion_renovable"), r.ind("volumen_embalses")
        t_prom, tono_prom = cambio(prom, invertir=True)
        t_dm, tono_dm = cambio(dm, neutral=True)
        t_ren, tono_ren = cambio(ren, puntos=True)
        t_emb, tono_emb = cambio(emb)
        self._cifras(c, [
            dict(etiqueta="Precio promedio", valor=soles(prom.valor), unidad="por MWh", cambio=t_prom, tono=tono_prom,
                 explicacion=explicacion("cmg_promedio")),
            dict(etiqueta="Demanda máxima", valor=numero(dm.valor), unidad="MW", cambio=t_dm, tono=tono_dm,
                 explicacion=explicacion("demanda_maxima")),
            dict(etiqueta="Energía renovable", valor=porcentaje(ren.valor), cambio=t_ren, tono=tono_ren,
                 explicacion=explicacion("participacion_renovable")),
            dict(etiqueta="Agua en embalses", valor=numero(emb.valor) if emb.valor else "s/d", unidad="Hm³",
                 cambio=t_emb, tono=tono_emb, explicacion=explicacion("volumen_embalses")),
        ])

        fila = self._fila(c, [2, 1], uniforme=False)
        if not r.perfil_cmg.empty and r.perfil_cmg["actual"].notna().any():
            imax = r.perfil_cmg["actual"].idxmax()
            hora, valor = int(r.perfil_cmg.loc[imax, "hora"]), r.perfil_cmg.loc[imax, "actual"]
            nota = f"Lo más caro: {hora % 12 or 12} {'a. m.' if hora < 12 else 'p. m.'}, {soles(valor)}"
            self._tarjeta_grafico(fila, "Precio por hora del día", G.perfil_horario(r.perfil_cmg), nota, alto=250).grid(
                row=0, column=0, sticky="nsew", padx=(0, 14))
        self._tarjeta_mix(fila).grid(row=0, column=1, sticky="nsew")

        destacado = ui.tarjeta(c)
        destacado.pack(fill="x", pady=(0, 16))
        ui.texto(destacado, "Lo destacado", 13, peso="bold").pack(anchor="w", pady=(0, 12))
        filas = tk.Frame(destacado, bg="#FFFFFF")
        filas.pack(fill="x")
        iconos = {"variacion": ("↕", "info"), "record": ("★", "alerta"), "rareza": ("!", "alerta"),
                  "anomalia": ("!", "alerta"), "dato": ("•", "neutro")}
        for i, (h, titular) in enumerate(zip(r.hechos, n.titulares, strict=False)):
            filas.columnconfigure(i, weight=1, uniform="d")
            item = tk.Frame(filas, bg="#FFFFFF")
            item.grid(row=0, column=i, sticky="nw", padx=(0, 16))
            simbolo, tono = iconos.get(h.tipo, ("•", "neutro"))
            fondo, color = ui.TONOS[tono]
            tk.Label(item, text=simbolo, font=ui.fuente(12, "bold"), bg=fondo, fg=color, width=3, pady=4).pack(side="left", anchor="n")
            ui.texto(item, titular, 10, peso="bold", bg="#FFFFFF", ancho=300).pack(side="left", padx=(10, 0))

    def _tarjeta_mix(self, padre):
        r = self.r
        t = ui.tarjeta(padre)
        ui.texto(t, "De dónde vino la energía", 13, peso="bold").pack(anchor="w")
        tecs = [k for k in sorted(r.mix, key=r.mix.get, reverse=True) if r.mix[k] >= 0.005]
        barra = tk.Canvas(t, height=16, bg="#FFFFFF", highlightthickness=0)
        barra.pack(fill="x", pady=(14, 14))

        def dibujar(_e=None):
            barra.delete("all")
            ancho, x = barra.winfo_width(), 0
            for k in tecs:
                w = ancho * r.mix[k]
                barra.create_rectangle(x, 0, x + w, 16, fill=config.color_tecnologia(k), width=0)
                x += w

        barra.bind("<Configure>", dibujar)
        for k in tecs:
            fila = tk.Frame(t, bg="#FFFFFF")
            fila.pack(fill="x", pady=3)
            tk.Label(fila, text="  ", bg=config.color_tecnologia(k)).pack(side="left")
            ui.texto(fila, config.nombre_tecnologia(k), 10, bg="#FFFFFF").pack(side="left", padx=(10, 0))
            ui.texto(fila, porcentaje(r.mix[k]), 10, peso="bold", bg="#FFFFFF").pack(side="right")
        sin = r.ind("participacion_renovable_sin_hidro")
        ui.texto(t, f"Renovable sin hidro: {porcentaje(sin.valor)}", 9, P["gris"], bg="#FFFFFF").pack(anchor="w", pady=(12, 0))
        return t

    def vista_ahora(self):
        e = self.e
        panel = self.paneles["ahora"]
        panel.limpiar()
        c = panel.interior
        fila = tk.Frame(c, bg=P["papel"])
        fila.pack(fill="x", pady=(0, 20))
        izq = tk.Frame(fila, bg=P["papel"])
        izq.pack(side="left")
        ui.texto(izq, "Ahora", 22, peso="xbold").pack(anchor="w")
        if e is not None and not e.sin_datos:
            antig = e.antiguedad_min or 0
            viejo = antig > 90
            estado_txt = (f"Sin datos nuevos del COES hace {antig / 60:.1f} h" if viejo
                          else f"Último dato hace {antig:.0f} min · se actualiza cada 30 min")
            linea = tk.Frame(izq, bg=P["papel"])
            linea.pack(anchor="w", pady=(2, 0))
            tk.Label(linea, text="●", font=ui.fuente(10), fg=P["naranja"] if viejo else "#1E8A5A", bg=P["papel"]).pack(side="left")
            ui.texto(linea, estado_txt, 11, P["gris"]).pack(side="left", padx=(4, 0))
        der = tk.Frame(fila, bg=P["papel"])
        der.pack(side="right")
        ui.boton(der, "↻  Actualizar ahora", self.actualizar_ahora).pack(side="right")
        tk.Checkbutton(der, text="Cada 30 min", variable=self.auto, font=ui.fuente(9), bg=P["papel"], fg=P["gris"],
                       activebackground=P["papel"], selectcolor="#FFFFFF").pack(side="right", padx=(0, 12))
        if e is None or e.sin_datos:
            ui.texto(c, "Aún no hay datos en vivo. Pulsa «Actualizar ahora».", 13, peso="bold").pack(anchor="w")
            return

        fila = self._fila(c, [5, 4], uniforme=False)
        grande = tk.Frame(fila, bg=P["marino"], padx=28, pady=24)
        grande.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        ui.texto(grande, f"Precio en Lima · {hora_corta(e.momento)}", 11, "#9FC3E8", "bold", bg=P["marino"]).pack(anchor="w")
        cifra = tk.Frame(grande, bg=P["marino"])
        cifra.pack(anchor="w", pady=(10, 14))
        tk.Label(cifra, text=soles(e.valor), font=ui.fuente(44, "xbold"), fg="#FFFFFF", bg=P["marino"]).pack(side="left")
        tk.Label(cifra, text="por MWh", font=ui.fuente(13, "bold"), fg="#9FC3E8", bg=P["marino"]).pack(side="left", padx=(10, 0),
                                                                                                       pady=(18, 0))
        mensaje, tono = self._lectura_ahora(e)
        ui.etiqueta_cambio(grande, mensaje, tono).pack(anchor="w")

        refs = tk.Frame(fila, bg=P["papel"])
        refs.grid(row=0, column=1, sticky="nsew")
        for i, ref in enumerate(e.referencias):
            t = ui.tarjeta(refs, 18, 12)
            t.pack(fill="x", pady=(0 if i == 0 else 10, 0))
            izq = tk.Frame(t, bg="#FFFFFF")
            izq.pack(side="left")
            ui.texto(izq, ref.nombre.capitalize(), 10, P["gris"], "bold", bg="#FFFFFF").pack(anchor="w")
            ui.texto(izq, soles(ref.valor), 15, peso="bold", bg="#FFFFFF").pack(anchor="w")
            if ref.var is None:
                ui.etiqueta_cambio(t, "s/d").pack(side="right")
            else:
                tono_ref = "neutro" if abs(ref.var) < 0.05 else ("malo" if ref.var > 0 else "bueno")
                ui.etiqueta_cambio(t, f"{'▲' if ref.var > 0 else '▼'} {abs(ref.var) * 100:.0f}%", tono_ref).pack(side="right")

        prog = self.prog or {}
        hoy_prog, manana = prog.get("hoy"), prog.get("manana")
        fila = self._fila(c, [3, 2], uniforme=False)
        self._tarjeta_grafico(fila, "Hoy frente a ayer y a lo programado",
                              G.ahora(e.serie_hoy, e.serie_ayer, programado=hoy_prog), alto=260).grid(
            row=0, column=0, sticky="nsew", padx=(0, 14))
        lado = tk.Frame(fila, bg=P["papel"])
        lado.grid(row=0, column=1, sticky="nsew")
        # Lo programado por el COES: cuanto se aleja el dato real y que se espera manana
        if hoy_prog is not None and len(hoy_prog):
            mismo = hoy_prog[hoy_prog["fecha_hora"] == e.momento]
            if len(mismo):
                plan = float(mismo["cmg_soles"].iloc[0])
                dif = e.valor / plan - 1 if plan else 0
                tono_p = "alerta" if dif > 0.3 else ("info" if dif < -0.3 else "neutro")
                ui.tarjeta_cifra(lado, "Programado a esta hora", soles(plan), "por MWh",
                                 f"El real va {abs(dif) * 100:.0f}% {'arriba' if dif > 0 else 'abajo'}", tono_p,
                                 "Costo marginal que el COES calculó el día anterior en su Programa Diario de "
                                 "Operación (modelo YUPANA, en dólares, convertido a soles con el tipo de cambio BCRP).",
                                 tam=20).pack(fill="x", pady=(0, 14))
        if manana is not None and len(manana):
            imax = manana["cmg_soles"].idxmax()
            pico = manana.loc[imax, "fecha_hora"]
            ui.tarjeta_cifra(lado, "Mañana se espera", soles(manana["cmg_soles"].mean()), "por MWh en promedio",
                             f"pico de {soles(manana.loc[imax, 'cmg_soles'])} a las {hora_corta(pico)}", "info",
                             "Programa Diario de Operación del COES para mañana. Es una previsión: el precio real "
                             "puede ser muy distinto si cambian el agua, la demanda o salen centrales.", tam=20).pack(
                fill="x", pady=(0, 14))
        else:
            ui.texto(lado, "El programa de mañana lo publica el COES por la tarde.", 9, P["gris"], ancho=300).pack(
                anchor="w", pady=(0, 10))
        if e.demanda:
            d = e.demanda
            desvio = d["desvio"]
            if desvio is None:
                txt, tono_d = "sin programa", "neutro"
            elif abs(desvio) < 0.02:
                txt, tono_d = f"Casi igual a lo previsto ({desvio * 100:+.1f}%)", "neutro"
            else:
                txt, tono_d = f"{desvio * 100:+.1f}% vs lo previsto", "info"
            ui.tarjeta_cifra(lado, "Consumo del país", numero(d["valor"]), "MW", txt, tono_d,
                             explicacion("demanda_maxima"), tam=20).pack(fill="x")
        nota = tk.Frame(lado, bg=P["celeste"], padx=16, pady=14)
        nota.pack(fill="x", pady=(14, 0))
        ui.texto(nota, "Dato preliminar: el COES lo confirma en 1 o 2 días.", 10, bg=P["celeste"], ancho=260).pack(anchor="w")

    @staticmethod
    def _lectura_ahora(e):
        ev = e.evaluacion
        if ev is None or not ev.mediana:
            return "Sin historia suficiente para comparar", "neutro"
        razon = e.valor / ev.mediana
        if ev.es_rara:
            return "Inusual para esta hora", "alerta"
        if razon >= 1.8:
            veces = round(razon * 2) / 2
            texto_veces = f"{veces:.0f}" if veces.is_integer() else f"{veces:.1f}"
            return f"Unas {texto_veces} veces lo normal para esta hora", "alerta"
        if razon <= 0.6:
            return "Mucho más barato que lo normal", "info"
        return "Normal para esta hora", "bueno"

    def vista_precios(self):
        r, n = self.r, self.n
        panel = self.paneles["precios"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Precios", n.titulos_graficos.get("precios_serie", rango_corto(r.semana)))
        prom, mx, mn, alto = r.ind("cmg_promedio"), r.ind("cmg_maximo"), r.ind("cmg_minimo"), r.ind("horas_precio_alto")
        t_prom, tono_prom = cambio(prom, invertir=True)
        t_alto, tono_alto = cambio(alto, invertir=True)
        self._cifras(c, [
            dict(etiqueta="Promedio", valor=soles(prom.valor), unidad="por MWh", cambio=t_prom, tono=tono_prom,
                 explicacion=explicacion("cmg_promedio")),
            dict(etiqueta="Más alto", valor=soles(mx.valor), detalle=dia_y_hora(mx.momento) if mx.momento is not None else "",
                 explicacion=explicacion("cmg_maximo")),
            dict(etiqueta="Más bajo", valor=soles(mn.valor), detalle=dia_y_hora(mn.momento) if mn.momento is not None else "",
                 explicacion=explicacion("cmg_minimo")),
            dict(etiqueta="Horas caras", valor=numero(alto.valor, 1), unidad="h", cambio=t_alto, tono=tono_alto,
                 explicacion=explicacion("horas_precio_alto")),
        ])
        if not r.serie_cmg.empty:
            self._tarjeta_grafico(c, "Precio de la semana", G.precio_semana(r.serie_cmg, r.umbrales_precio),
                                  "S/ por MWh · Santa Rosa 220 kV", alto=260).pack(fill="x", pady=(0, 16))
        fila = self._fila(c, [2, 1], uniforme=False)
        self._tarjeta_grafico(fila, "Por hora del día", G.perfil_horario(r.perfil_cmg), alto=230).grid(
            row=0, column=0, sticky="nsew", padx=(0, 14))
        lado = tk.Frame(fila, bg=P["papel"])
        lado.grid(row=0, column=1, sticky="nsew")
        tono_rz = "alerta" if r.n_rarezas else "bueno"
        ui.tarjeta_cifra(lado, "Precios inusuales", str(r.n_rarezas), "medias horas",
                         "fuera de lo normal" if r.n_rarezas else "todo dentro de lo normal", tono_rz,
                         explicacion("rarezas")).pack(fill="x")
        if r.revision:
            ui.tarjeta_cifra(lado, "Cambio al confirmarse", porcentaje(r.revision["diferencia_media_pct"]), "",
                             "preliminar vs confirmado", "info", explicacion("revision_cmg")).pack(fill="x", pady=(14, 0))

    def vista_demanda(self):
        r, n = self.r, self.n
        panel = self.paneles["demanda"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Demanda", n.titulos_graficos.get("demanda", rango_corto(r.semana)))
        dm, ene, err = r.ind("demanda_maxima"), r.ind("energia_semana"), r.ind("error_programa_diario")
        t_dm, tono_dm = cambio(dm, neutral=True)
        t_ene, tono_ene = cambio(ene, neutral=True)
        self._cifras(c, [
            dict(etiqueta="Demanda máxima", valor=numero(dm.valor), unidad="MW", cambio=t_dm, tono=tono_dm,
                 explicacion=explicacion("demanda_maxima")),
            dict(etiqueta="Energía de la semana", valor=numero(ene.valor), unidad="GWh", cambio=t_ene, tono=tono_ene,
                 explicacion=explicacion("energia_semana")),
            dict(etiqueta="Diferencia con lo previsto", valor=porcentaje(err.valor), cambio="pronóstico del COES",
                 tono="neutro", explicacion=explicacion("error_programa_diario")),
        ])
        if not r.serie_demanda.empty:
            self._tarjeta_grafico(c, "Consumo real vs previsto", G.demanda(r.serie_demanda), "MW", alto=280).pack(fill="x")

    def vista_generacion(self):
        r, n = self.r, self.n
        panel = self.paneles["generacion"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Generación", n.titulos_graficos.get("generacion", rango_corto(r.semana)))
        ren, sin = r.ind("participacion_renovable"), r.ind("participacion_renovable_sin_hidro")
        sol, eol, prom = r.ind("precio_capturado_solar"), r.ind("precio_capturado_eolica"), r.ind("cmg_promedio")
        t_ren, tono_ren = cambio(ren, puntos=True)
        t_sin, tono_sin = cambio(sin, puntos=True)

        def vs_promedio(ind):
            if not ind.valor or not prom.valor:
                return "", "neutro"
            dif = ind.valor / prom.valor - 1
            return f"{abs(dif) * 100:.0f}% {'bajo' if dif < 0 else 'sobre'} el promedio", "neutro"

        self._cifras(c, [
            dict(etiqueta="Renovable", valor=porcentaje(ren.valor), cambio=t_ren, tono=tono_ren,
                 explicacion=explicacion("participacion_renovable")),
            dict(etiqueta="Renovable sin hidro", valor=porcentaje(sin.valor), cambio=t_sin, tono=tono_sin,
                 explicacion=explicacion("participacion_renovable_sin_hidro")),
            dict(etiqueta="Precio de la solar", valor=soles(sol.valor), unidad="por MWh", cambio=vs_promedio(sol)[0],
                 explicacion=explicacion("precio_capturado_solar")),
            dict(etiqueta="Precio de la eólica", valor=soles(eol.valor), unidad="por MWh", cambio=vs_promedio(eol)[0],
                 explicacion=explicacion("precio_capturado_eolica")),
        ])
        if r.mix:
            self._tarjeta_grafico(c, "Generación por fuente", G.generacion(r.serie_generacion), "MW", alto=290).pack(
                fill="x", pady=(0, 16))
            self._tarjeta_grafico(c, "Participación de cada fuente", G.mix(r.mix, r.mix_anterior), alto=250).pack(fill="x")

    def vista_embalses(self):
        r, n = self.r, self.n
        panel = self.paneles["embalses"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Embalses", n.titulos_graficos.get("embalses", rango_corto(r.semana)))
        emb = r.ind("volumen_embalses")
        t_emb, tono_emb = cambio(emb)
        t_anio = "sin comparación" if emb.var_anio is None else \
            f"{'▲' if emb.var_anio > 0 else '▼'} {abs(emb.var_anio) * 100:.1f}% vs hace un año"
        self._cifras(c, [
            dict(etiqueta="Agua guardada", valor=numero(emb.valor, 1) if emb.valor else "s/d", unidad="Hm³", cambio=t_emb,
                 tono=tono_emb, explicacion=explicacion("volumen_embalses")),
            dict(etiqueta="Frente a hace un año", valor=t_anio.split(" vs")[0], cambio="misma semana de "
                 + str(r.desde.year - 1), tono="neutro", explicacion=explicacion("volumen_embalses")),
        ])
        if not r.serie_embalses.empty:
            fila = self._fila(c, [1, 1])
            self._tarjeta_grafico(fila, "Día a día", G.embalses(r.serie_embalses), "Hm³", alto=250).grid(
                row=0, column=0, sticky="nsew", padx=(0, 14))
            self._tarjeta_grafico(fila, "Los que más agua tienen", G.embalses_detalle(r.embalses_detalle), alto=250).grid(
                row=0, column=1, sticky="nsew")

    def vista_mapa(self):
        r, n = self.r, self.n
        panel = self.paneles["mapa"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Mapa", n.titulos_graficos.get("mapa", "Precio por zona"))
        barras = r.cmg_barras.dropna(subset=["latitud"]) if not r.cmg_barras.empty else r.cmg_barras
        if barras.empty:
            ui.texto(c, "No hay datos por zona esta semana.", 12).pack(anchor="w")
            return
        fila = self._fila(c, [3, 2], uniforme=False)
        self._tarjeta_grafico(fila, "Precio promedio por zona", G.mapa(r.cmg_barras), "pasa el mouse por un punto").grid(
            row=0, column=0, sticky="nsew", padx=(0, 14))
        lado = tk.Frame(fila, bg=P["papel"])
        lado.grid(row=0, column=1, sticky="nsew")
        for titulo, datos, tono in (("Más caras", barras.nlargest(5, "cmg_promedio"), "malo"),
                                    ("Más baratas", barras.nsmallest(5, "cmg_promedio"), "bueno")):
            t = ui.tarjeta(lado)
            t.pack(fill="x", pady=(0, 14))
            ui.texto(t, titulo, 13, peso="bold").pack(anchor="w", pady=(0, 8))
            for _, f in datos.iterrows():
                linea = tk.Frame(t, bg="#FFFFFF")
                linea.pack(fill="x", pady=3)
                ui.texto(linea, f["barra"].title(), 10, bg="#FFFFFF").pack(side="left")
                ui.etiqueta_cambio(linea, soles(f["cmg_promedio"]), tono).pack(side="right")

    def vista_fuentes(self):
        r = self.r
        panel = self.paneles["fuentes"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Fuentes", "De dónde salen los datos y cuándo se actualizaron")
        fuentes = config.fuentes()
        est = estado.leer()
        nombres = {"demanda": "Demanda", "generacion": "Generación", "costo_marginal": "Precios (IEOD)",
                   "ieod_anexo": "Embalses (IEOD)", "ahora_costo_marginal": "Precio en vivo", "ahora_demanda": "Demanda en vivo"}
        filas = [(k, f) for k, f in fuentes["fuentes"].items() if k in nombres]
        filas += [(f"ahora_{k}", f) for k, f in fuentes["ahora"].items() if isinstance(f, dict)]
        t = ui.tarjeta(c)
        t.pack(fill="x", pady=(0, 16))
        for j, peso in enumerate((3, 2, 2, 3)):
            t.columnconfigure(j, weight=peso)
        for j, cab in enumerate(("Dato", "Frecuencia", "Estado", "Última actualización")):
            ui.texto(t, cab, 9, P["gris"], "bold", bg="#FFFFFF").grid(row=0, column=j, sticky="w", pady=(0, 8))
        for i, (clave, f) in enumerate(filas, start=1):
            info = est.get(clave, {})
            ok = info.get("ultima_extraccion_exitosa")
            ultima = ok.replace("T", " ")[:16] if ok else "pendiente"
            estado_dato = "preliminar" if f.get("estado_dato") == "preliminar" else "confirmado"
            ui.texto(t, nombres[clave], 11, peso="bold", bg="#FFFFFF").grid(row=i, column=0, sticky="w", pady=6)
            ui.texto(t, f.get("frecuencia_objetivo", ""), 10, bg="#FFFFFF").grid(row=i, column=1, sticky="w")
            ui.etiqueta_cambio(t, estado_dato, "info" if estado_dato == "confirmado" else "neutro").grid(row=i, column=2, sticky="w")
            ui.texto(t, ultima, 10, P["gris"] if not ok else P["marino"], bg="#FFFFFF").grid(row=i, column=3, sticky="w")
        fila = self._fila(c, [1, 1])
        ui.tarjeta_cifra(fila, "Avisos de calidad esta semana", str(len(r.avisos)), "",
                         "huecos o datos raros del COES" if r.avisos else "sin problemas",
                         "alerta" if r.avisos else "bueno").grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        aviso = tk.Frame(fila, bg=P["celeste"], padx=18, pady=16)
        aviso.grid(row=0, column=1, sticky="nsew")
        ui.texto(aviso, " ".join(PROYECTO["aviso"].split()), 10, bg=P["celeste"], ancho=420).pack(anchor="w")

    # ----- eventos -----

    def vista_eventos(self):
        r = self.r
        panel = self.paneles["eventos"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Eventos", f"Salidas de servicio, mantenimientos y fallas · {rango_corto(r.semana)}")
        ev = centrales.eventos_semana(r.semana)
        if ev.empty:
            ui.texto(c, "No hay eventos registrados para esta semana.", 12).pack(anchor="w")
            return
        gen = ev[(ev["clase"] == "G") & (ev["mw"] > 0)]
        forzadas = gen[~gen["programado"]]
        dia = centrales.indisponible_por_dia(ev, r.desde, r.hasta)
        maximo = (dia["programado"] + dia["forzado"]).max() if len(dia) else 0
        self._cifras(c, [
            dict(etiqueta="Salidas forzadas", valor=str(len(forzadas)), unidad="de generación",
                 cambio=f"{forzadas['mw'].sum():,.0f} MW en total" if len(forzadas) else "ninguna",
                 tono="alerta" if len(forzadas) else "bueno",
                 explicacion="Centrales o unidades que salieron de servicio sin estar programado (fallas, emergencias)."),
            dict(etiqueta="Mantenimientos programados", valor=str(int(gen["programado"].sum())), unidad="de generación",
                 explicacion="Salidas avisadas con anticipación al COES."),
            dict(etiqueta="Máximo fuera de servicio", valor=numero(maximo), unidad="MW en un día",
                 explicacion="Suma de la potencia de las unidades de generación que estuvieron fuera ese día."),
            dict(etiqueta="Eventos en la red", valor=str(int((ev["origen"] == "evento").sum())),
                 unidad="desconexiones", explicacion="Desconexiones de líneas, transformadores o generadores reportadas."),
        ])
        self._tarjeta_grafico(c, "Generación fuera de servicio por día", G.indisponibilidad(dia), "MW",
                              alto=240).pack(fill="x", pady=(0, 16))
        lista = ui.tarjeta(c)
        lista.pack(fill="x", pady=(0, 16))
        ui.texto(lista, "Las salidas más grandes de la semana", 13, peso="bold").pack(anchor="w", pady=(0, 4))
        ui.texto(lista, "El precio es el promedio en Santa Rosa mientras duró la salida: muestra coincidencia, no causa.",
                 9, P["gris"], bg="#FFFFFF").pack(anchor="w", pady=(0, 10))
        cmg = r.serie_cmg.rename(columns={"valor": "total"})
        tabla = tk.Frame(lista, bg="#FFFFFF")
        tabla.pack(fill="x")
        for j, peso in enumerate((4, 3, 3, 2, 2, 2)):
            tabla.columnconfigure(j, weight=peso)
        for j, cab in enumerate(("Central / unidad", "Empresa", "Desde → hasta", "MW", "Tipo", "Precio mientras")):
            ui.texto(tabla, cab, 9, P["gris"], "bold", bg="#FFFFFF").grid(row=0, column=j, sticky="w", pady=(0, 6))
        for i, (_, f) in enumerate(gen.sort_values("mw", ascending=False).head(12).iterrows(), start=1):
            nombre = f["ubicacion"].title() + ("" if f["equipo"] in ("CENTRAL", "") else f" · {f['equipo']}")
            ui.texto(tabla, nombre, 10, peso="bold", bg="#FFFFFF").grid(row=i, column=0, sticky="w", pady=4)
            ui.texto(tabla, str(f["empresa"]).title()[:28], 9, bg="#FFFFFF").grid(row=i, column=1, sticky="w")
            ui.texto(tabla, f"{f['inicio']:%d/%m %H:%M} → {f['final']:%d/%m %H:%M}", 9, bg="#FFFFFF").grid(
                row=i, column=2, sticky="w")
            ui.texto(tabla, f"{f['mw']:,.0f}", 10, peso="bold", bg="#FFFFFF").grid(row=i, column=3, sticky="w")
            ui.etiqueta_cambio(tabla, "Programada" if f["programado"] else "Forzada",
                               "neutro" if f["programado"] else "malo").grid(row=i, column=4, sticky="w")
            precio = centrales.precio_durante(cmg, f["inicio"], f["final"])
            ui.texto(tabla, soles(precio) if precio else "s/d", 9, bg="#FFFFFF").grid(row=i, column=5, sticky="w")
        red = ev[ev["origen"] == "evento"].sort_values("inicio", ascending=False).head(8)
        if len(red):
            t = ui.tarjeta(c)
            t.pack(fill="x")
            ui.texto(t, "Últimos eventos en la red", 13, peso="bold").pack(anchor="w", pady=(0, 8))
            for _, f in red.iterrows():
                linea = tk.Frame(t, bg="#FFFFFF")
                linea.pack(fill="x", pady=3)
                ui.texto(linea, f"{f['inicio']:%d/%m %H:%M}", 9, P["gris"], "bold", bg="#FFFFFF").pack(side="left")
                ui.texto(linea, f"  {str(f['ubicacion']).title()} · {f['equipo']}: {str(f['descripcion'])[:90].capitalize()}",
                         9, bg="#FFFFFF").pack(side="left")

    # ----- centrales -----

    def vista_centrales(self, central=None):
        r = self.r
        panel = self.paneles["centrales"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Centrales y empresas", f"Generación por central · {rango_corto(r.semana)}")
        cen = leer_tabla("centrales", r.semana)
        if cen.empty:
            ui.texto(c, "No hay datos por central para esta semana.", 12).pack(anchor="w")
            return
        nombres = centrales.lista_centrales(cen)
        central = central or (nombres[0] if config.interno().get("mis_centrales") else
                              centrales.top_centrales(cen, 1)["central"].iloc[0])
        # Selector y detalle de una central
        sel = ui.tarjeta(c, 18, 12)
        sel.pack(fill="x", pady=(0, 16))
        ui.texto(sel, "Central", 9, P["gris"], "bold", bg="#FFFFFF").pack(side="left")
        combo = ttk.Combobox(sel, state="readonly", width=34, values=nombres, font=ui.fuente(10))
        combo.set(central)
        combo.bind("<<ComboboxSelected>>", lambda e: self.vista_centrales(combo.get()))
        combo.pack(side="left", padx=(8, 16))
        barra, aproximada = centrales.barra_de(central)
        cmg = serie.cmg_rango(r.desde, r.hasta, barra)
        d = centrales.detalle_central(cen, central, cmg)
        if d:
            vs = ""
            if d["precio_capturado"] and d["precio_promedio"]:
                dif = d["precio_capturado"] / d["precio_promedio"] - 1
                vs = f"{abs(dif) * 100:.0f}% {'sobre' if dif > 0 else 'bajo'} el promedio"
            self._cifras(c, [
                dict(etiqueta="Energía de la semana", valor=numero(d["energia_mwh"]), unidad="MWh",
                     detalle=f"{d['empresa'].title()} · {config.nombre_tecnologia(d['tecnologia'])}"),
                dict(etiqueta="Potencia máxima", valor=numero(d["mw_max"]), unidad="MW",
                     detalle=f"generó {d['horas_generando']:,.0f} de 168 horas"),
                dict(etiqueta="Precio capturado", valor=soles(d["precio_capturado"]), unidad="por MWh", cambio=vs,
                     explicacion="Precio promedio ponderado por lo que generó la central en cada media hora."),
                dict(etiqueta="Ingreso spot estimado", valor=f"S/ {numero((d['ingreso_estimado'] or 0) / 1e6, 2)} M",
                     cambio=f"con precio de {barra.title()}" + (" (aproximado)" if aproximada else ""),
                     tono="info" if not aproximada else "neutro",
                     explicacion="Generación por costo marginal, media hora a media hora. Es una estimación: no incluye "
                                 "potencia, contratos ni retiros; no es la valorización oficial del COES."),
            ])
            self._tarjeta_grafico(c, f"{central.title()}: generación de la semana", G.generacion_central(d["serie"]),
                                  "MW", alto=230).pack(fill="x", pady=(0, 16))
        fila = self._fila(c, [1, 1])
        emp = centrales.participacion_empresas(cen, leer_tabla("centrales", r.semana_anterior))
        self._tarjeta_grafico(fila, "Participación por empresa",
                              G.barras_horizontales(emp["empresa"].tolist(), emp["cuota"].tolist(),
                                                    emp["cuota_anterior"].tolist()), "% de la energía").grid(
            row=0, column=0, sticky="nsew", padx=(0, 14))
        top = centrales.top_centrales(cen, 10)
        self._tarjeta_grafico(fila, "Centrales con más energía",
                              G.barras_horizontales(top["central"].tolist(), (top["energia_mwh"] / 1000).tolist(),
                                                    formato="{:,.1f} GWh"), "GWh").grid(row=0, column=1, sticky="nsew")

    # ----- evolucion (rango libre) -----

    def cargar_evolucion(self, atajo=None):
        """Lee la serie continua del rango elegido (y el tipo de cambio si se pide USD)."""
        if atajo:
            self.ev_desde, self.ev_hasta = serie.rango_atajo(atajo, hoy_peru(), serie.primera_fecha())
        desde, hasta, barra, moneda = self.ev_desde, self.ev_hasta, self.ev_barra, self.ev_moneda

        def tarea():
            datos = serie.cmg_rango(desde, hasta, barra)
            if moneda == "USD":
                from src.extract import bcrp
                datos = serie.en_dolares(datos, bcrp.actualizar(desde, hasta))
            return datos

        def listo(datos):
            self.ev_datos = datos
            self.vista_evolucion()
            self.avisar("Listo.")

        self._en_fondo("Armando la evolución", tarea, listo)

    def _rango_escrito(self):
        from datetime import date
        try:
            desde = date.fromisoformat(self.ev_entrada_desde.get().strip())
            hasta = date.fromisoformat(self.ev_entrada_hasta.get().strip())
        except ValueError:
            self.avisar("Fechas no válidas: usa el formato AAAA-MM-DD (por ejemplo 2026-09-01).")
            return
        if hasta < desde:
            desde, hasta = hasta, desde
        self.ev_desde, self.ev_hasta = desde, hasta
        self.cargar_evolucion()

    def _cambiar_barra(self, _e=None):
        self.ev_barra = self.ev_combo_barra.get()
        self.cargar_evolucion()

    def _cambiar_moneda(self, moneda):
        self.ev_moneda = moneda
        self.cargar_evolucion()

    def exportar_excel(self):
        from tkinter import filedialog
        if self.ev_datos is None or self.ev_datos.empty:
            self.avisar("No hay datos para exportar en este rango.")
            return
        nombre = f"cmg_{self.ev_barra.replace(' ', '_').lower()}_{self.ev_desde}_{self.ev_hasta}.xlsx"
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=nombre,
                                            filetypes=[("Excel", "*.xlsx")], title="Guardar como Excel")
        if not ruta:
            return
        datos, barra, moneda = self.ev_datos, self.ev_barra, self.ev_moneda
        self._en_fondo("Exportando a Excel", lambda: serie.exportar_excel(datos, ruta, barra, moneda),
                       lambda r: (self.avisar(f"Excel guardado: {r}"), abrir_archivo(r)))

    def vista_evolucion(self):
        panel = self.paneles["evolucion"]
        panel.limpiar()
        c = panel.interior
        datos, moneda = self.ev_datos, self.ev_moneda
        unidad = "USD" if moneda == "USD" else "S/"

        def dinero(v):
            return "s/d" if v is None or v != v else f"{unidad} {numero(v, 1)}"

        self._cabecera(c, "Evolución del precio", f"{self.ev_barra.title()} · del {self.ev_desde:%d/%m/%Y} al "
                                                  f"{self.ev_hasta:%d/%m/%Y}")
        # Controles: atajos, fechas, barra, moneda, exportar
        controles = ui.tarjeta(c, 18, 12)
        controles.pack(fill="x", pady=(0, 16))
        fila1 = tk.Frame(controles, bg="#FFFFFF")
        fila1.pack(fill="x")
        for etiqueta, atajo in (("7 días", "7d"), ("30 días", "30d"), ("Este mes", "mes"),
                                ("Año hidrológico", "hidro"), ("Este año", "anio"), ("Todo", "todo")):
            ui.boton(fila1, etiqueta, lambda a=atajo: self.cargar_evolucion(a), primario=False).pack(side="left", padx=(0, 6))
        ui.boton(fila1, "Exportar a Excel", self.exportar_excel,
                 ayuda="Guarda cada media hora del rango y el resumen diario en un Excel.").pack(side="right")
        fila2 = tk.Frame(controles, bg="#FFFFFF")
        fila2.pack(fill="x", pady=(12, 0))
        ui.texto(fila2, "Desde", 9, P["gris"], "bold", bg="#FFFFFF").pack(side="left")
        self.ev_entrada_desde = ttk.Entry(fila2, width=11, font=ui.fuente(10))
        self.ev_entrada_desde.insert(0, f"{self.ev_desde:%Y-%m-%d}")
        self.ev_entrada_desde.pack(side="left", padx=(6, 12))
        ui.texto(fila2, "Hasta", 9, P["gris"], "bold", bg="#FFFFFF").pack(side="left")
        self.ev_entrada_hasta = ttk.Entry(fila2, width=11, font=ui.fuente(10))
        self.ev_entrada_hasta.insert(0, f"{self.ev_hasta:%Y-%m-%d}")
        self.ev_entrada_hasta.pack(side="left", padx=(6, 8))
        ui.boton(fila2, "Ver", self._rango_escrito).pack(side="left", padx=(0, 18))
        ui.texto(fila2, "Barra", 9, P["gris"], "bold", bg="#FFFFFF").pack(side="left")
        self.ev_combo_barra = ttk.Combobox(fila2, state="readonly", width=24, values=serie.barras_disponibles(),
                                           font=ui.fuente(10))
        self.ev_combo_barra.set(self.ev_barra)
        self.ev_combo_barra.bind("<<ComboboxSelected>>", self._cambiar_barra)
        self.ev_combo_barra.pack(side="left", padx=(6, 18))
        for m in ("S/", "USD"):
            ui.boton(fila2, m, lambda x=m: self._cambiar_moneda(x), primario=(m == moneda)).pack(side="left", padx=(0, 4))

        if datos is None or datos.empty:
            ui.texto(c, "No hay datos en este rango. Prueba otro rango o pulsa «Actualizar» en Resumen.", 12).pack(anchor="w")
            return
        r = serie.resumir(datos, self.ev_desde, self.ev_hasta, self.ev_barra, moneda)
        self._cifras(c, [
            dict(etiqueta="Promedio", valor=dinero(r.base), unidad="por MWh (todo el día)",
                 explicacion="Promedio de todas las medias horas del rango."),
            dict(etiqueta="Punta (6 a 11 p. m.)", valor=dinero(r.punta), unidad="por MWh",
                 cambio=(f"{(r.punta / r.base - 1) * 100:+.0f}% vs promedio" if r.punta and r.base else ""),
                 tono="alerta" if r.punta and r.base and r.punta > r.base * 1.1 else "neutro",
                 explicacion="Las horas de mayor consumo. Los contratos y la potencia se miran en este bloque."),
            dict(etiqueta="Fuera de punta", valor=dinero(r.fuera_punta), unidad="por MWh",
                 explicacion="Todas las horas menos las de punta."),
            dict(etiqueta="Más alto", valor=dinero(r.maximo), detalle=dia_y_hora(r.momento_max) if r.momento_max is not None else "",
                 explicacion=explicacion("cmg_maximo")),
            dict(etiqueta="Más bajo", valor=dinero(r.minimo), detalle=dia_y_hora(r.momento_min) if r.momento_min is not None else "",
                 explicacion=explicacion("cmg_minimo")),
        ])
        calidad = (f"{r.cobertura * 100:.0f}% de las medias horas con dato · {r.dias} días · "
                   f"{r.dias_preliminares} días con datos preliminares (punto hueco en el gráfico)")
        if r.congestion_media is not None:
            calidad += f" · congestión media {unidad} {r.congestion_media:,.1f}"
        if moneda == "USD":
            calidad += " · tipo de cambio BCRP (venta)"
        ui.texto(c, calidad, 9, P["gris"]).pack(anchor="w", pady=(0, 12))

        dia = serie.diario(datos)
        self._tarjeta_grafico(c, "Precio día por día", G.evolucion_diaria(dia, unidad), f"{unidad} por MWh",
                              alto=300).pack(fill="x", pady=(0, 16))
        matriz = serie.matriz_calor(datos)
        alto_calor = int(min(max(240, 11 * len(matriz) + 110), 720))
        self._tarjeta_grafico(c, "Mapa de calor: cada día, cada media hora", G.mapa_calor(matriz, unidad),
                              "más oscuro = más caro", alto=alto_calor).pack(fill="x", pady=(0, 16))
        mes = serie.mensual(datos)
        if len(mes) > 1:
            self._tarjeta_grafico(c, "Promedio por mes", G.mensual_barras(mes, unidad), f"{unidad} por MWh",
                                  alto=260).pack(fill="x")

    def vista_glosario(self):
        panel = self.paneles["glosario"]
        panel.limpiar()
        c = panel.interior
        self._cabecera(c, "Glosario", "Cada término en una línea")
        entradas = sorted(list(GLOSARIO["indicadores"].values()) + list(GLOSARIO["terminos"].values()),
                          key=lambda g: g["nombre"])
        t = ui.tarjeta(c)
        t.pack(fill="x")
        for i, g in enumerate(entradas):
            if i:
                tk.Frame(t, height=1, bg="#EEF2F7").pack(fill="x", pady=8)
            ui.texto(t, g["nombre"], 11, peso="bold", bg="#FFFFFF").pack(anchor="w")
            primera = " ".join(g["explicacion_simple"].split()).split(". ")[0].rstrip(".") + "."
            ui.texto(t, primera, 10, P["gris"], bg="#FFFFFF", ancho=1000).pack(anchor="w")

    def correr(self):
        self.raiz.mainloop()


def main():
    """Abre la app de escritorio."""
    configurar_logging()
    App().correr()


if __name__ == "__main__":
    main()
