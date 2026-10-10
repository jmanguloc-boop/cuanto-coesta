"""Plantillas de texto. Varias por caso para que no suene igual cada semana.

Reglas: espanol simple, sin guion largo, sin afirmar causas que los datos no respalden.
"""

TITULARES = {
    ("variacion", "cmg_promedio", "sube"): [
        "El precio de la electricidad subió {var} en la semana",
        "Producir electricidad salió {var} más caro que la semana pasada",
        "Semana cara: el costo marginal subió {var}",
    ],
    ("variacion", "cmg_promedio", "baja"): [
        "El precio de la electricidad bajó {var} en la semana",
        "Producir electricidad salió {var} más barato que la semana pasada",
        "Respiro en el precio: el costo marginal cayó {var}",
    ],
    ("variacion", "demanda_maxima", "sube"): [
        "El pico de consumo subió {var} y llegó a {valor}",
        "El país pidió más electricidad en su peor momento: {valor}",
    ],
    ("variacion", "demanda_maxima", "baja"): [
        "El pico de consumo bajó {var}, hasta {valor}",
        "Semana más tranquila en el pico: {valor}",
    ],
    ("variacion", "energia_semana", "sube"): [
        "El Perú consumió {var} más electricidad que la semana pasada",
        "Más consumo: {valor} en la semana",
    ],
    ("variacion", "energia_semana", "baja"): [
        "El consumo de electricidad bajó {var} en la semana",
        "Menos consumo: {valor} en la semana",
    ],
    ("variacion", "participacion_renovable", "sube"): [
        "Las renovables ganaron terreno: {valor} de la electricidad",
        "Más agua, sol y viento: las renovables subieron a {valor}",
    ],
    ("variacion", "participacion_renovable", "baja"): [
        "Las renovables retrocedieron a {valor} de la electricidad",
        "Menos renovable en la semana: {valor} del total",
    ],
    ("variacion", "volumen_embalses", "sube"): [
        "Los embalses ganaron {var} de agua",
        "Más agua guardada: los embalses subieron {var}",
    ],
    ("variacion", "volumen_embalses", "baja"): [
        "Los embalses perdieron {var} de agua",
        "Baja la reserva de agua: los embalses cayeron {var}",
    ],
    ("record", "max"): [
        "{nombre}: récord de las últimas {semanas} semanas",
        "Récord del periodo: {nombre} en su punto más alto en {semanas} semanas",
    ],
    ("record", "min"): [
        "{nombre}: mínimo de las últimas {semanas} semanas",
        "Récord del periodo: {nombre} en su punto más bajo en {semanas} semanas",
    ],
    ("anomalia", "sube"): [
        "El {dia} la electricidad salió {veces} más cara que el resto de la semana",
        "Un día caro: el {dia} el precio promedio fue {valor}",
    ],
    ("anomalia", "baja"): [
        "El {dia} la electricidad salió mucho más barata que el resto de la semana",
        "Un día barato: el {dia} el precio promedio bajó a {valor}",
    ],
    ("rareza",): [
        "{n} medias horas con precios raros para su hora; la más llamativa, el {momento}",
        "Precio fuera de lo habitual: {valor} el {momento}, cuando lo normal es {mediana}",
    ],
    ("dato", "demanda_maxima"): [
        "El mayor consumo de la semana fue el {momento}: {valor}",
        "Pico de la semana: {valor} el {momento}",
    ],
    ("dato", "mix_generacion"): [
        "{tecnologia} aportó {participacion} de la electricidad",
        "{participacion} de la energía de la semana vino de {tecnologia_min}",
    ],
    ("dato", "cmg_minimo"): [
        "La media hora más barata fue el {momento}: {valor}",
        "Precio mínimo de la semana: {valor}, el {momento}",
    ],
    ("dato", "precio_capturado_solar"): [
        "La solar vendió a {valor}, {comparacion} el promedio del sistema",
        "El sol produjo en horas {calidad}: precio capturado de {valor}",
    ],
}

APERTURA_PRECIOS = [
    "En Lima (barra Santa Rosa), el costo marginal promedió {valor}",
    "El precio mayorista de la electricidad, medido en la barra Santa Rosa de Lima, promedió {valor}",
    "Producir el último MWh que necesitó el sistema costó en promedio {valor} en la barra Santa Rosa",
]

APERTURA_DEMANDA = [
    "El país consumió {energia} de electricidad {periodo}",
    "{Periodo}, hogares, comercios, minas e industrias usaron {energia}",
]

APERTURA_GENERACION = [
    "{lider} fue la principal fuente de electricidad, con {part_lider} del total",
    "La mayor parte de la electricidad salió de {lider_min}: {part_lider}",
]

APERTURA_HIDRO = [
    "Los principales embalses cerraron la semana con {valor} de agua útil",
    "Al cierre de la semana, los embalses guardaban {valor} de agua útil",
]
