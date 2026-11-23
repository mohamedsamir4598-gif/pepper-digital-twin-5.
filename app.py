
import streamlit as st

st.set_page_config(
    page_title="Pepper Digital Twin",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Pepper Digital Twin")
st.subheader("Smart Irrigation Decision Engine")

st.header("1. Current Soil Conditions")

soil_moisture = st.slider(
    "Current Soil Moisture (%)",
    10, 50, 24
)

col1, col2 = st.columns(2)

with col1:
    st.metric("Current Soil Moisture", f"{soil_moisture}%")

with col2:
    st.metric("Valve Status", "CLOSED")

st.divider()

st.header("2. Irrigation Scenarios")

target_min = 28.0
target_max = 30.0

st.write("Target soil moisture range: 28–30%")

soil_volume = 20.0
water_flow = 6.0

durations = [10, 15, 20]
scenarios = []

for duration in durations:

    water_added = water_flow * duration / 60

    predicted_moisture = (
        soil_moisture +
        (water_added / soil_volume) * 100
    )

    scenarios.append({
        "Duration (min)": duration,
        "Water Added (L)": round(water_added, 2),
        "Predicted Moisture (%)": round(
            predicted_moisture, 2
        ),
        "Suitable": (
            target_min <= predicted_moisture <= target_max
        )
    })

st.dataframe(
    scenarios,
    use_container_width=True,
    hide_index=True
)

st.divider()

st.header("3. Intelligent Decision")

suitable_scenarios = [
    scenario for scenario in scenarios
    if scenario["Suitable"]
]

if suitable_scenarios:

    best_scenario = min(
        suitable_scenarios,
        key=lambda x: x["Duration (min)"]
    )

    st.success("Suitable irrigation scenario found!")

    st.metric(
        "Recommended Irrigation Time",
        f"{best_scenario['Duration (min)']} minutes"
    )

    st.metric(
        "Expected Soil Moisture",
        f"{best_scenario['Predicted Moisture (%)']}%"
    )

    st.metric(
        "Water Requirement",
        f"{best_scenario['Water Added (L)']} Liter"
    )

else:

    st.warning(
        "No tested scenario reaches the target moisture range."
    )

    st.write(
        "The system needs to test additional irrigation durations."
    )

st.caption(
    "Educational simulation using assumed soil volume and water flow. "
    "Not yet calibrated with real sensor measurements."
)
