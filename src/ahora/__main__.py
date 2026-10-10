"""CLI: python -m src.ahora [--desde-ayer] [--bucle]

Una pasada baja los procesos de costo marginal y la demanda que falten de hoy.
Con --bucle repite cada 30 minutos (config/fuentes.yaml: ahora.cada_minutos).
"""

import argparse
import time

from src.ahora.extractor import actualizar
from src.ahora.memoria import estado_precio
from src.utils import config
from src.utils.fechas import dia_y_hora
from src.utils.formato import numero, texto_variacion
from src.utils.logs import configurar_logging, obtener_logger

log = obtener_logger("src.ahora")


def imprimir_estado():
    """Resumen corto del ultimo dato en consola."""
    e = estado_precio()
    if e.sin_datos:
        print("Aún no hay datos.")
        return
    print(f"\n{e.barra}: S/ {numero(e.valor, 1)} por MWh, intervalo que terminó el {dia_y_hora(e.momento)} "
          f"(hace {e.antiguedad_min:.0f} min)")
    for ref in e.referencias:
        print(f"  vs {ref.nombre:<18} {texto_variacion(ref.var)}")
    if not e.evaluacion.es_rara:
        print("  " + e.evaluacion.regla)
    for alerta in e.alertas:
        print(f"  ALERTA: {alerta}")
    if e.demanda:
        print(f"  Demanda: {numero(e.demanda['valor'])} MW ({dia_y_hora(e.demanda['momento'])}), "
              f"vs programado {texto_variacion(e.demanda['desvio'])}")


def main(argv=None):
    """Punto de entrada de la linea de comandos."""
    parser = argparse.ArgumentParser(description="Cuanto COESta Ahora: costo marginal y demanda cada 30 min")
    parser.add_argument("--desde-ayer", action="store_true", help="incluye el dia anterior (primera carga)")
    parser.add_argument("--bucle", action="store_true", help="repetir cada N minutos hasta Ctrl+C")
    args = parser.parse_args(argv)
    configurar_logging()
    minutos = config.fuentes()["ahora"]["cada_minutos"]
    while True:
        resumen = actualizar(desde_ayer=args.desde_ayer)
        log.info("Resumen: %s", resumen)
        imprimir_estado()
        if not args.bucle:
            return 0 if all(r["ok"] for r in resumen.values()) else 1
        args.desde_ayer = False
        log.info("Próxima consulta en %s minutos (Ctrl+C para salir)", minutos)
        time.sleep(minutos * 60)


if __name__ == "__main__":
    raise SystemExit(main())
