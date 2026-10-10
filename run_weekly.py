"""Pipeline semanal completo: extract -> transform -> analysis -> narrative -> report.

Uso:
  python run_weekly.py                      # ultima semana completa
  python run_weekly.py --semana 2026-W40
  python run_weekly.py --historico 8        # ademas baja las 8 semanas previas (para records)
  python run_weekly.py --sin-descarga       # solo recalcula con lo que ya hay en data/raw

Nunca falla por datos incompletos: si el COES aun no publico todo, el reporte sale
marcado como preliminar. Devuelve 1 solo si no se pudo generar el PDF.
"""

import argparse
import sys

from src.analysis import calcular_resumen
from src.extract.__main__ import descargar_todo
from src.extract.cliente import ClienteCoes
from src.narrative import generar_narrativa
from src.report import generar_pdf
from src.transform import transformar_semana
from src.utils.fechas import misma_semana_anio_anterior, rango_semana, semana_anterior, ultima_semana_completa
from src.utils.logs import configurar_logging, obtener_logger

log = obtener_logger("run_weekly")


def semanas_a_preparar(semana, historico):
    """La semana pedida, las previas (al menos 1 para comparar) y la del anio anterior."""
    previas = [semana_anterior(semana, i) for i in range(max(historico, 1), 0, -1)]
    return previas + [misma_semana_anio_anterior(semana), semana]


def correr(semana, historico=1, descargar=True):
    """Corre todo el pipeline para una semana y devuelve la ruta del PDF."""
    semanas = semanas_a_preparar(semana, historico)
    cliente = ClienteCoes()
    errores_extraccion = {}
    for s in semanas:
        if descargar:
            desde, hasta = rango_semana(s)
            log.info("== Descargando %s", s)
            _, errores = descargar_todo(desde, hasta, cliente=cliente)
            errores_extraccion.update({f"{s}:{k}": v for k, v in errores.items()})
        log.info("== Transformando %s", s)
        transformar_semana(s)

    resumen = calcular_resumen(semana)
    narrativa = generar_narrativa(resumen)
    ruta_pdf = generar_pdf(semana)

    print(f"\n{resumen.texto_semana} ({semana}){'  [PRELIMINAR]' if resumen.es_preliminar else ''}")
    for titular in narrativa.titulares:
        print(f"  * {titular}")
    print(f"PDF: {ruta_pdf}")
    if errores_extraccion:
        print(f"Fuentes con error (se uso lo disponible): {', '.join(errores_extraccion)}")
    if resumen.avisos:
        print(f"Avisos de calidad: {len(resumen.avisos)} (ver data/processed/avisos/avisos_{semana}.json)")
    return ruta_pdf


def main(argv=None):
    """Punto de entrada de la linea de comandos."""
    parser = argparse.ArgumentParser(description="Corre el pipeline semanal completo")
    parser.add_argument("--semana", default=None, help="AAAA-Www (por defecto la ultima completa)")
    parser.add_argument("--historico", type=int, default=1, help="semanas previas a bajar (max 8 recomendado)")
    parser.add_argument("--sin-descarga", action="store_true")
    args = parser.parse_args(argv)
    configurar_logging()
    semana = args.semana or ultima_semana_completa()
    try:
        correr(semana, args.historico, not args.sin_descarga)
    except Exception:
        log.exception("El pipeline no pudo generar el reporte de %s", semana)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
