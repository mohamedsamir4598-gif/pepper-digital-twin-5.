import unittest

import numpy as np
from models.crop_growth import simulate_pepper_growth
from models.simulation import make_literature_weather


class PepperSalinityResponseTests(unittest.TestCase):
    def test_no_salinity_factor_when_ece_not_supplied(self):
        weather = make_literature_weather(90)
        neutral = simulate_pepper_growth(weather, np.ones(90), np.ones(90))
        self.assertTrue((neutral["Salinity_Response_Factor"] == 1.0).all())

    def test_ec_e_above_threshold_reduces_growth(self):
        weather = make_literature_weather(90)
        control = simulate_pepper_growth(
            weather, np.ones(90), np.ones(90), rootzone_ece_ds_m=1.5
        )
        saline = simulate_pepper_growth(
            weather, np.ones(90), np.ones(90), rootzone_ece_ds_m=3.0
        )
        self.assertLess(
            saline["Biomass_t_ha"].iloc[-1],
            control["Biomass_t_ha"].iloc[-1],
        )
        self.assertTrue(
            (saline["Salinity_Response_Factor"] < 1.0).all()
        )

    def test_reject_negative_ece(self):
        weather = make_literature_weather(5)
        with self.assertRaises(ValueError):
            simulate_pepper_growth(
                weather, np.ones(5), np.ones(5), rootzone_ece_ds_m=-0.1
            )


if __name__ == "__main__":
    unittest.main()
