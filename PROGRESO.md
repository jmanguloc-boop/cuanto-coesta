# PROGRESO

## Bloques

- [x] Bloque 1: Setup del repo
- [x] Bloque 2: Reconocimiento de fuentes del COES
- [x] Bloque 3: Extractor
- [x] Bloque 4: Transformacion y modelo de datos
- [x] Bloque 5: Indicadores semanales
- [ ] Bloque 6: Narrativa automatica
- [ ] Bloque 7: Dashboard Streamlit
- [ ] Bloque 8: PDF semanal
- [ ] Bloque 9: Pipeline semanal y automatizacion
- [ ] Bloque 10: Calidad y documentacion
- [ ] Bloque 11: Entrega final comprimida

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

## Pendientes

- Eventos, mantenimientos e indisponibilidades (ya vienen en el Anexo A) para una version futura.
- CMg revisados (mensuales, definitivos) no se usan: llegan con ~1 mes de retraso.
- Huecos propios del COES en CMg (ej. 02/10/2026: 39 de 48 intervalos). Los promedios usan los intervalos disponibles.
- Reportar al COES el cruce de etiquetas SOLAR/BAGAZO de su portal (opcional, accion del usuario).
