"""Helpers de fechas: semanas ISO, hora Peru y textos legibles."""

from datetime import date, datetime, timedelta, timezone

# Peru no tiene horario de verano: UTC-5 fijo (evita depender de tzdata en Windows)
HORA_PERU = timezone(timedelta(hours=-5), "PET")

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def ahora_peru():
    """Fecha y hora actual en Peru."""
    return datetime.now(HORA_PERU)


def hoy_peru():
    """Fecha actual en Peru."""
    return ahora_peru().date()


def semana_iso(fecha: date) -> str:
    """Codigo ISO de semana (2026-W40) de una fecha."""
    anio, semana, _ = fecha.isocalendar()
    return f"{anio}-W{semana:02d}"


def rango_semana(codigo: str):
    """'2026-W40' -> (lunes, domingo)."""
    anio, semana = codigo.upper().split("-W")
    lunes = date.fromisocalendar(int(anio), int(semana), 1)
    return lunes, lunes + timedelta(days=6)


def semana_anterior(codigo: str, semanas=1) -> str:
    """Codigo de la semana n semanas antes."""
    lunes, _ = rango_semana(codigo)
    return semana_iso(lunes - timedelta(weeks=semanas))


def misma_semana_anio_anterior(codigo: str) -> str:
    """Misma semana ISO del anio anterior."""
    anio, semana = codigo.upper().split("-W")
    try:
        return semana_iso(date.fromisocalendar(int(anio) - 1, int(semana), 1))
    except ValueError:  # semana 53 que no existe el anio anterior
        return semana_iso(date.fromisocalendar(int(anio) - 1, 52, 1))


def ultima_semana_completa(hoy: date = None) -> str:
    """Ultima semana lunes a domingo ya terminada."""
    hoy = hoy or hoy_peru()
    return semana_iso(hoy - timedelta(days=hoy.weekday() + 7))


def fecha_larga(fecha: date) -> str:
    """Fecha legible: 4 de octubre de 2026."""
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


def dia_y_hora(momento: datetime) -> str:
    """'jueves 2 de octubre, 7:30 p. m.'"""
    hora = momento.hour % 12 or 12
    sufijo = "a. m." if momento.hour < 12 else "p. m."
    return f"{DIAS[momento.weekday()]} {momento.day} de {MESES[momento.month - 1]}, {hora}:{momento.minute:02d} {sufijo}"


def texto_semana(codigo: str) -> str:
    """'Semana del 28 de septiembre al 4 de octubre de 2026'."""
    lunes, domingo = rango_semana(codigo)
    if lunes.month == domingo.month:
        return f"Semana del {lunes.day} al {domingo.day} de {MESES[domingo.month - 1]} de {domingo.year}"
    if lunes.year == domingo.year:
        return (f"Semana del {lunes.day} de {MESES[lunes.month - 1]} al {domingo.day} de "
                f"{MESES[domingo.month - 1]} de {domingo.year}")
    return f"Semana del {fecha_larga(lunes)} al {fecha_larga(domingo)}"
