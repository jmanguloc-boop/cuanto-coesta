# PROGRESO

## Bloques

- [x] Bloque 1: Setup del repo
- [x] Bloque 2: Reconocimiento de fuentes del COES
- [x] Bloque 3: Extractor
- [ ] Bloque 4: Transformacion y modelo de datos
- [ ] Bloque 5: Indicadores semanales
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

## Pendientes

- Eventos, mantenimientos e indisponibilidades (ya vienen en el Anexo A) para una version futura.
- CMg revisados (mensuales, definitivos) no se usan: llegan con ~1 mes de retraso.
