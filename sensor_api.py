"""HTTP ingestion API for ESP8266/ESP32 or a greenhouse gateway.

Run: uvicorn sensor_api:app --host 0.0.0.0 --port 8000
Post JSON observations to /api/v1/observations.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from models.data_store import add_observation, get_observations

app = FastAPI(
    title="Pepper Digital Twin Sensor API",
    version="0.1.0",
    description="Receives timestamped greenhouse observations. Values are stored as IoT-origin records.",
)

class SensorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestamp: Optional[str] = None
    plot_id: str = "Plot-1"
    device_id: str = Field(min_length=1, max_length=80)
    soil_moisture_pct: Optional[float] = Field(default=None, ge=0, le=100)
    soil_temperature_c: Optional[float] = Field(default=None, ge=-10, le=80)
    soil_ec_ds_m: Optional[float] = Field(default=None, ge=0, le=100)
    soil_ph: Optional[float] = Field(default=None, ge=0, le=14)
    air_temperature_c: Optional[float] = Field(default=None, ge=-10, le=80)
    relative_humidity_pct: Optional[float] = Field(default=None, ge=0, le=100)
    water_ec_ds_m: Optional[float] = Field(default=None, ge=0, le=100)
    water_ph: Optional[float] = Field(default=None, ge=0, le=14)
    irrigation_l: Optional[float] = Field(default=None, ge=0)
    drainage_l: Optional[float] = Field(default=None, ge=0)
    pot_weight_kg: Optional[float] = Field(default=None, ge=0)
    drainage_weight_kg: Optional[float] = Field(default=None, ge=0)
    nitrogen_mg_l: Optional[float] = Field(default=None, ge=0)
    phosphorus_mg_l: Optional[float] = Field(default=None, ge=0)
    potassium_mg_l: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "service": "pepper-digital-twin-sensor-api"}

@app.post("/api/v1/observations", status_code=201)
def receive_observation(payload: SensorPayload):
    record = payload.model_dump()
    record["timestamp"] = record["timestamp"] or datetime.now(timezone.utc).isoformat()
    record["source"] = "iot"
    try:
        new_id = add_observation(record, source_override="iot")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"accepted": True, "observation_id": new_id, "source": "iot"}

@app.get("/api/v1/observations")
def recent_observations(limit: int = 100, plot_id: Optional[str] = None):
    if not 1 <= limit <= 5000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 5000")
    return {"items": get_observations(limit=limit, plot_id=plot_id)}
