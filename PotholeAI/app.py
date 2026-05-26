"""
PotholeAI — Entry Point
=======================
Run:
    python app.py

Dependencies:
    pip install flask opencv-python-headless numpy

Optional (better detection):
    pip install tflite-runtime
    (or) pip install tensorflow
    Place best_int8.tflite in this folder for YOLOv8 mode.
"""

import os
import warnings
import logging

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL']  = '3'
warnings.filterwarnings('ignore')
logging.getLogger('tensorflow').setLevel(logging.ERROR)

from flask import Flask
from config.settings        import SECRET_KEY, SAVE_IMAGES, IMAGES_DIR
from core.database          import init_db
from core.detector          import load_model, DETECTION_ENGINE

from routes.auth_routes      import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.map_routes       import map_bp
from routes.about_routes     import about_bp
from routes.api_routes       import api_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(about_bp)
    app.register_blueprint(api_bp)
    return app


if __name__ == "__main__":
    if SAVE_IMAGES and not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    init_db()
    load_model()
    app = create_app()

    engine_label = "🤖 YOLOv8 INT8 (TFLite)" if DETECTION_ENGINE == "tflite" else "🔷 OpenCV (fallback)"

    print("=" * 60)
    print("  🛣️  PotholeAI — Pothole Detection System")
    print(f"  Engine     : {engine_label}")
    print("  Dashboard  : http://0.0.0.0:5000/")
    print("  Map        : http://0.0.0.0:5000/map")
    print("  About      : http://0.0.0.0:5000/about")
    print("  ESP-CAM    : POST http://0.0.0.0:5000/detect  (no login needed)")
    print("  Admin ID   : Vinayak")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5000, debug=False)
