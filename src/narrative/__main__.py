"""CLI: python -m src.narrative [--semana AAAA-Www] -> imprime titulares y parrafos."""

import argparse
import textwrap

from src.analysis import calcular_resumen
from src.narrative import generar_narrativa
from src.utils.fechas import ultima_semana_completa
from src.utils.logs import configurar_logging


def main(argv=None):
    """Punto de entrada de la linea de comandos."""
    parser = argparse.ArgumentParser(description="Genera los textos de una semana")
    parser.add_argument("--semana", default=None)
    args = parser.parse_args(argv)
    configurar_logging()
    resumen = calcular_resumen(args.semana or ultima_semana_completa())
    n = generar_narrativa(resumen)
    print(resumen.texto_semana)
    for t in n.titulares:
        print(f"  * {t}")
    for seccion, texto in n.parrafos.items():
        print(f"\n[{seccion}]\n" + textwrap.fill(texto, 100))
    print("\n[titulos de graficos]")
    for clave, titulo in n.titulos_graficos.items():
        print(f"  {clave}: {titulo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
