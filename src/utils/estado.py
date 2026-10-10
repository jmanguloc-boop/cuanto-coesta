"""Estado de cada fuente: ultima extraccion exitosa y ultimo error (data/estado_fuentes.json).

Permite mostrar en la app que esta actualizado y que no, sin ocultar problemas.
"""

import json
from pathlib import Path

from src.utils import config
from src.utils.fechas import ahora_peru

RUTA = config.DIR_DATA / "estado_fuentes.json"


def leer(ruta=None):
    """Estado de todas las fuentes, o {} si aun no hay extracciones."""
    ruta = Path(ruta or RUTA)
    if not ruta.exists():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def registrar(fuente, ok, detalle="", ruta=None):
    """Anota el resultado de una extraccion (no falla nunca: es solo informativo)."""
    ruta = Path(ruta or RUTA)
    estado = leer(ruta)
    item = estado.setdefault(fuente, {})
    momento = ahora_peru().isoformat(timespec="seconds")
    item["ultimo_intento"] = momento
    if ok:
        item["ultima_extraccion_exitosa"] = momento
        item["ultimo_detalle"] = detalle
        item.pop("ultimo_error", None)
    else:
        item["ultimo_error"] = detalle
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return item
