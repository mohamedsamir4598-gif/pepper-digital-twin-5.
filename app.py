
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

st.header("2. Irrigation Optimization")

target_min = 28.0
target_max = 30.0

soil_volume = 20.0
water_flow = 6.0

best_scenario = None
scenarios = []

for duration in range(61):

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
        )
    })

    if (
        best_scenario is None
        and target_min <= predicted_moisture <= target_max
    ):
        best_scenario = {
            "duration": duration,
            "water": water_added,
            "moisture": predicted_moisture
        }

st.subheader("Tested Irrigation Scenarios")

st.dataframe(
    scenarios,
    use_container_width=True,
    hide_index=True
)

st.divider()

st.header("3. Intelligent Irrigation Decision")

if best_scenario is not None:

    st.success("Suitable irrigation scenario found!")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Recommended Duration",
            f"{best_scenario['duration']} min"
        )

    with col2:
        st.metric(
            "Water Required",
            f"{best_scenario['water']:.2f} L"
        )

    with col3:
        st.metric(
            "Predicted Moisture",
            f"{best_scenario['moisture']:.2f}%"
        )

else:
    st.warning(
        "No suitable scenario found within 60 minutes."
    )

st.caption(
    "Educational model using assumed parameters. "
    "Real sensor calibration and field validation are required."
)
