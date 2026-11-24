
import numpy as np
import pandas as pd

REQUIRED_WEATHER_COLUMNS = [
    "Day", "ETo_mm", "Temperature_C",
    "RH_pct", "Solar_MJ_m2", "Rain_mm"
]


def make_literature_weather(days):
    day = np.arange(1, days + 1)

    stage1 = max(1, round(days * 35 / 300))
    stage2 = max(stage1 + 1, round(days * 270 / 300))

    eto = np.where(
        day <= stage1, 5.6,
        np.where(day <= stage2, 3.5, 5.6)
    )

    temp = (
        24.6
        + 1.5 * np.sin(2 * np.pi * day / 17)
        + 0.6 * np.sin(2 * np.pi * day / 43)
    )

    rh = np.clip(
        50.2 + 1.4 * np.sin(2 * np.pi * (day + 4) / 19),
        35, 70
    )

    solar = (
        15.5
        + 2.0 * np.sin(2 * np.pi * (day - 8) / max(days, 1))
    )

    rain = np.zeros(days)

    return pd.DataFrame({
        "Day": day,
        "ETo_mm": eto,
        "Temperature_C": temp,
        "RH_pct": rh,
        "Solar_MJ_m2": solar,
        "Rain_mm": rain
    })


def make_demo_weather(days):
    return make_literature_weather(days)


def _crop_coefficient(day, days):
    stage1 = max(1, round(days * 35 / 300))
    stage2 = max(stage1 + 1, round(days * 270 / 300))

    if day <= stage1:
        return 0.65
    elif day <= stage2:
        return 1.00
    return 0.95


def simulate_crop(params, weather=None):

    days = int(params["days"])

    if weather is None:
        w = make_literature_weather(days)
    else:
        w = weather.copy().reset_index(drop=True)

    if len(w) != days:
        days = len(w)

    for col in REQUIRED_WEATHER_COLUMNS:
        if col not in w.columns:
            raise ValueError(f"Missing weather column: {col}")

    if (w["ETo_mm"] < 0).any():
        raise ValueError("ETo must be non-negative.")

    if (w["Rain_mm"] < 0).any():
        raise ValueError("Rainfall must be non-negative.")

    fc = float(params["fc"])
    wp = float(params["wp"])
    zr = float(params["root_depth_m"])

    taw = max(1.0, 1000 * (fc - wp) * zr)

    depletion_fraction = float(
        params.get("depletion_fraction", 0.40)
    )

    storage = np.clip(
        float(params["initial_theta"]), wp, fc
    )

    storage_mm = (storage - wp) * 1000 * zr
    storage_mm = float(np.clip(storage_mm, 0, taw))

    lai = float(params["initial_lai"])
    biomass = float(params["initial_biomass_t_ha"])

    irrigation_target = float(params["irrigation_pct"]) / 100
    fert_pct = float(params["fertilizer_pct"])
    efficiency = float(params["irrigation_efficiency"])

    rows = []

    for i, row in w.iterrows():

        day = int(row["Day"]) if pd.notna(row["Day"]) else i + 1

        eto = float(row["ETo_mm"])
        temp = float(row["Temperature_C"])
        solar = float(row["Solar_MJ_m2"])
        rain = float(row["Rain_mm"])

        kc = _crop_coefficient(day, days)
        etc = eto * kc

        gross_irrigation = (
            etc * irrigation_target / max(efficiency, 0.01)
        )

        effective_irrigation = gross_irrigation * efficiency

        storage_mm += rain + effective_irrigation

        drainage = max(0.0, storage_mm - taw)
        storage_mm = min(storage_mm, taw)

        depletion = taw - storage_mm
        raw = depletion_fraction * taw

        if depletion <= raw:
            ks = 1.0
        else:
            ks = max(
                0.0,
                (taw - depletion) / max(taw - raw, 1e-6)
            )

        eta = min(etc * ks, storage_mm)
        storage_mm -= eta

        theta = wp + storage_mm / (1000 * zr)
        theta = float(np.clip(theta, wp, fc))

        depletion_after = taw - storage_mm

        nutrient_factor = float(
            np.clip(0.65 + 0.35 * fert_pct / 100, 0.45, 1.0)
        )

        temp_factor = float(
            np.clip(
                1 - (abs(temp - 24) / 20) ** 1.5,
                0.25, 1.0
            )
        )

        water_factor = float(np.clip(ks, 0, 1))

        intercepted_par = (
            0.48 * solar * (1 - np.exp(-0.65 * max(lai, 0.01)))
        )

        rue = float(params.get("rue_g_mj", 2.2))

        delta_biomass = (
            rue * intercepted_par * temp_factor
            * water_factor * nutrient_factor * 0.01
        )

        biomass += max(0.0, delta_biomass)

        lai_growth = (
            0.035 * temp_factor * water_factor
            * nutrient_factor * (1 - lai / 4.0)
        )

        lai = float(np.clip(lai + lai_growth, 0.05, 5.0))

        rows.append({
            "Day": day,
            "Temperature_C": temp,
            "RH_pct": float(row["RH_pct"]),
            "Solar_MJ_m2": solar,
            "ETo_mm": eto,
            "Kc": kc,
            "ETc_mm": etc,
            "ETa_mm": eta,
            "Rain_mm": rain,
            "Gross_Irrigation_mm": gross_irrigation,
            "Irrigation_mm": effective_irrigation,
            "Drainage_mm": drainage,
            "Depletion_mm": depletion_after,
            "Soil_Moisture_pct": theta * 100,
            "Ks": ks,
            "Nutrient_Factor": nutrient_factor,
            "LAI": lai,
            "Biomass_t_ha": biomass
        })

    daily = pd.DataFrame(rows)

    harvest_index = 0.35
    estimated_yield = max(0.0, biomass * harvest_index)

    total_irrigation = float(daily["Irrigation_mm"].sum())

    water_productivity = (
        estimated_yield * 1000 / total_irrigation
        if total_irrigation > 0 else 0.0
    )

    summary = {
        "TAW_mm": taw,
        "RAW_mm": depletion_fraction * taw,
        "Seasonal_ETc_mm": float(daily["ETc_mm"].sum()),
        "Seasonal_ETa_mm": float(daily["ETa_mm"].sum()),
        "Total_Effective_Irrigation_mm": total_irrigation,
        "Total_Gross_Irrigation_mm": float(
            daily["Gross_Irrigation_mm"].sum()
        ),
        "Total_Drainage_mm": float(daily["Drainage_mm"].sum()),
        "Final_Soil_Moisture_pct": float(
            daily["Soil_Moisture_pct"].iloc[-1]
        ),
        "Final_LAI": float(daily["LAI"].iloc[-1]),
        "Final_Biomass_t_ha": float(
            daily["Biomass_t_ha"].iloc[-1]
        ),
        "Illustrative_Harvest_Index": harvest_index,
        "Illustrative_Fruit_Yield_t_ha": estimated_yield,
        "Illustrative_Water_Productivity_kg_m3": water_productivity,
        "Weather_Provenance": (
            "Literature-based scenario with assumed daily variation"
        )
    }

    return {
        "daily": daily,
        "summary": summary
    }


def compare_scenarios(
    base_params,
    weather,
    irrigation_levels,
    fertilizer_levels
):

    records = []

    for irrigation in irrigation_levels:
        for fertilizer in fertilizer_levels:

            p = dict(base_params)

            p["irrigation_pct"] = irrigation
            p["fertilizer_pct"] = fertilizer

            result = simulate_crop(p, weather)
            s = result["summary"]

            records.append({
                "Irrigation_pct": irrigation,
                "Fertilizer_pct": fertilizer,
                "Irrigation_Total_mm": (
                    s["Total_Effective_Irrigation_mm"]
                ),
                "ETa_Total_mm": s["Seasonal_ETa_mm"],
                "Final_LAI": s["Final_LAI"],
                "Simulated_Biomass_t_ha": (
                    s["Final_Biomass_t_ha"]
                ),
                "Illustrative_Fruit_Yield_t_ha": (
                    s["Illustrative_Fruit_Yield_t_ha"]
                ),
                "Water_Productivity_kg_m3": (
                    s["Illustrative_Water_Productivity_kg_m3"]
                )
            })

    return pd.DataFrame(records)
