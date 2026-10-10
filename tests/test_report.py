"""Tests del PDF semanal con la semana de muestra."""

import pypdfium2 as pdfium
import pytest

from src.report import exportar_portada_png, generar_pdf
from tests.conftest import SEMANA_MUESTRA


@pytest.fixture(scope="module")
def pdf(processed_muestra, tmp_path_factory):
    destino = tmp_path_factory.mktemp("reports") / f"prueba_{SEMANA_MUESTRA}.pdf"
    return generar_pdf(SEMANA_MUESTRA, destino=destino, raiz=processed_muestra[0])


def texto_paginas(ruta):
    doc = pdfium.PdfDocument(str(ruta))
    textos = [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
    doc.close()
    return textos


def test_pdf_maximo_6_paginas(pdf):
    paginas = texto_paginas(pdf)
    assert 1 < len(paginas) <= 6


def test_pdf_tiene_todas_las_secciones(pdf):
    texto = "\n".join(texto_paginas(pdf))
    for seccion in ("01 / LA SEÑAL", "02 / DEMANDA Y GENERACIÓN", "03 / HIDROLOGÍA", "04 / LO QUE MERECE ATENCIÓN",
                    "05 / MÉTODO Y FUENTES", "GLOSARIO", "¿QUÉ SIGNIFICA ESTO?", "NO AFILIADO AL COES", "Página 2 de",
                    "EL PULSO EN CUATRO CIFRAS", "LECTURA RÁPIDA", "NOTA TÉCNICA"):
        assert seccion in texto, seccion
    assert "PRELIMINAR" in texto  # la muestra tiene 1 de 7 dias


def test_pdf_sin_guion_largo_ni_asteriscos(pdf):
    texto = "\n".join(texto_paginas(pdf))
    assert "—" not in texto
    assert "m.." not in texto


def test_portada_png(pdf, tmp_path):
    destino = exportar_portada_png(pdf, tmp_path / "portada.png", escala=0.5)
    assert destino.exists() and destino.stat().st_size > 5000
