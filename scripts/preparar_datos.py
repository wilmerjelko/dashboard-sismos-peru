# -*- coding: utf-8 -*-
"""
Preparacion y control de calidad del catalogo sismico del Peru (1960-2026).

Toma el catalogo descargado desde la API publica del USGS (Servicio Geologico
de los Estados Unidos), normaliza su estructura y aplica un pipeline de
validaciones antes de generar el dataset final que alimenta el dashboard,
junto a un reporte de auditoria que documenta cada corte aplicado.

El script es tolerante a distintas fuentes, dado que detecta automaticamente
el separador, la codificacion y los nombres de columna tanto del formato del
USGS (time, latitude, longitude, depth, mag, place) como del formato del
catalogo nacional del IGP (FECHA_UTC, LATITUD, LONGITUD, PROFUNDIDAD,
MAGNITUD), de modo que cualquiera de los dos archivos funciona como entrada.

Uso:    python scripts/preparar_datos.py
Espera: un unico archivo .csv dentro de data/raw/
Genera: data/sismos_peru.csv y docs/reporte_calidad.txt

Autor: Wilmer Jelko Lazaro Guerra
"""
import glob
import os
import sys
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR = os.path.join(BASE, "data", "raw")
SALIDA = os.path.join(BASE, "data", "sismos_peru.csv")
REPORTE = os.path.join(BASE, "docs", "reporte_calidad.txt")

lineas = []


def log(msg=""):
    print(msg)
    lineas.append(msg)


def cargar_archivo():
    candidatos = glob.glob(os.path.join(RAW_DIR, "*.csv"))
    if not candidatos:
        sys.exit(f"No se encontro ningun CSV en {os.path.abspath(RAW_DIR)} - "
                 "descarga el catalogo del IGP y colocalo en esa carpeta")
    ruta = candidatos[0]
    log(f"Archivo de entrada: {os.path.basename(ruta)}")
    for enc in ("utf-8-sig", "latin-1"):
        for sep in (",", ";"):
            try:
                df = pd.read_csv(ruta, encoding=enc, sep=sep)
                if df.shape[1] >= 5:
                    log(f"Lectura correcta con codificacion {enc} y separador '{sep}'")
                    return df
            except Exception:
                continue
    sys.exit("No fue posible interpretar el archivo con las combinaciones probadas")


def normalizar_columnas(df):
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    equivalencias = {
        # Formato USGS
        "TIME": "FechaUTC", "LATITUDE": "Latitud", "LONGITUDE": "Longitud",
        "DEPTH": "ProfundidadKm", "MAG": "Magnitud", "PLACE": "Lugar", "TYPE": "TipoEvento",
        # Formato IGP (datos abiertos)
        "FECHA_UTC": "FechaUTC", "HORA_UTC": "HoraUTC", "LATITUD": "Latitud",
        "LONGITUD": "Longitud", "PROFUNDIDAD": "ProfundidadKm", "MAGNITUD": "Magnitud",
    }
    presentes = {k: v for k, v in equivalencias.items() if k in df.columns}
    df = df.rename(columns=presentes)
    # El catalogo del USGS incluye eventos no tectonicos (explosiones de cantera,
    # etc.), por lo cual se conservan unicamente los sismos propiamente dichos
    if "TipoEvento" in df.columns:
        no_sismos = int((df["TipoEvento"] != "earthquake").sum())
        df = df[df["TipoEvento"] == "earthquake"]
        log(f"Eventos no tectonicos excluidos del catalogo: {no_sismos:,}")
    return df


def main():
    log("=" * 62)
    log("REPORTE DE CALIDAD - Catalogo Sismico del Peru (fuente USGS)")
    log("=" * 62)

    df = cargar_archivo()
    df = normalizar_columnas(df)
    total_inicial = len(df)
    log(f"Registros recibidos: {total_inicial:,}")
    log("")

    # 1) Tipos: fecha en formato AAAAMMDD o AAAA-MM-DD segun la version del archivo
    df["FechaUTC"] = pd.to_datetime(df["FechaUTC"].astype(str).str.replace("/", "-"),
                                    format="mixed", errors="coerce")
    for col in ("Latitud", "Longitud", "ProfundidadKm", "Magnitud"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    fechas_malas = int(df["FechaUTC"].isna().sum())
    df = df.dropna(subset=["FechaUTC", "Latitud", "Longitud", "Magnitud"])
    log(f"[1] Registros con fecha o coordenadas invalidas eliminados: {fechas_malas + (total_inicial - len(df) - fechas_malas):,}")

    # 2) Duplicados exactos
    dups = int(df.duplicated().sum())
    df = df.drop_duplicates()
    log(f"[2] Duplicados exactos eliminados: {dups:,}")

    # 3) Reglas de dominio: el catalogo cubre el territorio peruano y zonas vecinas
    fuera_zona = int((~df["Latitud"].between(-21, 1) | ~df["Longitud"].between(-84, -66)).sum())
    df = df[df["Latitud"].between(-21, 1) & df["Longitud"].between(-84, -66)]
    mag_invalida = int((~df["Magnitud"].between(2, 10)).sum())
    df = df[df["Magnitud"].between(2, 10)]
    log(f"[3] Registros fuera de la zona de estudio: {fuera_zona:,} | Magnitudes fuera de rango: {mag_invalida:,}")

    # 4) Campos derivados para el analisis
    df["Anio"] = df["FechaUTC"].dt.year
    df["Mes"] = df["FechaUTC"].dt.month
    df["Decada"] = (df["Anio"] // 10 * 10).astype(str) + "s"
    df["RangoMagnitud"] = pd.cut(
        df["Magnitud"], bins=[0, 3.9, 4.9, 5.9, 6.9, 10],
        labels=["Menor a 4.0", "4.0 a 4.9", "5.0 a 5.9", "6.0 a 6.9", "7.0 o mas"])
    df["TipoProfundidad"] = pd.cut(
        df["ProfundidadKm"], bins=[-1, 60, 300, 1000],
        labels=["Superficial (0-60 km)", "Intermedio (60-300 km)", "Profundo (mas de 300 km)"])
    log("[4] Campos derivados: Anio, Mes, Decada, RangoMagnitud, TipoProfundidad")

    # Validacion final
    assert df.duplicated().sum() == 0
    assert df["Magnitud"].between(2, 10).all()

    os.makedirs(os.path.dirname(REPORTE), exist_ok=True)
    df.to_csv(SALIDA, index=False, encoding="utf-8-sig")

    log("")
    log(f"Registros finales: {len(df):,}  (descartados: {total_inicial - len(df):,})")
    log(f"Periodo cubierto: {df['FechaUTC'].min().date()} a {df['FechaUTC'].max().date()}")
    log(f"Magnitud maxima: {df['Magnitud'].max():.1f} | Promedio: {df['Magnitud'].mean():.2f}")
    log(f"Sismos de magnitud 7.0 o mas: {int((df['Magnitud'] >= 7).sum()):,}")
    log("")
    log("RESULTADO: dataset listo para Power BI -> data/sismos_peru.csv")

    with open(REPORTE, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"\nReporte guardado en {os.path.abspath(REPORTE)}")


if __name__ == "__main__":
    main()
