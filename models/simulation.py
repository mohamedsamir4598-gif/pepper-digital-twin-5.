
import numpy as np
import pandas as pd

from models.crop_growth import simulate_pepper_growth

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
    """Run a daily root-zone bucket simulation.

    Irrigation strategies:
      - fixed_etc: gross irrigation is a selected fraction of ETc.
      - soil_moisture_trigger: irrigate only when depletion exceeds a
        fraction of total available water, then refill to a target fraction.

    The bucket assumes a single homogeneous root zone, no capillary rise,
    no runoff, and instantaneous mixing. These assumptions require calibration.
    """
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
    for col in ["ETo_mm", "Rain_mm"]:
        w[col] = pd.to_numeric(w[col], errors="coerce")
        if w[col].isna().any() or (w[col] < 0).any():
            raise ValueError(f"{col} must contain non-negative numeric values.")

    fc = float(params["fc"])
    wp = float(params["wp"])
    zr = float(params["root_depth_m"])
    efficiency = float(params["irrigation_efficiency"])
    if not 0 <= wp < fc <= 1:
        raise ValueError("Require 0 <= wilting point < field capacity <= 1 (VWC).")
    if zr <= 0:
        raise ValueError("Root depth must be positive.")
    if not 0 < efficiency <= 1:
        raise ValueError("Irrigation efficiency must be in (0, 1].")

    taw = 1000.0 * (fc - wp) * zr
    depletion_fraction = float(params.get("depletion_fraction", 0.40))
    if not 0 < depletion_fraction <= 1:
        raise ValueError("depletion_fraction must be in (0, 1].")

    initial_theta = float(params["initial_theta"])
    if not wp <= initial_theta <= fc:
        raise ValueError("Initial VWC must be between wilting point and field capacity.")
    storage_mm = (initial_theta - wp) * 1000.0 * zr

    strategy = str(params.get("irrigation_strategy", "fixed_etc"))
    if strategy not in {"fixed_etc", "soil_moisture_trigger"}:
        raise ValueError("Unknown irrigation_strategy.")
    trigger_fraction = float(params.get("trigger_fraction", depletion_fraction))
    target_fraction = float(params.get("target_fraction", 0.90))
    if not 0 < trigger_fraction < target_fraction <= 1:
        raise ValueError("Require 0 < trigger_fraction < target_fraction <= 1.")

    lai = float(params["initial_lai"])
    biomass = float(params["initial_biomass_t_ha"])
    irrigation_target = float(params["irrigation_pct"]) / 100.0
    fert_pct = float(params["fertilizer_pct"])
    rows = []

    for i, row in w.iterrows():
        day = int(row["Day"]) if pd.notna(row["Day"]) else i + 1
        eto = float(row["ETo_mm"])
        temp = float(row["Temperature_C"])
        solar = float(row["Solar_MJ_m2"])
        rain = float(row["Rain_mm"])
        kc = _crop_coefficient(day, days)
        etc = eto * kc

        storage_start_mm = storage_mm
        # Rain enters the bucket first; excess is counted as drainage.
        storage_mm += rain
        drainage_from_rain_mm = max(0.0, storage_mm - taw)
        storage_mm = min(storage_mm, taw)

        depletion_before_irrigation = taw - storage_mm
        irrigation_event = False
        if strategy == "fixed_etc":
            gross_irrigation = etc * irrigation_target / efficiency
            irrigation_event = gross_irrigation > 0
        else:
            irrigation_event = depletion_before_irrigation >= trigger_fraction * taw
            if irrigation_event:
                desired_storage = target_fraction * taw
                net_refill_mm = max(0.0, desired_storage - storage_mm)
                gross_irrigation = net_refill_mm / efficiency
            else:
                gross_irrigation = 0.0

        effective_irrigation = gross_irrigation * efficiency
        storage_mm += effective_irrigation
        drainage_from_irrigation_mm = max(0.0, storage_mm - taw)
        storage_mm = min(storage_mm, taw)
        drainage = drainage_from_rain_mm + drainage_from_irrigation_mm

        depletion_before_et = taw - storage_mm
        raw = depletion_fraction * taw
        if depletion_before_et <= raw:
            ks = 1.0
        else:
            ks = max(0.0, (taw - depletion_before_et) / max(taw - raw, 1e-9))

        eta = min(etc * ks, storage_mm)
        storage_mm -= eta
        storage_end_mm = storage_mm
        theta = wp + storage_mm / (1000.0 * zr)
        theta = float(np.clip(theta, wp, fc))
        depletion_after = taw - storage_mm

        # Diagnostic closure of the daily root-zone water balance.
        balance_residual = (
            storage_start_mm + rain + effective_irrigation
            - drainage - eta - storage_end_mm
        )

        nutrient_factor = float(np.clip(0.65 + 0.35 * fert_pct / 100.0, 0.45, 1.0))
        temp_factor = float(np.clip(
            1 - (abs(temp - 24.0) / 20.0) ** 1.5, 0.25, 1.0
        ))
        water_factor = float(np.clip(ks, 0, 1))
        intercepted_par = 0.48 * solar * (1 - np.exp(-0.65 * max(lai, 0.01)))
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
            "Irrigation_Event": bool(irrigation_event),
            "Irrigation_Strategy": strategy,
            "Drainage_mm": drainage,
            "Storage_Start_mm": storage_start_mm,
            "Storage_End_mm": storage_end_mm,
            "Depletion_mm": depletion_after,
            "Soil_Moisture_pct": theta * 100.0,
            "Ks": ks,
            "Nutrient_Factor": nutrient_factor,
            "Water_Balance_Residual_mm": balance_residual,
            "LAI": lai,
            "Biomass_t_ha": biomass,
        })

    daily = pd.DataFrame(rows)

    # Replace the former illustrative LAI/biomass trend with the dedicated
    # thermal-time and intercepted-PAR crop growth submodel.
    crop_growth = simulate_pepper_growth(
        w,
        daily["Ks"].to_numpy(),
        daily["Nutrient_Factor"].to_numpy(),
        initial_lai=float(params["initial_lai"]),
        initial_total_biomass_t_ha=float(params["initial_biomass_t_ha"]),
        rue_g_mj=float(params.get("rue_g_mj", 1.6)),
        extinction_coefficient=float(params.get("extinction_coefficient", 0.70)),
        specific_leaf_area_m2_kg=float(params.get("specific_leaf_area_m2_kg", 25.0)),
        base_temperature_c=float(params.get("base_temperature_c", 10.0)),
        optimum_temperature_c=float(params.get("optimum_temperature_c", 25.0)),
        upper_temperature_c=float(params.get("upper_temperature_c", 35.0)),
        flowering_gdd=float(params.get("flowering_gdd", 300.0)),
        fruit_set_gdd=float(params.get("fruit_set_gdd", 500.0)),
        harvest_gdd=float(params.get("harvest_gdd", 1000.0)),
        fruit_dry_matter_fraction=float(params.get("fruit_dry_matter_fraction", 0.08)),
        harvest_recovery_fraction=float(params.get("harvest_recovery_fraction", 0.80)),
    )
    replaced_columns = [col for col in crop_growth.columns if col != "Day" and col in daily.columns]
    daily = daily.drop(columns=replaced_columns)
    daily = daily.merge(crop_growth, on="Day", how="left", validate="one_to_one")
    estimated_yield = float(
        daily["Illustrative_Fresh_Fruit_Yield_t_ha"].iloc[-1]
    )
    total_irrigation = float(daily["Irrigation_mm"].sum())
    total_gross = float(daily["Gross_Irrigation_mm"].sum())
    water_productivity = (
        estimated_yield * 1000.0 / total_irrigation
        if total_irrigation > 0 else 0.0
    )
    summary = {
        "TAW_mm": taw,
        "RAW_mm": depletion_fraction * taw,
        "Seasonal_ETc_mm": float(daily["ETc_mm"].sum()),
        "Seasonal_ETa_mm": float(daily["ETa_mm"].sum()),
        "Total_Effective_Irrigation_mm": total_irrigation,
        "Total_Gross_Irrigation_mm": total_gross,
        "Total_Drainage_mm": float(daily["Drainage_mm"].sum()),
        "Maximum_Absolute_Water_Balance_Residual_mm": float(
            daily["Water_Balance_Residual_mm"].abs().max()
        ),
        "Irrigation_Events": int(daily["Irrigation_Event"].sum()),
        "Irrigation_Strategy": strategy,
        "Final_Soil_Moisture_pct": float(daily["Soil_Moisture_pct"].iloc[-1]),
        "Final_LAI": float(daily["LAI"].iloc[-1]),
        "Final_Biomass_t_ha": float(daily["Biomass_t_ha"].iloc[-1]),
        "Final_Leaf_Biomass_t_ha": float(daily["Leaf_Biomass_t_ha"].iloc[-1]),
        "Final_Stem_Biomass_t_ha": float(daily["Stem_Biomass_t_ha"].iloc[-1]),
        "Final_Fruit_Dry_Biomass_t_ha": float(daily["Fruit_Dry_Biomass_t_ha"].iloc[-1]),
        "Final_Cumulative_GDD_C_day": float(daily["Cumulative_GDD_C_day"].iloc[-1]),
        "Final_Growth_Stage": str(daily["Growth_Stage"].iloc[-1]),
        "Illustrative_Fruit_Yield_t_ha": estimated_yield,
        "Illustrative_Water_Productivity_kg_m3": water_productivity,
        "Weather_Provenance": "Literature-based scenario with assumed daily variation",
        "Model_Assumptions": (
            "Single root-zone bucket; no runoff/capillary rise; "
            "instantaneous mixing; crop growth driven by thermal time "
            "and intercepted PAR; cultivar-specific parameters require calibration"
        ),
    }
    return {"daily": daily, "summary": summary}


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
            # This factorial matrix explicitly compares fixed ETc fractions.
            # Trigger-based schedules are evaluated in the main simulation.
            p["irrigation_strategy"] = "fixed_etc"

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
