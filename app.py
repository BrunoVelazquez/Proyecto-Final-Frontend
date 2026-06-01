import sys
import os
import uuid
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# ── Adaptador base (Módulo 1 — Actividad 1.1) ────────────────────────────────
from adapters.base import ModelService

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "yolo_uploads"
RESULTS_FOLDER = Path(tempfile.gettempdir()) / "yolo_results"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

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

@app.route("/results/<path:filename>")
def serve_result(filename):
    return send_from_directory(str(RESULTS_FOLDER), filename)

@app.route("/procesar", methods=["POST"])
def procesar():
    # ... tu código intacto de procesamiento ...
    pass

if __name__ == "__main__":
    app.run()