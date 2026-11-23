
import streamlit as st

st.set_page_config(
    page_title="Pepper Digital Twin",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Pepper Digital Twin")
st.subheader("Soil Water Balance Model")

st.header("1. Initial Conditions")

soil_moisture = st.slider(
    "Initial Soil Moisture (%)",
    10, 50, 28
)

irrigation_time = st.slider(
    "Irrigation Duration (minutes)",
    0, 60, 10
)

simulation_time = st.slider(
    "Simulation Period (minutes)",
    0, 180, 60
)

st.header("2. Model Parameters")

soil_volume = 20.0
water_flow = 6.0
crop_water_uptake = 0.02

initial_water = (
    soil_volume * soil_moisture / 100
)

water_added = (
    water_flow * irrigation_time / 60
)

water_consumed = (
    crop_water_uptake * simulation_time
)

final_water = (
    initial_water + water_added - water_consumed
)

final_moisture = (
    final_water / soil_volume * 100
)

st.header("3. Simulation Results")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Water Added", f"{water_added:.2f} L")

with col2:
    st.metric("Water Uptake", f"{water_consumed:.2f} L")

with col3:
    st.metric(
        "Final Soil Moisture",
        f"{final_moisture:.2f}%"
    )

st.write("### Water Balance")

st.write(f"Initial water: {initial_water:.2f} L")
st.write(f"Added water: {water_added:.2f} L")
st.write(f"Consumed water: {water_consumed:.2f} L")
st.write(f"Final water: {final_water:.2f} L")

st.caption(
    "Educational model with assumed water uptake. "
    "No drainage or water redistribution is included."
)
