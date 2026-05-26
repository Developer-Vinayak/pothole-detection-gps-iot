"""
core/database.py — SQLite helpers
"""

import sqlite3
from datetime import datetime
from config.settings import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS potholes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            confidence    REAL    NOT NULL,
            count         INTEGER DEFAULT 1,
            area_m2       REAL    DEFAULT 0,
            volume_m3     REAL    DEFAULT 0,
            cement_kg     REAL    DEFAULT 0,
            sand_kg       REAL    DEFAULT 0,
            aggregate_kg  REAL    DEFAULT 0,
            image_path    TEXT,
            latitude      REAL    DEFAULT NULL,
            longitude     REAL    DEFAULT NULL,
            timestamp     TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Database initialised:", DB_PATH)


def save_detection(confidence, count, mats, image_path=None, lat=None, lng=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO potholes
        (confidence, count, area_m2, volume_m3,
         cement_kg, sand_kg, aggregate_kg,
         image_path, latitude, longitude, timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        confidence, count,
        mats.get("area_m2",    0),
        mats.get("volume_m3",  0),
        mats.get("cement_kg",  0),
        mats.get("sand_kg",    0),
        mats.get("aggregate_kg", 0),
        image_path, lat, lng,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    conn.commit()
    conn.close()


def get_all_detections():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM potholes ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT
            COUNT(*),
            AVG(confidence),
            SUM(area_m2),
            SUM(cement_kg),
            SUM(sand_kg),
            SUM(aggregate_kg),
            MAX(timestamp)
        FROM potholes
    """).fetchone()
    conn.close()
    return {
        "total":           row[0] or 0,
        "avg_confidence":  round((row[1] or 0) * 100, 1),
        "total_area":      round(row[2] or 0, 3),
        "total_cement":    round(row[3] or 0, 2),
        "total_sand":      round(row[4] or 0, 2),
        "total_aggregate": round(row[5] or 0, 2),
        "last_detection":  row[6] or "N/A",
    }


def get_map_points():
    """Return only detections that have GPS coordinates."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, confidence, count, area_m2,
               latitude, longitude, timestamp
        FROM potholes
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY timestamp DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
