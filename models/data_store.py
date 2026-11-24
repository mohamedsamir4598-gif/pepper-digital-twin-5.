"""Persistent data store for manual, imported, and IoT greenhouse observations.

All records retain their provenance in the `source` field. Synthetic
simulation outputs should not be inserted here as measured observations.
"""
from pathlib import Path
import os
import math
import sqlite3
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("PEPPER_DB_PATH", ROOT / "data" / "pepper_observations.sqlite3"))

FIELDS = [
    "timestamp", "plot_id", "source", "device_id",
    "soil_moisture_pct", "soil_temperature_c", "soil_ec_ds_m", "soil_ph",
    "air_temperature_c", "relative_humidity_pct",
    "water_ec_ds_m", "water_ph", "irrigation_l", "drainage_l",
    "pot_weight_kg", "drainage_weight_kg",
    "nitrogen_mg_l", "phosphorus_mg_l", "potassium_mg_l", "notes",
]

NUMERIC_FIELDS = set(FIELDS) - {"timestamp", "plot_id", "source", "device_id", "notes"}

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_store():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                plot_id TEXT NOT NULL DEFAULT 'Plot-1',
                source TEXT NOT NULL CHECK(source IN ('manual','csv','iot')),
                device_id TEXT,
                soil_moisture_pct REAL,
                soil_temperature_c REAL,
                soil_ec_ds_m REAL,
                soil_ph REAL,
                air_temperature_c REAL,
                relative_humidity_pct REAL,
                water_ec_ds_m REAL,
                water_ph REAL,
                irrigation_l REAL,
                drainage_l REAL,
                pot_weight_kg REAL,
                drainage_weight_kg REAL,
                nitrogen_mg_l REAL,
                phosphorus_mg_l REAL,
                potassium_mg_l REAL,
                notes TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_observations_time ON observations(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_observations_plot ON observations(plot_id)")

def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def _clean_record(record, source_override=None):
    row = {key: record.get(key) for key in FIELDS}
    if _is_missing(row.get("timestamp")):
        row["timestamp"] = datetime.now(timezone.utc).isoformat()
    else:
        row["timestamp"] = str(row["timestamp"])
    if _is_missing(row.get("plot_id")):
        row["plot_id"] = "Plot-1"
    else:
        row["plot_id"] = str(row["plot_id"])
    row["source"] = source_override or (
        "manual" if _is_missing(row.get("source")) else str(row["source"])
    )
    if row["source"] not in {"manual", "csv", "iot"}:
        raise ValueError("source must be manual, csv, or iot")
    for key in NUMERIC_FIELDS:
        value = row.get(key)
        if _is_missing(value):
            row[key] = None
        else:
            try:
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError
                row[key] = number
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be a finite numeric value") from None
    return row

def add_observation(record, source_override=None):
    initialize_store()
    row = _clean_record(record, source_override)
    columns = ", ".join(FIELDS)
    placeholders = ", ".join(["?"] * len(FIELDS))
    values = [row[k] for k in FIELDS]
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO observations ({columns}) VALUES ({placeholders})",
            values,
        )
        return cur.lastrowid

def add_observations(records, source_override="csv"):
    initialize_store()
    cleaned = [_clean_record(record, source_override) for record in records]
    if not cleaned:
        return 0
    columns = ", ".join(FIELDS)
    placeholders = ", ".join(["?"] * len(FIELDS))
    values = [[row[k] for k in FIELDS] for row in cleaned]
    with get_connection() as conn:
        conn.executemany(
            f"INSERT INTO observations ({columns}) VALUES ({placeholders})",
            values,
        )
    return len(cleaned)

def get_observations(limit=5000, plot_id=None):
    initialize_store()
    query = "SELECT * FROM observations"
    params = []
    if plot_id:
        query += " WHERE plot_id = ?"
        params.append(str(plot_id))
    query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
    params.append(int(limit))
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
