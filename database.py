
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "pepper_digital_twin.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        crop TEXT DEFAULT 'Pepper',
        location TEXT,
        start_date TEXT,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY(experiment_id) REFERENCES experiments(id)
    );

    CREATE TABLE IF NOT EXISTS plots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id INTEGER NOT NULL,
        treatment_id INTEGER NOT NULL,
        plot_code TEXT NOT NULL,
        replication INTEGER,
        area_m2 REAL,
        FOREIGN KEY(experiment_id) REFERENCES experiments(id),
        FOREIGN KEY(treatment_id) REFERENCES treatments(id),
        UNIQUE(experiment_id, plot_code)
    );

    CREATE TABLE IF NOT EXISTS plants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER NOT NULL,
        plant_code TEXT NOT NULL,
        FOREIGN KEY(plot_id) REFERENCES plots(id),
        UNIQUE(plot_id, plant_code)
    );

    CREATE TABLE IF NOT EXISTS plot_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER NOT NULL,
        observation_date TEXT NOT NULL,
        soil_moisture REAL,
        soil_ec REAL,
        soil_ph REAL,
        water_ec REAL,
        water_ph REAL,
        air_temperature REAL,
        relative_humidity REAL,
        notes TEXT,
        source TEXT DEFAULT 'manual',
        FOREIGN KEY(plot_id) REFERENCES plots(id)
    );

    CREATE TABLE IF NOT EXISTS plant_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plant_id INTEGER NOT NULL,
        observation_date TEXT NOT NULL,
        plant_height_cm REAL,
        canopy_width_cm REAL,
        leaf_number INTEGER,
        leaf_area_cm2 REAL,
        growth_stage TEXT,
        visual_notes TEXT,
        FOREIGN KEY(plant_id) REFERENCES plants(id)
    );

    CREATE TABLE IF NOT EXISTS irrigation_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER NOT NULL,
        start_time TEXT,
        end_time TEXT,
        water_volume_liter REAL,
        irrigation_method TEXT,
        notes TEXT,
        FOREIGN KEY(plot_id) REFERENCES plots(id)
    );

    CREATE TABLE IF NOT EXISTS fertigation_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER NOT NULL,
        event_date TEXT,
        fertilizer_name TEXT,
        nitrogen_g REAL,
        phosphorus_g REAL,
        potassium_g REAL,
        total_amount_g REAL,
        notes TEXT,
        FOREIGN KEY(plot_id) REFERENCES plots(id)
    );

    CREATE TABLE IF NOT EXISTS harvests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER NOT NULL,
        harvest_date TEXT,
        fruit_number INTEGER,
        yield_kg REAL,
        average_fruit_weight_g REAL,
        notes TEXT,
        FOREIGN KEY(plot_id) REFERENCES plots(id)
    );

    CREATE TABLE IF NOT EXISTS sensors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_code TEXT NOT NULL,
        sensor_type TEXT NOT NULL,
        plot_id INTEGER,
        unit TEXT,
        calibration_date TEXT,
        active INTEGER DEFAULT 1,
        FOREIGN KEY(plot_id) REFERENCES plots(id)
    );

    CREATE TABLE IF NOT EXISTS sensor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sensor_id INTEGER NOT NULL,
        reading_time TEXT NOT NULL,
        raw_value REAL,
        calibrated_value REAL,
        unit TEXT,
        quality_status TEXT DEFAULT 'unchecked',
        sequence_number INTEGER,
        source TEXT DEFAULT 'iot',
        FOREIGN KEY(sensor_id) REFERENCES sensors(id)
    );

    CREATE TABLE IF NOT EXISTS ai_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER,
        decision_time TEXT,
        decision_type TEXT,
        recommended_water_liter REAL,
        recommended_nitrogen_g REAL,
        recommended_phosphorus_g REAL,
        recommended_potassium_g REAL,
        model_name TEXT,
        confidence REAL,
        explanation TEXT,
        approval_status TEXT DEFAULT 'pending',
        FOREIGN KEY(plot_id) REFERENCES plots(id)
    );

    CREATE TABLE IF NOT EXISTS control_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER,
        execution_time TEXT,
        actual_water_liter REAL,
        actual_fertilizer_g REAL,
        execution_status TEXT,
        notes TEXT,
        FOREIGN KEY(decision_id) REFERENCES ai_decisions(id)
    );
    """)

    conn.commit()
    conn.close()
