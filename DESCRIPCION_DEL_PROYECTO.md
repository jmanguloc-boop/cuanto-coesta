# Cuánto COESta: descripción completa del proyecto

> El sistema eléctrico peruano, explicado al toque.

**Ubicación:** `C:\Users\Usuario nuevo\Desktop\pulso-electrico-peru`
**Estado al 11 de octubre de 2026:** terminado y funcionando. 22 commits, 58 pruebas automáticas en verde.
**Aviso:** proyecto independiente, no afiliado al COES. Usa solo datos públicos de www.coes.org.pe.

---

## 1. Qué es

Un programa en Python que descarga los datos públicos del COES (el organismo que
coordina la operación del sistema eléctrico del Perú), los ordena, calcula
indicadores y los muestra de forma simple, para que cualquier persona entienda
cuánto cuesta la electricidad, cuánto consume el país y de dónde sale la energía.

Tiene cuatro salidas:

| Salida | Qué es | Cómo se abre |
|---|---|---|
| **App de escritorio** (principal) | Una ventana de Python con menú lateral y tarjetas | `python app\escritorio.py` |
| **Ahora** | Precio y demanda en vivo, cada 30 minutos | Pestaña *Ahora* de la app, o `python run_ahora.py` |
| **PDF semanal** (opcional) | Informe de 6 páginas | Botón *Descargar PDF* en la app, o `python run_weekly.py --pdf` |
| **Dashboard web** (opcional) | Versión Streamlit, por si se quiere publicar en internet | `streamlit run app\streamlit_app.py` |

---

## 2. Cómo usarlo

### Primera vez

```bat
cd "C:\Users\Usuario nuevo\Desktop\pulso-electrico-peru"
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### Uso normal

```bat
.venv\Scripts\python run_weekly.py          :: baja y procesa la última semana completa (2 a 3 min)
.venv\Scripts\python app\escritorio.py      :: abre la app
```

### Otros comandos

| Comando | Qué hace |
|---|---|
| `run_weekly.py --semana 2026-W40` | Procesa una semana específica |
| `run_weekly.py --historico 8` | Baja también las 8 semanas previas (para récords y rarezas) |
| `run_weekly.py --pdf` | Además genera el PDF |
| `run_weekly.py --sin-descarga` | Recalcula sin volver a descargar |
| `run_ahora.py` | Una consulta del precio y la demanda en vivo |
| `run_ahora.py --bucle` | Consulta cada 30 minutos hasta cerrar con Ctrl+C |
| `python -m src.report --semana 2026-W40 --png` | Solo el PDF (y su portada en imagen) |
| `python -m src.analysis --semana 2026-W40` | Resumen de indicadores en la consola |
| `python -m src.narrative --semana 2026-W40` | Titulares y párrafos de la semana |
| `python -m pytest -q` | Corre las 58 pruebas |
| `python -m src.utils.empaquetar` | Crea el zip de entrega |

---

## 3. La app de escritorio

Ventana Tkinter (viene con Python, no abre el navegador). Diseño amigable con
paleta azul institucional, fondo gris azulado claro, tarjetas blancas y naranja
solo para lo que pide atención. Tipografía Plus Jakarta Sans (incluida en el proyecto).

**Menú lateral:**

| Sección | Qué muestra |
|---|---|
| **Resumen** | Frase principal de la semana, 4 cifras (precio, demanda máxima, % renovable, embalses), precio por hora del día, de dónde vino la energía y los 3 hechos destacados. Selector de semana y botones *Actualizar* y *Descargar PDF* |
| **Ahora** | Último precio en Lima, si es normal para esa hora, comparación con media hora antes, ayer y hace una semana, curva de hoy frente a ayer y consumo actual del país |
| **Precios** | Promedio, más alto, más bajo, horas caras, curva de la semana, precio por hora, precios inusuales y cuánto cambia el dato al confirmarse |
| **Demanda** | Demanda máxima, energía de la semana, diferencia con lo previsto y curva real vs prevista |
| **Generación** | % renovable con y sin hidro, precio que obtuvieron la solar y la eólica, generación por fuente y participación de cada una |
| **Embalses** | Agua guardada, comparación con hace un año, evolución diaria y embalses con más agua |
| **Mapa** | Precio promedio por zona sobre el mapa del Perú, con las 5 barras más caras y más baratas |
| **Fuentes** | De dónde sale cada dato, cada cuánto se actualiza, si es preliminar o confirmado y cuándo se descargó |
| **Glosario** | Cada término explicado en una línea |

Detalles: cada cifra tiene un botón **i** con su explicación al pasar el mouse;
los gráficos muestran el valor exacto al pasar el mouse; mientras la app está
abierta consulta el precio cada 30 minutos; las tareas largas corren en segundo
plano sin congelar la ventana; se ve nítida en pantallas con escala de Windows.

---

## 4. Datos del COES que usa

Todo se descarga con `requests` (sin navegador automatizado), con pausa de 2
segundos entre pedidos, caché local y sin volver a bajar días cerrados.

| Fuente | Qué trae | Frecuencia | Estado |
|---|---|---|---|
| Demanda (portal) | Demanda ejecutada, programa diario y semanal cada 30 min | Semanal | Preliminar |
| Generación (portal) | MW por tipo de recurso y por central cada 30 min | Semanal | Preliminar |
| Costo marginal (IEOD, zip diario) | Precio en 235 barras cada 30 min | Semanal | Confirmado (post operación) |
| Costo marginal en tiempo real | Precio en ~120 barras; respaldo y comparación | Semanal y cada 30 min | Preliminar |
| IEOD Anexo A | Embalses, caudales, eventos, mantenimientos, despacho por central | Semanal | Confirmado |
| Demanda en tiempo real | Consumo del SEIN del día | Cada 30 min | Preliminar |

**Hallazgos importantes sobre los datos del COES** (detalle en `docs\fuentes_coes.md`):

- La exportación de costo marginal del portal pierde ~13 de las 48 medias horas del día; por eso se usa el zip diario del IEOD.
- El portal de generación publica las series **SOLAR** y **BAGAZO** con las etiquetas cruzadas; el programa lo detecta por la forma del día y lo corrige (verificado contra el IEOD al MWh).
- Algunos nombres llegan con tildes rotas desde el servidor; se normalizan.
- El dato en tiempo real se publica ~30 minutos después; el IEOD, 1 o 2 días después.
- El precio preliminar cambia en promedio 13.5% cuando el COES lo confirma (semana del 28/09 al 04/10/2026).

---

## 5. Indicadores que calcula

Cada uno se compara con la semana anterior y con la misma semana del año anterior.

| Tema | Indicadores |
|---|---|
| Precios (barra Santa Rosa 220 kV, Lima) | Costo marginal promedio, máximo y mínimo (con día y hora), horas con precio alto (más de S/ 500 por MWh) y bajo (menos de S/ 100), precio por hora del día |
| Demanda | Demanda máxima (con día y hora), energía de la semana, diferencia con el programa del COES |
| Generación | Mix por tecnología, % renovable con y sin hidro, precio capturado por la solar y la eólica |
| Hidrología | Agua útil en los principales embalses |
| Extras | Precios inusuales para su hora, cuánto cambia el dato preliminar, precio por zona (mapa) |
| Hechos destacados | Los 3 más relevantes de la semana, elegidos por reglas: grandes variaciones, récords del periodo, días y horas fuera de lo normal |

**Reglas importantes:**

- **Precio con memoria:** el precio en vivo se compara con la media hora anterior, la misma hora de ayer y la de hace una semana.
- **Precios inusuales:** una media hora es inusual si rompe el rango visto a esa misma hora en las 4 semanas previas (con margen de 10% y S/ 60).
- **Semanas incompletas:** no se comparan totales y se marcan como preliminares.
- **Récords:** solo sobre semanas consecutivas, y se dice "del periodo con datos", no "histórico".
- **Sin inventar causas:** los textos se arman con plantillas y reglas fijas, sin inteligencia artificial.

---

## 6. Cómo está construido (carpetas y archivos)

```
pulso-electrico-peru\
├── app\
│   ├── escritorio.py        App de escritorio (ventana principal y sus 9 secciones)
│   ├── tk_ui.py             Componentes visuales: tarjetas, botones, menú, tooltips
│   ├── streamlit_app.py     Dashboard web opcional
│   ├── graficos.py          Gráficos Plotly del dashboard web
│   └── .streamlit\config.toml
├── src\
│   ├── extract\             Descargadores: uno por fuente + cliente con pausas, reintentos y caché
│   ├── transform\           Convierte lo descargado en tablas limpias (parquet) y valida
│   ├── analysis\            Indicadores, hechos destacados y detector de precios inusuales
│   ├── narrative\           Titulares, párrafos y explicaciones en 3 niveles, por reglas
│   ├── visual\              Gráficos matplotlib (los usan la app y el PDF)
│   ├── ahora\               Módulo en vivo: extractor, base SQLite con versiones, memoria del precio
│   ├── report\              PDF semanal (fpdf2)
│   └── utils\               Configuración, fechas, formato, estilo, estado de fuentes, empaquetado
├── config\
│   ├── proyecto.yaml        Nombre, eslogan, paleta de colores, tipografía, color por tecnología
│   ├── fuentes.yaml         URLs y reglas de cada fuente del COES
│   ├── glosario.yaml        Todas las explicaciones (fuente única para app y PDF)
│   ├── analisis.yaml        Umbrales de precio, relevancia de hechos, reglas de rarezas
│   └── mapeos.yaml          Recursos del COES -> tecnologías del proyecto
├── assets\
│   ├── fuentes\             Plus Jakarta Sans (licencia OFL)
│   └── mapas\               Contorno del Perú y coordenadas de 115 barras
├── data\
│   ├── raw\                 Descargas del COES (no se versiona)
│   ├── processed\           Tablas por semana en parquet (no se versiona)
│   ├── ahora\ahora.sqlite   Base del módulo en vivo (no se versiona)
│   └── samples\             Muestras pequeñas de un día para las pruebas
├── docs\
│   ├── fuentes_coes.md      Cada fuente, sus endpoints y sus trampas
│   ├── diccionario_datos.md Tablas y columnas
│   └── capturas\            Imágenes de la app, el dashboard y el PDF
├── tests\                   58 pruebas automáticas
├── reports\                 PDFs generados
├── run_weekly.py            Proceso semanal completo
├── run_ahora.py             Consulta en vivo (sirve para el Programador de tareas)
├── .github\workflows\semanal.yml   Automatización semanal en GitHub
├── README.md, PROGRESO.md, CONTRIBUTING.md, CLAUDE.md, LICENSE (MIT)
└── ENTREGA_cuanto-coesta_2026-10-10.zip   Paquete de entrega
```

**Flujo de los datos:**

```
COES (portal + IEOD) -> extract -> data\raw
                        transform -> data\processed (tablas por semana)
                        analysis  -> indicadores, hechos, rarezas, mapa
                        narrative -> textos
                        visual    -> gráficos
                        app (ventana)  /  report (PDF opcional)
COES tiempo real ----> ahora -> data\ahora\ahora.sqlite -> sección Ahora
```

**Tablas procesadas por semana:** demanda, generación, costo marginal, costo
marginal preliminar, embalses y generación por central (176 unidades).

**Datos disponibles hoy:** semanas 2026-W32 a 2026-W41, más 2025-W40 y 2025-W41
para comparar con el año anterior.

---

## 7. Configuración que se puede cambiar sin tocar código

| Quiero cambiar... | Archivo |
|---|---|
| Nombre, eslogan, colores, tipografía | `config\proyecto.yaml` |
| Una explicación o un término del glosario | `config\glosario.yaml` |
| Qué es precio "alto" o "bajo", cuándo algo es noticia | `config\analisis.yaml` |
| Barra de referencia, pausas, fuentes | `config\fuentes.yaml` |

---

## 8. Automatización

- **Cada lunes 7:00 a. m. (Lima)** en GitHub Actions (`.github\workflows\semanal.yml`): baja la semana, corre las pruebas, guarda los datos y publica el PDF como Release. Se activa al subir el proyecto a GitHub.
- **Cada 30 minutos con la app cerrada** (opcional), con el Programador de tareas de Windows:

```bat
schtasks /Create /SC MINUTE /MO 30 /TN "CuantoCOEStaAhora" ^
  /TR "\"C:\Users\Usuario nuevo\Desktop\pulso-electrico-peru\.venv\Scripts\python.exe\" \"C:\Users\Usuario nuevo\Desktop\pulso-electrico-peru\run_ahora.py\"" /F
```

---

## 9. Calidad

- 58 pruebas automáticas (descargas simuladas, transformación, indicadores, textos, PDF, app y dashboard).
- Probado desde cero: copia limpia, entorno nuevo, instalación, descarga real y pruebas.
- Las pruebas no tocan los datos reales.
- Código sin tildes; textos visibles en español correcto, sin guiones largos.
- Historial completo de decisiones y problemas resueltos en `PROGRESO.md`.

---

## 10. Pendientes

| Pendiente | Quién |
|---|---|
| Crear el repositorio en GitHub y activar permisos del workflow | Usuario |
| Programar `run_ahora.py` si se quieren datos en vivo con la app cerrada | Usuario (opcional) |
| La columna "Última actualización" de algunas fuentes dirá "pendiente" hasta la próxima descarga semanal | Se resuelve solo |
| 13 barras del mapa público no cruzan por nombre con el IEOD | Mejora futura |
| El PDF mantiene su diagramación anterior con los colores nuevos | Mejora futura |
| Eventos, mantenimientos e indisponibilidades ya se descargan, pero aún no se muestran | Mejora futura |
