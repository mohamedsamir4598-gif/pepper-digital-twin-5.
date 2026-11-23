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

    irrigation_pct = st.select_slider(
        "Irrigation (% ETc)",
        options=[60, 75, 90, 100, 105],
        value=90,
    )

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

if wp >= fc:
    st.error("Wilting point must be lower than field capacity.")
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

params = {
    "days": crop_days,
    "fc": fc,
    "wp": wp,
    "root_depth_m": root_depth,
    "initial_theta": initial_theta,
    "irrigation_pct": irrigation_pct,
    "fertilizer_pct": fertilizer_pct,
    "irrigation_efficiency": irrigation_eff,
    "initial_lai": initial_lai,
    "initial_biomass_t_ha": initial_biomass,
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
        use_container_width=True,
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

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Leaf Area Index")

    fig = px.line(
        df,
        x="Day",
        y="LAI",
        title="LAI development",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Daily simulation data")
    st.dataframe(df, use_container_width=True)

with tabs[1]:
    st.subheader("Soil-water balance")

    fig = px.line(
        df,
        x="Day",
        y=["ETc_mm", "ETa_mm", "Irrigation_mm"],
    )

    st.plotly_chart(fig, use_container_width=True)

    fig = px.line(
        df,
        x="Day",
        y=["Depletion_mm", "Drainage_mm"],
    )

    st.plotly_chart(fig, use_container_width=True)

    st.json(summary)

with tabs[2]:
    st.subheader("Crop growth")

    fig = px.line(
        df,
        x="Day",
        y="Biomass_t_ha",
        title="Biomass development",
    )

    st.plotly_chart(fig, use_container_width=True)

    fig = px.line(
        df,
        x="Day",
        y=["Ks", "Nutrient_Factor"],
    )

    st.plotly_chart(fig, use_container_width=True)

    st.metric(
        "Illustrative fruit yield",
        f"{summary['Illustrative_Fruit_Yield_t_ha']:.2f} t/ha",
    )

    st.warning(
        "Fruit yield is currently an illustrative estimate, "
        "not a validated prediction."
    )

with tabs[3]:
    st.subheader("Irrigation and fertilizer scenarios")

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

        st.dataframe(sc, use_container_width=True)

        fig = px.scatter(
            sc,
            x="Irrigation_Total_mm",
            y="Simulated_Biomass_t_ha",
            color="Fertilizer_pct",
            size="Final_LAI",
        )

        st.plotly_chart(fig, use_container_width=True)

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
        st.dataframe(metrics_df, use_container_width=True)

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
                use_container_width=True,
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
                    use_container_width=True,
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
            use_container_width=True,
        )
    else:
        st.warning("Literature data file is missing.")

    if provenance_path.exists():
        provenance = pd.read_csv(provenance_path)

        st.subheader("Parameter sources")
        st.dataframe(
            provenance,
            use_container_width=True,
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
