# Pepper Greenhouse Digital Twin

Research prototype for pepper greenhouse water management, crop simulation, data acquisition and decision-support experiments.

## Current modules

- **Mechanistic simulation** (models/simulation.py): simplified root-zone water balance, ETc/ETa, stress coefficient, LAI and biomass proxies.
- **Synthetic AI surrogate**: Random Forest trained on simulator-generated scenarios. Its reported scores describe agreement with the simulator, not field accuracy.
- **Data acquisition** (models/data_store.py): manual observations and CSV imports stored in SQLite with source tags (manual, csv, iot).
- **IoT ingestion API** (sensor_api.py): FastAPI endpoints for future ESP8266/ESP32/gateway integration.
- **Decision support** (models/decision_support.py): transparent root-zone moisture threshold irrigation schedule and fertilizer product-mass calculator based on a user-entered elemental nutrient label fraction.
- **Scenario comparison, literature data and CSV exports** in the Streamlit interface.

## Run the Streamlit application

Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Run the sensor API

In a second terminal, from the project root:

```bash
uvicorn sensor_api:app --host 0.0.0.0 --port 8000
```

- Health check: GET /health
- Receive one observation: POST /api/v1/observations
- Read recent observations: GET /api/v1/observations?limit=100
- Interactive API schema: http://localhost:8000/docs

Example JSON payload:

```json
{
  "plot_id": "Plot-1",
  "device_id": "ESP8266-GW-01",
  "soil_moisture_pct": 27.4,
  "soil_temperature_c": 23.8,
  "air_temperature_c": 26.1,
  "relative_humidity_pct": 61.0
}
```

The API marks incoming records as iot. It validates ranges and rejects unknown JSON fields.

## Database location

By default, the observation database is created at data/pepper_observations.sqlite3.

Set PEPPER_DB_PATH to override the path. For the Streamlit app and API to see the same SQLite records, both processes must run on the same host and use the same database path. If deployed on separate machines or ephemeral cloud containers, use a shared server database or a secured ingestion service; a local SQLite file is not automatically shared between deployments.

## Data provenance and scientific limits

- Simulation outputs are not measurements. The app keeps synthetic simulation output separate from manual, CSV and IoT observation records.
- The current crop and water models are simplified research prototypes. Parameters such as Kc, root-zone depth, depletion fraction, crop response and yield conversion require crop- and greenhouse-specific calibration.
- The candidate irrigation schedule is a rule-based post-processing demonstration using the displayed daily moisture trajectory. It is not yet a closed-loop predictive controller and does not actuate valves or pumps.
- Emitter count, emitter flow and efficiency in the interface are editable illustrative assumptions. Replace them with measured system specifications and field-calibrated values.
- The fertilizer calculator computes product mass only from a specified target elemental nutrient concentration, solution volume and labelled elemental nutrient fraction. It does not determine crop demand, convert oxide labels automatically, or verify solubility, compatibility, alkalinity or EC limits.
- Synthetic AI metrics measure agreement with simulator-generated targets only. The literature model is exploratory and uses a small number of treatment means. Neither is independently validated against real greenhouse pepper data.
- Do not connect this prototype directly to actuators without independent verification, authentication, hardware interlocks, watchdogs, emergency stop, pressure/flow limits and fail-safe logic.

## Next research development steps

1. Calibrate soil hydraulic and irrigation parameters using substrate/soil measurements and sensor calibration.
2. Validate water balance against independent pot weighing, irrigation volume and drainage measurements.
3. Calibrate crop growth and nutrient-response submodels against replicated pepper observations.
4. Use plot/season-grouped validation for experimental ML updates and preserve a locked independent test set.
5. Develop a tested safety state machine and hardware-in-the-loop tests before any physical actuation.
