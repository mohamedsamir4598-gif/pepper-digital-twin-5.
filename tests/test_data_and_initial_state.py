import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from models import data_store
from models.simulation import simulate_crop, make_literature_weather


class ObservationStoreTests(unittest.TestCase):
    def test_manual_and_csv_sources_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.sqlite3"
            with patch.object(data_store, "DB_PATH", db_path):
                data_store.initialize_store()
                data_store.add_observation({
                    "plot_id": "A1",
                    "soil_moisture_pct": 26.5,
                    "source": "manual",
                }, source_override="manual")
                data_store.add_observations([{
                    "plot_id": "A2",
                    "soil_moisture_pct": 28.0,
                }], source_override="csv")
                rows = data_store.get_observations(limit=10)
                self.assertEqual({row["source"] for row in rows}, {"manual", "csv"})
                self.assertEqual(len(rows), 2)

    def test_blank_and_nan_csv_cells_become_null(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.sqlite3"
            with patch.object(data_store, "DB_PATH", db_path):
                data_store.add_observations([{
                    "plot_id": "A1",
                    "soil_moisture_pct": float("nan"),
                    "soil_ph": None,
                }], source_override="csv")
                row = data_store.get_observations(limit=1)[0]
                self.assertIsNone(row["soil_moisture_pct"])
                self.assertIsNone(row["soil_ph"])


class SimulationInitializationTests(unittest.TestCase):
    def test_simulator_accepts_measured_initial_vwc(self):
        weather = make_literature_weather(3)
        params = {
            "days": 3,
            "fc": 0.30,
            "wp": 0.10,
            "root_depth_m": 0.30,
            "initial_theta": 0.25,
            "irrigation_pct": 0,
            "fertilizer_pct": 75,
            "irrigation_efficiency": 0.90,
            "initial_lai": 0.15,
            "initial_biomass_t_ha": 0.05,
        }
        result = simulate_crop(params, weather)
        self.assertEqual(len(result["daily"]), 3)
        self.assertGreaterEqual(result["daily"]["Soil_Moisture_pct"].iloc[0], 10)
        self.assertLessEqual(result["daily"]["Soil_Moisture_pct"].iloc[0], 30)


if __name__ == "__main__":
    unittest.main()
