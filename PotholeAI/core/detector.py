"""
core/detector.py
YOLOv8 INT8 TFLite pothole detector with OpenCV fallback.
"""

import os
import warnings
import numpy as np
import cv2

from config.settings import (
    TFLITE_MODEL_PATH, TFLITE_INPUT_H, TFLITE_INPUT_W,
    TFLITE_NMS_THRESH, CONFIDENCE_THR,
    ROAD_WIDTH_M, POTHOLE_DEPTH, CEMENT_KG, SAND_KG, AGGREGATE_KG,
)

# ── Globals set once at startup ──────────────────────────────────
_interpreter      = None
_input_details    = None
_output_details   = None
DETECTION_ENGINE  = "opencv"


# ══════════════════════════════════════════════════════════════
# Startup loader
# ══════════════════════════════════════════════════════════════

def load_model():
    """Load TFLite model. Sets DETECTION_ENGINE to 'tflite' on success."""
    global _interpreter, _input_details, _output_details, DETECTION_ENGINE

    if not os.path.exists(TFLITE_MODEL_PATH):
        print(f"[DETECTOR] Model not found at '{TFLITE_MODEL_PATH}' — OpenCV fallback active.")
        return False

    try:
        try:
            import tflite_runtime.interpreter as tflite
            interp = tflite.Interpreter(model_path=TFLITE_MODEL_PATH)
        except ImportError:
            import tensorflow as tf
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                interp = tf.lite.Interpreter(model_path=TFLITE_MODEL_PATH)

        interp.allocate_tensors()
        _interpreter    = interp
        _input_details  = interp.get_input_details()
        _output_details = interp.get_output_details()
        DETECTION_ENGINE = "tflite"

        print(f"[DETECTOR] ✅ Model loaded : {TFLITE_MODEL_PATH}")
        print(f"[DETECTOR]    Input shape  : {_input_details[0]['shape']}")
        print(f"[DETECTOR]    Input dtype  : {_input_details[0]['dtype']}")
        print(f"[DETECTOR]    Output count : {len(_output_details)}")
        return True

    except Exception as exc:
        print(f"[DETECTOR] ❌ Failed to load model: {exc} — OpenCV fallback active.")
        return False


def get_engine():
    return DETECTION_ENGINE


# ══════════════════════════════════════════════════════════════
# Shared helpers
# ══════════════════════════════════════════════════════════════

def _calculate_materials(pothole_list, image_width):
    if not pothole_list:
        return {}
    px_per_m      = image_width / ROAD_WIDTH_M
    total_px_area = sum(p["area"] for p in pothole_list)
    area_m2       = round(total_px_area / (px_per_m ** 2), 4)
    volume        = round(area_m2 * POTHOLE_DEPTH, 5)
    return {
        "area_m2":      area_m2,
        "volume_m3":    volume,
        "cement_kg":    round(volume * CEMENT_KG,    2),
        "sand_kg":      round(volume * SAND_KG,      2),
        "aggregate_kg": round(volume * AGGREGATE_KG, 2),
    }


# ══════════════════════════════════════════════════════════════
# YOLOv8 TFLite detector
# ══════════════════════════════════════════════════════════════

def _run_tflite(img):
    """
    YOLOv8 INT8 inference.
    Model I/O (inspected from binary):
      Input  : [1, 160, 160, 3]  float32
      Output : [1, 5, 525]  → transpose → [525, 5]
               cols = [cx, cy, w, h, confidence]  (single class)
    """
    height, width = img.shape[:2]
    annotated     = img.copy()

    # 1. Pre-process
    resized    = cv2.resize(img, (TFLITE_INPUT_W, TFLITE_INPUT_H))
    rgb        = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    inp_detail = _input_details[0]
    inp_dtype  = inp_detail['dtype']

    if inp_dtype == np.float32:
        inp_tensor = np.expand_dims(rgb.astype(np.float32) / 255.0, axis=0)
    elif inp_dtype == np.uint8:
        inp_tensor = np.expand_dims(rgb.astype(np.uint8), axis=0)
    else:
        scale, zp  = inp_detail['quantization']
        inp_tensor = np.expand_dims(
            (rgb.astype(np.float32) / 255.0 / scale + zp).astype(np.int8), axis=0)

    # 2. Inference
    _interpreter.set_tensor(inp_detail['index'], inp_tensor)
    _interpreter.invoke()

    raw_out     = _interpreter.get_tensor(_output_details[0]['index'])  # [1,5,525]
    predictions = raw_out.astype(np.float32)

    # 3. Reshape [1,5,525] → [525,5]
    preds  = predictions[0].T
    scores = preds[:, 4]
    mask   = scores >= CONFIDENCE_THR

    if not np.any(mask):
        _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return _empty(buf)

    filtered   = preds[mask]
    conf_vals  = filtered[:, 4]

    # 4. cx,cy,w,h (normalised) → pixel x,y,w,h
    cx, cy = filtered[:,0]*width,  filtered[:,1]*height
    bw, bh = filtered[:,2]*width,  filtered[:,3]*height
    boxes  = [[int(cx[i]-bw[i]/2), int(cy[i]-bh[i]/2),
               int(bw[i]), int(bh[i])] for i in range(len(filtered))]

    # 5. NMS
    idxs = cv2.dnn.NMSBoxes(boxes, conf_vals.tolist(), CONFIDENCE_THR, TFLITE_NMS_THRESH)
    if len(idxs) == 0:
        _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return _empty(buf)

    idxs     = idxs.flatten()
    count    = len(idxs)
    avg_conf = float(np.mean(conf_vals[idxs]))

    # 6. Draw + build area list
    pothole_data = []
    for i in idxs:
        x, y, w, h = boxes[i]
        x, y = max(0,x), max(0,y)
        w = min(w, width-x);  h = min(h, height-y)
        w, h = max(w,1), max(h,1)
        pothole_data.append({"area": w*h, "bbox": (x,y,w,h)})

        label       = f"Pothole {int(conf_vals[i]*100)}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(annotated, (x, max(0,y-th-8)), (x+tw+6, y), (0,80,255), -1)
        cv2.rectangle(annotated, (x,y), (x+w,y+h), (0,80,255), 2)
        cv2.putText(annotated, label, (x+3, max(th, y-5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

    cv2.putText(annotated, f"[YOLOv8] {count} Pothole(s)  {int(avg_conf*100)}%",
                (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,80,255), 2)

    materials = _calculate_materials(pothole_data, width)
    _, buf    = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return {"detected": True, "confidence": round(avg_conf,3),
            "count": count, "materials": materials,
            "annotated_image": buf.tobytes(), "engine": "tflite"}


# ══════════════════════════════════════════════════════════════
# OpenCV fallback detector
# ══════════════════════════════════════════════════════════════

def _run_opencv(img):
    height, width = img.shape[:2]
    annotated     = img.copy()
    roi_start     = height // 3
    roi           = img[roi_start:, :]

    gray     = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred  = cv2.GaussianBlur(gray, (11,11), 0)
    mean_br  = np.mean(blurred)
    dark_thr = max(50, int(mean_br * 0.65))
    _, mask  = cv2.threshold(blurred, dark_thr, 255, cv2.THRESH_BINARY_INV)
    kernel   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
    mask     = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
    mask     = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    edges    = cv2.Canny(blurred, 50, 150)
    edge_den = np.sum(edges>0) / edges.size
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    potholes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < (width*height)*0.003 or area > (width*height)*0.35: continue
        x,y,w,h = cv2.boundingRect(cnt)
        ratio = float(w)/h if h>0 else 0
        if ratio < 0.2 or ratio > 5.0: continue
        peri = cv2.arcLength(cnt, True)
        if peri == 0: continue
        circ = 4*np.pi*area/(peri**2)
        if circ < 0.15: continue
        hull_area = cv2.contourArea(cv2.convexHull(cnt))
        if hull_area == 0 or area/hull_area < 0.4: continue
        potholes.append({"area":area, "bbox":(x,y+roi_start,w,h),
                         "circularity":circ, "solidity":area/hull_area})

    confidence = 0.0
    if potholes:
        max_circ = max(p["circularity"] for p in potholes)
        max_sol  = max(p["solidity"]    for p in potholes)
        area_sc  = min(1.0, sum(p["area"] for p in potholes)/(width*height*0.05))
        confidence = min(0.99, max(0.45,
            max_circ*0.30 + max_sol*0.30 + area_sc*0.25 + min(1.0,edge_den*10)*0.15))

        for p in potholes:
            x,y,w,h = p["bbox"]
            cv2.rectangle(annotated,(x,y),(x+w,y+h),(0,165,255),2)
            cv2.putText(annotated, f"Pothole {int(confidence*100)}%", (x,y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,165,255), 2)
        cv2.putText(annotated, f"[OpenCV] {len(potholes)} Pothole(s)  {int(confidence*100)}%",
                    (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,165,255), 2)

    materials = _calculate_materials(potholes, width) if potholes else {}
    _, buf    = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return {"detected": confidence >= CONFIDENCE_THR,
            "confidence": round(confidence,3),
            "count": len(potholes),
            "materials": materials,
            "annotated_image": buf.tobytes(),
            "engine": "opencv"}


# ══════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════

def _empty(buf):
    return {"detected":False,"confidence":0.0,"count":0,
            "materials":{},"annotated_image":buf.tobytes(),"engine":"tflite"}


def run_detection(image_bytes):
    """Entry point — TFLite primary, OpenCV fallback."""
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"detected":False,"confidence":0.0,"count":0,
                "materials":{},"annotated_image":image_bytes,"engine":"error"}

    if DETECTION_ENGINE == "tflite":
        try:
            return _run_tflite(img)
        except Exception as exc:
            print(f"[DETECTOR] TFLite runtime error: {exc} — OpenCV fallback for this frame.")

    return _run_opencv(img)
