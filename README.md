
import streamlit as st

st.set_page_config(
    page_title="Pepper Digital Twin",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Pepper Digital Twin")
st.subheader("Smart Irrigation and Fertigation System")

st.info("Welcome to your Smart Agriculture Dashboard")

st.header("Current Soil Conditions")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Soil Moisture", "24 %")

with col2:
    st.metric("Soil Temperature", "25 °C")

with col3:
    st.metric("Valve Status", "CLOSED")

st.divider()

st.header("💧 Irrigation Simulation")

soil_moisture = st.slider(
    "Current Soil Moisture (%)",
    min_value=10,
    max_value=50,
    value=24
)

irrigation_time = st.slider(
    "Irrigation Duration (minutes)",
    min_value=0,
    max_value=60,
    value=15
)

if st.button("Run Digital Twin Simulation"):

    soil_volume = 20.0
    water_flow = 6.0

    water_added = water_flow * irrigation_time / 60

    predicted_moisture = (
        soil_moisture + water_added / soil_volume * 100
    )

    st.success("Simulation Completed!")

    st.metric(
        "Predicted Soil Moisture",
        f"{predicted_moisture:.2f} %"
    )

    st.metric(
        "Water Added",
        f"{water_added:.2f} Liter"
    )
# pepper-digital-twin-5.
