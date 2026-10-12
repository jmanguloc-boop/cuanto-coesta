# Cuánto COESta

**El sistema eléctrico peruano, explicado al toque.**

Un medio de análisis eléctrico independiente y open source: descarga los datos
públicos del [COES](https://www.coes.org.pe), los ordena, calcula indicadores y
los explica como una historia que se puede leer en los datos. Riguroso con las
cifras, directo en el lenguaje y transparente con el método.

> **Aviso.** Proyecto independiente, **no afiliado al COES**. Usa datos públicos del
> portal www.coes.org.pe, que pueden ser preliminares y cambiar después.

![La señal de la semana](docs/capturas/escritorio_senal.png)

## Dos productos

| | Cuánto COESta **Ahora** | **La semana eléctrica** |
|---|---|---|
| Qué es | Seguimiento frecuente del precio y la demanda | Edición semanal que explica qué pasó y qué cambió |
| Frecuencia | Cada 30 minutos (lo que el COES publica de verdad) | Lunes, 7:00 a. m. de Lima |
| Datos | Costo marginal en tiempo real por barra, demanda del SEIN | Precios, demanda, mix, renovables, precio capturado, embalses, mapa |
| Dónde | Pestaña *Ahora* de la app | Resto de pestañas y PDF opcional |

Si el COES no publicó un dato nuevo, se conserva el último y se muestra su
antigüedad: **nunca se finge una actualización**.

| El precio en vivo, con memoria | El mapa del costo eléctrico |
|---|---|
| ![Ahora](docs/capturas/escritorio_ahora.png) | ![Mapa](docs/capturas/escritorio_mapa.png) |

## La app de escritorio

Una ventana de Python (Tkinter, viene con Python: no hay que instalar nada extra ni abrir el navegador).

```bash
python app/escritorio.py
```

Pestañas: **La señal** (portada editorial), **Ahora**, **Precios**, **Demanda**,
**Generación**, **Hidrología**, **Mapa**, **Método y fuentes** y **Glosario**.
Botones: *↻ Ahora* (consulta al COES en segundos), *↓ Descargar semana* (2 a 3 minutos) y
*PDF* (opcional). Mientras está abierta, consulta el precio cada 30 minutos.

Las tipografías (Barlow, Barlow Condensed e IBM Plex Mono, licencia OFL) vienen en
`assets/fuentes` y se cargan solo para el programa, sin instalarlas.

## Qué hace distinto

- **El precio tiene memoria.** Cada precio se compara con la media hora anterior,
  la misma hora de ayer y la misma hora de hace una semana.
- **Detector de rarezas, no solo de máximos.** Marca las medias horas que rompen el
  rango visto a esa misma hora en las 4 semanas previas, y explica qué regla se activó.
- **Explicación en tres niveles.** Lectura rápida, explicación sencilla y nota técnica
  para cada indicador, todo desde [`config/glosario.yaml`](config/glosario.yaml).
- **El mapa del costo eléctrico.** Precio promedio por barra sobre el mapa del Perú.
- **Lo que el sistema creía.** Se guardan las versiones del dato preliminar y se mide
  cuánto cambia cuando el COES lo confirma (en la semana del 28/09 al 04/10/2026: 13.5 % en promedio).
- **Sin inventar causas.** Los textos se arman con reglas fijas, sin inteligencia
  artificial, y solo relacionan dos hechos cuando los datos lo respaldan.

## En la PC de la empresa (doble clic, sin .exe ni administrador)

1. `DiagnosticoConexion.bat`: prueba si la PC llega al COES, al BCRP y a PyPI (no instala nada) y deja `diagnostico_conexion.txt`.
2. `AbrirCuantoCOESta.bat`: la primera vez prepara todo (unos minutos); después abre la app al instante.
3. Opcional: `ActivarActualizacionAutomatica.bat` consulta el precio cada 30 minutos al prender la PC.

Usa el proxy y los certificados de Windows; si TI da un proxy distinto, va en `config/fuentes.yaml`.
Tus centrales y barras van en `config/interno.yaml` (copia de `interno.ejemplo.yaml`), que nunca se sube a GitHub.
Descripción completa en [`DESCRIPCION_DEL_PROYECTO.md`](DESCRIPCION_DEL_PROYECTO.md).

## Cómo correrlo (3 comandos)

Requiere Python 3.11 o más nuevo.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt   # Windows: .venv\Scripts\pip
.venv/bin/python run_weekly.py                                      # baja y procesa la última semana
.venv/bin/python app/escritorio.py                                  # abre la app
```

Más opciones:

```bash
python run_ahora.py                        # una consulta "Ahora" (costo marginal y demanda)
python run_ahora.py --desde-ayer --bucle   # primera carga y luego cada 30 minutos (Ctrl+C para salir)
python run_weekly.py --pdf                 # además genera el PDF semanal
python run_weekly.py --semana 2026-W40     # una semana específica
python run_weekly.py --historico 8         # baja también 8 semanas previas (para récords y rarezas)
python -m src.report --semana 2026-W40     # solo el PDF
python -m pytest -q
```

### Consultar cada 30 minutos aunque la app esté cerrada (Windows)

```bat
schtasks /Create /SC MINUTE /MO 30 /TN "CuantoCOEStaAhora" ^
  /TR "\"C:\ruta\al\proyecto\.venv\Scripts\python.exe\" \"C:\ruta\al\proyecto\run_ahora.py\"" /F
```

(En Mac o Linux, la línea equivalente de `cron` es `*/30 * * * * /ruta/.venv/bin/python /ruta/run_ahora.py`.)

## El informe semanal en PDF (opcional)

Seis páginas apaisadas con la misma identidad editorial: portada con el pulso en
cuatro cifras, la señal de la semana, demanda y generación, hidrología y mapa, lo
que merece atención y método y fuentes. Se genera solo si lo pides (botón *PDF* o
`--pdf`).

![PDF](docs/capturas/pdf_portada.png)

## Cómo funciona

```
COES (portal + IEOD) --> src/extract --> data/raw
                         src/transform --> data/processed/*.parquet (formato largo, DuckDB)
                         src/analysis  --> ResumenSemanal (indicadores, rarezas, mapa, revisiones)
                         src/narrative --> titulares, párrafos, tres niveles
                         src/visual    --> gráficos editoriales (app y PDF)
COES tiempo real   ----> src/ahora     --> data/ahora/ahora.sqlite (con versiones)
                         app/escritorio.py (Tkinter)   src/report (PDF opcional)
```

- Fuentes y hallazgos: [`docs/fuentes_coes.md`](docs/fuentes_coes.md)
- Tablas y columnas: [`docs/diccionario_datos.md`](docs/diccionario_datos.md)
- Decisiones y estado: [`PROGRESO.md`](PROGRESO.md)

El bot es respetuoso con el servidor del COES: se identifica, espera 2 segundos
entre pedidos, guarda todo en caché y solo pide lo que le falta.

## Automatización semanal (GitHub Actions)

[`.github/workflows/semanal.yml`](.github/workflows/semanal.yml) corre cada **lunes a las
7:00 a. m. (Lima)**: corre `run_weekly.py --pdf` y los tests, guarda `data/processed`
en el repo y publica el PDF como **GitHub Release**.

## Versión web (opcional)

También existe un dashboard en Streamlit (`streamlit run app/streamlit_app.py`) por
si algún día quieres publicarlo en internet con
[Streamlit Community Cloud](https://share.streamlit.io): repositorio `cuanto-coesta`,
rama `main`, archivo `app/streamlit_app.py`, Python 3.12.

## Cambiar el nombre o los colores

Nombre, slug, tagline, paleta y tipografías viven en [`config/proyecto.yaml`](config/proyecto.yaml).

## Licencia

Código: [MIT](LICENSE). Tipografías: SIL Open Font License (ver `assets/fuentes`).
Contorno del Perú: Natural Earth (dominio público). Los datos pertenecen al COES.
