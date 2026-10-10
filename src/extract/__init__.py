"""Descargadores por fuente. Todos exponen descargar(desde, hasta) -> lista de archivos."""

from src.extract import costo_marginal, demanda, generacion, ieod_anexo

# costo_marginal_tr no se lista: lo llama costo_marginal como respaldo
DESCARGADORES = {
    "costo_marginal": costo_marginal.descargar,
    "demanda": demanda.descargar,
    "generacion": generacion.descargar,
    "ieod_anexo": ieod_anexo.descargar,
}
