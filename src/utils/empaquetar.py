"""Crea ENTREGA_<slug>_<AAAA-MM-DD>.zip en la raiz del proyecto.

Uso: python -m src.utils.empaquetar

Incluye los archivos versionados en git (codigo, config, docs, tests, workflow,
data/samples, capturas) mas el ultimo PDF generado y un COMO_CORRERLO.txt.
Excluye venv, .git, __pycache__, data/raw, data/processed y otros zip.
"""

import subprocess
import zipfile
from pathlib import Path

from src.utils import config
from src.utils.fechas import hoy_peru

EXCLUIR = (".venv/", "venv/", ".git/", "__pycache__/", "data/raw/", "data/processed/")

COMO_CORRERLO = """{nombre}: {tagline}
==========================================================

Requisitos: Python 3.11 o mas nuevo (https://www.python.org/downloads/).
En Windows, al instalar Python marca la casilla "Add Python to PATH".

-------------------------------------------
WINDOWS (PowerShell o Simbolo del sistema)
-------------------------------------------
1. Descomprime el zip y entra a la carpeta:
     cd ruta\\a\\la\\carpeta
2. Crea el entorno e instala (solo la primera vez, tarda unos minutos):
     python -m venv .venv
     .venv\\Scripts\\pip install -r requirements.txt
3. Descarga y procesa la ultima semana del COES (2 a 3 minutos):
     .venv\\Scripts\\python run_weekly.py
4. Abre la app (una ventana, sin navegador):
     .venv\\Scripts\\python app\\escritorio.py
   Dentro: el boton AHORA trae el precio en vivo y PDF genera el informe (opcional).

-------------------------------------------
MAC (Terminal)
-------------------------------------------
1. Descomprime el zip y entra a la carpeta:
     cd ruta/a/la/carpeta
2. Crea el entorno e instala (solo la primera vez):
     python3 -m venv .venv
     .venv/bin/pip install -r requirements.txt
3. Descarga y procesa la ultima semana del COES:
     .venv/bin/python run_weekly.py
4. Abre la app:
     .venv/bin/python app/escritorio.py

-------------------------------------------
Otras opciones
-------------------------------------------
  run_weekly.py --semana 2026-W40     una semana especifica
  run_weekly.py --historico 8         baja tambien las 8 semanas previas (records y rarezas)
  run_weekly.py --pdf                 genera tambien el PDF semanal
  run_ahora.py --bucle                precio y demanda cada 30 minutos (Ctrl + C para salir)
  python -m pytest -q                 corre los tests

En Linux puede hacer falta instalar Tkinter: sudo apt install python3-tk
Mas detalle en README.md. {aviso}
"""


def archivos_versionados(raiz):
    """Archivos que git conoce (respeta .gitignore)."""
    salida = subprocess.run(["git", "ls-files"], cwd=raiz, capture_output=True, text=True, check=True)
    return [linea for linea in salida.stdout.splitlines() if linea and not linea.startswith(EXCLUIR)]


def ultimo_pdf(raiz):
    """PDF mas reciente de reports/ o None."""
    pdfs = sorted((Path(raiz) / "reports").glob("*.pdf"), key=lambda p: p.stat().st_mtime)
    return pdfs[-1] if pdfs else None


def empaquetar(raiz=None):
    """Arma el zip de entrega y devuelve su ruta."""
    raiz = Path(raiz or config.RAIZ)
    proyecto = config.proyecto()
    destino = raiz / f"ENTREGA_{proyecto['slug']}_{hoy_peru():%Y-%m-%d}.zip"
    carpeta = proyecto["slug"]
    archivos = [a for a in archivos_versionados(raiz) if not a.endswith(".zip")]
    pdf = ultimo_pdf(raiz)
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for archivo in archivos:
            z.write(raiz / archivo, f"{carpeta}/{archivo}")
        if pdf:
            z.write(pdf, f"{carpeta}/reports/{pdf.name}")
        texto = COMO_CORRERLO.format(nombre=proyecto["nombre"], tagline=proyecto["tagline"],
                                     aviso=" ".join(proyecto["aviso"].split()))
        z.writestr(f"{carpeta}/COMO_CORRERLO.txt", texto)
    return destino


if __name__ == "__main__":
    ruta = empaquetar()
    with zipfile.ZipFile(ruta) as z:
        n = len(z.namelist())
    print(f"{ruta} ({ruta.stat().st_size / 1024 / 1024:.2f} MB, {n} archivos)")
