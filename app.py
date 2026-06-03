import sys
import os
import uuid
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from adapters.base import ModelService

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "yolo_uploads"
RESULTS_FOLDER = Path(tempfile.gettempdir()) / "yolo_results"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

DATA_IMAGES_FOLDER = Path(__file__).parent / "data" / "images"

DEFAULT_MODEL_PATH = str(Path(__file__).parent / "modelos" / "best.pt")

model_service = ModelService(
    default_model_path=DEFAULT_MODEL_PATH,
    model_type="yolov8",
    default_device="cpu",
    default_confidence=0.3,
)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/procesar", methods=["POST"])
def procesar():
    # ... tu código intacto de procesamiento ...
    pass

@app.route("/results/<path:filename>")
def serve_result(filename):
    return send_from_directory(str(RESULTS_FOLDER), filename)

# 2. Creamos la nueva ruta para servir las fotos originales de la campaña
@app.route("/data/images/<path:filename>")
def serve_data_image(filename):
    return send_from_directory(str(DATA_IMAGES_FOLDER), filename)

import json
from pathlib import Path

DATA_LABELS_FOLDER = Path(__file__).parent / "data" / "labels"
NOTES_FILE         = Path(__file__).parent / "data" / "notes.json"

@app.route("/data/labels/<path:filename>")
def serve_label(filename):
    """Devuelve el .txt YOLO de una imagen como JSON [{id, cx, cy, w, h}]"""
    stem = Path(filename).stem
    label_path = DATA_LABELS_FOLDER / f"{stem}.txt"
    
    # Cargar categorías desde notes.json
    with open(NOTES_FILE, encoding="utf-8") as f:
        notes = json.load(f)
    categories = {c["id"]: c["name"] for c in notes["categories"]}
    
    boxes = []
    if label_path.exists():
        for line in label_path.read_text().splitlines():
            parts = line.strip().split()
            if len(parts) == 5:
                cid, cx, cy, w, h = int(parts[0]), *map(float, parts[1:])
                boxes.append({
                    "id": cid,
                    "name": categories.get(cid, f"clase_{cid}"),
                    "cx": cx, "cy": cy, "w": w, "h": h
                })
    return jsonify({"boxes": boxes, "categories": categories})


@app.route("/data/labels/<path:filename>", methods=["POST"])
def save_label(filename):
    """Recibe [{id, cx, cy, w, h}] y sobreescribe el .txt YOLO"""
    stem = Path(filename).stem
    label_path = DATA_LABELS_FOLDER / f"{stem}.txt"
    DATA_LABELS_FOLDER.mkdir(parents=True, exist_ok=True)
    
    boxes = request.get_json().get("boxes", [])
    lines = [f"{b['id']} {b['cx']} {b['cy']} {b['w']} {b['h']}" for b in boxes]
    label_path.write_text("\n".join(lines))
    return jsonify({"ok": True, "saved": len(lines)})


@app.route("/data/categories")
def serve_categories():
    with open(NOTES_FILE, encoding="utf-8") as f:
        return jsonify(json.load(f))

@app.route("/data/labels/count/<path:filename>")
def label_count(filename):
    """Devuelve la cantidad de bboxes del .txt YOLO de una imagen."""
    stem = Path(filename).stem
    label_path = DATA_LABELS_FOLDER / f"{stem}.txt"
    count = 0
    if label_path.exists():
        lines = [l for l in label_path.read_text().splitlines() if l.strip()]
        count = len(lines)
    return jsonify({"count": count})

if __name__ == "__main__":
    app.run()