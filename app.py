import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from models.simulation import (
    simulate_crop,
    compare_scenarios,
    REQUIRED_WEATHER_COLUMNS,
)
from models.training import (
    train_residual_model,
    predict_with_pretrained_model,
    PRETRAINED_MODEL_PATH,
    PRETRAINED_REPORT_PATH,
    PRETRAINED_DATA_PATH,
    LITERATURE_MODEL_PATH,
)

from models.data_store import (
    initialize_store,
    add_observation,
    add_observations,
    get_observations,
)

from models.decision_support import (
    build_irrigation_schedule,
    fertilizer_mass_for_target,
)

st.set_page_config(
    page_title="Pepper Greenhouse Digital Twin",
    page_icon="🌱",
    layout="wide",
)

st.title("🌱 Pepper Greenhouse Digital Twin")
st.caption(
    "Research prototype | Crop growth simulation | "
    "Smart irrigation and fertigation | Pretrained AI"
)

with st.sidebar:
    st.header("Greenhouse configuration")

    crop_days = st.slider(
        "Simulation duration (days)", 60, 180, 120, 5
    )

    area_m2 = st.number_input(
        "Greenhouse area (m²)",
        min_value=20.0,
        max_value=10000.0,
        value=300.0,
        step=10.0,
    )

    plant_density = st.number_input(
        "Plant density (plants/m²)",
        min_value=1.0,
        max_value=8.0,
        value=2.5,
        step=0.1,
    )

    st.divider()
    st.subheader("Soil properties")

    fc = st.slider(
        "Field capacity (%)", 15.0, 55.0, 32.0, 0.5
    ) / 100

    wp = st.slider(
        "Wilting point (%)", 5.0, 35.0, 15.0, 0.5
    ) / 100

    root_depth = st.slider(
        "Root depth (m)", 0.10, 0.80, 0.35, 0.05
    )

    initial_theta = st.slider(
        "Initial soil moisture (%)", 5.0, 55.0, 28.0, 0.5
    ) / 100

    st.divider()
    st.subheader("Irrigation and fertilization")

    irrigation_strategy = st.selectbox(
        "Irrigation strategy",
        options=["fixed_etc", "soil_moisture_trigger"],
        format_func=lambda x: (
            "Fixed fraction of ETc" if x == "fixed_etc"
            else "Soil-moisture trigger and refill"
        ),
    )

    irrigation_pct = st.select_slider(
        "Irrigation (% ETc) — used in fixed strategy",
        options=[60, 75, 90, 100, 105],
        value=90,
    )

    trigger_fraction = st.slider(
        "Trigger depletion (% TAW)", 10, 80, 40
    ) / 100.0

    target_fraction = st.slider(
        "Refill target (% TAW)", 60, 100, 90
    ) / 100.0

    fertilizer_pct = st.select_slider(
        "Fertilizer (% reference)",
        options=[25, 50, 75, 100],
        value=75,
    )

    irrigation_eff = st.slider(
        "Irrigation efficiency (%)", 60, 100, 90
    ) / 100

    initial_lai = st.slider(
        "Initial LAI", 0.05, 1.0, 0.15, 0.05
    )

    initial_biomass = st.number_input(
        "Initial biomass (t/ha)",
        0.0, 5.0, 0.05, 0.01
    )

    st.divider()
    st.subheader("Pepper growth model parameters")
    rue_g_mj = st.number_input(
        "Radiation use efficiency (g DM/MJ intercepted PAR)",
        min_value=0.1, max_value=5.0, value=1.6, step=0.1
    )
    specific_leaf_area = st.number_input(
        "Specific leaf area (m²/kg)",
        min_value=1.0, max_value=60.0, value=25.0, step=1.0
    )
    extinction_coefficient = st.number_input(
        "Canopy extinction coefficient (k)",
        min_value=0.1, max_value=2.0, value=0.70, step=0.05
    )
    flowering_gdd = st.number_input(
        "Flowering threshold (°C·day)",
        min_value=50.0, max_value=1500.0, value=300.0, step=25.0
    )
    fruit_set_gdd = st.number_input(
        "Fruit-set threshold (°C·day)",
        min_value=100.0, max_value=2000.0, value=500.0, step=25.0
    )
    harvest_gdd = st.number_input(
        "Harvest-stage threshold (°C·day)",
        min_value=200.0, max_value=3000.0, value=1000.0, step=25.0
    )

    st.divider()
    st.subheader("Root-zone salinity (laboratory ECe)")
    use_rootzone_ece = st.checkbox(
        "Apply salinity response using measured saturation-extract ECe",
        value=False,
    )
    rootzone_ece_ds_m = st.number_input(
        "Root-zone ECe (dS/m)",
        min_value=0.0, max_value=30.0, value=1.5, step=0.1,
        disabled=not use_rootzone_ece,
    )
    st.caption(
        "Use only laboratory ECe from a saturated-paste extract. "
        "Do not enter irrigation-water EC, nutrient-solution EC, or an "
        "uncalibrated in-situ bulk soil EC sensor reading here."
    )

if wp >= fc:
    st.error("Wilting point must be lower than field capacity.")
    st.stop()

if not flowering_gdd < fruit_set_gdd < harvest_gdd:
    st.error(
        "Growth-stage thermal thresholds must increase: "
        "flowering < fruit set < harvest."
    )
    st.stop()

st.header("Weather data")

weather_file = st.file_uploader(
    "Upload daily weather CSV",
    type=["csv"],
)

if weather_file is not None:
    try:
        weather = pd.read_csv(weather_file)

        missing = [
            col for col in REQUIRED_WEATHER_COLUMNS
            if col not in weather.columns
        ]

        if missing:
            st.error(f"Missing columns: {missing}")
            st.stop()

        weather = weather.head(crop_days).copy()

        if len(weather) < crop_days:
            crop_days = len(weather)

        weather_source = "Uploaded weather data"

    except Exception as exc:
        st.error(f"Weather file error: {exc}")
        st.stop()
else:
    weather = None
    weather_source = "Literature-based assumed weather"

# Optional measured-state initialization for the digital twin.
# This does not silently overwrite the user's configured initial condition.
initialize_store()
stored_rows = get_observations(limit=5000)
moisture_rows = [
    row for row in stored_rows
    if row.get("soil_moisture_pct") is not None
]
simulation_initial_theta = initial_theta

if moisture_rows:
    st.subheader("Initialize the digital twin from an observation")
    latest_by_plot = {}
    for observation in moisture_rows:
        plot_key = observation.get("plot_id") or "Plot-1"
        if plot_key not in latest_by_plot:
            latest_by_plot[plot_key] = observation
    selected_plot = st.selectbox(
        "Observation plot",
        options=sorted(latest_by_plot.keys()),
        key="initial_state_plot",
    )
    selected_observation = latest_by_plot[selected_plot]
    measured_vwc = float(selected_observation["soil_moisture_pct"])
    use_measured_state = st.checkbox(
        "Use latest stored soil-moisture reading as the simulation initial condition",
        value=False,
        key="use_measured_initial_vwc",
    )
    st.caption(
        f"Latest available record: {selected_observation.get('timestamp')} | "
        f"Source: {selected_observation.get('source')} | "
        f"VWC: {measured_vwc:.2f}%"
    )
    if use_measured_state:
        if wp * 100 <= measured_vwc <= fc * 100:
            simulation_initial_theta = measured_vwc / 100.0
            st.success(
                "The digital twin will start from this measured VWC value."
            )
        else:
            st.warning(
                "The selected reading is outside the configured wilting-point "
                "to field-capacity interval. It will not be used; review soil "
                "parameters or sensor calibration."
            )
else:
    st.info(
        "No stored moisture readings are available yet. The model will use "
        "the initial moisture value configured in the sidebar."
    )

params = {
    "days": crop_days,
    "fc": fc,
    "wp": wp,
    "root_depth_m": root_depth,
    "initial_theta": simulation_initial_theta,
    "irrigation_pct": irrigation_pct,
    "irrigation_strategy": irrigation_strategy,
    "trigger_fraction": trigger_fraction,
    "target_fraction": target_fraction,
    "fertilizer_pct": fertilizer_pct,
    "irrigation_efficiency": irrigation_eff,
    "initial_lai": initial_lai,
    "initial_biomass_t_ha": initial_biomass,
    "rue_g_mj": rue_g_mj,
    "specific_leaf_area_m2_kg": specific_leaf_area,
    "extinction_coefficient": extinction_coefficient,
    "flowering_gdd": flowering_gdd,
    "fruit_set_gdd": fruit_set_gdd,
    "harvest_gdd": harvest_gdd,
    "rootzone_ece_ds_m": rootzone_ece_ds_m if use_rootzone_ece else None,
    "salinity_threshold_ece_ds_m": 1.5,
    "salinity_slope_pct_per_ds_m": 14.1,
    "area_m2": area_m2,
    "plant_density": plant_density,
}

if "active_result" not in st.session_state:
    st.session_state.active_result = None

col1, col2 = st.columns([1, 4])

with col1:
    run_now = st.button(
        "Run Digital Twin",
        type="primary",
        width="stretch",
    )

with col2:
    st.caption(f"Weather source: {weather_source}")

if run_now or st.session_state.active_result is None:
    st.session_state.active_result = simulate_crop(
        params, weather
    )

result = st.session_state.active_result
df = result["daily"]
summary = result["summary"]

if weather is None:
    st.warning(
        "Weather and some crop parameters are assumed or "
        "literature-based. Simulation outputs are not field measurements."
    )

# ---------------------------------------------------------------------
# Unified data acquisition: manual entry, CSV import, and IoT records
# ---------------------------------------------------------------------
initialize_store()
st.header("Greenhouse data acquisition")
st.caption(
    "Manual and imported observations are stored separately from "
    "the synthetic digital-twin simulation outputs."
)

with st.expander("Add a manual greenhouse observation", expanded=False):
    with st.form("manual_observation_form", clear_on_submit=True):
        m1, m2, m3 = st.columns(3)
        with m1:
            manual_plot = st.text_input("Plot / treatment ID", value="Plot-1")
            manual_time = st.text_input(
                "Timestamp (ISO format; optional)", value=""
            )
            manual_vwc = st.number_input(
                "Soil moisture (% VWC)", min_value=0.0,
                max_value=100.0, value=25.0, step=0.5
            )
            manual_soil_temp = st.number_input(
                "Soil temperature (°C)", value=24.0, step=0.5
            )
            manual_soil_ec = st.number_input(
                "Soil EC (dS/m)", min_value=0.0, value=1.0, step=0.1
            )
            manual_soil_ph = st.number_input(
                "Soil pH", min_value=0.0, max_value=14.0,
                value=6.5, step=0.1
            )
        with m2:
            manual_air_temp = st.number_input(
                "Air temperature (°C)", value=25.0, step=0.5
            )
            manual_rh = st.number_input(
                "Relative humidity (%)", min_value=0.0,
                max_value=100.0, value=60.0, step=1.0
            )
            manual_water_ec = st.number_input(
                "Irrigation water EC (dS/m)", min_value=0.0,
                value=0.8, step=0.1
            )
            manual_water_ph = st.number_input(
                "Irrigation water pH", min_value=0.0,
                max_value=14.0, value=7.0, step=0.1
            )
            manual_irrigation = st.number_input(
                "Applied irrigation (L)", min_value=0.0,
                value=0.0, step=0.1
            )
            manual_drainage = st.number_input(
                "Drainage volume (L)", min_value=0.0,
                value=0.0, step=0.1
            )
        with m3:
            manual_pot_weight = st.number_input(
                "Pot weight (kg)", min_value=0.0, value=0.0, step=0.1
            )
            manual_drain_weight = st.number_input(
                "Drainage container weight (kg)", min_value=0.0,
                value=0.0, step=0.1
            )
            manual_n = st.number_input(
                "N concentration (mg/L)", min_value=0.0, value=0.0, step=1.0
            )
            manual_p = st.number_input(
                "P concentration (mg/L)", min_value=0.0, value=0.0, step=1.0
            )
            manual_k = st.number_input(
                "K concentration (mg/L)", min_value=0.0, value=0.0, step=1.0
            )
            manual_notes = st.text_input("Notes")
        save_manual = st.form_submit_button(
            "Save manual observation", type="primary"
        )
        if save_manual:
            record = {
                "timestamp": manual_time or None,
                "plot_id": manual_plot,
                "source": "manual",
                "soil_moisture_pct": manual_vwc,
                "soil_temperature_c": manual_soil_temp,
                "soil_ec_ds_m": manual_soil_ec,
                "soil_ph": manual_soil_ph,
                "air_temperature_c": manual_air_temp,
                "relative_humidity_pct": manual_rh,
                "water_ec_ds_m": manual_water_ec,
                "water_ph": manual_water_ph,
                "irrigation_l": manual_irrigation,
                "drainage_l": manual_drainage,
                "pot_weight_kg": manual_pot_weight,
                "drainage_weight_kg": manual_drain_weight,
                "nitrogen_mg_l": manual_n,
                "phosphorus_mg_l": manual_p,
                "potassium_mg_l": manual_k,
                "notes": manual_notes,
            }
            try:
                add_observation(record, source_override="manual")
                st.success("Observation saved to the local database.")
            except Exception as exc:
                st.error(f"Could not save observation: {exc}")

with st.expander("Import observations from CSV", expanded=False):
    st.write(
        "CSV columns supported: timestamp, plot_id, device_id, "
        "soil_moisture_pct, soil_temperature_c, soil_ec_ds_m, soil_ph, "
        "air_temperature_c, relative_humidity_pct, water_ec_ds_m, water_ph, "
        "irrigation_l, drainage_l, pot_weight_kg, drainage_weight_kg, "
        "nitrogen_mg_l, phosphorus_mg_l, potassium_mg_l, notes."
    )
    observation_file = st.file_uploader(
        "Upload observation CSV", type=["csv"], key="observation_csv_upload"
    )
    if observation_file is not None:
        try:
            imported = pd.read_csv(observation_file)
            st.dataframe(imported.head(10), width="stretch")
            if st.button("Import these observations", key="import_observations"):
                count = add_observations(
                    imported.to_dict(orient="records"), source_override="csv"
                )
                st.success(f"Imported {count} observations. Source tagged as CSV.")
        except Exception as exc:
            st.error(f"CSV import failed: {exc}")

observations = pd.DataFrame(get_observations(limit=5000))
if not observations.empty:
    st.subheader("Stored measured / manually entered observations")
    source_filter = st.multiselect(
        "Filter by data source",
        options=["manual", "csv", "iot"],
        default=["manual", "csv", "iot"],
        key="observation_source_filter",
    )
    visible_observations = observations[
        observations["source"].isin(source_filter)
    ]
    st.dataframe(visible_observations, width="stretch")
    st.download_button(
        "Download observation database as CSV",
        visible_observations.to_csv(index=False).encode("utf-8-sig"),
        file_name="pepper_greenhouse_observations.csv",
        mime="text/csv",
    )
else:
    st.info(
        "No observations have been entered yet. The simulation can run "
        "without sensors; add manual data or import a CSV whenever available."
    )

with st.expander("Connect an IoT gateway (future hardware integration)"):
    st.markdown(
        "The API stores incoming sensor records in the same local database "
        "when it runs on the same computer/environment as this Streamlit app."
    )
    st.code(
        "uvicorn sensor_api:app --host 0.0.0.0 --port 8000\n"
        "POST http://localhost:8000/api/v1/observations",
        language="bash",
    )
    st.caption(
        "For remote deployment, configure PEPPER_DB_PATH to a shared "
        "persistent database location or replace SQLite with a server database. "
        "Do not expose the API publicly without authentication and network security."
    )

st.header("Greenhouse status")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Soil moisture",
    f"{df.Soil_Moisture_pct.iloc[-1]:.1f}%"
)

c2.metric(
    "Seasonal ETa",
    f"{df.ETa_mm.sum():.1f} mm"
)

c3.metric(
    "Applied irrigation",
    f"{df.Irrigation_mm.sum():.1f} mm"
)

c4.metric(
    "Final LAI",
    f"{df.LAI.iloc[-1]:.2f}"
)

c5.metric(
    "Final biomass",
    f"{df.Biomass_t_ha.iloc[-1]:.2f} t/ha"
)

st.header("Decision support and virtual operation")
st.caption(
    "The following is a transparent rule-based candidate schedule. "
    "It is not an autonomous controller and must be calibrated before field use."
)
with st.expander("Configure irrigation network assumptions", expanded=True):
    d1, d2, d3 = st.columns(3)
    with d1:
        decision_trigger = st.slider(
            "Irrigation trigger (% available water)", 20, 80, 45
        ) / 100
        decision_target = st.slider(
            "Refill target (% available water)", 60, 100, 90
        ) / 100
    with d2:
        decision_emitters = st.number_input(
            "Number of emitters", min_value=1, max_value=100000,
            value=300, step=10
        )
        decision_flow = st.number_input(
            "Emitter flow (L/h)", min_value=0.1, max_value=100.0,
            value=2.0, step=0.1
        )
    with d3:
        decision_eff = st.slider(
            "Application efficiency (%)", 50, 100, 90
        ) / 100
        decision_max_runtime = st.number_input(
            "Maximum runtime per event (min)", min_value=1.0,
            max_value=1440.0, value=180.0, step=5.0
        )
    st.caption(
        "Emitter count, emitter discharge and efficiency are editable "
        "illustrative defaults, not measured greenhouse specifications."
    )

try:
    irrigation_plan = build_irrigation_schedule(
        df,
        field_capacity_pct=fc * 100,
        wilting_point_pct=wp * 100,
        root_depth_m=root_depth,
        area_m2=area_m2,
        trigger_fraction=decision_trigger,
        target_fraction=decision_target,
        application_efficiency=decision_eff,
        emitter_count=int(decision_emitters),
        emitter_flow_lph=decision_flow,
        max_runtime_min=decision_max_runtime,
    )
    event_plan = irrigation_plan[irrigation_plan["Irrigation_Event"]]
    dcol1, dcol2, dcol3 = st.columns(3)
    dcol1.metric("Candidate irrigation events", len(event_plan))
    dcol2.metric(
        "Candidate gross water",
        f"{irrigation_plan['Gross_Water_L'].sum():.1f} L"
    )
    dcol3.metric(
        "Maximum event runtime",
        f"{event_plan['Valve_Runtime_min'].max():.1f} min"
        if not event_plan.empty else "No event"
    )
    st.dataframe(irrigation_plan, width="stretch")
    st.download_button(
        "Download candidate irrigation schedule",
        irrigation_plan.to_csv(index=False).encode("utf-8-sig"),
        file_name="pepper_candidate_irrigation_schedule.csv",
        mime="text/csv",
    )
except Exception as exc:
    st.error(f"Could not calculate irrigation schedule: {exc}")

with st.expander("Fertilizer solution mass calculator (label-based)"):
    st.warning(
        "This calculates product mass for a user-specified nutrient "
        "concentration. It does not infer crop nutrient demand or check "
        "chemical compatibility, water alkalinity, solubility or salinity."
    )
    f1, f2, f3 = st.columns(3)
    with f1:
        nutrient_target = st.number_input(
            "Target nutrient concentration (mg/L)", min_value=0.0,
            value=100.0, step=10.0
        )
    with f2:
        nutrient_solution_volume = st.number_input(
            "Final solution volume (L)", min_value=0.0,
            value=100.0, step=10.0
        )
    with f3:
        nutrient_grade_pct = st.number_input(
            "Labelled elemental nutrient (%)", min_value=0.1,
            max_value=100.0, value=15.0, step=0.5
        )
    try:
        dose = fertilizer_mass_for_target(
            nutrient_target,
            nutrient_solution_volume,
            nutrient_grade_pct / 100.0,
        )
        st.metric(
            "Calculated fertilizer product mass",
            f"{dose['fertilizer_product_g']:.2f} g"
        )
        st.caption(
            f"Elemental nutrient required: {dose['target_nutrient_g']:.2f} g. "
            "Enter elemental nutrient percentage from the label; do not "
            "enter P2O5 or K2O as if they were elemental P or K."
        )
    except Exception as exc:
        st.error(str(exc))

tabs = st.tabs([
    "Overview",
    "Soil and Water",
    "Crop Growth",
    "Scenarios",
    "Artificial Intelligence",
    "Literature Data",
    "Export Data",
    "Scientific Notes",
])

with tabs[0]:
    st.subheader("Soil moisture development")

    fig = px.line(
        df,
        x="Day",
        y="Soil_Moisture_pct",
        title="Daily soil moisture",
    )

    st.plotly_chart(fig, width="stretch")

    st.subheader("Leaf Area Index")

    fig = px.line(
        df,
        x="Day",
        y="LAI",
        title="LAI development",
    )

    st.plotly_chart(fig, width="stretch")

    st.subheader("Daily simulation data")
    st.dataframe(df, width="stretch")

with tabs[1]:
    st.subheader("Soil-water balance")

    fig = px.line(
        df,
        x="Day",
        y=["ETc_mm", "ETa_mm", "Irrigation_mm"],
    )

    st.plotly_chart(fig, width="stretch")

    fig = px.line(
        df,
        x="Day",
        y=["Depletion_mm", "Drainage_mm"],
    )

    st.plotly_chart(fig, width="stretch")

    st.subheader("Root-zone storage and water-balance closure")
    storage_fig = px.line(
        df,
        x="Day",
        y=["Storage_Start_mm", "Storage_End_mm"],
        title="Root-zone water storage",
    )
    st.plotly_chart(storage_fig, width="stretch")
    residual_fig = px.line(
        df,
        x="Day",
        y="Water_Balance_Residual_mm",
        title="Daily water-balance residual (should be near zero)",
    )
    st.plotly_chart(residual_fig, width="stretch")
    st.metric(
        "Maximum absolute balance residual",
        f"{summary['Maximum_Absolute_Water_Balance_Residual_mm']:.8f} mm",
    )
    st.caption(
        "The residual is a numerical closure diagnostic for the simplified "
        "root-zone bucket, not evidence that the model matches field conditions."
    )

    st.json(summary)

with tabs[2]:
    st.subheader("Pepper phenology and crop growth")
    g1, g2, g3 = st.columns(3)
    g1.metric("Current simulated stage", str(summary["Final_Growth_Stage"]))
    g2.metric("Accumulated thermal time", f"{summary['Final_Cumulative_GDD_C_day']:.0f} °C·day")
    g3.metric("Final LAI", f"{summary['Final_LAI']:.2f}")

    fig = px.line(
        df,
        x="Day",
        y=["Leaf_Biomass_t_ha", "Stem_Biomass_t_ha", "Fruit_Dry_Biomass_t_ha"],
        title="Dry-matter partitioning among plant organs",
    )
    st.plotly_chart(fig, width="stretch")

    fig = px.line(
        df,
        x="Day",
        y="LAI",
        title="Leaf area index development",
    )
    st.plotly_chart(fig, width="stretch")

    fig = px.line(
        df,
        x="Day",
        y=["Cumulative_GDD_C_day"],
        title="Accumulated growing degree days",
    )
    st.plotly_chart(fig, width="stretch")

    fig = px.line(
        df,
        x="Day",
        y=[
            "Fraction_Intercepted_PAR", "Water_Stress_Factor",
            "Temperature_Response", "Salinity_Response_Factor",
        ],
        title="Radiation interception and growth constraints",
    )
    st.plotly_chart(fig, width="stretch")

    st.metric(
        "Illustrative fresh fruit yield",
        f"{summary['Illustrative_Fruit_Yield_t_ha']:.2f} t/ha",
    )
    st.warning(
        "Thermal thresholds, specific leaf area, RUE, dry-matter "
        "partitioning and fruit dry-matter fraction are prototype "
        "parameters. Yield is an illustrative model output, not a "
        "validated greenhouse prediction."
    )
    with st.expander("Daily crop growth state"):
        st.dataframe(
            df[[
                "Day", "Growth_Stage", "Cumulative_GDD_C_day",
                "PAR_MJ_m2", "Intercepted_PAR_MJ_m2",
                "Leaf_Biomass_t_ha", "Stem_Biomass_t_ha",
                "Fruit_Dry_Biomass_t_ha", "LAI",
            ]],
            width="stretch",
        )

with tabs[3]:
    st.subheader("Irrigation and fertilizer scenarios")
    st.info(
        "The factorial scenario matrix compares fixed ETc irrigation "
        "fractions. The soil-moisture-trigger strategy is evaluated in "
        "the main daily simulation above."
    )

    irrigation_options = st.multiselect(
        "Irrigation levels",
        [60, 75, 90, 100, 105],
        default=[75, 90, 105],
    )

    fertilizer_options = st.multiselect(
        "Fertilizer levels",
        [25, 50, 75, 100],
        default=[50, 75, 100],
    )

    if st.button("Compare scenarios"):
        scenarios = compare_scenarios(
            params,
            weather,
            irrigation_options,
            fertilizer_options,
        )

        st.session_state.scenarios = scenarios

    if "scenarios" in st.session_state:
        sc = st.session_state.scenarios

        st.dataframe(sc, width="stretch")

        fig = px.scatter(
            sc,
            x="Irrigation_Total_mm",
            y="Simulated_Biomass_t_ha",
            color="Fertilizer_pct",
            size="Final_LAI",
        )

        st.plotly_chart(fig, width="stretch")

with tabs[4]:
    st.subheader("Pretrained Artificial Intelligence")

    if (
        PRETRAINED_MODEL_PATH.exists()
        and PRETRAINED_REPORT_PATH.exists()
    ):
        report = json.loads(
            PRETRAINED_REPORT_PATH.read_text(
                encoding="utf-8"
            )
        )

        st.success(
            f"AI model available: "
            f"{report['total_scenarios']:,} scenarios"
        )

        st.warning(
            "This model was trained on simulated data. "
            "It predicts simulator-equivalent outputs, "
            "not independently validated real crop measurements."
        )

        metrics_df = pd.DataFrame(
            report["metrics_by_target"]
        ).T.reset_index(names="Predicted variable")

        st.subheader("AI performance")
        st.dataframe(metrics_df, width="stretch")

        if st.button(
            "Predict crop growth using AI",
            type="primary",
        ):
            source = (
                weather
                if weather is not None
                else result["daily"]
            )

            features = pd.DataFrame([{
                "Days": params["days"],
                "Irrigation_pct": params["irrigation_pct"],
                "Fertilizer_pct": params["fertilizer_pct"],
                "Field_Capacity_pct": params["fc"] * 100,
                "Wilting_Point_pct": params["wp"] * 100,
                "Root_Depth_m": params["root_depth_m"],
                "Initial_Moisture_pct": params["initial_theta"] * 100,
                "Irrigation_Efficiency_pct": (
                    params["irrigation_efficiency"] * 100
                ),
                "Initial_LAI": params["initial_lai"],
                "Initial_Biomass_t_ha": (
                    params["initial_biomass_t_ha"]
                ),
                "Mean_Temperature_C": (
                    source["Temperature_C"].mean()
                ),
                "Mean_ETo_mm": source["ETo_mm"].mean(),
                "Mean_Solar_MJ_m2": (
                    source["Solar_MJ_m2"].mean()
                ),
                "Plant_Density": params["plant_density"],
            }])

            prediction = predict_with_pretrained_model(
                features
            )

            st.subheader("AI prediction")
            st.dataframe(
                prediction,
                width="stretch",
            )

            st.caption(
                "These predictions approximate the simulator "
                "and are not validated field predictions."
            )

        with st.expander("View AI training data"):
            if PRETRAINED_DATA_PATH.exists():
                training_data = pd.read_csv(
                    PRETRAINED_DATA_PATH
                )

                st.write(
                    f"Training dataset: "
                    f"{len(training_data):,} rows"
                )

                st.dataframe(
                    training_data.head(30),
                    width="stretch",
                )

                st.download_button(
                    "Download training data",
                    training_data.to_csv(
                        index=False
                    ).encode("utf-8-sig"),
                    file_name="AI_SIMULATED_TRAINING_DATA.csv",
                    mime="text/csv",
                )

    else:
        st.error(
            "AI model files are missing. "
            "The model files must be uploaded with the project."
        )

    st.divider()
    st.subheader("Literature-trained model")

    literature_report_path = (
        Path(__file__).parent / "LITERATURE_AI_REPORT.json"
    )

    if (
        LITERATURE_MODEL_PATH.exists()
        and literature_report_path.exists()
    ):
        literature_report = json.loads(
            literature_report_path.read_text(
                encoding="utf-8"
            )
        )

        st.success(
            "Literature model is available."
        )

        st.json(literature_report)

    else:
        st.warning(
            "Literature model report or model file is missing."
        )

    st.divider()
    st.subheader("Train with future experimental data")

    st.write(
        "Upload plot-level experimental measurements "
        "when available. Do not label simulated data as field data."
    )

    st.code(
        "Plot_ID,Season,Mechanistic_Biomass_t_ha,"
        "Mean_LAI,Seasonal_ETa_mm,Mean_Temperature_C,"
        "Measured_Biomass_t_ha"
    )

    ai_file = st.file_uploader(
        "Upload experimental CSV",
        type=["csv"],
        key="ai_upload",
    )

    if ai_file is not None:
        ai_data = pd.read_csv(ai_file)

        st.dataframe(ai_data.head(10))

        if st.button("Train experimental correction"):
            try:
                report_exp = train_residual_model(ai_data)

                st.success("Experimental model training completed.")

                st.write(report_exp)

            except Exception as exc:
                st.error(str(exc))

with tabs[5]:
    st.subheader("Published literature data")

    literature_path = (
        Path(__file__).parent
        / "LITERATURE_TREATMENT_DATA.csv"
    )

    provenance_path = (
        Path(__file__).parent
        / "PARAMETER_PROVENANCE.csv"
    )

    if literature_path.exists():
        literature = pd.read_csv(literature_path)
        st.dataframe(
            literature,
            width="stretch",
        )
    else:
        st.warning("Literature data file is missing.")

    if provenance_path.exists():
        provenance = pd.read_csv(provenance_path)

        st.subheader("Parameter sources")
        st.dataframe(
            provenance,
            width="stretch",
        )

with tabs[6]:
    st.subheader("Export simulation results")

    st.download_button(
        "Download daily simulation CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="pepper_digital_twin_simulation.csv",
        mime="text/csv",
    )

    st.subheader("Experimental data template")

    columns = [
        "Season",
        "Plot_ID",
        "Treatment",
        "Date",
        "DAT",
        "Temperature_C",
        "RH_pct",
        "Solar_MJ_m2",
        "ETo_mm",
        "Soil_Moisture_pct",
        "Irrigation_mm",
        "Fertilizer_N_kg_ha",
        "Fertilizer_P_kg_ha",
        "Fertilizer_K_kg_ha",
        "EC_dS_m",
        "pH",
        "LAI",
        "Plant_Height_cm",
        "Measured_Biomass_t_ha",
        "Fruit_Number_per_Plant",
        "Mean_Fruit_Weight_g",
        "Marketable_Yield_t_ha",
    ]

    template = pd.DataFrame(columns=columns)

    st.download_button(
        "Download experimental template",
        template.to_csv(index=False).encode("utf-8-sig"),
        file_name="pepper_experimental_template.csv",
        mime="text/csv",
    )

with tabs[7]:
    st.subheader("Scientific notes and limitations")

    st.markdown("""
- Weather data are literature-based or assumed.
- Soil-water balance uses a simplified root-zone bucket.
- Crop growth parameters require calibration.
- Nutrient response is a simplified proxy.
- Fruit yield is not independently validated.
- AI was pretrained on simulated scenarios.
- Literature model uses published treatment means.
- Real greenhouse data are needed for independent validation.
- Repeated readings from one plot are not independent replicates.
""")

    st.info(
        "This is a research prototype, not a certified "
        "irrigation or fertigation controller."
    )

st.divider()

st.caption(
    "Pepper Greenhouse Digital Twin | Research prototype"
)
