# Cuánto COESta: descripción completa del proyecto

> El sistema eléctrico peruano, explicado al toque.

**Ubicación:** `C:\Users\Usuario nuevo\Desktop\pulso-electrico-peru`
**Versión:** 0.5.0 (12 de octubre de 2026). 73 pruebas automáticas en verde.
**Usuario objetivo:** analista o gerente de una empresa generadora (ver `ANALISIS_GERENCIAL_2026-10-11.md`).
**Aviso:** proyecto independiente, no afiliado al COES. Usa solo datos públicos de www.coes.org.pe y del BCRP.

---

## 1. Qué es

Un programa en Python que descarga los datos públicos del COES, los ordena,
calcula indicadores y los muestra en una app de escritorio pensada para
quien trabaja en una generadora: precio día por día, en soles o dólares, lo
programado frente a lo real, salidas de centrales y generación por central.

| Salida | Qué es | Cómo se abre |
|---|---|---|
| **App de escritorio** (principal) | Ventana de Python con menú lateral y tarjetas | Doble clic en `AbrirCuantoCOESta.bat` |
| **Ahora** | Precio y demanda en vivo cada 30 min, con lo programado por el COES | Sección *Ahora* de la app, o `run_ahora.py` |
| **Excel** | Cualquier rango de precios exportado | Botón *Exportar a Excel* en *Evolución* |
| **PDF semanal** (opcional) | Informe de 6 páginas | Botón *Descargar PDF* en *Resumen* |
| **Dashboard web** (opcional) | Versión Streamlit para publicar en internet | `streamlit run app\streamlit_app.py` |

---

## 2. Cómo usarlo

### En la PC de la empresa (sin .exe y sin permisos de administrador)

| Paso | Qué hacer |
|---|---|
| 1 | Copiar la carpeta del proyecto (o descomprimir el zip de entrega) |
| 2 | Doble clic en **`DiagnosticoConexion.bat`**. Prueba si la PC llega al COES, al BCRP y a PyPI, sin instalar nada, y deja `diagnostico_conexion.txt` |
| 3 | Doble clic en **`AbrirCuantoCOESta.bat`**. La primera vez crea el entorno e instala lo necesario (unos minutos); luego abre la app directamente |
| 4 | Opcional: **`ActivarActualizacionAutomatica.bat`** deja la consulta del precio cada 30 min al prender la PC (acceso directo en la carpeta Inicio de Windows, sin Programador de tareas) |

Detalles pensados para redes corporativas:

- **Proxy:** se usa el de Windows automáticamente. Si TI da otro, se pone en `config\fuentes.yaml` (`cliente.proxy`).
- **Certificados:** usa los de Windows (librería `truststore`), necesario cuando la red inspecciona el tráfico SSL.
- **Sin internet para pip:** si existe una carpeta `wheels\` con las librerías, se instala desde ahí sin conexión.
- **OneDrive:** si el proyecto está en OneDrive o SharePoint, los datos se guardan en `%LOCALAPPDATA%\CuantoCOESta\data` (la sincronización corrompe bases SQLite).
- **Python:** usa `py -3` o `python`, el que exista. Requiere Python 3.11 o superior.

### Desde la consola (desarrollo)

```bat
.venv\Scripts\python run_weekly.py          :: baja y procesa la última semana (2 a 3 min)
.venv\Scripts\python app\escritorio.py      :: abre la app
.venv\Scripts\python run_ahora.py           :: una consulta en vivo (rellena huecos de hasta 7 días)
.venv\Scripts\python -m pytest -q           :: 73 pruebas
```

Otras opciones: `run_weekly.py --semana 2026-W40`, `--historico 8`, `--pdf`, `--sin-descarga`;
`run_ahora.py --bucle`; `python -m src.utils.diagnostico`; `python -m src.utils.empaquetar`.

---

## 3. La app de escritorio

Diseño amigable: menú lateral azul marino, fondo gris azulado claro, tarjetas
blancas, naranja solo para lo que pide atención, tipografía Plus Jakarta Sans
(incluida). Cada cifra tiene un botón **i** con su explicación; los gráficos
muestran el valor exacto al pasar el mouse.

**Siempre visible (menú lateral):** botón **↻ Actualizar ahora** y sello de
frescura ("Último dato 6:00 a. m., hace 17 min, preliminar"; en naranja si pasa
más de una hora). Al abrir, si el dato tiene más de 40 minutos, se actualiza solo
y rellena los días que faltan si la PC estuvo apagada.

| Sección | Qué muestra |
|---|---|
| **Resumen** | Frase de la semana, 4 cifras, precio por hora, mix de energía, 3 hechos destacados, selector de semana, *Actualizar* y *Descargar PDF* |
| **Ahora** | Precio en Lima de la última media hora, si es normal para esa hora, comparación con media hora antes, ayer y hace una semana, curva de hoy vs ayer **vs lo programado por el COES**, cuánto se aleja el real de lo programado, **qué se espera mañana**, consumo actual |
| **Evolución** (nueva) | Rango libre (7 días, 30 días, este mes, año hidrológico, este año, todo o fechas a mano), cualquier barra, **soles o dólares**; promedio, **punta (6 a 11 p. m.)**, fuera de punta, máximo y mínimo; precio día por día con banda mín-máx y días preliminares marcados; **mapa de calor día × media hora**; promedio por mes; **exportar a Excel** |
| **Precios** | Promedio, extremos, horas caras, curva de la semana, precio por hora, precios inusuales y cuánto cambia el dato al confirmarse |
| **Demanda** | Demanda máxima, energía, diferencia con lo previsto y curva real vs prevista |
| **Generación** | % renovable con y sin hidro, precio capturado por solar y eólica, generación por fuente |
| **Embalses** | Agua guardada, comparación con hace un año, evolución diaria y embalses con más agua |
| **Eventos** (nueva) | Salidas forzadas y mantenimientos de generación, MW fuera de servicio por día, las salidas más grandes con el precio mientras duraron, últimos eventos en la red |
| **Centrales** (nueva) | Cualquier central: energía, potencia máxima, horas generando, **precio capturado** e **ingreso spot estimado**; participación de cada empresa vs la semana anterior; centrales con más energía |
| **Mapa** | Precio promedio por zona sobre el mapa del Perú, con las barras más caras y más baratas |
| **Fuentes** | Cada fuente, su frecuencia, si es preliminar o confirmada y cuándo se descargó por última vez |
| **Glosario** | Cada término en una línea |

---

## 4. Datos que usa

Todo con `requests`, pausa de 2 segundos entre pedidos, caché local y sin volver a bajar días cerrados.

| Fuente | Qué trae | Frecuencia | Estado |
|---|---|---|---|
| Demanda (portal COES) | Ejecutada, programa diario y semanal cada 30 min | Semanal y cada 30 min | Preliminar |
| Generación (portal COES) | MW por recurso y por central | Semanal | Preliminar |
| Costo marginal (IEOD, zip diario) | Precio, energía y congestión en 235 barras | Semanal | Confirmado |
| Costo marginal en tiempo real | ~120 barras; respaldo y medición de revisiones | Semanal y cada 30 min | Preliminar |
| IEOD Anexo A | Embalses, despacho por central, eventos, mantenimientos, indisponibilidades | Semanal | Confirmado |
| **Programa Diario de Operación** (nueva) | Costo marginal **programado** en Santa Rosa, Trujillo y Socabaya (US$/MWh) | Diario (el de mañana sale por la tarde) | Programado |
| **Tipo de cambio BCRP** (nueva) | S/ por US$, venta, sistema bancario SBS | Diario hábil | Oficial |

**Cómo se arma la serie continua:** para cada media hora se usa la mejor
versión disponible: confirmado (IEOD) antes que preliminar (tiempo real) antes
que en vivo. Las semanas dejaron de ser un límite: se puede ver cualquier rango.

**Hallazgos sobre los datos del COES** (detalle en `docs\fuentes_coes.md`):
la exportación de costo marginal pierde ~13 de 48 medias horas (se usa el IEOD);
el portal cruza las etiquetas SOLAR y BAGAZO (se corrige); el precio preliminar
cambia en promedio 13.5% al confirmarse; el costo marginal programado viene en
dólares; el 12/10/2026 el real llegó a ir 431% sobre lo programado.

---

## 5. Indicadores y reglas

| Tema | Indicadores |
|---|---|
| Precios (Santa Rosa 220 kV u otra barra) | Promedio base, punta y fuera de punta; máximo y mínimo con fecha y hora; horas caras y baratas; precio por hora; promedio diario y mensual; congestión media; en S/ o USD |
| En vivo | Último precio, vs media hora antes, ayer y semana pasada; vs lo programado; previsión de mañana |
| Demanda | Máxima con día y hora, energía, diferencia con el programa del COES |
| Generación | Mix, % renovable con y sin hidro, precio capturado por tecnología y por central |
| Centrales y empresas | Energía, potencia máxima, horas generando, ingreso spot estimado por central, cuota de cada empresa |
| Oferta | Salidas forzadas, mantenimientos y MW fuera de servicio por día |
| Hidrología | Agua útil en embalses vs semana anterior y año anterior |
| Calidad | Precios inusuales, cuánto cambia el preliminar, cobertura del rango, días preliminares |

Reglas clave: precio inusual = rompe el rango de su hora en 4 semanas (margen 10% y S/ 60);
punta = de 18:00 a 23:00; año hidrológico = noviembre a octubre; el ingreso spot es una
**estimación** (generación × costo marginal; no incluye potencia, contratos ni retiros);
los textos no inventan causas ("coincidencia, no causa").

---

## 6. Cómo está construido

```
pulso-electrico-peru\
├── AbrirCuantoCOESta.bat              Abre la app (instala la primera vez, sin admin)
├── DiagnosticoConexion.bat            Prueba la red de la PC sin instalar nada
├── ActivarActualizacionAutomatica.bat Consulta cada 30 min al prender la PC
├── app\
│   ├── escritorio.py        App de escritorio (12 secciones)
│   ├── tk_ui.py             Componentes: tarjetas, botones, menú, tooltips, gráficos con hover
│   ├── streamlit_app.py     Dashboard web opcional (+ graficos.py)
├── src\
│   ├── extract\             Descargadores COES + bcrp.py (tipo de cambio) + programa.py (programado)
│   │                        cliente.py: pausas, reintentos, caché, proxy y certificados de Windows
│   ├── transform\           Tablas limpias por semana (incluye eventos)
│   ├── analysis\            Indicadores, hechos, rarezas, serie.py (rango libre), centrales.py
│   ├── narrative\           Textos por reglas
│   ├── visual\              Gráficos matplotlib (app y PDF): evolución, calor, mensual, eventos, centrales
│   ├── ahora\               En vivo: extractor con relleno de huecos, SQLite con versiones, memoria
│   ├── report\              PDF
│   └── utils\               Config, fechas, formato, estilo, estado, diagnóstico, empaquetado
├── config\
│   ├── proyecto.yaml        Nombre, versión, paleta, tipografía, colores por tecnología
│   ├── fuentes.yaml         Fuentes, proxy, certificados
│   ├── analisis.yaml        Umbrales, punta, año hidrológico, reglas de rarezas
│   ├── glosario.yaml        Todas las explicaciones
│   ├── mapeos.yaml          Recursos del COES -> tecnologías
│   ├── interno.ejemplo.yaml Plantilla para centrales y barras propias
│   └── interno.yaml         (lo creas tú; NUNCA se sube a GitHub)
├── assets\                  Fuente Plus Jakarta Sans (OFL), mapa del Perú, coordenadas de barras
├── data\                    raw, processed, ahora\ahora.sqlite, tipo_cambio.csv (no se versionan); samples
├── docs\                    fuentes_coes.md, diccionario_datos.md, capturas
├── tests\                   73 pruebas
├── requirements.txt         Todo (incluye web y pruebas)
├── requirements-app.txt     Solo lo que necesita la app (para la PC de la empresa)
└── run_weekly.py, run_ahora.py, README.md, PROGRESO.md, LICENSE (MIT)
```

---

## 7. Configuración sin tocar código

| Quiero... | Archivo |
|---|---|
| Ver primero mis centrales y calcular su ingreso con su barra | `config\interno.yaml` (copiar de `interno.ejemplo.yaml`) |
| Poner un proxy | `config\fuentes.yaml` → `cliente.proxy` |
| Cambiar qué es punta, precio alto o bajo, año hidrológico | `config\analisis.yaml` |
| Cambiar colores, nombre o versión | `config\proyecto.yaml` |
| Cambiar una explicación | `config\glosario.yaml` |

---

## 8. Estado frente al análisis gerencial (11/10/2026)

| Punto del análisis | Estado |
|---|---|
| **Fase 0** Diagnóstico de conexión, proxy y certificados, `.bat` sin admin, librerías empaquetadas, datos fuera de OneDrive | Hecho. Probado con una copia limpia: el `.bat` instaló todo y abrió la app |
| 3.1 Ver día por día, rango libre, base/punta/fuera de punta, mapa de calor, promedio mensual, exportar a Excel | Hecho (sección *Evolución*) |
| 3.2 Actualizar ahora visible siempre, relleno de huecos, sello de frescura, actualización al iniciar Windows | Hecho |
| 3.2 Reemplazo preliminar por confirmado | Hecho en la serie continua (confirmado tiene prioridad); llega con la descarga semanal |
| 3.2 Mostrar energía y congestión | Parcial: congestión media en *Evolución* y en el Excel |
| A. Precio en dólares (BCRP) | Hecho en *Evolución* y en el Excel |
| B. Costo marginal programado y "mañana se espera"; programado vs real | Hecho para el precio en *Ahora* |
| D. Eventos, mantenimientos e indisponibilidades | Hecho (sección *Eventos*) |
| F. Elegir barra y ver su evolución | Hecho (selector en *Evolución*); falta el gráfico de diferencia contra Santa Rosa |
| J. Generación, precio capturado e ingreso spot por central; participación por empresa | Hecho (sección *Centrales*), con barra de referencia hasta que configures `interno.yaml` |
| Versión visible | Hecho (v0.5.0 en el menú) |
| C. Hidrología vs promedio histórico | Pendiente: necesita años de historia |
| E. Tecnología que marca el precio y horas de estrés | Pendiente |
| G. Comparación con precio en barra de Osinergmin | Pendiente |
| H. Alertas por notificación o correo | Pendiente: faltan tus umbrales |
| I. Histórico de 3 años | Pendiente: es una descarga larga (unas horas); se hace una vez |
| J. Margen spot de térmicas, programado vs ejecutado por central | Pendiente |
| Modo "analista", guía de una página, prueba diaria contra el COES | Pendiente |

---

## 9. Lo que necesito de ti

1. **Correr `DiagnosticoConexion.bat` en la laptop de la empresa** y enviarme `diagnostico_conexion.txt`.
2. **Tus centrales y sus barras** en `config\interno.yaml` (o pásame los nombres y lo lleno yo).
3. **Umbrales de alerta** y si prefieres notificación de Windows, correo o ambos.
4. **Un reporte interno de producción de un mes cerrado** para validar las cifras por central.
5. Si TI pide aprobación para usar Python en la laptop.
