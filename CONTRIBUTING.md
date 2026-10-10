# Cómo contribuir

¡Gracias por querer ayudar! Algunas reglas cortas para que el proyecto siga siendo simple.

## Preparar el entorno

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
.venv/bin/python -m pytest -q                  # todo debe pasar antes de empezar
```

## Reglas del código

- Python 3.11+, rutas con `pathlib`, mensajes con `logging` (no `print` salvo en las CLI).
- Código, nombres de variables, funciones, archivos y comentarios **sin tildes ni eñe**.
  Los textos que ve el público (dashboard, PDF, glosario) sí llevan tildes.
- Nunca uses el guion largo en textos visibles: usa dos puntos, coma o paréntesis.
- Nada de HTML escrito a mano.
- Docstring corto en cada función pública.
- Solo datos públicos. Si agregas una fuente del COES: requests primero, pausa entre
  pedidos, caché, y documéntala en `docs/fuentes_coes.md` y `config/fuentes.yaml`.

## Dónde va cada cosa

| Quiero... | Toco... |
|---|---|
| Cambiar el nombre, colores o tagline | `config/proyecto.yaml` |
| Cambiar una explicación | `config/glosario.yaml` (fuente única de verdad) |
| Ajustar umbrales de precio o de "noticia" | `config/analisis.yaml` |
| Agregar un indicador | `src/analysis/` + entrada en el glosario + test |
| Cambiar cómo se redacta algo | `src/narrative/plantillas.py` |

Todo indicador nuevo necesita entrada en el glosario: hay un test que lo verifica.

## Antes de abrir un Pull Request

1. `python -m pytest -q` en verde.
2. Si cambiaste algo visible, corre `python run_weekly.py --sin-descarga` y revisa el PDF y el dashboard.
3. Describe qué cambiaste y por qué, en español simple.
