import unittest

import pandas as pd

from models.decision_support import (
    build_irrigation_schedule,
    fertilizer_mass_for_target,
)


class DecisionSupportTests(unittest.TestCase):
    def test_irrigation_volume_and_runtime_cap(self):
        daily = pd.DataFrame({
            "Day": [1, 2],
            "Soil_Moisture_pct": [18.0, 22.0],
        })
        result = build_irrigation_schedule(
            daily,
            field_capacity_pct=30,
            wilting_point_pct=10,
            root_depth_m=0.3,
            area_m2=100,
            trigger_fraction=0.45,
            target_fraction=0.90,
            application_efficiency=0.90,
            emitter_count=300,
            emitter_flow_lph=2.0,
            max_runtime_min=180,
        )
        self.assertTrue(bool(result.loc[0, "Irrigation_Event"]))
        self.assertFalse(bool(result.loc[1, "Irrigation_Event"]))
        self.assertTrue(bool(result.loc[0, "Runtime_Capped"]))
        self.assertAlmostEqual(result.loc[0, "Valve_Runtime_min"], 180.0)
        self.assertAlmostEqual(result.loc[0, "Gross_Water_L"], 1800.0)

    def test_fertilizer_mass_from_elemental_label_fraction(self):
        result = fertilizer_mass_for_target(100, 100, 0.20)
        self.assertAlmostEqual(result["target_nutrient_g"], 10.0)
        self.assertAlmostEqual(result["fertilizer_product_g"], 50.0)

    def test_reject_invalid_trigger_target(self):
        daily = pd.DataFrame({"Soil_Moisture_pct": [20.0]})
        with self.assertRaises(ValueError):
            build_irrigation_schedule(
                daily,
                field_capacity_pct=30,
                wilting_point_pct=10,
                root_depth_m=0.3,
                area_m2=100,
                trigger_fraction=0.9,
                target_fraction=0.5,
            )


if __name__ == "__main__":
    unittest.main()
