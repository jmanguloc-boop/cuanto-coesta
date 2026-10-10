# PROGRESO

## Bloques

- [x] Bloque 1: Setup del repo
- [x] Bloque 2: Reconocimiento de fuentes del COES
- [x] Bloque 3: Extractor
- [x] Bloque 4: Transformacion y modelo de datos
- [x] Bloque 5: Indicadores semanales
- [x] Bloque 6: Narrativa automatica
- [x] Bloque 7: Dashboard Streamlit
- [x] Bloque 8: PDF semanal
- [x] Bloque 9: Pipeline semanal y automatizacion
- [x] Bloque 10: Calidad y documentacion
- [x] Bloque 11: Entrega final comprimida

### Mejoras v2 (propuesta editorial, 2026-10-10)

- [x] Fase 1: identidad editorial (paleta, fuentes OFL, mapa) y metadatos de fuentes
- [x] Fase 2: Cuanto COESta Ahora (cada 30 min, versiones, memoria del precio)
- [x] Fase 3: rarezas, preliminar vs revisado, costo por barra, explicacion en 3 niveles
- [x] Fase 4: graficos editoriales compartidos
- [x] Fase 5: app de escritorio Tkinter (producto principal)
- [x] Fase 6: PDF editorial apaisado y opcional
- [x] Fase 7: documentacion, capturas y entrega

## Bitacora

### Fase previa (2026-10-09, antes del prompt maestro)
Reconocimiento inicial y descargadores de demanda, generacion y costo marginal
(ver docs/fuentes_coes.md). Se reutilizan en los bloques 2 y 3.

### Bloque 1: Setup del repo (2026-10-10)
- Estructura objetivo creada: src/utils, app/.streamlit, data/samples, reports,
  docs/capturas, .github/workflows. data/muestras pasa a data/samples.
- config/proyecto.yaml con nombre, slug, tagline, aviso y paleta (color fijo
  por tecnologia).
- src/utils: config.py (lector de config y rutas), logs.py, fechas.py (semana
  ISO, hora Peru UTC-5, fechas legibles), formato.py (numeros estilo peruano).
- CLAUDE.md reescrito, LICENSE MIT, requirements.txt con versiones fijadas.
- Criterio: `python -c "from src.utils import config"` OK.

### Bloque 2: Reconocimiento de fuentes (2026-10-10)
- Se encontro el visor de archivos del COES (`/browser/vistadatos` y `/browser/download`)
  que da acceso al IEOD diario desde 2011.
- 5 fuentes probadas con muestra de 1 dia en data/samples/ (~2 MB): demanda,
  generacion, costo marginal IEOD, costo marginal tiempo real, IEOD Anexo A.
- docs/fuentes_coes.md con tabla resumen; config/fuentes.yaml reescrito.
- MVP: costo marginal, demanda, generacion por tecnologia, hidrologia.
- Todo con requests; no hace falta Playwright.

### Bloque 3: Extractor (2026-10-10)
- Un modulo por fuente en src/extract/ (demanda, generacion, costo_marginal,
  costo_marginal_tr, ieod_anexo), todos con `descargar(desde, hasta) -> lista de archivos`.
- base.py: tramos de fechas, cache, validacion (rechaza HTML disfrazado de Excel).
- cliente.py: pausa 2 s, reintentos con espera exponencial, timeout, acceso al
  visor de archivos del COES. Un archivo vacio del visor = "aun no publicado".
- costo_marginal baja el zip del IEOD, guarda solo CMgCP (~270 KB) y, si faltan
  dias, baja el respaldo en tiempo real.
- CLI `python -m src.extract --desde --hasta [--fuente]`; si una fuente falla se
  registra y siguen las demas (codigo de salida 1).
- Semana 2026-W40 completa en 35 s (22 archivos, ~13 MB). Respaldo probado con el 09/10.
- 10 tests sin red, usando data/samples.

### Bloque 4: Transformacion y modelo de datos (2026-10-10)
- src/transform/: comun.py (formato largo, fechas, validaciones), tablas.py (un
  lector por tabla), CLI `python -m src.transform --semana AAAA-Www`.
- 5 tablas parquet por semana: demanda, generacion (por tecnologia), costo_marginal
  (235 barras), embalses (Hm3 y msnm), centrales (176 unidades con empresa, area y tecnologia).
- config/mapeos.yaml: recursos y tipos de central -> tecnologia del proyecto.
- Validaciones que avisan sin romper (duplicados, faltantes, fuera de rango) en
  data/processed/avisos/. docs/diccionario_datos.md.
- Semana 2026-W40: 5 tablas en 13 s, 1 aviso (CMg del 02/10 con 39 de 48
  intervalos en el propio IEOD). Consultable con DuckDB.
- **Hallazgo**: el portal de generacion publica SOLAR y BAGAZO con las etiquetas
  cruzadas. Se detecta por la forma diaria y se corrige; tras la correccion la
  solar del portal cuadra al MWh con el IEOD los 7 dias.
- 22 tests en verde.

### Bloque 5: Indicadores semanales (2026-10-10)
- src/analysis/: modelo.py (Indicador, Hecho, ResumenSemanal), indicadores.py,
  hechos.py, CLI `python -m src.analysis --semana AAAA-Www`.
- 15 indicadores: CMg promedio/max/min (con momento), horas con precio bajo/alto,
  perfil horario, demanda maxima (con momento), energia semanal, error del
  programa diario, mix, renovable con y sin hidro, precio capturado solar y
  eolica, volumen de embalses. Cada uno vs semana anterior y vs anio anterior.
- Hechos destacados por reglas: variaciones sobre umbral de relevancia, records
  (con >= 4 semanas de historia), dia anomalo de precio, y datos de respaldo para
  completar siempre 3.
- config/analisis.yaml (barra, umbrales, relevancia). glosario.yaml reescrito con
  el formato pedido (nombre, explicacion_simple, por_que_importa, unidad,
  ejemplo_cotidiano) para 15 indicadores y 16 terminos.
- Datos de comparacion bajados: 2026-W39 y 2025-W40.
- W40: CMg promedio S/ 330.9 por MWh (-43.4% vs W39, +273.8% vs 2025), demanda
  maxima 8,346 MW, renovable 48.7%.
- 33 tests en verde (incluye: todo indicador tiene glosario, sin guion largo).

### Bloque 6: Narrativa automatica (2026-10-10)
- src/narrative/: plantillas.py (2 a 3 variantes por caso) y __init__.py
  (generar_narrativa -> Narrativa con 3 titulares, 4 parrafos y titulos de graficos
  que dicen la conclusion). CLI `python -m src.narrative --semana`.
- Variante elegida con hash de semana+caso: reproducible y distinta entre semanas.
- Unica relacion causal permitida: precio vs hidro, solo si el precio cambia >= 10%
  y la hidro >= 2 pp en sentido opuesto, y se dice "coincidio con", no "porque".
- pulir(): contracciones (del, al) y puntuacion.
- Probado con W40 (con comparaciones) y W39 (sin semana previa: solo describe).
- 39 tests en verde (estilo, sin palabras causales, regla hidro con y sin respaldo).

### Bloque 7: Dashboard Streamlit (2026-10-10)
- app/streamlit_app.py: encabezado con nombre, tagline y selector de semana; portada
  con 3 titulares y 4 st.metric (help del glosario, delta vs semana anterior, color
  invertido en precio); pestanas Precios, Demanda, Generacion, Hidrologia, Glosario,
  Sobre el proyecto; expander "Que significa esto" bajo cada grafico; boton de PDF;
  aviso de datos preliminares; pie con fuente, fecha de actualizacion y no afiliacion.
- app/graficos.py: 7 graficos Plotly con hover en espanol (valor, unidad y frase
  simple), ejes con dias en espanol, color fijo por tecnologia, separadores 12,345.6.
- app/.streamlit/config.toml con la paleta (test verifica que coincida con proyecto.yaml);
  Streamlit lee la config junto al script, verificado en su codigo fuente.
- st.cache_data para resumen y lista de semanas.
- Capturas automaticas con Playwright en docs/capturas/ (portada, generacion,
  hidrologia y celular 390 px).
- Serie diaria de embalses: solo embalses con dato los 7 dias (robustez).
- 42 tests en verde (incluye AppTest de Streamlit sin navegador).

### Bloque 8: PDF semanal (2026-10-10)
- src/report/: graficos.py (matplotlib, misma paleta y colores por tecnologia, ejes
  con dias en espanol) y __init__.py (ReportePDF con fpdf2, sin HTML).
- 6 paginas: portada (nombre, semana legible, aviso preliminar, 3 titulares, 8
  tarjetas de indicadores con flecha y color), Precios, Demanda, Generacion,
  Hidrologia (grafico + parrafo + cajita "Que significa esto" del glosario) y
  Nota metodologica + Glosario completo a dos columnas. Encabezado, pie con aviso
  y "Pagina X de N".
- Fuente DejaVu tomada de matplotlib (tildes y flechas en cualquier sistema operativo).
- CLI `python -m src.report --semana AAAA-Www [--png]` -> reports/cuanto-coesta_AAAA-Www.pdf;
  portada exportada a docs/capturas/pdf_portada.png con pypdfium2.
- Revisado visualmente y corregido: justificado raro, asteriscos de markdown,
  alto de cajitas, dia extra en eje, leyenda encima de la linea.
- 46 tests en verde (secciones, max 6 paginas, sin guion largo).

### Bloque 9: Pipeline semanal y automatizacion (2026-10-10)
- run_weekly.py: extract + transform de la semana, la(s) anterior(es) y la del anio
  pasado; luego analysis, narrative y report. Opciones --semana, --historico N,
  --sin-descarga. Solo devuelve 1 si no se pudo generar el PDF.
- Probado con 8 semanas de historico (W32 a W40 + 2025-W40): 7 min 52 s, sin
  intervencion. Primer record real detectado: embalses en su punto mas bajo en 9 semanas
  (bajaron todas las semanas de 716 a 529 Hm3).
- Probado con la semana en curso (W41, 5 dias completos): sale marcada PRELIMINAR,
  sin fallar.
- Corregido al probar:
  - Algunos zips del IEOD traen el Excel sin carpeta: ahora se busca por nombre.
  - Un dia con formato raro ya no tumba la semana entera de esa fuente.
  - Semana incompleta: los totales (energia, horas) no se comparan y el texto dice
    "en los N dias con datos completos".
  - Dias anomalos solo con dias de al menos 3/4 de sus intervalos.
  - "Records" solo sobre semanas consecutivas (un hueco corta la racha).
- .github/workflows/semanal.yml: lunes 12:00 UTC, cache de data/raw entre corridas,
  tests, commit de data/processed y Release `semana-AAAA-Www` con el PDF.
- README con despliegue en Streamlit Community Cloud (no desplegado: requiere cuentas).
- 47 tests en verde.

### Bloque 10: Calidad y documentacion (2026-10-10)
- pytest: 47 tests en verde.
- ruff (F, E9, B): imports sin usar, variables muertas, zip sin strict y lambda en
  bucle corregidos. 101 docstrings cortos agregados a funciones publicas.
- Fines de linea normalizados a LF en todo el repo + .gitattributes (Windows estaba
  guardando CRLF en algunos archivos).
- README completo (que es, capturas, indicadores, 3 comandos, automatizacion,
  despliegue, aviso, licencia) y CONTRIBUTING.md.
- Dashboard: abre por defecto en la ultima semana completa; marcas del eje al mediodia
  para que aparezcan los 7 dias. Capturas regeneradas.
- **Prueba desde cero OK**: clon del repo en carpeta temporal, venv nuevo con Python
  3.14, `pip install -r requirements.txt`, `python run_weekly.py` (exit 0, mismo
  resultado de W40) y `pytest` (47 passed).

### Bloque 11: Entrega final comprimida (2026-10-10)
- src/utils/empaquetar.py (`python -m src.utils.empaquetar`) arma con zipfile
  `ENTREGA_cuanto-coesta_2026-10-10.zip` en la raiz: archivos versionados en git
  (codigo, config, docs, tests, workflow, data/samples, capturas), el ultimo PDF y
  COMO_CORRERLO.txt con pasos para Windows y Mac.
- Verificado: sin .venv, .git, __pycache__, data/raw, data/processed ni otros zip.

### Mejoras v2 (2026-10-10)
- **Identidad**: papel #F1F0E8, carbon #171916, verde #315D45, lima #D5FF42, cobre
  #E46F3D. Barlow Condensed (cifras y titulares), Barlow (texto), IBM Plex Mono
  (etiquetas), en assets/fuentes con licencia OFL; se cargan sin instalarse
  (matplotlib por archivo, Tkinter con AddFontResourceEx privado, fpdf2 por archivo).
- **Ahora** (src/ahora, run_ahora.py): costo marginal en tiempo real (procesos del
  COES) y demanda, base SQLite con versiones. Primera carga: 7,590 valores y 66
  revisiones del propio COES. Memoria del precio: vs media hora antes, ayer y hace
  una semana. Si no hay dato nuevo se muestra la antiguedad.
- **Rarezas**: un valor es raro si rompe el rango de su misma hora en 28 dias (con
  margen de 10 % y S/ 60). Se probo mediana+MAD y marcaba hasta 193 medias horas por
  semana (el precio salta entre ~S/ 180 y ~S/ 800); con el rango salen 0 a 4.
- **Preliminar vs confirmado**: sin desfase horario (probado), 13.5 % de cambio medio
  en W40, maximo S/ 660.7. El preliminar ahora se baja siempre (1 pedido por semana).
- **Mapa**: 115 barras con coordenadas del mapa publico del COES; 102 cruzan con el
  IEOD. Contorno del Peru de Natural Earth.
- **Tres niveles**: nota_tecnica en las 19 entradas de indicadores del glosario;
  lectura rapida e intermedia generadas con los datos de la semana.
- **App de escritorio** (app/escritorio.py + app/tk_ui.py): 9 pestanas, tareas en
  segundo plano en cola, consulta Ahora cada 30 min mientras esta abierta, DPI
  consciente en Windows (nitida con escala 125 %).
- **PDF opcional**: run_weekly.py ya no lo genera por defecto (--pdf); el workflow
  de GitHub lo pide. A4 apaisado, 6 paginas, identidad del concepto.
- Corregido al probar: los tests escribian en data/estado_fuentes.json real (ahora
  aislados con un fixture); textos con "m.." (se pule todo parrafo).

## Decisiones

- **Carpeta del proyecto**: se mantiene en `Desktop/pulso-electrico-peru` en lugar
  de renombrarla a `cuanto-coesta`. El `.venv` de Windows guarda rutas absolutas y
  se romperia; ademas el nombre real se lee de config/proyecto.yaml. Al subir a
  GitHub el repo puede llamarse `cuanto-coesta`.
- **Hora Peru**: UTC-5 fijo con `datetime.timezone` (Peru no usa horario de
  verano). Asi no hace falta el paquete tzdata en Windows.
- **Python 3.14** en esta PC (cumple 3.11+). El workflow de GitHub usa 3.12.

- **Costo marginal**: fuente principal = zip diario del IEOD (48 intervalos, 235
  barras). La exportacion del portal pierde ~13 intervalos/dia (madrugada), lo que
  sesgaria el perfil horario; queda como respaldo preliminar para dias sin IEOD.
- **Barra de referencia**: SANTA ROSA 220 (Lima), barra de referencia historica del SEIN.
- **Hidrologia**: volumen util total (Hm3) de los embalses del IEOD. No hay un
  dato publico simple de capacidad maxima por embalse, asi que se compara contra
  semana anterior y anio anterior, no como % de llenado.

- **IEOD Anexo A completo** (~1.1 MB/dia) en vez de solo la hoja de embalses: no
  se puede pedir una hoja suelta, y el mismo archivo sirve luego para eventos y
  mantenimientos.

- **fecha_hora** = fin del intervalo, hora Peru sin zona guardada (mas simple en
  parquet/DuckDB). La columna `fecha` da el dia operativo.
- **es_preliminar** = el dia no tiene IEOD publicado todavia (o el dato es del respaldo en tiempo real).
- **Termicas por central**: el IEOD no dice el combustible por unidad, asi que en la
  tabla centrales quedan como "termica". El mix por combustible sale de la tabla generacion.
- **Correccion SOLAR/BAGAZO** por deteccion de forma, no con un intercambio fijo,
  para no romper si el COES arregla su portal.

- **Umbrales de precio**: bajo < S/ 100 por MWh, alto > S/ 500 por MWh, sobre Santa Rosa 220
  (config/analisis.yaml). Son fijos y no relativos para que "precio alto" signifique lo mismo cada semana.
- **Embalses**: valor = suma de la ultima lectura de la semana de cada embalse con
  volumen util. La variacion se calcula solo con embalses que tienen dato en ambas
  semanas, para no confundir un embalse sin lectura con agua que desaparecio.
- **Precio capturado**: promedio del CMg de Santa Rosa ponderado por la generacion de
  la tecnologia en cada media hora.
- **Hechos**: un hecho por indicador; los "records" solo se afirman con 4 o mas
  semanas previas disponibles.
- **Glosario sin cifras dudosas**: se quito "1 MW = 1,000 casas" (no verificado);
  solo quedan conversiones exactas (1 GWh = 1 millon de kWh, 1 Hm3 = mil millones de litros).

- **Graficos Plotly en app/graficos.py** (no en src/) porque solo los usa el dashboard;
  el PDF usa matplotlib con la misma paleta.
- **Modo viewer** en Streamlit (`toolbarMode = "viewer"`) para ocultar el boton Deploy al publico.

- **fpdf2 + matplotlib** (no reportlab): mas liviano y suficiente. pypdfium2 se agrega
  solo para exportar la portada a PNG y para leer el PDF en los tests.

- **Datos para el dashboard en la nube**: el workflow commitea `data/processed`
  (~1 MB por semana, la mayor parte el costo marginal de 235 barras). Es simple y
  Streamlit Cloud lo lee directo del repo. Si crece demasiado, recortar costo_marginal
  a la barra de referencia.

- **ruff** se uso solo para revisar; no se agrega a requirements (dependencias minimas).

- **Tkinter** como pantalla principal: viene con Python, no abre navegador y funciona
  en cualquier PC; el Streamlit queda como opcion para publicar en la web.
- **SQLite** para Ahora: viene con Python y permite versionar cada observacion.
- **Rarezas por rango** en vez de mediana+MAD (ver Mejoras v2).

## Pendientes

- Eventos, mantenimientos e indisponibilidades (ya vienen en el Anexo A) para una version futura.
- CMg revisados (mensuales, definitivos) no se usan: llegan con ~1 mes de retraso.
- Huecos propios del COES en CMg (ej. 02/10/2026: 39 de 48 intervalos). Los promedios usan los intervalos disponibles.
- Reportar al COES el cruce de etiquetas SOLAR/BAGAZO de su portal (opcional, accion del usuario).
- Records de embalses comparan totales aunque cambie levemente el numero de embalses
  que reportan (24 vs 25). Mejorar comparando solo el conjunto comun.
### Acciones que requieren al usuario
1. Crear el repo en GitHub (`cuanto-coesta`, publico) y subirlo:
   `git remote add origin https://github.com/<usuario>/cuanto-coesta.git` y `git push -u origin main`.
2. En GitHub: Settings > Actions > General > Workflow permissions: "Read and write".
3. Correr el workflow una vez a mano (Actions > Reporte semanal > Run workflow).
4. Desplegar en share.streamlit.io: repo cuanto-coesta, rama main, archivo app/streamlit_app.py, Python 3.12.
5. Completar `repositorio:` en config/proyecto.yaml con la URL del repo.
- Las columnas "Ultima extraccion OK" de demanda, generacion e IEOD dicen "sin registro"
  hasta la proxima descarga semanal (el registro se agrego en v2).
- Mapa: 13 barras del mapa publico no cruzan por nombre con el IEOD; se podria mapear a mano.
- La consulta cada 30 min con la app cerrada requiere programarla (README: Programador de tareas o cron).
