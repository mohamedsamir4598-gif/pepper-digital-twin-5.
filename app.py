
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Pepper Digital Twin",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Pepper Digital Twin")
st.subheader("Hybrid Irrigation and Fertigation Management")

st.info("Prototype simulation - using assumed educational parameters.")

# 1. INPUT DATA
st.header("1. Greenhouse Measurements")

c1, c2, c3 = st.columns(3)

with c1:
    moisture = st.number_input(
        "Soil Moisture (%)", 10.0, 50.0, 24.0
    )

with c2:
    ec = st.number_input(
        "Root Zone EC (dS/m)", 0.1, 5.0, 1.5
    )

with c3:
    ph = st.number_input(
        "Solution pH", 3.0, 10.0, 6.0
    )

temperature = st.slider(
    "Air Temperature (°C)", 10, 45, 28
)

st.divider()

# 2. MODEL PARAMETERS
st.header("2. Crop and Model Parameters")

target_moisture = st.slider(
    "Target Soil Moisture (%)", 20, 40, 30
)

soil_volume = 20.0
water_flow = 6.0

# Illustrative nutrient requirements (mg)
required_n = 100.0
required_p = 20.0
required_k = 120.0

# Illustrative water uptake
water_uptake = 0.02

# 3. SCENARIO GENERATION
st.header("3. Scenario Simulation")

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

        nutrient_ok = (
            n_added >= required_n
            and p_added >= required_p
            and k_added >= required_k
        )

        moisture_ok = (
            predicted_moisture >= target_moisture
            and predicted_moisture <= 35
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
            "N (mg)": round(n_added, 1),
            "P (mg)": round(p_added, 1),
            "K (mg)": round(k_added, 1),
            "Predicted Moisture (%)": round(
                predicted_moisture, 2
            ),
            "Suitable": suitable
        })

df = pd.DataFrame(scenarios)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)

# 4. OPTIMIZATION
st.divider()
st.header("4. Optimal Scenario Selection")

suitable = df[df["Suitable"] == True]

if not suitable.empty:

    best = suitable.sort_values(
        by=["Water (L)", "N (mg)", "K (mg)"]
    ).iloc[0]

    st.success("Suitable scenario identified!")

    a, b, c = st.columns(3)

    a.metric(
        "Irrigation Time",
        f"{int(best['Irrigation (min)'])} min"
    )

    b.metric(
        "Water Requirement",
        f"{best['Water (L)']} L"
    )

    c.metric(
        "Predicted Moisture",
        f"{best['Predicted Moisture (%)']}%"
    )

    st.subheader("Recommended Fertilizer Doses")

    x, y, z = st.columns(3)

    x.metric("Nitrogen N", f"{best['N (mg)']} mg")
    y.metric("Phosphorus P", f"{best['P (mg)']} mg")
    z.metric("Potassium K", f"{best['K (mg)']} mg")

    st.warning(
        "This is a simulated recommendation, not a real fertilizer prescription."
    )

else:

    st.error(
        "No suitable scenario found. "
        "Review the input conditions or expand the tested scenarios."
    )

# 5. EC AND PH MONITORING
st.divider()
st.header("5. Solution Quality Monitoring")

col1, col2 = st.columns(2)

with col1:
    if ec <= 2.5:
        st.success(f"EC reading: {ec} dS/m")
    else:
        st.error("EC exceeds the illustrative model limit.")

with col2:
    if 5.5 <= ph <= 6.5:
        st.success(f"pH reading: {ph}")
    else:
        st.warning("pH is outside the illustrative target range.")

# 6. WATER UPTAKE
st.divider()
st.header("6. Crop Water Uptake")

simulation_hours = st.slider(
    "Prediction Horizon (hours)",
    1, 24, 6
)

predicted_water_uptake = (
    water_uptake * simulation_hours * 60
)

st.metric(
    "Estimated Crop Water Uptake",
    f"{predicted_water_uptake:.2f} L"
)

st.caption(
  "Research prototype: values are illustrative only."
    )
# AI MODEL - FIRST MACHINE LEARNING MODEL

from sklearn.ensemble import RandomForestRegressor

# Training data
data = {
    "temperature": [20, 25, 30, 35, 40, 22, 28, 33, 38, 26],
    "initial_moisture": [30, 28, 25, 22, 20, 32, 27, 24, 21, 29],
    "irrigation_minutes": [0, 5, 10, 15, 20, 0, 10, 15, 20, 5],
    "final_moisture": [29, 29, 29, 29, 29, 31, 31, 30, 30, 30]
}

import pandas as pd

df_ai = pd.DataFrame(data)

# Inputs and target
X = df_ai[
    ["temperature", "initial_moisture", "irrigation_minutes"]
]

y = df_ai["final_moisture"]

# Create and train AI model
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

model.fit(X, y)

# Make a prediction
new_data = pd.DataFrame([{
    "temperature": 30,
    "initial_moisture": 24,
    "irrigation_minutes": 10
}])

prediction = model.predict(new_data)

st.header("AI Prediction")

st.metric(
    "Predicted Soil Moisture",
    f"{prediction[0]:.2f}%"
)

    "Research prototype: nutrient requirements, "
    "water uptake, EC limits and pH limits are assumed values. "
    "They must be replaced with calibrated crop-specific models "
    "and experimental measurements before real operation."
)
