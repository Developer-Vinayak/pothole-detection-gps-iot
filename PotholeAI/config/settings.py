# ─────────────────────────────────────────────
#  PotholeAI — Configuration
# ─────────────────────────────────────────────

# Admin credentials (change before deployment)
ADMIN_ID       = "Vinayak"
ADMIN_PASSWORD = "vinayak@123"
SECRET_KEY     = "vinayak_pothole_secret_2024"

# Database
DB_PATH = "potholes.db"

# Image storage
SAVE_IMAGES = True
IMAGES_DIR  = "detected_images"

# Detection threshold (raise to 0.55 to reduce false positives)
CONFIDENCE_THR = 0.45

# TFLite model (YOLOv8 single-class pothole, INT8 quantized)
#   Input  : [1, 160, 160, 3]
#   Output : [1, 5, 525] → [cx, cy, w, h, conf] per anchor
TFLITE_MODEL_PATH = "best_int8.tflite"
TFLITE_INPUT_H    = 160
TFLITE_INPUT_W    = 160
TFLITE_NMS_THRESH = 0.45

# Road & repair material constants
ROAD_WIDTH_M  = 3.5   # metres
POTHOLE_DEPTH = 0.08  # 8 cm assumed depth
CEMENT_KG     = 350   # kg per m³
SAND_KG       = 700
AGGREGATE_KG  = 1050
