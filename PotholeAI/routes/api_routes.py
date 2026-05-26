"""
routes/api_routes.py
====================
REST endpoints consumed by the frontend JS and ESP-CAM.

PUBLIC  (no login needed):
    POST /detect            ← ESP-CAM sends images here

PROTECTED (login required):
    GET  /api/detections
    GET  /api/stats
    GET  /api/map-points
    GET  /api/status
    GET  /api/image/<file>
    POST /api/detect        ← same logic, for dashboard testing
"""

import os
from datetime import datetime

from flask import Blueprint, request, jsonify, send_from_directory

from core.auth     import login_required
from core.detector import run_detection, get_engine, DETECTION_ENGINE
from core.database import save_detection, get_all_detections, get_stats, get_map_points
from config.settings import (
    SAVE_IMAGES, IMAGES_DIR, TFLITE_MODEL_PATH, CONFIDENCE_THR
)

api_bp = Blueprint("api", __name__)


# ══════════════════════════════════════════════════════════════
# Shared detection logic
# ══════════════════════════════════════════════════════════════

def _run_detect_pipeline():
    """
    Core detection pipeline — called by both public and protected routes.
    Reads multipart/form-data: field 'image' (required), 'lat'/'lng' (optional).
    Returns a Flask JSON response.
    """
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image provided. Send field name: 'image'"}), 400

        image_bytes = request.files["image"].read()
        lat = request.form.get("lat", type=float)
        lng = request.form.get("lng", type=float)

        print(f"[DETECT] {len(image_bytes):,} bytes received  GPS={lat},{lng}")

        result     = run_detection(image_bytes)
        image_path = None

        if result["detected"]:
            if SAVE_IMAGES:
                fname = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
                fpath = os.path.join(IMAGES_DIR, fname)
                with open(fpath, "wb") as f:
                    f.write(result["annotated_image"])
                image_path = fname

            save_detection(
                result["confidence"], result["count"],
                result["materials"], image_path, lat, lng,
            )
            m = result["materials"]
            print(f"[DETECT] ✅ Pothole! conf={result['confidence']:.2f} "
                  f"area={m.get('area_m2', 0)} m²  "
                  f"cement={m.get('cement_kg', 0)} kg")
        else:
            print(f"[DETECT] ✔  Road clear  conf={result['confidence']:.2f}")

        return jsonify({
            "pothole_detected": result["detected"],
            "confidence":       result["confidence"],
            "pothole_count":    result["count"],
            "materials":        result["materials"],
            "engine":           result.get("engine", "unknown"),
            "timestamp":        datetime.now().isoformat(),
        })

    except Exception as exc:
        print(f"[DETECT] ERROR: {exc}")
        return jsonify({"error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════
# PUBLIC endpoint — ESP-CAM / any device sends here directly
# No session cookie required. Just POST the image.
#
# Arduino / ESP-CAM example:
#   HTTPClient http;
#   http.begin("http://<server-ip>:5000/detect");
#   http.POST(imageBuffer, imageLength);
# ══════════════════════════════════════════════════════════════

@api_bp.route("/detect", methods=["POST"])
def detect_public():
    """Public detection endpoint — for ESP-CAM and embedded devices."""
    return _run_detect_pipeline()


# ══════════════════════════════════════════════════════════════
# PROTECTED endpoints — require admin login session
# ══════════════════════════════════════════════════════════════

@api_bp.route("/api/detect", methods=["POST"])
@login_required
def detect_admin():
    """Protected detection endpoint — for testing via the dashboard."""
    return _run_detect_pipeline()


@api_bp.route("/api/detections")
@login_required
def detections():
    return jsonify(get_all_detections())


@api_bp.route("/api/stats")
@login_required
def stats():
    return jsonify(get_stats())


@api_bp.route("/api/map-points")
@login_required
def map_points():
    return jsonify(get_map_points())


@api_bp.route("/api/status")
@login_required
def status():
    return jsonify({
        "engine":               get_engine(),
        "model_path":           TFLITE_MODEL_PATH if get_engine() == "tflite" else None,
        "model_loaded":         get_engine() == "tflite",
        "confidence_threshold": CONFIDENCE_THR,
        "detect_endpoint":      "/detect  (public — for ESP-CAM)",
    })


@api_bp.route("/api/image/<filename>")
@login_required
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)
