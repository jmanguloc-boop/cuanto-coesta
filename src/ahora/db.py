"""Base SQLite de "Cuanto COESta Ahora" (data/ahora/ahora.sqlite).

Cada observacion se guarda con su hora de referencia, hora de extraccion y version.
Si el COES cambia un valor ya publicado, se agrega una version nueva y la anterior
se conserva: asi se puede medir cuanto se revisa el dato preliminar.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from src.utils import config

RUTA = config.DIR_DATA / "ahora" / "ahora.sqlite"
TOLERANCIA = 1e-6

ESQUEMA = """
create table if not exists cmg (
    fecha_hora text not null,       -- fin del intervalo, hora Peru (AAAA-MM-DD HH:MM)
    barra text not null,
    version integer not null,
    cmg_total real, cmg_energia real, cmg_congestion real,
    correlativo integer,            -- id del proceso en el COES
    extraido_en text not null,
    primary key (fecha_hora, barra, version)
);
create table if not exists demanda (
    fecha_hora text not null,
    variable text not null,         -- ejecutada, programa_diario
    version integer not null,
    valor real,
    extraido_en text not null,
    primary key (fecha_hora, variable, version)
);
create table if not exists extracciones (
    id integer primary key autoincrement,
    fuente text, inicio text, fin text, ok integer,
    nuevos integer, revisados integer, detalle text
);
"""


@contextmanager
def conectar(ruta=None):
    """Conexion con el esquema creado; hace commit al salir."""
    ruta = Path(ruta or RUTA)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta)
    try:
        con.executescript(ESQUEMA)
        yield con
        con.commit()
    finally:
        con.close()


def _guardar_versionado(con, tabla, claves, valores, filas, extraido_en):
    """Inserta solo lo nuevo o lo que cambio. Devuelve (nuevos, revisados)."""
    nuevos = revisados = 0
    filtro = " and ".join(f"{c} = ?" for c in claves)
    for fila in filas:
        clave = [fila[c] for c in claves]
        previo = con.execute(
            f"select version, {', '.join(valores)} from {tabla} where {filtro} order by version desc limit 1", clave
        ).fetchone()
        actuales = [fila.get(v) for v in valores]
        if previo is None:
            version = 1
            nuevos += 1
        else:
            iguales = all(
                (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= TOLERANCIA)
                for a, b in zip(actuales, previo[1:], strict=True))
            if iguales:
                continue
            version = previo[0] + 1
            revisados += 1
        extras = [c for c in fila if c not in claves and c not in valores]
        columnas = list(claves) + ["version"] + list(valores) + extras + ["extraido_en"]
        datos = clave + [version] + actuales + [fila[c] for c in extras] + [extraido_en]
        con.execute(f"insert into {tabla} ({', '.join(columnas)}) values ({', '.join('?' * len(datos))})", datos)
    return nuevos, revisados


def guardar_cmg(con, filas, extraido_en):
    """filas: dicts con fecha_hora, barra, cmg_total, cmg_energia, cmg_congestion, correlativo."""
    return _guardar_versionado(con, "cmg", ["fecha_hora", "barra"],
                               ["cmg_total", "cmg_energia", "cmg_congestion"], filas, extraido_en)


def guardar_demanda(con, filas, extraido_en):
    """filas: dicts con fecha_hora, variable, valor."""
    return _guardar_versionado(con, "demanda", ["fecha_hora", "variable"], ["valor"], filas, extraido_en)


def registrar_extraccion(con, fuente, inicio, fin, ok, nuevos=0, revisados=0, detalle=""):
    con.execute("insert into extracciones (fuente, inicio, fin, ok, nuevos, revisados, detalle) values (?,?,?,?,?,?,?)",
                (fuente, inicio, fin, int(ok), nuevos, revisados, detalle))


def horas_con_cmg(con, barra):
    """Conjunto de fecha_hora ya guardadas para una barra."""
    return {r[0] for r in con.execute("select distinct fecha_hora from cmg where barra = ?", (barra,))}


def cmg_vigente(con, barra=None, desde=None):
    """Ultima version de cada (fecha_hora, barra) como DataFrame."""
    filtros, params = [], []
    if barra:
        filtros.append("barra = ?")
        params.append(barra)
    if desde:
        filtros.append("fecha_hora >= ?")
        params.append(str(desde))
    donde = ("where " + " and ".join(filtros)) if filtros else ""
    sql = f"""
        select c.* from cmg c
        join (select fecha_hora, barra, max(version) v from cmg {donde} group by fecha_hora, barra) u
          on c.fecha_hora = u.fecha_hora and c.barra = u.barra and c.version = u.v
        order by c.fecha_hora"""
    df = pd.read_sql_query(sql, con, params=params)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df


def demanda_vigente(con, desde=None):
    """Ultima version de cada (fecha_hora, variable) en formato ancho."""
    params = [str(desde)] if desde else []
    donde = "where fecha_hora >= ?" if desde else ""
    sql = f"""
        select d.fecha_hora, d.variable, d.valor from demanda d
        join (select fecha_hora, variable, max(version) v from demanda {donde} group by fecha_hora, variable) u
          on d.fecha_hora = u.fecha_hora and d.variable = u.variable and d.version = u.v"""
    df = pd.read_sql_query(sql, con, params=params)
    if df.empty:
        return pd.DataFrame(columns=["fecha_hora", "ejecutada", "programa_diario"])
    ancho = df.pivot_table(index="fecha_hora", columns="variable", values="valor").reset_index()
    ancho["fecha_hora"] = pd.to_datetime(ancho["fecha_hora"])
    return ancho.sort_values("fecha_hora").reset_index(drop=True)


def revisiones(con, barra=None):
    """Valores que el COES cambio despues de publicarlos: primera vs ultima version."""
    filtro = "where barra = ?" if barra else ""
    params = [barra] if barra else []
    sql = f"""
        with ext as (
            select fecha_hora, barra, max(version) vn from cmg {filtro} group by fecha_hora, barra having max(version) > 1)
        select e.fecha_hora, e.barra, e.vn as versiones,
               p.cmg_total as primero, u.cmg_total as ultimo, u.cmg_total - p.cmg_total as cambio
        from ext e
        join cmg p on p.fecha_hora = e.fecha_hora and p.barra = e.barra and p.version = 1
        join cmg u on u.fecha_hora = e.fecha_hora and u.barra = e.barra and u.version = e.vn
        order by e.fecha_hora"""
    return pd.read_sql_query(sql, con, params=params)


def ultima_extraccion(con, fuente, solo_ok=True):
    """Fila de la ultima extraccion de una fuente o None."""
    sql = "select * from extracciones where fuente = ?" + (" and ok = 1" if solo_ok else "") + " order by id desc limit 1"
    cur = con.execute(sql, (fuente,))
    fila = cur.fetchone()
    return dict(zip([c[0] for c in cur.description], fila, strict=True)) if fila else None
