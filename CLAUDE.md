# Cuanto COESta (slug: cuanto-coesta)

El nombre, slug y tagline viven en config/proyecto.yaml. Nunca hardcodearlos.

Bot open source en Python que descarga data publica del COES (coes.org.pe), la
limpia, calcula indicadores semanales y genera:
1. Dashboard Streamlit (producto principal) con explicaciones al pasar el mouse
2. PDF semanal con cajitas "Que significa esto" y glosario

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
- Al cerrar cada bloque: tests, PROGRESO.md, commit "Bloque N: ..."

## Estructura
- src/extract/    un descargador por fuente + CLI (`python -m src.extract`)
- src/transform/  crudo -> parquet largo en data/processed (`python -m src.transform`)
- src/analysis/   indicadores -> ResumenSemanal (`python -m src.analysis`)
- src/narrative/  titulares y parrafos por reglas
- src/report/     PDF con fpdf2 + matplotlib (`python -m src.report`)
- src/utils/      config, logging, fechas, formato
- app/streamlit_app.py   dashboard
- run_weekly.py   pipeline completo
- docs/fuentes_coes.md, docs/diccionario_datos.md

## Comandos (Windows)
- `.venv\Scripts\python -m pytest -q`
- `.venv\Scripts\python run_weekly.py [--semana 2026-W40]`
- `.venv\Scripts\streamlit run app/streamlit_app.py`

Estado y decisiones: PROGRESO.md
