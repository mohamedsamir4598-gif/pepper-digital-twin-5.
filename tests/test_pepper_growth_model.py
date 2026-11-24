import unittest

import numpy as np
import pandas as pd

from models.crop_growth import simulate_pepper_growth, temperature_response
from models.simulation import make_literature_weather, simulate_crop


class PepperGrowthModelTests(unittest.TestCase):
    def test_temperature_response_cardinal_points(self):
        self.assertEqual(temperature_response(10), 0)
        self.assertEqual(temperature_response(25), 1)
        self.assertEqual(temperature_response(35), 0)

    def test_growth_outputs_are_finite_and_nonnegative(self):
        weather = make_literature_weather(120)
        result = simulate_pepper_growth(
            weather,
            water_stress=np.ones(120),
            nutrient_factor=np.ones(120),
        )
        numeric = result.select_dtypes(include=[np.number])
        self.assertTrue(np.isfinite(numeric.to_numpy()).all())
        self.assertTrue((result[[
            "Leaf_Biomass_t_ha", "Stem_Biomass_t_ha",
            "Fruit_Dry_Biomass_t_ha", "LAI",
        ]] >= 0).all().all())
        self.assertGreater(result["Fruit_Dry_Biomass_t_ha"].iloc[-1], 0)
        self.assertEqual(result["Growth_Stage"].iloc[0], "Vegetative")
        self.assertEqual(result["Growth_Stage"].iloc[-1], "Harvest period")

    def test_zero_water_stress_stops_new_growth(self):
        weather = make_literature_weather(5)
        result = simulate_pepper_growth(
            weather,
            water_stress=np.zeros(5),
            nutrient_factor=np.ones(5),
        )
        self.assertTrue((result["Daily_Dry_Matter_Increment_t_ha"] == 0).all())

    def test_integrated_simulator_uses_new_crop_model(self):
        weather = make_literature_weather(120)
        params = {
            "days": 120,
            "fc": 0.30,
            "wp": 0.10,
            "root_depth_m": 0.30,
            "initial_theta": 0.25,
            "irrigation_pct": 90,
            "irrigation_strategy": "fixed_etc",
            "fertilizer_pct": 75,
            "irrigation_efficiency": 0.90,
            "initial_lai": 0.15,
            "initial_biomass_t_ha": 0.05,
        }
        result = simulate_crop(params, weather)
        daily = result["daily"]
        self.assertIn("Fruit_Dry_Biomass_t_ha", daily.columns)
        self.assertIn("Growth_Stage", daily.columns)
        self.assertIn("Intercepted_PAR_MJ_m2", daily.columns)
        self.assertAlmostEqual(
            result["summary"]["Final_LAI"],
            float(daily["LAI"].iloc[-1]),
        )


if __name__ == "__main__":
    unittest.main()
