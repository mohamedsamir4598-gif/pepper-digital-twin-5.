
import streamlit as st
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# =====================================
# 1. PAGE SETTINGS
# =====================================

st.set_page_config(
    page_title="Pepper Digital Twin",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Pepper Digital Twin")
st.subheader("AI-Based Irrigation and Fertigation Management")

st.info(
    "Educational research prototype. "
    "All model training data and crop parameters are illustrative."
)

# =====================================
# 2. GREENHOUSE INPUTS
# =====================================

st.header("1. Greenhouse Measurements")

col1, col2 = st.columns(2)

with col1:
    temperature = st.number_input(
        "Air Temperature (°C)",
        min_value=10.0,
        max_value=45.0,
        value=30.0
    )

    moisture = st.number_input(
        "Initial Soil Moisture (%)",
        min_value=10.0,
        max_value=50.0,
        value=24.0
    )

with col2:
    ec = st.number_input(
        "Root Zone EC (dS/m)",
        min_value=0.1,
        max_value=5.0,
        value=1.5
    )

    ph = st.number_input(
        "Solution pH",
        min_value=3.0,
        max_value=10.0,
        value=6.0
    )

st.divider()

# =====================================
# 3. MODEL PARAMETERS
# =====================================

st.header("2. Crop and Irrigation Parameters")

col1, col2 = st.columns(2)

with col1:
    target_moisture = st.slider(
        "Target Soil Moisture (%)",
        min_value=20,
        max_value=40,
        value=30
    )

with col2:
    simulation_hours = st.slider(
        "Prediction Horizon (hours)",
        min_value=1,
        max_value=24,
        value=6
    )

soil_volume = 20.0
water_flow = 6.0

# Illustrative nutrient requirements (mg)
required_n = 100.0
required_p = 20.0
required_k = 120.0

# =====================================
# 4. MACHINE LEARNING MODEL
# =====================================

st.divider()
st.header("3. Artificial Intelligence Model")

# Illustrative training data
training_data = {
    "temperature": [
        20, 25, 30, 35, 40,
        22, 28, 33, 38, 26,
        24, 32, 36, 29, 21
    ],

    "initial_moisture": [
        30, 28, 25, 22, 20,
        32, 27, 24, 21, 29,
        26, 23, 20, 31, 33
    ],

    "irrigation_minutes": [
        0, 5, 10, 15, 20,
        0, 10, 15, 20, 5,
        10, 15, 20, 0, 5
    ],

    "final_moisture": [
        29, 29, 29, 29, 29,
        31, 31, 30, 30, 30,
        29, 29, 28, 30, 32
    ]
}

df_training = pd.DataFrame(training_data)

X = df_training[
    [
        "temperature",
        "initial_moisture",
        "irrigation_minutes"
    ]
]

y = df_training["final_moisture"]

# Create and train the model
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

model.fit(X, y)

st.success("Machine Learning model trained successfully.")

# =====================================
# 5. AI PREDICTION
# =====================================

st.subheader("AI Soil Moisture Prediction")

prediction_data = pd.DataFrame([
    {
        "temperature": temperature,
        "initial_moisture": moisture,
        "irrigation_minutes": 10
    }
])

ai_prediction = model.predict(prediction_data)[0]

st.metric(
    "Predicted Soil Moisture after 10 minutes of irrigation",
    f"{ai_prediction:.2f}%"
)

# =====================================
# 6. IRRIGATION SCENARIOS
# =====================================

st.divider()
st.header("4. Irrigation Scenario Simulation")

irrigation_options = [5, 10, 15, 20, 25, 30]
fertilizer_options = [0.8, 1.0, 1.2]

scenarios = []

initial_water = soil_volume * moisture / 100

for irrigation_time in irrigation_options:

    water_added = water_flow * irrigation_time / 60

    predicted_moisture = (
        initial_water + water_added
    ) / soil_volume * 100

    for fertilizer_rate in fertilizer_options:

        n_added = required_n * fertilizer_rate
        p_added = required_p * fertilizer_rate
        k_added = required_k * fertilizer_rate

        moisture_ok = (
            predicted_moisture >= target_moisture
            and predicted_moisture <= 35
        )

        nutrient_ok = (
            n_added >= required_n
            and p_added >= required_p
            and k_added >= required_k
        )

        ec_ok = ec <= 2.5
        ph_ok = 5.5 <= ph <= 6.5

        suitable = (
            moisture_ok
            and nutrient_ok
            and ec_ok
            and ph_ok
        )

        scenarios.append({
            "Irrigation (min)": irrigation_time,
            "Water (L)": round(water_added, 2),
            "Fertilizer Rate": fertilizer_rate,
            "N (mg)": round(n_added, 1),
            "P (mg)": round(p_added, 1),
            "K (mg)": round(k_added, 1),
            "Predicted Moisture (%)": round(
                predicted_moisture, 2
            ),
            "Suitable": suitable
        })

df_scenarios = pd.DataFrame(scenarios)

st.dataframe(
    df_scenarios,
    use_container_width=True,
    hide_index=True
)

# =====================================
# 7. OPTIMAL SCENARIO
# =====================================

st.divider()
st.header("5. Best Suitable Scenario")

suitable_scenarios = df_scenarios[
    df_scenarios["Suitable"] == True
]

if not suitable_scenarios.empty:

    best = suitable_scenarios.sort_values(
        by=["Water (L)", "N (mg)", "K (mg)"]
    ).iloc[0]

    st.success("A suitable scenario was identified.")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Irrigation Time",
        f"{int(best['Irrigation (min)'])} min"
    )

    col2.metric(
        "Water Added",
        f"{best['Water (L)']} L"
    )

    col3.metric(
        "Predicted Moisture",
        f"{best['Predicted Moisture (%)']}%"
    )

    st.subheader("Illustrative Nutrient Doses")

    col1, col2, col3 = st.columns(3)

    col1.metric("Nitrogen (N)", f"{best['N (mg)']} mg")
    col2.metric("Phosphorus (P)", f"{best['P (mg)']} mg")
    col3.metric("Potassium (K)", f"{best['K (mg)']} mg")

else:

    st.warning(
        "No suitable scenario was found. "
        "Review the input measurements and target conditions."
    )

# =====================================
# 8. EC AND PH MONITORING
# =====================================

st.divider()
st.header("6. Nutrient Solution Monitoring")

col1, col2 = st.columns(2)

with col1:

    if ec <= 2.5:
        st.success(f"EC = {ec} dS/m")
    else:
        st.error("EC is above the illustrative model limit.")

with col2:

    if 5.5 <= ph <= 6.5:
        st.success(f"pH = {ph}")
    else:
        st.warning("pH is outside the illustrative target range.")

# =====================================
# 9. WATER UPTAKE ESTIMATION
# =====================================

st.divider()
st.header("7. Crop Water Uptake")

illustrative_water_uptake = 0.02

predicted_water_uptake = (
    illustrative_water_uptake * simulation_hours * 60
)

st.metric(
    "Illustrative Water Uptake",
    f"{predicted_water_uptake:.2f} L"
)

# =====================================
# 10. SCIENTIFIC LIMITATIONS
# =====================================

st.divider()

st.caption(
    "Research prototype: the AI model uses illustrative training data. "
    "Irrigation and fertilizer calculations are simplified. "
    "Real greenhouse measurements, crop-specific calibration, "
    "independent validation and experimental data are required "
    "before using this system for actual irrigation or fertigation."
)
