"""Pepper crop growth submodel driven by intercepted PAR and thermal time.

This is a transparent research prototype. Thermal-time stage thresholds,
specific leaf area and fruit dry-matter fraction are editable parameters
and must be calibrated for the cultivar, greenhouse and production system.
"""
import numpy as np
import pandas as pd


def temperature_response(temp_c, base=10.0, optimum=25.0, upper=35.0):
    """Triangular cardinal-temperature response between 0 and 1."""
    if not base < optimum < upper:
        raise ValueError("Require base < optimum < upper temperature.")
    if temp_c <= base or temp_c >= upper:
        return 0.0
    if temp_c <= optimum:
        return (temp_c - base) / (optimum - base)
    return (upper - temp_c) / (upper - optimum)


def simulate_pepper_growth(
    weather: pd.DataFrame,
    water_stress,
    nutrient_factor,
    *,
    initial_lai=0.15,
    initial_total_biomass_t_ha=0.05,
    rue_g_mj=1.6,
    extinction_coefficient=0.70,
    specific_leaf_area_m2_kg=25.0,
    base_temperature_c=10.0,
    optimum_temperature_c=25.0,
    upper_temperature_c=35.0,
    flowering_gdd=300.0,
    fruit_set_gdd=500.0,
    harvest_gdd=1000.0,
    fruit_dry_matter_fraction=0.08,
    harvest_recovery_fraction=0.80,
    rootzone_ece_ds_m=None,
    salinity_threshold_ece_ds_m=1.5,
    salinity_slope_pct_per_ds_m=14.1,
):
    """Return daily phenology, LAI and dry-matter partitioning.

    Solar_MJ_m2 is assumed to be global solar radiation; PAR is estimated
    as 0.48 of global solar radiation. RUE is expressed per intercepted PAR.
    Daily water_stress and nutrient_factor must be dimensionless [0, 1].
    """
    required = {"Day", "Temperature_C", "Solar_MJ_m2"}
    missing = required - set(weather.columns)
    if missing:
        raise ValueError(f"Missing growth weather columns: {sorted(missing)}")
    if rue_g_mj <= 0 or specific_leaf_area_m2_kg <= 0:
        raise ValueError("RUE and specific leaf area must be positive.")
    if not 0 < extinction_coefficient <= 2:
        raise ValueError("Extinction coefficient must be in (0, 2].")
    if not 0 < fruit_dry_matter_fraction <= 1:
        raise ValueError("Fruit dry matter fraction must be in (0, 1].")
    if not 0 < harvest_recovery_fraction <= 1:
        raise ValueError("Harvest recovery fraction must be in (0, 1].")
    if salinity_threshold_ece_ds_m < 0 or salinity_slope_pct_per_ds_m < 0:
        raise ValueError("Salinity threshold and slope cannot be negative.")
    if rootzone_ece_ds_m is not None and rootzone_ece_ds_m < 0:
        raise ValueError("Root-zone ECe cannot be negative.")
    if not 0 < flowering_gdd < fruit_set_gdd < harvest_gdd:
        raise ValueError("Require 0 < flowering GDD < fruit-set GDD < harvest GDD.")

    salinity_factor = 1.0
    if rootzone_ece_ds_m is not None:
        salinity_factor = max(
            0.0,
            1.0 - (salinity_slope_pct_per_ds_m / 100.0)
            * max(0.0, float(rootzone_ece_ds_m) - salinity_threshold_ece_ds_m),
        )

    n = len(weather)
    water = np.broadcast_to(np.asarray(water_stress, dtype=float), (n,))
    nutrients = np.broadcast_to(np.asarray(nutrient_factor, dtype=float), (n,))
    if np.any(~np.isfinite(water)) or np.any((water < 0) | (water > 1)):
        raise ValueError("Water stress factors must be finite and within [0, 1].")
    if np.any(~np.isfinite(nutrients)) or np.any((nutrients < 0) | (nutrients > 1)):
        raise ValueError("Nutrient factors must be finite and within [0, 1].")

    # 1 t/ha = 0.1 kg/m2. Convert initial LAI to leaf dry matter.
    leaf_dm = float(initial_lai) / (0.1 * specific_leaf_area_m2_kg)
    total_initial = max(float(initial_total_biomass_t_ha), leaf_dm)
    stem_dm = max(0.0, total_initial - leaf_dm)
    fruit_dm = 0.0
    cumulative_gdd = 0.0
    rows = []

    for i, (_, row) in enumerate(weather.reset_index(drop=True).iterrows()):
        temp = float(row["Temperature_C"])
        solar = max(0.0, float(row["Solar_MJ_m2"]))
        thermal_effect = temperature_response(
            temp, base_temperature_c, optimum_temperature_c, upper_temperature_c
        )
        daily_gdd = max(0.0, temp - base_temperature_c)
        cumulative_gdd += daily_gdd

        if cumulative_gdd < flowering_gdd:
            stage = "Vegetative"
            fractions = (0.60, 0.40, 0.00)
        elif cumulative_gdd < fruit_set_gdd:
            stage = "Flowering"
            fractions = (0.40, 0.40, 0.20)
        elif cumulative_gdd < harvest_gdd:
            stage = "Fruit development"
            fractions = (0.20, 0.25, 0.55)
        else:
            stage = "Harvest period"
            fractions = (0.15, 0.20, 0.65)

        lai = max(0.0, leaf_dm * 0.1 * specific_leaf_area_m2_kg)
        par = solar * 0.48
        fipar = 1.0 - np.exp(-extinction_coefficient * lai)
        intercepted_par = par * fipar
        growth_stress = thermal_effect * water[i] * nutrients[i] * salinity_factor
        delta_dm_g_m2 = rue_g_mj * intercepted_par * growth_stress
        delta_total_t_ha = max(0.0, delta_dm_g_m2 * 0.01)

        leaf_increment = delta_total_t_ha * fractions[0]
        stem_increment = delta_total_t_ha * fractions[1]
        fruit_increment = delta_total_t_ha * fractions[2]
        leaf_dm += leaf_increment
        stem_dm += stem_increment
        fruit_dm += fruit_increment

        # Small empirical leaf turnover after fruit set; calibrate from observations.
        senescence = 0.0015 * leaf_dm if cumulative_gdd >= fruit_set_gdd else 0.0
        leaf_dm = max(0.0, leaf_dm - senescence)
        total_dm = leaf_dm + stem_dm + fruit_dm
        lai = leaf_dm * 0.1 * specific_leaf_area_m2_kg
        fresh_fruit_yield = (
            fruit_dm / fruit_dry_matter_fraction * harvest_recovery_fraction
        )

        rows.append({
            "Day": int(row["Day"]),
            "Daily_GDD_C_day": daily_gdd,
            "Cumulative_GDD_C_day": cumulative_gdd,
            "Growth_Stage": stage,
            "Temperature_Response": thermal_effect,
            "PAR_MJ_m2": par,
            "Fraction_Intercepted_PAR": fipar,
            "Intercepted_PAR_MJ_m2": intercepted_par,
            "Water_Stress_Factor": water[i],
            "Nutrient_Response_Factor": nutrients[i],
            "Salinity_Response_Factor": salinity_factor,
            "Daily_Dry_Matter_Increment_t_ha": delta_total_t_ha,
            "Leaf_Biomass_t_ha": leaf_dm,
            "Stem_Biomass_t_ha": stem_dm,
            "Fruit_Dry_Biomass_t_ha": fruit_dm,
            "Biomass_t_ha": total_dm,
            "LAI": lai,
            "Leaf_Senescence_t_ha": senescence,
            "Illustrative_Fresh_Fruit_Yield_t_ha": fresh_fruit_yield,
        })

    return pd.DataFrame(rows)
