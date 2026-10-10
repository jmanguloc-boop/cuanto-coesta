"""Formato de numeros al estilo peruano: 12,345.6 (miles con coma, decimales con punto)."""


def numero(valor, decimales=0):
    if valor is None:
        return "s/d"
    return f"{valor:,.{decimales}f}"


def porcentaje(valor, decimales=1):
    """valor en fraccion (0.123 -> '12.3%')."""
    if valor is None:
        return "s/d"
    return f"{valor * 100:,.{min(decimales, 1)}f}%"


def variacion(actual, anterior):
    """Variacion relativa o None si no se puede calcular."""
    if actual is None or anterior in (None, 0):
        return None
    return actual / anterior - 1


def flecha(var):
    if var is None:
        return ""
    if abs(var) < 0.0005:
        return "="
    return "▲" if var > 0 else "▼"


def texto_variacion(var):
    """'▲ 3.2%' o 's/d'."""
    if var is None:
        return "s/d"
    return f"{flecha(var)} {abs(var) * 100:.1f}%"
