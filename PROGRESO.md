# PROGRESO

## Bloques

- [x] Bloque 1: Setup del repo
- [ ] Bloque 2: Reconocimiento de fuentes del COES
- [ ] Bloque 3: Extractor
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

## Decisiones

- **Carpeta del proyecto**: se mantiene en `Desktop/pulso-electrico-peru` en lugar
  de renombrarla a `cuanto-coesta`. El `.venv` de Windows guarda rutas absolutas y
  se romperia; ademas el nombre real se lee de config/proyecto.yaml. Al subir a
  GitHub el repo puede llamarse `cuanto-coesta`.
- **Hora Peru**: UTC-5 fijo con `datetime.timezone` (Peru no usa horario de
  verano). Asi no hace falta el paquete tzdata en Windows.
- **Python 3.14** en esta PC (cumple 3.11+). El workflow de GitHub usa 3.12.

## Pendientes

(se completa por bloque)
