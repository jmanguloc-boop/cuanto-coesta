"""Uso: python -m src.extract.run [--desde AAAA-MM-DD] [--hasta AAAA-MM-DD] [--forzar]

Sin fechas descarga la ultima semana completa (lunes a domingo).
"""

import argparse
from datetime import date, timedelta

from src.extract.coes import descargar_todo


def ultima_semana_completa(hoy: date):
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    lunes_anterior = lunes_actual - timedelta(days=7)
    return lunes_anterior, lunes_anterior + timedelta(days=6)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Descarga data publica del COES")
    parser.add_argument("--desde", type=date.fromisoformat)
    parser.add_argument("--hasta", type=date.fromisoformat)
    parser.add_argument("--forzar", action="store_true", help="ignora la cache y vuelve a bajar todo")
    args = parser.parse_args(argv)

    desde, hasta = ultima_semana_completa(date.today())
    desde = args.desde or desde
    hasta = args.hasta or hasta
    resultado = descargar_todo(desde, hasta, forzar=args.forzar)
    total = sum(len(v) for v in resultado.values())
    print(f"Listo: {total} archivos en data/raw")


if __name__ == "__main__":
    main()
