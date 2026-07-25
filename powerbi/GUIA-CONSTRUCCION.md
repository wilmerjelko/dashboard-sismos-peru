# Guía de construcción del dashboard sísmico en Power BI Desktop

> Este proyecto introduce el **visual de mapa** con coordenadas reales, de modo que conviene seguir los pasos en orden. El resultado es una página tipo observatorio con más de seis décadas de actividad sísmica del Perú.

---

## Paso 0 — Habilitar los mapas (solo la primera vez)

Archivo → Opciones y configuración → Opciones → **Seguridad** → marca **"Usar objetos visuales de mapas y mapas coropléticos"** → Aceptar y reinicia Power BI si lo pide.

## Paso 1 — Importar los datos

1. **Obtener datos → Texto o CSV** → `data\sismos_peru.csv` → **Transformar datos**.
2. En Power Query verifica los tipos: `FechaUTC` = Fecha/Hora · `Latitud`, `Longitud`, `Magnitud` = Número decimal · `ProfundidadKm` = Número decimal · `Anio`, `Mes` = Número entero.
3. Un detalle importante para el mapa: selecciona `Latitud` → pestaña Transformar → Tipo de datos ya correcto; luego, ya en el modelo, marca `Latitud` con la categoría de datos **Latitud** y `Longitud` con **Longitud** (Herramientas de columna → Categoría de datos), ya que así Power BI las ubica sin ambigüedad.
4. **Cerrar y aplicar.**

## Paso 2 — Medidas DAX (vista de consultas DAX, todas de un solo golpe)

Pega este bloque en la vista de consultas DAX, ejecútalo para validar y luego pulsa **"Actualizar modelo con cambios"**:

```dax
DEFINE
    MEASURE sismos_peru[Total Sismos] = COUNTROWS ( sismos_peru )
    MEASURE sismos_peru[Magnitud Maxima] = MAX ( sismos_peru[Magnitud] )
    MEASURE sismos_peru[Magnitud Promedio] = AVERAGE ( sismos_peru[Magnitud] )
    MEASURE sismos_peru[Profundidad Promedio] = AVERAGE ( sismos_peru[ProfundidadKm] )
    MEASURE sismos_peru[Sismos Fuertes] =
        CALCULATE ( COUNTROWS ( sismos_peru ), sismos_peru[Magnitud] >= 6 )
    MEASURE sismos_peru[Sismos por Anio] =
        DIVIDE ( [Total Sismos], DISTINCTCOUNT ( sismos_peru[Anio] ) )

EVALUATE
ROW (
    "Total", [Total Sismos],
    "Maxima", [Magnitud Maxima],
    "Fuertes 6+", [Sismos Fuertes],
    "Promedio anual", [Sismos por Anio]
)
```

**Formatos:** `Total Sismos` y `Sismos Fuertes` → número entero con separador de miles · `Magnitud Maxima` y `Magnitud Promedio` → 1 decimal · `Profundidad Promedio` → 0 decimales con sufijo km en la tarjeta.

## Paso 3 — Diseño de la página

**Título:** "Actividad Sísmica del Perú — Catálogo IGP 1960-2023".

| Zona | Visual |
|---|---|
| Fila superior (4 tarjetas) | `Total Sismos` · `Magnitud Maxima` · `Sismos Fuertes` (6.0+) · `Sismos por Anio` |
| Izquierda (protagonista, grande) | **Mapa**: Latitud = `Latitud`, Longitud = `Longitud`, Tamaño = `Magnitud`, Leyenda = `TipoProfundidad` — se dibuja la costa peruana sola, ya que la subducción concentra los eventos frente al litoral |
| Derecha arriba | **Columnas**: Eje = `Anio`, Valores = `Total Sismos` (la cobertura instrumental crece con las décadas) |
| Derecha centro | **Barras**: Eje = `RangoMagnitud`, Valores = `Total Sismos` |
| Derecha abajo | **Tabla Top 10**: `FechaUTC`, `Magnitud`, `ProfundidadKm` → Filtro del visual: N superior = 10 por `Magnitud` |
| Franja izquierda | **Segmentadores**: `Decada`, `RangoMagnitud`, `TipoProfundidad` |

**Tema:** pestaña Ver → Temas → flecha ˅ → Buscar temas → `powerbi\tema_sismos.json`.

## Paso 4 — Detalles finales

- En el mapa reduce el tamaño de burbuja al mínimo legible, dado que hay decenas de miles de puntos, y sube la transparencia del relleno a un 40 % para que la densidad se lea como calor.
- Ordena `RangoMagnitud` y `TipoProfundidad` por su orden natural (Columna → Ordenar por columna) en caso aparezcan alfabéticos.
- Pie de página: "Elaborado por Wilmer Lazaro · Fuente: catálogo sísmico del USGS (Servicio Geológico de los Estados Unidos) · 2026".

## Paso 5 — Capturas

Las mismas cuatro del proyecto anterior: página completa, acercamiento al mapa, vista del modelo y reporte de calidad, guardadas en `docs\capturas\` con los nombres `01-dashboard.png`, `02-mapa.png`, `03-modelo.png`, `04-calidad.png`.

## Paso 6 — Guardar

Guarda como `powerbi\dashboard_sismos_peru.pbix`, puesto que el archivo forma parte del repositorio para quien desee explorarlo.
