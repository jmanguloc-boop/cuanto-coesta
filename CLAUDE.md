# Cuanto COESta (slug: cuanto-coesta)

El nombre, slug y tagline viven en config/proyecto.yaml. Nunca hardcodearlos.

Medio de analisis electrico independiente y open source. Descarga data publica del
COES (coes.org.pe), la limpia, calcula indicadores y la explica con identidad editorial
("periodismo de datos industrial": papel, carbon, verde profundo, lima electrica).
Productos:
1. App de escritorio Tkinter (app/escritorio.py), producto principal, sin navegador
2. "Ahora": costo marginal y demanda cada 30 min con versiones (src/ahora, SQLite)
3. PDF semanal apaisado, OPCIONAL (boton en la app o run_weekly.py --pdf)
4. Dashboard Streamlit (app/streamlit_app.py), opcional para publicar en la web

Publico: desde analistas del sector hasta alguien que no sabe nada de
electricidad. Si un dato no se entiende sin contexto, esta mal hecho.

## Reglas
- Python 3.11+. Rutas con pathlib. Logging con `logging` (src/utils/logs.py)
- Codigo, variables, funciones, archivos y comentarios SIN tildes ni enie. Los
  textos visibles (dashboard, PDF, glosario) si llevan tildes
- Nunca usar guion largo (em dash) en textos visibles
- Nada de HTML escrito a mano ni HTML a PDF
- Solo data publica. Pausa >= 2 s entre descargas, cache, nunca bajar dos veces lo mismo
- requests primero; Playwright solo si no hay otra forma
- Todo texto explicativo vive en config/glosario.yaml (fuente unica de verdad)
- Una paleta y un color por tecnologia: config/proyecto.yaml
- Numeros: 12,345.6 ; porcentajes max 1 decimal ; fechas legibles en espanol
- Titulos de graficos que digan la conclusion
- Aviso de no afiliacion al COES en dashboard, PDF y README
- Sin APIs de IA: la narrativa es por plantillas y reglas
- Nunca fingir datos nuevos: si el COES no publico, mostrar el ultimo y su antiguedad
- Los tests no deben escribir en data/ real (fixture estado_aislado en conftest)
- Para editar codigo preferir la herramienta Edit: en heredocs de bash los escapes con
  barra invertida (salto de linea, rutas de Windows) se deforman
- Al cerrar cada bloque: tests, PROGRESO.md, commit "Bloque N: ..."

## Estructura
- src/extract/    un descargador por fuente + CLI (`python -m src.extract`)
- src/transform/  crudo -> parquet largo en data/processed (`python -m src.transform`)
- src/analysis/   indicadores -> ResumenSemanal (`python -m src.analysis`)
- src/narrative/  titulares y parrafos por reglas
- src/report/     PDF editorial con fpdf2 (`python -m src.report`)
- src/visual/     graficos matplotlib editoriales (los usan la app y el PDF)
- src/ahora/      extractor 30 min, base SQLite versionada, memoria del precio
- app/escritorio.py + app/tk_ui.py   app de escritorio
- assets/         fuentes OFL (Barlow, Barlow Condensed, IBM Plex Mono) y mapa del Peru
- src/utils/      config, logging, fechas, formato
- app/streamlit_app.py   dashboard
- run_weekly.py   pipeline completo
- docs/fuentes_coes.md, docs/diccionario_datos.md

## Comandos (Windows)
- `.venv\Scripts\python -m pytest -q`
- `.venv\Scripts\python run_weekly.py [--semana 2026-W40] [--pdf]`
- `.venv\Scripts\python run_ahora.py [--bucle]`
- `.venv\Scripts\python app\escritorio.py`

Estado y decisiones: PROGRESO.md
