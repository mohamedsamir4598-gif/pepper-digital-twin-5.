"""Transparent rule-based decision support for irrigation and fertigation.

This module generates auditable candidate schedules. It does not actuate
hardware and is not a calibrated crop-specific recommendation model.
"""
import math
import pandas as pd


def build_irrigation_schedule(
    daily: pd.DataFrame,
    *,
    field_capacity_pct: float,
    wilting_point_pct: float,
    root_depth_m: float,
    area_m2: float,
    trigger_fraction: float = 0.45,
    target_fraction: float = 0.90,
    application_efficiency: float = 0.90,
    emitter_count: int = 300,
    emitter_flow_lph: float = 2.0,
    max_runtime_min: float = 180.0,
) -> pd.DataFrame:
    """Calculate irrigation events from root-zone VWC depletion.

    Fractions refer to the available-water interval between WP and FC.
    Daily moisture is treated as representative of the managed root zone.
    """
    if not 0 <= wilting_point_pct < field_capacity_pct <= 100:
        raise ValueError("Require 0 <= wilting point < field capacity <= 100.")
    if root_depth_m <= 0 or area_m2 <= 0:
        raise ValueError("Root depth and greenhouse area must be positive.")
    if not 0 < trigger_fraction < target_fraction <= 1:
        raise ValueError("Require 0 < trigger fraction < target fraction <= 1.")
    if not 0 < application_efficiency <= 1:
        raise ValueError("Application efficiency must be in (0, 1].")
    if emitter_count <= 0 or emitter_flow_lph <= 0:
        raise ValueError("Emitter count and emitter flow must be positive.")
    if "Soil_Moisture_pct" not in daily.columns:
        raise ValueError("Daily data must contain Soil_Moisture_pct.")

    available = field_capacity_pct - wilting_point_pct
    trigger_vwc = wilting_point_pct + trigger_fraction * available
    target_vwc = wilting_point_pct + target_fraction * available
    total_flow_lph = emitter_count * emitter_flow_lph
    rows = []

    for _, row in daily.iterrows():
        current = float(row["Soil_Moisture_pct"])
        event = current <= trigger_vwc
        net_depth_mm = (
            max(0.0, (target_vwc - current) / 100.0 * 1000.0 * root_depth_m)
            if event else 0.0
        )
        gross_volume_l = net_depth_mm * area_m2 / application_efficiency
        runtime_min = gross_volume_l / total_flow_lph * 60.0
        capped = runtime_min > max_runtime_min
        if capped:
            runtime_min = max_runtime_min
            gross_volume_l = total_flow_lph * runtime_min / 60.0
        rows.append({
            "Day": int(row.get("Day", len(rows) + 1)),
            "Soil_Moisture_pct": current,
            "Trigger_VWC_pct": trigger_vwc,
            "Target_VWC_pct": target_vwc,
            "Irrigation_Event": bool(event),
            "Net_Refill_Depth_mm": net_depth_mm,
            "Gross_Water_L": gross_volume_l,
            "Total_System_Flow_L_h": total_flow_lph,
            "Valve_Runtime_min": runtime_min,
            "Runtime_Capped": bool(capped),
            "Decision_Basis": "Root-zone VWC threshold rule; requires field calibration",
        })
    return pd.DataFrame(rows)


def fertilizer_mass_for_target(
    target_concentration_mg_l: float,
    solution_volume_l: float,
    nutrient_fraction: float,
) -> dict:
    """Mass of a labelled fertilizer to reach a target nutrient concentration.

    nutrient_fraction must be the fraction of the specific nutrient element
    on the product label (e.g. 0.15 for 15% N), not oxide-equivalent P2O5/K2O.
    """
    if target_concentration_mg_l < 0 or solution_volume_l < 0:
        raise ValueError("Concentration and volume cannot be negative.")
    if not 0 < nutrient_fraction <= 1:
        raise ValueError("Nutrient fraction must be in (0, 1].")
    nutrient_g = target_concentration_mg_l * solution_volume_l / 1000.0
    fertilizer_g = nutrient_g / nutrient_fraction
    return {
        "target_nutrient_g": nutrient_g,
        "fertilizer_product_g": fertilizer_g,
        "target_concentration_mg_l": target_concentration_mg_l,
        "solution_volume_l": solution_volume_l,
        "labelled_nutrient_fraction": nutrient_fraction,
    }
