"""Cuanto COESta Ahora: una consulta de costo marginal y demanda en tiempo real.

Funciona desde cualquier carpeta (util para el Programador de tareas o cron):
  python C:/ruta/al/proyecto/run_ahora.py
  python run_ahora.py --bucle          # repetir cada 30 minutos
"""

import sys

from src.ahora.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
