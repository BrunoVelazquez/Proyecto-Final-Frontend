"""
aerial_gps_matcher.py
=====================
Asocia fotos aéreas oblicuas a imágenes satelitales (Bing) usando:
  - Un CSV de trazas GPS (formato GPS Logger)
  - Un .txt con rutas de imágenes (una por línea)
  - EXIF de cada imagen para cruzar timestamp con el GPS más cercano

Pipeline por imagen
-------------------
1. Leer CSV GPS → lista de puntos (datetime, lat, lon)
2. Leer .txt → lista de rutas de imágenes
3. Por cada imagen:
   a. Extraer datetime del EXIF
   b. Encontrar el punto GPS más cercano en tiempo
   c. Descargar mosaico de tiles Bing centrado en ese punto
   d. Ortorectificar la foto oblicua (corrección de perspectiva)
   e. Matching de features SIFT + RANSAC
   f. Convertir matches a coordenadas GPS
   g. Guardar GeoJSON, CSV y visualización

Requisitos
----------
    pip install opencv-python-headless numpy requests Pillow

Uso
---
    python aerial_gps_matcher.py --gps puntos.csv --images rutas.txt
    python aerial_gps_matcher.py --gps puntos.csv --images rutas.txt --zoom 19 --output resultados/
"""

import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image
from PIL.ExifTags import TAGS


# ──────────────────────────────────────────────────────────────────────────────
# LECTURA DE ARCHIVOS DE ENTRADA
# ──────────────────────────────────────────────────────────────────────────────

def load_gps_csv(path: str) -> list:
    """
    Lee el CSV de GPS Logger con columnas:
        type, date time, latitude, longitude, accuracy(m), altitude(m), ...
    Devuelve lista de dicts con keys: datetime, lat, lon, alt
    Solo procesa filas de tipo 'T' (trackpoints).
    """
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
                alt = float(row["altitude(m)"]) if row.get("altitude(m)") else 0.0
                points.append({"datetime": dt, "lat": lat, "lon": lon, "alt": alt})
            except (ValueError, KeyError):
                continue

    if not points:
        sys.exit(f"ERROR: No se encontraron trackpoints válidos en '{path}'")
    print(f"  GPS: {len(points)} puntos cargados "
          f"({points[0]['datetime']} → {points[-1]['datetime']})")
    return points


# ──────────────────────────────────────────────────────────────────────────────
# EXIF Y CRUCE TEMPORAL
# ──────────────────────────────────────────────────────────────────────────────

def get_exif_datetime(image_path: Path):
    """Extrae la fecha/hora del EXIF. Devuelve None si no tiene."""
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
    """Encuentra el punto GPS más cercano en tiempo al datetime de la imagen."""
    best = min(gps_points, key=lambda p: abs((p["datetime"] - image_dt).total_seconds()))
    delta = abs((best["datetime"] - image_dt).total_seconds())
    print(f"  EXIF: {image_dt}  →  GPS más cercano: {best['datetime']} "
          f"(Δ {delta:.0f}s) → ({best['lat']:.6f}, {best['lon']:.6f})")
    if delta > 300:
        print(f"  ADVERTENCIA: diferencia de {delta:.0f}s (>5 min). "
              "Verificar sincronización de relojes.")
    return best


# ──────────────────────────────────────────────────────────────────────────────
# GEO UTILITIES
# ──────────────────────────────────────────────────────────────────────────────

def lat_lon_to_tile(lat, lon, zoom):
    lat_r = math.radians(lat)
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def pixel_to_lat_lon(px, py, tile_x, tile_y, zoom, tile_size=256):
    n = 2 ** zoom
    ftx = tile_x + px / tile_size
    fty = tile_y + py / tile_size
    lon = ftx / n * 360.0 - 180.0
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * fty / n)))
    lat = math.degrees(lat_r)
    return lat, lon


# ──────────────────────────────────────────────────────────────────────────────
# DESCARGA DE TILES BING
# ──────────────────────────────────────────────────────────────────────────────

BING_TILE_URL = "https://ecn.t{s}.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1"


def _tile_to_quadkey(tx, ty, zoom):
    qk = []
    for i in range(zoom, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if tx & mask:
            digit += 1
        if ty & mask:
            digit += 2
        qk.append(str(digit))
    return "".join(qk)


def fetch_bing_tile(tx, ty, zoom):
    qk = _tile_to_quadkey(tx, ty, zoom)
    server = (tx + ty) % 4
    url = BING_TILE_URL.format(s=server, q=qk)
    headers = {"User-Agent": "aerial-gps-matcher/1.0 (research tool)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    arr = np.frombuffer(resp.content, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"No se pudo decodificar el tile {url}")
    return img


def fetch_satellite_patch(lat, lon, zoom=18, radius_tiles=1):
    cx, cy = lat_lon_to_tile(lat, lon, zoom)
    tiles = []
    for dy in range(-radius_tiles, radius_tiles + 1):
        row = []
        for dx in range(-radius_tiles, radius_tiles + 1):
            print(f"    Descargando tile ({cx+dx}, {cy+dy}) z{zoom} …")
            tile = fetch_bing_tile(cx + dx, cy + dy, zoom)
            row.append(tile)
        tiles.append(row)
    mosaic = cv2.vconcat([cv2.hconcat(row) for row in tiles])
    return mosaic, cx - radius_tiles, cy - radius_tiles


# ──────────────────────────────────────────────────────────────────────────────
# ORTORECTIFICACIÓN
# ──────────────────────────────────────────────────────────────────────────────

def auto_orthorectify(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_quad, best_area = None, 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < (h * w * 0.05):
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and area > best_area:
            best_area = area
            best_quad = approx.reshape(4, 2).astype(np.float32)

    if best_quad is None:
        print("    [ortho] No se detectó cuadrilátero, se usa imagen original.")
        return img

    def order_pts(pts):
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    src = order_pts(best_quad)
    out_w = max(int(np.linalg.norm(src[1]-src[0])), int(np.linalg.norm(src[2]-src[3])))
    out_h = max(int(np.linalg.norm(src[3]-src[0])), int(np.linalg.norm(src[2]-src[1])))
    dst = np.array([[0,0],[out_w,0],[out_w,out_h],[0,out_h]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (out_w, out_h))
    print(f"    [ortho] {w}×{h} → {out_w}×{out_h}")
    return warped


# ──────────────────────────────────────────────────────────────────────────────
# MATCHING DE FEATURES
# ──────────────────────────────────────────────────────────────────────────────

def match_features(query, reference, max_features=5000, ratio_thresh=0.75):
    sift = cv2.SIFT_create(nfeatures=max_features)
    kp1, des1 = sift.detectAndCompute(query, None)
    kp2, des2 = sift.detectAndCompute(reference, None)

    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        raise RuntimeError("Pocos keypoints detectados. Probá mayor zoom o mejor foto.")

    print(f"    Keypoints — aérea: {len(kp1)}, satélite: {len(kp2)}")

    index_params = dict(algorithm=1, trees=5)
    flann = cv2.FlannBasedMatcher(index_params, dict(checks=50))
    matches = flann.knnMatch(des1, des2, k=2)
    good = [m for m, n in matches if m.distance < ratio_thresh * n.distance]
    print(f"    Matches buenos (ratio test): {len(good)}")

    if len(good) < 4:
        raise RuntimeError(f"Solo {len(good)} matches (necesita ≥4). Probá --zoom más alto.")

    q_pts = np.float32([kp1[m.queryIdx].pt for m in good])
    r_pts = np.float32([kp2[m.trainIdx].pt for m in good])
    _, mask = cv2.findHomography(q_pts, r_pts, cv2.RANSAC, 5.0)
    inlier_mask = mask.ravel().astype(bool)

    q_in = q_pts[inlier_mask].tolist()
    r_in = r_pts[inlier_mask].tolist()
    good_in = [m for m, k in zip(good, inlier_mask) if k]
    print(f"    Inliers tras RANSAC: {len(q_in)}")

    vis = cv2.drawMatches(query, kp1, reference, kp2, good_in, None,
                          matchColor=(0,255,0), singlePointColor=(0,0,255),
                          flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    return q_in, r_in, vis


# ──────────────────────────────────────────────────────────────────────────────
# EXPORTAR GPS
# ──────────────────────────────────────────────────────────────────────────────

def matches_to_geojson(query_pts, ref_pts, tl_x, tl_y, zoom, image_name, gps_seed):
    features = []
    for i, (qp, rp) in enumerate(zip(query_pts, ref_pts)):
        lat, lon = pixel_to_lat_lon(rp[0], rp[1], tl_x, tl_y, zoom)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "match_id": i,
                "image": image_name,
                "gps_seed_lat": gps_seed["lat"],
                "gps_seed_lon": gps_seed["lon"],
                "gps_seed_time": gps_seed["datetime"].isoformat(),
                "latitude": round(lat, 8),
                "longitude": round(lon, 8),
                "aerial_px": qp,
                "satellite_px": rp,
            },
        })
    return {"type": "FeatureCollection", "features": features}


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    # ══════════════════════════════════════════════════════════════════════════
    # CONFIGURACIÓN — editá estas rutas según tu estructura de carpetas
    # ══════════════════════════════════════════════════════════════════════════
    GPS_FILE    = "../data/datosGPS_censos_aereos_2023/20231004-130551 - Censo PV 2023.txt"
    IMAGES_DIR  = "../data/images"
    OUTPUT_DIR  = "output"
    ZOOM        = 18      # nivel de zoom Bing (16-19, más alto = más detalle)
    RADIUS      = 1       # radio de tiles: 1 → mosaico 3×3
    ORTHO       = True    # True = ortorectificar fotos oblicuas
    MAX_DELTA_S = 300     # diferencia máxima en segundos entre EXIF y GPS
    IMG_EXTS    = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    # ══════════════════════════════════════════════════════════════════════════

    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Cargar entradas ───────────────────────────────────────────────────────
    print("\n[1/2] Cargando archivos de entrada …")
    gps_points = load_gps_csv(GPS_FILE)

    images_path = Path(IMAGES_DIR)
    if not images_path.exists():
        sys.exit(f"ERROR: No se encontró la carpeta de imágenes '{IMAGES_DIR}'")
    image_paths = sorted([p for p in images_path.iterdir()
                          if p.suffix.lower() in IMG_EXTS])
    if not image_paths:
        sys.exit(f"ERROR: No se encontraron imágenes en '{IMAGES_DIR}'")
    print(f"  Imágenes: {len(image_paths)} encontradas en '{IMAGES_DIR}'")

    all_features = []

    # ── Procesar cada imagen ──────────────────────────────────────────────────
    for idx, img_path in enumerate(image_paths):
        print(f"\n{'═'*60}")
        print(f"  Imagen {idx+1}/{len(image_paths)}: {img_path.name}")
        print(f"{'═'*60}")

        img_out = out_dir / img_path.stem
        img_out.mkdir(exist_ok=True)

        # EXIF datetime
        exif_dt = get_exif_datetime(img_path)
        if exif_dt is None:
            print(f"  ADVERTENCIA: '{img_path.name}' no tiene EXIF datetime. Se omite.")
            continue

        # GPS más cercano
        gps_pt = find_nearest_gps(exif_dt, gps_points)
        delta = abs((gps_pt["datetime"] - exif_dt).total_seconds())
        if delta > MAX_DELTA_S:
            print(f"  OMITIDA: Δt={delta:.0f}s > MAX_DELTA_S={MAX_DELTA_S}s")
            continue

        # Cargar imagen
        aerial = cv2.imread(str(img_path))
        if aerial is None:
            print(f"  ERROR: No se pudo leer la imagen. Se omite.")
            continue

        # Ortorectificar
        if ORTHO:
            print("  Ortorectificando …")
            ortho = auto_orthorectify(aerial)
        else:
            ortho = aerial
        cv2.imwrite(str(img_out / "orthorectified.jpg"), ortho)

        # Descargar tiles
        print(f"  Descargando tiles Bing z{ZOOM} …")
        try:
            satellite, tl_x, tl_y = fetch_satellite_patch(
                gps_pt["lat"], gps_pt["lon"], ZOOM, RADIUS
            )
        except Exception as e:
            print(f"  ERROR descargando tiles: {e}. Se omite imagen.")
            continue
        cv2.imwrite(str(img_out / "satellite_mosaic.jpg"), satellite)

        # Matching
        print("  Matching de features SIFT + RANSAC …")
        try:
            q_pts, r_pts, vis = match_features(ortho, satellite)
        except RuntimeError as e:
            print(f"  ERROR en matching: {e}. Se omite imagen.")
            continue
        cv2.imwrite(str(img_out / "matches_visualization.jpg"), vis)

        # Exportar GPS
        geojson = matches_to_geojson(q_pts, r_pts, tl_x, tl_y, ZOOM,
                                     img_path.name, gps_pt)
        all_features.extend(geojson["features"])

        with open(img_out / "matched_points.geojson", "w") as f:
            json.dump(geojson, f, indent=2)

        with open(img_out / "matched_points.csv", "w") as f:
            f.write("match_id,latitude,longitude,aerial_px_x,aerial_px_y,"
                    "satellite_px_x,satellite_px_y,gps_seed_time\n")
            for feat in geojson["features"]:
                p = feat["properties"]
                f.write(f"{p['match_id']},{p['latitude']},{p['longitude']},"
                        f"{p['aerial_px'][0]:.1f},{p['aerial_px'][1]:.1f},"
                        f"{p['satellite_px'][0]:.1f},{p['satellite_px'][1]:.1f},"
                        f"{p['gps_seed_time']}\n")

        print(f"  ✅ {len(q_pts)} puntos GPS → {img_out}/")

    # ── GeoJSON global ────────────────────────────────────────────────────────
    if all_features:
        global_geojson = {"type": "FeatureCollection", "features": all_features}
        global_path = out_dir / "all_matches.geojson"
        with open(global_path, "w") as f:
            json.dump(global_geojson, f, indent=2)
        print(f"\n{'═'*60}")
        print(f"✅ Proceso completo.")
        print(f"   Total matches GPS : {len(all_features)}")
        print(f"   GeoJSON global    : {global_path}")
        print(f"   Resultados        : {out_dir}/")
        print(f"\n   → Arrastrá 'all_matches.geojson' a https://geojson.io para ver en el mapa")
    else:
        print("\n⚠️  No se generaron matches. Revisá los timestamps y las imágenes.")


if __name__ == "__main__":
    main()