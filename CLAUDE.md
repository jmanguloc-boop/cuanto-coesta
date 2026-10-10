# Pulso Electrico Peru

Bot open source que descarga data publica del COES (coes.org.pe), la procesa
y genera cada semana:
1. Un dashboard en Streamlit (producto principal)
2. Un PDF semanal descargable

Publico objetivo: cualquier persona, desde analistas del sector energetico
hasta alguien sin conocimiento tecnico. Todo indicador debe tener una
explicacion en lenguaje simple.

Reglas del proyecto:
- Solo data publica del COES y fuentes publicas. Nada de data privada
- Python 3.11+. Nada de HTML escrito a mano
- Codigo, nombres de variables y comentarios sin tildes ni caracteres especiales
- Preferir requests/descarga directa de archivos. Usar Playwright solo si
  la pagina no expone los archivos de otra forma
- Respetar robots.txt y no saturar el servidor (pausas entre descargas, cache)
- Todo explicativo vive en config/glosario.yaml (fuente unica de verdad)
- Al terminar cada fase, actualizar PROGRESO.md con: que se hizo, que falta,
  decisiones tomadas y problemas encontrados

Estructura:
src/extract/   descargadores por fuente
src/transform/ limpieza y normalizacion
src/analysis/  calculo de indicadores
src/narrative/ textos automaticos
src/report/    generacion del PDF
app/           dashboard Streamlit
config/        glosario.yaml, fuentes.yaml
data/raw, data/processed (data/ en .gitignore salvo muestras)
docs/          documentacion de fuentes
tests/

Comandos:
- Entorno: `python -m venv .venv` y `.venv\Scripts\pip install -r requirements.txt`
- Descargar la ultima semana completa: `.venv\Scripts\python -m src.extract.run`
- Rango especifico: `.venv\Scripts\python -m src.extract.run --desde 2026-10-01 --hasta 2026-10-07`
- Tests: `.venv\Scripts\python -m pytest -q`

Detalles de las fuentes (endpoints, formatos, trampas conocidas): docs/fuentes_coes.md
