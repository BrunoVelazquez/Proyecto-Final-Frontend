"""
aerial_gps_matcher.py
=====================
Match an oblique aerial photo to a satellite tile (Bing) using
a GPS seed point, then output GPS coordinates of matched features.

Pipeline
--------
1. Fetch a Bing satellite tile centred on the GPS seed point
2. Orthorectify (de-oblique) the aerial photo via homography estimation
3. Match features between the orthorectified photo and the satellite tile (SIFT)
4. Convert pixel matches → GPS coordinates using the tile's geo-transform
5. Export matched keypoints as GeoJSON + a visual debug overlay image

Requirements
------------
    pip install opencv-python-headless numpy requests Pillow

Usage
-----
    python aerial_gps_matcher.py \
        --photo  my_aerial_photo.jpg \
        --lat    -38.7183 \
        --lon    -62.2663 \
        --zoom   18 \
        --output results/
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image

# ──────────────────────────────────────────────────────────────────────────────
# GEO UTILITIES
# ──────────────────────────────────────────────────────────────────────────────

def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert WGS-84 lat/lon to OSM/Bing tile XY at a given zoom level."""
    lat_r = math.radians(lat)
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_lat_lon(tx: int, ty: int, zoom: int) -> tuple[float, float]:
    """Return the NW corner (lat, lon) of a tile."""
    n = 2 ** zoom
    lon = tx / n * 360.0 - 180.0
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * ty / n)))
    lat = math.degrees(lat_r)
    return lat, lon


def pixel_to_lat_lon(px: float, py: float,
                     tile_x: int, tile_y: int,
                     zoom: int, tile_size: int = 256) -> tuple[float, float]:
    """
    Convert a pixel position within a tile image to WGS-84 lat/lon.
    px, py are relative to the TOP-LEFT of the fetched tile image.
    """
    n = 2 ** zoom
    # fractional tile coordinates
    ftx = tile_x + px / tile_size
    fty = tile_y + py / tile_size
    lon = ftx / n * 360.0 - 180.0
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * fty / n)))
    lat = math.degrees(lat_r)
    return lat, lon


# ──────────────────────────────────────────────────────────────────────────────
# TILE FETCHING  (Bing Aerial — no API key needed for direct tile URL)
# ──────────────────────────────────────────────────────────────────────────────

BING_TILE_URL = (
    "https://ecn.t{s}.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1"
)


def _tile_to_quadkey(tx: int, ty: int, zoom: int) -> str:
    """Convert tile XY + zoom to a Bing quadkey string."""
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


def fetch_bing_tile(tx: int, ty: int, zoom: int) -> np.ndarray:
    """Download a single Bing satellite tile and return it as a BGR numpy array."""
    qk = _tile_to_quadkey(tx, ty, zoom)
    server = (tx + ty) % 4  # cycle through Bing's tile servers 0-3
    url = BING_TILE_URL.format(s=server, q=qk)
    headers = {"User-Agent": "aerial-gps-matcher/1.0 (research tool)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    arr = np.frombuffer(resp.content, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Failed to decode tile image from {url}")
    return img


def fetch_satellite_patch(lat: float, lon: float,
                          zoom: int = 18,
                          radius_tiles: int = 1) -> tuple[np.ndarray, int, int]:
    """
    Fetch a (2*radius+1) × (2*radius+1) grid of Bing tiles centred on lat/lon.
    Returns (mosaic_image, top_left_tile_x, top_left_tile_y).
    """
    cx, cy = lat_lon_to_tile(lat, lon, zoom)
    tiles = []
    for dy in range(-radius_tiles, radius_tiles + 1):
        row = []
        for dx in range(-radius_tiles, radius_tiles + 1):
            print(f"  Fetching tile ({cx+dx}, {cy+dy}) z{zoom} …")
            tile = fetch_bing_tile(cx + dx, cy + dy, zoom)
            row.append(tile)
        tiles.append(row)

    mosaic = cv2.vconcat([cv2.hconcat(row) for row in tiles])
    tl_x = cx - radius_tiles
    tl_y = cy - radius_tiles
    return mosaic, tl_x, tl_y


# ──────────────────────────────────────────────────────────────────────────────
# OBLIQUE CORRECTION  (simple 4-point perspective warp)
# ──────────────────────────────────────────────────────────────────────────────

def auto_orthorectify(img: np.ndarray) -> np.ndarray:
    """
    Attempt automatic perspective correction for mildly oblique photos.
    Uses edge-based quadrilateral detection to find the dominant ground plane
    and warps it to a top-down view.

    For strongly oblique images, supply manual GCPs instead (see --gcps flag).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Detect edges and find contours
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_quad = None
    best_area = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < (h * w * 0.05):   # ignore tiny contours
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and area > best_area:
            best_area = area
            best_quad = approx.reshape(4, 2).astype(np.float32)

    if best_quad is None:
        print("  [ortho] No dominant quadrilateral found — returning original image.")
        return img

    # Order points: top-left, top-right, bottom-right, bottom-left
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
    out_w = max(
        int(np.linalg.norm(src[1] - src[0])),
        int(np.linalg.norm(src[2] - src[3]))
    )
    out_h = max(
        int(np.linalg.norm(src[3] - src[0])),
        int(np.linalg.norm(src[2] - src[1]))
    )
    dst = np.array([[0, 0], [out_w, 0], [out_w, out_h], [0, out_h]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (out_w, out_h))
    print(f"  [ortho] Perspective corrected: {w}×{h} → {out_w}×{out_h}")
    return warped


# ──────────────────────────────────────────────────────────────────────────────
# FEATURE MATCHING
# ──────────────────────────────────────────────────────────────────────────────

def match_features(
    query: np.ndarray,
    reference: np.ndarray,
    max_features: int = 5000,
    ratio_thresh: float = 0.75,
) -> tuple[list, list, np.ndarray]:
    """
    SIFT feature matching between query (aerial) and reference (satellite).

    Returns
    -------
    query_pts    : list of (x, y) pixel coords in query image
    ref_pts      : list of (x, y) pixel coords in reference image
    match_vis    : BGR image with match lines drawn
    """
    sift = cv2.SIFT_create(nfeatures=max_features)

    kp1, des1 = sift.detectAndCompute(query, None)
    kp2, des2 = sift.detectAndCompute(reference, None)

    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        raise RuntimeError("Not enough keypoints detected. Try a higher zoom level "
                           "or a less oblique photo.")

    print(f"  Keypoints — aerial: {len(kp1)}, satellite: {len(kp2)}")

    # FLANN-based matcher
    index_params = dict(algorithm=1, trees=5)   # FLANN_INDEX_KDTREE
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1, des2, k=2)

    # Lowe's ratio test
    good = [m for m, n in matches if m.distance < ratio_thresh * n.distance]
    print(f"  Good matches after ratio test: {len(good)}")

    if len(good) < 4:
        raise RuntimeError(
            f"Only {len(good)} good matches found (need ≥ 4). "
            "Consider increasing --zoom or improving oblique correction."
        )

    # RANSAC homography to filter outliers
    q_pts = np.float32([kp1[m.queryIdx].pt for m in good])
    r_pts = np.float32([kp2[m.trainIdx].pt for m in good])
    _, mask = cv2.findHomography(q_pts, r_pts, cv2.RANSAC, 5.0)
    inlier_mask = mask.ravel().astype(bool)

    q_inliers = q_pts[inlier_mask].tolist()
    r_inliers = r_pts[inlier_mask].tolist()
    good_inliers = [m for m, keep in zip(good, inlier_mask) if keep]
    print(f"  Inlier matches after RANSAC: {len(q_inliers)}")

    # Draw matches
    match_vis = cv2.drawMatches(
        query, kp1, reference, kp2,
        good_inliers, None,
        matchColor=(0, 255, 0),
        singlePointColor=(0, 0, 255),
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
    )

    return q_inliers, r_inliers, match_vis


# ──────────────────────────────────────────────────────────────────────────────
# GPS EXPORT
# ──────────────────────────────────────────────────────────────────────────────

def matches_to_geojson(
    query_pts: list,
    ref_pts: list,
    tl_tile_x: int,
    tl_tile_y: int,
    zoom: int,
    tile_size: int = 256,
) -> dict:
    """
    Convert matched reference pixel coordinates to GPS (lat/lon)
    and produce a GeoJSON FeatureCollection.
    """
    features = []
    for i, (qp, rp) in enumerate(zip(query_pts, ref_pts)):
        lat, lon = pixel_to_lat_lon(rp[0], rp[1], tl_tile_x, tl_tile_y, zoom, tile_size)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "match_id": i,
                "aerial_px": qp,
                "satellite_px": rp,
                "latitude": round(lat, 8),
                "longitude": round(lon, 8),
            },
        })
    return {"type": "FeatureCollection", "features": features}


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Match an oblique aerial photo to Bing satellite and extract GPS coords."
    )
    parser.add_argument("--photo",   required=True, help="Path to aerial photo (JPG/PNG)")
    parser.add_argument("--lat",     required=True, type=float, help="Seed latitude (WGS-84)")
    parser.add_argument("--lon",     required=True, type=float, help="Seed longitude (WGS-84)")
    parser.add_argument("--zoom",    default=18,    type=int,   help="Tile zoom level (16-19 recommended)")
    parser.add_argument("--radius",  default=1,     type=int,   help="Tile fetch radius around seed (1 = 3×3 grid)")
    parser.add_argument("--output",  default="output", help="Output directory")
    parser.add_argument("--no-ortho", action="store_true",
                        help="Skip automatic perspective correction (use for nadir photos)")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Load aerial photo ──────────────────────────────────────────────────
    print(f"\n[1/5] Loading aerial photo: {args.photo}")
    aerial = cv2.imread(args.photo)
    if aerial is None:
        sys.exit(f"ERROR: Cannot read photo at '{args.photo}'")
    print(f"      Size: {aerial.shape[1]}×{aerial.shape[0]} px")

    # ── 2. Orthorectify ───────────────────────────────────────────────────────
    if not args.no_ortho:
        print("\n[2/5] Orthorectifying oblique photo …")
        ortho = auto_orthorectify(aerial)
    else:
        print("\n[2/5] Skipping orthorectification (--no-ortho flag set)")
        ortho = aerial

    cv2.imwrite(str(out_dir / "orthorectified.jpg"), ortho)

    # ── 3. Fetch satellite tile mosaic ────────────────────────────────────────
    print(f"\n[3/5] Fetching Bing satellite tiles (z{args.zoom}, r={args.radius}) …")
    satellite, tl_x, tl_y = fetch_satellite_patch(
        args.lat, args.lon, args.zoom, args.radius
    )
    cv2.imwrite(str(out_dir / "satellite_mosaic.jpg"), satellite)
    print(f"      Mosaic size: {satellite.shape[1]}×{satellite.shape[0]} px")
    print(f"      Top-left tile: ({tl_x}, {tl_y})")

    # ── 4. Match features ─────────────────────────────────────────────────────
    print("\n[4/5] Matching features (SIFT + RANSAC) …")
    q_pts, r_pts, match_vis = match_features(ortho, satellite)
    cv2.imwrite(str(out_dir / "matches_visualization.jpg"), match_vis)
    print(f"      Match visualization saved.")

    # ── 5. Convert to GPS and export ──────────────────────────────────────────
    print("\n[5/5] Converting matches to GPS coordinates …")
    geojson = matches_to_geojson(q_pts, r_pts, tl_x, tl_y, args.zoom)

    geojson_path = out_dir / "matched_points.geojson"
    with open(geojson_path, "w") as f:
        json.dump(geojson, f, indent=2)

    # Also print a simple CSV summary
    csv_path = out_dir / "matched_points.csv"
    with open(csv_path, "w") as f:
        f.write("match_id,latitude,longitude,aerial_px_x,aerial_px_y,satellite_px_x,satellite_px_y\n")
        for feat in geojson["features"]:
            p = feat["properties"]
            f.write(
                f"{p['match_id']},"
                f"{p['latitude']},"
                f"{p['longitude']},"
                f"{p['aerial_px'][0]:.1f},{p['aerial_px'][1]:.1f},"
                f"{p['satellite_px'][0]:.1f},{p['satellite_px'][1]:.1f}\n"
            )

    print(f"\n✅ Done! {len(geojson['features'])} matched GPS points saved to:")
    print(f"   {geojson_path}")
    print(f"   {csv_path}")
    print(f"   {out_dir / 'matches_visualization.jpg'}")
    print(f"   {out_dir / 'orthorectified.jpg'}")

    # Print a preview of the top 10 matches
    print("\n── Top 10 matched GPS points ──────────────────────────────")
    print(f"{'ID':>4}  {'Latitude':>12}  {'Longitude':>13}")
    print("─" * 35)
    for feat in geojson["features"][:10]:
        p = feat["properties"]
        print(f"{p['match_id']:>4}  {p['latitude']:>12.6f}  {p['longitude']:>13.6f}")


if __name__ == "__main__":
    main()