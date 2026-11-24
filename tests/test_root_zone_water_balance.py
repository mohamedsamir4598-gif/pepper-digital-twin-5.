import unittest

from models.simulation import make_literature_weather, simulate_crop


def base_params(strategy):
    return {
        "days": 60,
        "fc": 0.30,
        "wp": 0.10,
        "root_depth_m": 0.30,
        "initial_theta": 0.25,
        "irrigation_pct": 90,
        "irrigation_strategy": strategy,
        "trigger_fraction": 0.40,
        "target_fraction": 0.90,
        "fertilizer_pct": 75,
        "irrigation_efficiency": 0.90,
        "initial_lai": 0.15,
        "initial_biomass_t_ha": 0.05,
    }


class RootZoneWaterBalanceTests(unittest.TestCase):
    def test_daily_water_balance_closes_for_fixed_etc(self):
        result = simulate_crop(
            base_params("fixed_etc"),
            make_literature_weather(60),
        )
        residual = result["daily"]["Water_Balance_Residual_mm"].abs()
        self.assertLess(float(residual.max()), 1e-8)
        self.assertGreater(result["summary"]["Total_Gross_Irrigation_mm"], 0)

    def test_trigger_strategy_creates_irrigation_events(self):
        result = simulate_crop(
            base_params("soil_moisture_trigger"),
            make_literature_weather(60),
        )
        daily = result["daily"]
        self.assertTrue(daily["Irrigation_Event"].any())
        self.assertTrue(
            (daily.loc[~daily["Irrigation_Event"], "Gross_Irrigation_mm"] == 0).all()
        )
        self.assertLess(
            result["summary"]["Maximum_Absolute_Water_Balance_Residual_mm"],
            1e-8,
        )

    def test_reject_initial_moisture_outside_limits(self):
        params = base_params("fixed_etc")
        params["initial_theta"] = 0.35
        with self.assertRaises(ValueError):
            simulate_crop(params, make_literature_weather(60))


if __name__ == "__main__":
    unittest.main()
