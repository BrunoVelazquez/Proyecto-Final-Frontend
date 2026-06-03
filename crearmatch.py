import csv
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS

# ──────────────────────────────────────────────────────────────────────────────
# 1. FUNCIONES ORIGINALES DE TU SCRIPT (load_gps_csv, get_exif, find_nearest)
# ──────────────────────────────────────────────────────────────────────────────

def load_gps_csv(path: str) -> list:
    points = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("type", "").strip().upper() != "T":
                continue
            try:
                dt_str = row["date time"].strip()
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                points.append({"datetime": dt, "lat": lat, "lon": lon})
            except (ValueError, KeyError):
                continue
    return points

def get_exif_datetime(image_path: Path):
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ("DateTimeOriginal", "DateTime", "DateTimeDigitized"):
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None

def find_nearest_gps(image_dt: datetime, gps_points: list) -> dict:
    best = min(gps_points, key=lambda p: abs((p["datetime"] - image_dt).total_seconds()))
    return best

# ──────────────────────────────────────────────────────────────────────────────
# 2. FUNCIÓN PRINCIPAL MODIFICADA (Solo exporta TXT)
# ──────────────────────────────────────────────────────────────────────────────

def main():
    # Rutas (Ajustalas si es necesario)
    GPS_FILE = "data/datosGPS_censos_aereos_2023/archivos_originales/20231004-130551_ censo PV_ 2023.txt"
    IMAGES_DIR = "data/images"
    OUTPUT_TXT = "coordenadas_fotos.txt"
    MAX_DELTA_S = 300  # 5 minutos de tolerancia máxima (igual que en tu script original)

    print("\n[1/2] Cargando puntos GPS...")
    try:
        gps_points = load_gps_csv(GPS_FILE)
        print(f"      Se cargaron {len(gps_points)} puntos.")
    except Exception as e:
        sys.exit(f"❌ Error al cargar el GPS: {e}")

    images_path = Path(IMAGES_DIR)
    image_paths = sorted([p for p in images_path.iterdir() if p.suffix.lower() in {".jpg", ".jpeg"}])

    print(f"\n[2/2] Procesando {len(image_paths)} imágenes y exportando a TXT...\n")

    # Abrimos el archivo TXT para escribir los resultados
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f_out:
        # Cabecera del archivo
        f_out.write("Nombre_Imagen,Latitud,Longitud,Hora_EXIF,Delta_Segundos\n")

        for img_path in image_paths:
            exif_dt = get_exif_datetime(img_path)
            
            if exif_dt is None:
                print(f"⚠️ {img_path.name} -> Sin datos EXIF de hora.")
                f_out.write(f"{img_path.name},N/A,N/A,Sin_EXIF,N/A\n")
                continue

            best_match = find_nearest_gps(exif_dt, gps_points)
            delta = abs((best_match["datetime"] - exif_dt).total_seconds())

            if delta > MAX_DELTA_S:
                print(f"⚠️ {img_path.name} -> Fuera de rango GPS (diferencia de {delta:.0f}s).")
                f_out.write(f"{img_path.name},N/A,N/A,{exif_dt},>{MAX_DELTA_S}\n")
            else:
                lat = best_match["lat"]
                lon = best_match["lon"]
                print(f"✅ {img_path.name} -> Lat: {lat:.6f}, Lon: {lon:.6f} (Δ {delta:.0f}s)")
                # Guardamos en el TXT
                f_out.write(f"{img_path.name},{lat:.8f},{lon:.8f},{exif_dt},{delta:.0f}\n")

    print("-" * 60)
    print(f"¡Proceso finalizado! Archivo guardado en: {Path(OUTPUT_TXT).absolute()}")

if __name__ == "__main__":
    main()