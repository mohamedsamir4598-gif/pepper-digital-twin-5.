
st.header("Automatic Irrigation Optimization")

target_min = 28.0
target_max = 30.0

soil_volume = 20.0
water_flow = 6.0

best_scenario = None

for duration in range(61):

    water_added = water_flow * duration / 60

    predicted_moisture = (
        soil_moisture +
        (water_added / soil_volume) * 100
    )

    if target_min <= predicted_moisture <= target_max:

        best_scenario = {
            "duration": duration,
            "water": water_added,
            "moisture": predicted_moisture
        }

        break

if best_scenario is not None:

    st.success("Optimal scenario found!")

    st.metric(
        "Recommended Duration",
        f"{best_scenario['duration']} minutes"
    )

    st.metric(
        "Water Required",
        f"{best_scenario['water']:.2f} L"
    )

    st.metric(
        "Predicted Moisture",
        f"{best_scenario['moisture']:.2f}%"
    )

else:
    st.warning("No suitable scenario found.")
