"""Prueba de humo de la app de escritorio (se salta si no hay pantalla, como en GitHub Actions)."""

import sys
import time

import pytest

from src.utils import config


@pytest.mark.skipif(not (config.DIR_PROCESSED / "demanda").exists(), reason="sin datos procesados locales")
def test_app_escritorio_carga_todas_las_pestanas():
    tk = pytest.importorskip("tkinter")
    try:
        prueba = tk.Tk()
        prueba.destroy()
    except tk.TclError:
        pytest.skip("sin pantalla disponible")
    sys.path.insert(0, str(config.RAIZ / "app"))
    import escritorio

    app = escritorio.App()
    app.raiz.withdraw()
    inicio = time.time()
    while (app.r is None or app.ev_datos is None or app.ocupado or app.pendientes) and time.time() - inicio < 150:
        app.raiz.update()
        time.sleep(0.05)
    try:
        assert app.r is not None, "la semana no termino de cargar"
        assert len(app.paneles) == len(escritorio.SECCIONES) == 10
        for clave, panel in app.paneles.items():
            assert panel.interior.winfo_children(), f"pestana vacia: {clave}"
    finally:
        app.raiz.destroy()
