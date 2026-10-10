# Fuentes de datos del COES

Reconocimiento hecho el 9 y 10 de octubre de 2026. Configuracion en
`config/fuentes.yaml`. Muestras de 1 dia (01/10/2026) en `data/samples/`.

## Tabla resumen

| Fuente | Que trae | Formato | Frecuencia | Retraso | Estado del dato | Historico | Acceso | MVP |
|---|---|---|---|---|---|---|---|---|
| Demanda (portal) | Demanda ejecutada, programa diario y semanal del SEIN | xlsx | 30 min | horas (tiempo real) | Preliminar | 2025 confirmado, rango largo | requests GET | Si |
| Generacion (portal) | MW por tipo de recurso (10) y por central | JSON | 30 min | horas | Preliminar | 2025 confirmado | requests POST, dia por dia | Si |
| Costo marginal CP (IEOD, zip diario) | CMg total, energia y congestion en 235 barras | xlsx dentro de zip | 30 min (48/dia) | ~1 a 2 dias | Post operacion (puede revisarse a fin de mes) | IEOD desde 2011 | requests GET, visor de archivos | Si (principal) |
| Costo marginal tiempo real (portal) | CMg en 121 barras >= 138 kV | xlsx | 30 min, **solo ~35 de 48 intervalos** | minutos | Preliminar | 2025 confirmado | requests GET, max 30 dias | Respaldo |
| IEOD Anexo A | 46 hojas: embalses, caudales, eventos, mantenimientos, indisponibilidades, despacho, combustibles, flujos | xlsx (~1.1 MB/dia) | diario, datos cada 30 min | ~1 a 2 dias | Post operacion | desde 2011 | requests GET, visor de archivos | Si (hidrologia) |
| CMg revisados | Informe mensual de CMg | carpetas pdf/xlsx | mensual | ~1 mes | Definitivo | desde 2018 | visor de archivos | No |
| Mantenimientos programados | Programas anual, mensual, semanal, diario | carpetas | segun programa | adelantado | Programado | si | visor de archivos | No |
| Eventos relevantes / Evaluacion de fallas | Informes de fallas | pdf | por evento | dias | Definitivo | si | visor | No |
| Estadisticas anuales | Anuario del SEIN | xlsx/pdf | anual | meses | Definitivo | si | visor | No |

## Fuentes elegidas para el MVP (4)

1. **Costo marginal** (IEOD, con respaldo en tiempo real): es el precio de la
   electricidad, el indicador estrella. Se usa la version del IEOD porque la
   exportacion del portal pierde ~13 intervalos al dia (sobre todo de madrugada),
   lo que sesgaria el perfil horario.
2. **Demanda**: cuanto consume el pais; necesaria para maxima demanda y energia.
3. **Generacion por tecnologia**: mix, renovables y precio capturado.
4. **Hidrologia** (hoja `PRINCIP_VOLÚMENES` del IEOD): el agua embalsada explica
   buena parte de los precios en el Peru.

Eventos, mantenimientos e indisponibilidades vienen gratis en el mismo Anexo A;
quedan disponibles para versiones futuras.

## robots.txt y terminos de uso

- `https://www.coes.org.pe/robots.txt` responde 404: no hay restricciones
  publicadas para bots.
- El portal no publica una pagina de terminos de uso (solo "Derechos ARCO",
  sobre datos personales, que no aplica: aqui no hay datos personales).
- La informacion es publica por mandato (Ley 28832 y procedimientos tecnicos
  del COES). Igual el bot: se identifica con su User-Agent, espera 2 s entre
  pedidos, guarda cache y no vuelve a bajar dias cerrados.
- Volumen por corrida semanal: ~9 pedidos del portal + 14 del IEOD (~45 MB).

## Detalle por fuente

### Demanda
- `GET {portal}/portalinformacion/ExportarDemanda?fechaInicial=dd/mm/aaaa&fechaFinal=dd/mm/aaaa`
- Hoja `DEMANDA`, encabezado en la fila 4: FECHA, EJECUTADO, PROG. DIARIA, PROG. SEMANAL.
- Intervalos: `dd/mm 00:30` es el primero del dia y `dd+1/mm 00:00` el ultimo.

### Generacion
- `POST {portal}/portalinformacion/Generacion` con `fechaInicial`, `fechaFinal`, `indicador=0`.
- JSON: `GraficoTipoCombustible.Series` (una serie por recurso, 48 valores en MW),
  `ListadoPorEmpresa` (por central, columnas H1..H48).
- Trampas: ignora el rango (solo devuelve el primer dia); los nombres llegan con
  `U+FFFD` en vez de tildes desde el servidor (`BIOG�S`, `E�LICA`);
  `indicador=1` devuelve vacio.
- Validado: suma por recurso x 0.5 h = demanda ejecutada del dia (ratio 1.000,
  semana 28/09 - 04/10/2026).

### Visor de archivos (IEOD y otras carpetas)
- Listar: `POST {portal}/browser/vistadatos` con `baseDirectory`, `url`,
  `indicador`, `initialLink`, `orderFolder` (devuelve HTML con las rutas).
- Bajar: `GET {portal}/browser/download?url=<ruta codificada en UTF-8>`.
- Estructura IEOD: `Post Operación/Reportes/IEOD/AAAA/MM_Mes/DD/` con
  `AnexoA_DDMM.xlsx`, `CMgAAAAMMDD.zip` y el informe pdf. Los meses usan
  "09_Setiembre".
- El 10/10/2026 el ultimo dia publicado era el 08/10: retraso de ~1 a 2 dias.

### Costo marginal (IEOD)
- Zip diario de 5.4 MB con `CMgCP{DDMM}.xlsx` (275 KB) mas archivos de modelos
  (GAMS, PSSE) que no se usan. Solo se guarda el Excel.
- Hojas `Cmg_Barra` (total), `Cmg_Ener`, `Cmg_Cong`. Fila 3: nombres de barra;
  columna B: fecha hora (00:30 ... 23:59, donde 23:59 = 24:00). 48 intervalos.
- Barra de referencia elegida: **SANTA ROSA 220** (Lima).

### Costo marginal tiempo real (respaldo)
- `GET {portal}/mercadomayorista/costosmarginales/ExportarMasivo?fechaInicio=...&fechaFin=...&defecto=S`
- `defecto=S`: barras >= 138 kV; vacio: todas; otro valor: Excel vacio.
- El COES calcula 48 procesos al dia (`listaproceso`), pero la exportacion solo
  trae ~35. Solo se usa para dias que el IEOD aun no publica (marcados preliminares).

### Hidrologia (IEOD Anexo A, hoja PRINCIP_VOLÚMENES)
- Filas 5 a 10: empresa, cuenca, instalacion, equipo, tipo, unidad.
- 25 embalses en volumen util (Hm3) y 3 en nivel (msnm). Valores cada 30 min;
  `--` cuando no hay lectura.
- Otras hojas utiles: `PRINCIP_CAUDALES`, `EVENTOS`, `INDISP`,
  `MANTENIMIENTO EJECUTADOS`, `TIPO_RECURSO`, `COSTO_OPE_EJEC`.

## Cuanto COESta Ahora (cada 30 minutos)

Verificado el 10/10/2026: a las 10:31 ya estaba publicado el intervalo de las
10:00 (costo marginal) y el de las 10:30 (demanda).

| Dato | Endpoint | Respuesta |
|---|---|---|
| Procesos de CMg del dia | `POST /mercadomayorista/costosmarginales/listaproceso` con `fecha` | JSON: `Cmgncorrelativo`, `FechaProceso` (hh:mm, 23:59 = fin del dia) |
| CMg de un proceso | `POST /mercadomayorista/costosmarginales/lista` con `correlativo`, `defecto=S` | Tabla HTML: hora, barra, energia, congestion, total (~115 barras >= 138 kV, ~36 KB) |
| Coordenadas de barras | `POST /mercadomayorista/costosmarginales/mapa` | HTML con `coorx` (latitud) y `coory` (longitud) por barra; guardado en `assets/mapas/barras_coordenadas.csv` (115 barras) |
| Demanda del dia | `POST /portalinformacion/Demanda` | JSON: series Ejecutado (hasta el ultimo intervalo), Programacion diaria y semanal |

- Un mismo intervalo puede tener varios procesos (el COES recalcula): el mas
  reciente se guarda como version nueva y la anterior se conserva.
- Algunos procesos vienen sin filas: se ignoran y se registran en el log.

## Preliminar vs confirmado

Comparando el CMg en tiempo real con el del IEOD en Santa Rosa 220 (semana
28/09 - 04/10/2026, 283 medias horas con ambas versiones): sin desfase horario
(probado con -60 a +60 min), 52 % de los valores iguales, cambio promedio de
S/ 46.5 por MWh (13.5 % del precio medio) y un maximo de S/ 660.7.
