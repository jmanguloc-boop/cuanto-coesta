# Fuentes de datos del COES

Investigado el 2026-10-09. Todas las fuentes son publicas y se bajan con
`requests`, sin Playwright. La configuracion vive en `config/fuentes.yaml`.

## Reglas de cortesia con el servidor

- `https://www.coes.org.pe/robots.txt` devuelve 404: no hay restricciones
  publicadas. Igual se aplica una pausa de 2 s entre pedidos y cache en disco.
- User-Agent propio que identifica al bot (`PulsoElectricoPeru/0.1`).
- Los dias viejos se bajan una sola vez. Los ultimos 3 dias se consideran
  provisionales y se refrescan si la copia tiene mas de 6 horas.
- Una semana completa son 9 pedidos y tarda ~25 s.

## 1. Demanda del SEIN

| | |
|---|---|
| Pagina | https://www.coes.org.pe/Portal/portalinformacion/demanda |
| Endpoint | `GET /Portal/portalinformacion/ExportarDemanda?fechaInicial=dd/mm/aaaa&fechaFinal=dd/mm/aaaa` |
| Formato | xlsx, hoja `DEMANDA` |
| Columnas | FECHA, EJECUTADO, PROG. DIARIA, PROG. SEMANAL (MW) |
| Resolucion | 30 min. El intervalo `dd/mm 00:30` es el primero del dia; `dd+1/mm 00:00` es el ultimo |

Tambien existe `POST /Portal/portalinformacion/Demanda` (JSON con la misma data
y series del grafico). Se prefiere el Excel.

## 2. Generacion por central y tipo de recurso

| | |
|---|---|
| Pagina | https://www.coes.org.pe/Portal/portalinformacion/generacion |
| Endpoint | `POST /Portal/portalinformacion/Generacion` con `fechaInicial`, `fechaFinal`, `indicador=0` |
| Formato | JSON. Claves: `ListadoPorEmpresa`, `GraficoPorEmpresa`, `GraficoTipoCombustible`, `Indicador` |
| Resolucion | 30 min |

- `GraficoTipoCombustible.Series`: una serie por recurso (BAGAZO, BIOGAS,
  CARBON, DIESEL, EOLICA, GAS, HIDRICO, NAFTA & GAS REFINERIA, RESIDUAL, SOLAR)
  con 48 valores en MW.
- `ListadoPorEmpresa`: detalle por central con columnas H1..H48.
- **Trampa 1**: aunque se pida un rango, solo devuelve el primer dia. Por eso se
  pide dia por dia (`max_dias_por_pedido: 1`).
- **Trampa 2**: el servidor manda los nombres con el caracter de reemplazo
  `U+FFFD` en lugar de las tildes (`BIOG�S`, `E�LICA`). El JSON es
  UTF-8 valido, el dano viene de origen. Hay que normalizar nombres en
  `src/transform` (pendiente).
- `indicador=1` devuelve listas vacias y `ExportarGeneracion?indicador=1` da
  error 500. Se usa `indicador=0`.
- `ExportarGeneracion?indicador=0` da un Excel con produccion diaria por
  central (MWh). Sirve para validar, no se descarga por ahora.

**Validacion**: la suma de generacion por recurso x 0.5 h coincide con la
demanda ejecutada del mismo dia (ratio 1.000 los 7 dias de la semana
28/09 - 04/10/2026). El 01/10/2026 dio 182 025 MWh, igual al total del Excel
oficial.

## 3. Costo marginal nodal

| | |
|---|---|
| Pagina | https://www.coes.org.pe/Portal/mercadomayorista/costosmarginales |
| Endpoint | `GET /Portal/mercadomayorista/costosmarginales/ExportarMasivo?fechaInicio=dd/mm/aaaa&fechaFin=dd/mm/aaaa&defecto=S` |
| Formato | xlsx, hoja `COSTOMARGINAL`, encabezado en la fila 5, columna A vacia |
| Columnas | FECHA HORA, NODO EMD, NOMBRE BARRA, ENERGIA, CONGESTION, TOTAL |
| Unidad | S/ por MWh |
| Limite | 30 dias por pedido |

- `defecto=S`: 121 barras de 138 kV o mas (~1 MB por semana). `defecto=` vacio
  baja todas las barras. Cualquier otro valor devuelve un Excel vacio.
- **Trampa 3**: hay huecos. Para la semana del 01 al 07/10/2026 los dias
  traen entre 26 y 48 de los 48 intervalos de media hora. Pendiente revisar si
  la seccion "Costos marginales revisados"
  (`/Portal/mercadomayorista/costosmarginales/revisados`) viene completa.

## Fuentes candidatas para fases siguientes

- Estadisticas anuales: `/Portal/publicaciones/estadisticas/estadistica?anio=AAAA`
- Programa diario de operacion: `/Portal/operacion/progoperacion/programadiario`
- Pronostico de demanda en tiempo real: `GET /Portal/portalinformacion/ObtenerPronosticoTiempoReal`
- Hidrologia (embalses): `/Portal/Operacion/Estudios/Hidrologia`
