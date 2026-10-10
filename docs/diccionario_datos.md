# Diccionario de datos

Las tablas procesadas viven en `data/processed/<tabla>/<tabla>_<AAAA-Www>.parquet`
(una por semana ISO, lunes a domingo). Se generan con
`python -m src.transform --semana AAAA-Www` y se consultan con DuckDB:

```sql
select tecnologia, sum(valor) * 0.5 / 1000 as gwh
from 'data/processed/generacion/*.parquet'
group by 1 order by 2 desc;
```

## Columnas comunes (formato largo)

| Columna | Tipo | Descripcion |
|---|---|---|
| fecha_hora | timestamp | Hora de Peru (UTC-5, sin zona guardada). En series de 30 min es el **fin** del intervalo: `00:30` es el primer intervalo del dia y `00:00` del dia siguiente el ultimo. En embalses es el instante de la lectura |
| fecha | date | Dia operativo al que pertenece el dato (el intervalo que termina a las 00:00 cuenta para el dia anterior) |
| entidad | texto | Que se mide: SEIN, una tecnologia, una barra, un embalse o una central |
| variable | texto | Nombre de la medicion (ver cada tabla) |
| valor | float | Valor numerico |
| unidad | texto | MW, MWh, S/ por MWh, Hm3, msnm |
| es_preliminar | bool | True si el COES aun no publico el IEOD (evaluacion post operacion) de ese dia, o si el dato viene del respaldo en tiempo real |
| fuente | texto | Origen: portal_demanda, portal_generacion, ieod_cmg, portal_cmg_tiempo_real, ieod_anexo, ieod_despacho |

## demanda

| variable | unidad | descripcion |
|---|---|---|
| demanda_ejecutada | MW | Demanda real del SEIN en el intervalo |
| demanda_prog_diaria | MW | Lo que el programa diario del COES esperaba |
| demanda_prog_semanal | MW | Lo que el programa semanal esperaba |

entidad: siempre `SEIN`. 48 filas por dia y variable.

## generacion

| variable | unidad | descripcion |
|---|---|---|
| generacion | MW | Potencia media producida por un tipo de recurso en el intervalo. Energia = valor x 0.5 h |

entidad: recurso del COES con nombre limpio (Hídrico, Gas natural, Solar, ...).
Columna extra `tecnologia`: hidro, gas, solar, eolica, diesel, carbon, biomasa,
otros (mapeo en `config/mapeos.yaml`).

Nota: el portal publica las series SOLAR y BAGAZO con etiquetas cruzadas; la
transformacion lo detecta por la forma diaria y lo corrige (verificado contra el IEOD).

## costo_marginal

| variable | unidad | descripcion |
|---|---|---|
| cmg_total | S/ por MWh | Costo marginal de corto plazo en la barra |
| cmg_energia | S/ por MWh | Componente de energia |
| cmg_congestion | S/ por MWh | Componente de congestion (puede ser negativo) |

entidad: nombre de la barra (235 en el IEOD; 121 en el respaldo en tiempo real).
Barra de referencia del proyecto: `SANTA ROSA 220`.

## embalses

| variable | unidad | descripcion |
|---|---|---|
| volumen_util | Hm3 | Volumen util almacenado (1 Hm3 = mil millones de litros) |
| nivel | msnm | Nivel de la superficie del agua (embalses que no reportan volumen) |

entidad: embalse o reservorio. Columnas extra: `cuenca`, `empresa`. Lecturas
cada 30 min desde las 00:00. ~25 embalses con volumen y ~4 con nivel.

## centrales

| variable | unidad | descripcion |
|---|---|---|
| generacion | MW | Potencia media de la central en el intervalo (suma de sus unidades) |

entidad: central o unidad segun la nombra el IEOD. Columnas extra: `empresa`,
`area` (NORTE, CENTRO, SUR), `tecnologia` (hidro, termica, solar, eolica; el
IEOD no indica el combustible de cada termica).

## avisos

`data/processed/avisos/avisos_<AAAA-Www>.json`: lista de textos con los avisos de
validacion de la semana (duplicados, intervalos faltantes, valores fuera de rango,
dias sin datos). Los avisos no detienen el proceso.
