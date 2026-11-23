
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = ROOT / "pepper_residual_model.joblib"
PRETRAINED_MODEL_PATH = ROOT / "pepper_pretrained_simulator.joblib"
PRETRAINED_DATA_PATH = ROOT / "AI_SIMULATED_TRAINING_DATA.csv"
PRETRAINED_REPORT_PATH = ROOT / "AI_PRETRAINING_REPORT.json"
LITERATURE_MODEL_PATH = ROOT / "pepper_literature_response_model.joblib"

AI_FEATURES = [
    "Days",
    "Irrigation_pct",
    "Fertilizer_pct",
    "Field_Capacity_pct",
    "Wilting_Point_pct",
    "Root_Depth_m",
    "Initial_Moisture_pct",
    "Irrigation_Efficiency_pct",
    "Initial_LAI",
    "Initial_Biomass_t_ha",
    "Mean_Temperature_C",
    "Mean_ETo_mm",
    "Mean_Solar_MJ_m2",
    "Plant_Density",
]

AI_TARGETS = [
    "Final_Biomass_t_ha",
    "Final_LAI",
    "Seasonal_ETa_mm",
    "Illustrative_Yield_t_ha",
]

FEATURES = [
    "Mechanistic_Biomass_t_ha",
    "Mean_LAI",
    "Seasonal_ETa_mm",
    "Mean_Temperature_C",
]

REQUIRED = [
    "Plot_ID",
    *FEATURES,
    "Measured_Biomass_t_ha",
]


def predict_with_pretrained_model(features):
    if not PRETRAINED_MODEL_PATH.exists():
        raise FileNotFoundError(
            "Pretrained AI model file is missing."
        )

    artifact = joblib.load(PRETRAINED_MODEL_PATH)

    missing = [
        col for col in artifact["features"]
        if col not in features.columns
    ]

    if missing:
        raise ValueError(
            "Missing AI input columns: " + ", ".join(missing)
        )

    prediction = artifact["model"].predict(
        features[artifact["features"]]
    )

    return pd.DataFrame(
        prediction,
        columns=artifact["targets"],
        index=features.index,
    )


def train_residual_model(data):
    missing = [
        col for col in REQUIRED
        if col not in data.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    d = data.copy()

    for col in FEATURES + ["Measured_Biomass_t_ha"]:
        d[col] = pd.to_numeric(d[col], errors="coerce")

    d = d.dropna(subset=REQUIRED)

    if len(d) < 18:
        raise ValueError(
            "At least 18 valid rows are required for this "
            "prototype workflow. This is not a scientific "
            "sample-size recommendation."
        )

    if d["Plot_ID"].nunique() < 3:
        raise ValueError(
            "At least 3 different Plot_ID groups are required."
        )

    d["Residual"] = (
        d["Measured_Biomass_t_ha"]
        - d["Mechanistic_Biomass_t_ha"]
    )

    X = d[FEATURES]
    y = d["Residual"]
    groups = d["Plot_ID"].astype(str)

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=42,
    )

    train_idx, test_idx = next(
        splitter.split(X, y, groups)
    )

    if set(groups.iloc[train_idx]) & set(groups.iloc[test_idx]):
        raise ValueError("Plot leakage detected.")

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X.iloc[train_idx],
        y.iloc[train_idx],
    )

    baseline = (
        d.iloc[test_idx]["Mechanistic_Biomass_t_ha"].to_numpy()
    )

    hybrid = baseline + model.predict(X.iloc[test_idx])

    actual = (
        d.iloc[test_idx]["Measured_Biomass_t_ha"].to_numpy()
    )

    def metrics(y_true, y_pred):
        return {
            "MAE": float(mean_absolute_error(y_true, y_pred)),
            "RMSE": float(
                np.sqrt(mean_squared_error(y_true, y_pred))
            ),
            "R2": float(r2_score(y_true, y_pred)),
        }

    joblib.dump(
        {
            "model": model,
            "features": FEATURES,
        },
        MODEL_PATH,
    )

    return {
        "baseline_metrics": metrics(actual, baseline),
        "hybrid_metrics": metrics(actual, hybrid),
        "training_rows": len(train_idx),
        "testing_rows": len(test_idx),
        "testing_plots": int(
            groups.iloc[test_idx].nunique()
        ),
    }


def predict_with_saved_model(data):
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "No experimental correction model has been trained."
        )

    artifact = joblib.load(MODEL_PATH)

    missing = [
        col for col in artifact["features"]
        if col not in data.columns
    ]

    if missing:
        raise ValueError(
            "Missing columns: " + ", ".join(missing)
        )

    correction = artifact["model"].predict(
        data[artifact["features"]]
    )

    return (
        data["Mechanistic_Biomass_t_ha"].to_numpy()
        + correction
    )
