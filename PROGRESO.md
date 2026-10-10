# PROGRESO

## Fase 1: Investigacion de fuentes y extraccion (2026-10-09) - TERMINADA

### Que se hizo
- Estructura de carpetas, CLAUDE.md, .gitignore, requirements.txt, entorno `.venv`.
- Investigacion del portal COES: se encontraron los endpoints que usa la propia
  web (leyendo su JavaScript) para demanda, generacion y costo marginal.
  Detalle en `docs/fuentes_coes.md`.
- `config/fuentes.yaml`: URL, metodo, parametros y limites de cada fuente.
- `src/extract/cliente.py`: cliente HTTP con pausa de 2 s entre pedidos,
  reintentos con espera creciente y cache en disco.
- `src/extract/coes.py`: descargador generico que parte el rango en tramos
  segun el limite de cada fuente y valida que la respuesta sea Excel/JSON real.
- `src/extract/run.py`: comando `python -m src.extract.run`, por defecto baja la
  ultima semana completa (lunes a domingo).
- `config/glosario.yaml`: 17 terminos iniciales con explicacion simple.
- 9 tests sin red (`tests/test_extract.py`), todos pasan.
- Prueba real: semana 28/09 - 04/10/2026 bajada en 23 s (9 archivos, ~3.8 MB).
  Segunda corrida usa la cache y no hace pedidos.
- Muestras en `data/muestras/` (demanda de la semana y generacion del 01/10).

### Decisiones tomadas
- Solo `requests`, sin Playwright: los tres datos se exponen como Excel o JSON.
- Generacion se pide dia por dia porque el endpoint ignora el rango.
- Costo marginal solo barras >= 138 kV (`defecto=S`): 121 barras, suficiente para
  el publico objetivo y 6 veces mas liviano que todas las barras.
- Los ultimos 3 dias se tratan como provisionales y se refrescan cada 6 h,
  porque el COES puede corregirlos.
- Los textos del glosario si llevan tildes (los lee el publico). Las claves,
  el codigo y los comentarios no.
- Se guarda la respuesta cruda tal cual llega; toda limpieza va en `src/transform`.

### Problemas encontrados
- Disco C: tenia 0.58 GB libres. Se limpio la cache de npm (quedaron 17 GB).
- El servidor manda tildes rotas (`U+FFFD`) en los nombres de recursos y tipos
  de generacion. Hay que normalizarlos en transform.
- Costo marginal en tiempo real tiene huecos (26 a 48 intervalos por dia).
- `indicador=1` en generacion no devuelve datos.

### Que falta
- Fase 2 (transform): leer los crudos a tablas limpias (parquet o csv) con fecha
  y hora como datetime, nombres normalizados sin `U+FFFD`, y unidades claras.
- Revisar si los "costos marginales revisados" vienen sin huecos y conviene
  usarlos para semanas cerradas.
- Verificar con una fuente publica la equivalencia "1 MW ~ 1 000 casas" del
  glosario antes de mostrarla.
- Fases siguientes: indicadores (analysis), textos automaticos (narrative),
  dashboard Streamlit (app), PDF semanal (report), automatizacion semanal.
