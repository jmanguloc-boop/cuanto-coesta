"""CLI: python -m src.analysis [--semana AAAA-Www] -> imprime el ResumenSemanal legible."""

import argparse

from src.analysis import calcular_resumen
from src.utils import config
from src.utils.fechas import dia_y_hora, ultima_semana_completa
from src.utils.formato import numero, porcentaje, texto_variacion
from src.utils.logs import configurar_logging


def _var(v, es_puntos):
    if v is None:
        return "s/d"
    return f"{v * 100:+.1f} pp" if es_puntos else texto_variacion(v)


def texto_resumen(r) -> str:
    """Resumen de varias lineas para la consola."""
    glosario = config.glosario()["indicadores"]
    lineas = [f"{config.proyecto()['nombre']}: {r.texto_semana} ({r.semana})"]
    if r.es_preliminar:
        lineas.append(f"  Datos preliminares ({r.dias_con_datos} de 7 dias)")
    lineas.append(f"  Barra de referencia: {r.barra_referencia}")
    lineas.append("")
    lineas.append(f"  {'Indicador':<34}{'Valor':>14}  {'vs sem. ant.':>12}  {'vs anio ant.':>12}")
    for clave, i in r.indicadores.items():
        nombre = glosario[clave]["nombre"]
        if i.valor is None:
            valor = "s/d"
        elif i.unidad == "%":
            valor = porcentaje(i.valor)
        else:
            valor = f"{numero(i.valor, 1 if i.valor < 1000 else 0)} {i.unidad.replace('S/ por MWh', 'S/MWh')}"
        lineas.append(f"  {nombre:<34}{valor:>14}  {_var(i.var_anterior, i.es_puntos):>12}  {_var(i.var_anio, i.es_puntos):>12}")
        if i.momento is not None:
            lineas.append(f"  {'':<34}{dia_y_hora(i.momento)}")
    lineas.append("")
    lineas.append("  Mix: " + ", ".join(f"{config.nombre_tecnologia(t)} {porcentaje(v)}" for t, v in r.mix.items() if v >= 0.001))
    lineas.append("")
    lineas.append("  Hechos destacados:")
    for h in r.hechos:
        lineas.append(f"   - [{h.tipo}] {h.clave} (puntaje {h.puntaje:.1f}): "
                      + ", ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in h.datos.items()))
    if r.avisos:
        lineas.append("")
        lineas.append(f"  Avisos de calidad: {len(r.avisos)}")
    return "\n".join(lineas)


def main(argv=None):
    """Punto de entrada de la linea de comandos."""
    parser = argparse.ArgumentParser(description="Calcula los indicadores de una semana")
    parser.add_argument("--semana", default=None)
    args = parser.parse_args(argv)
    configurar_logging()
    print(texto_resumen(calcular_resumen(args.semana or ultima_semana_completa())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
