"""
heart_predict.py
----------------
Loads the pre-trained heart_model.pkl and heart_scaler.pkl and exposes a
single function `predict_heart(input_dict)` that validates input, scales
it, runs the prediction, and returns the result + confidence score.

NOTE: No training happens here. The model was already trained and
selected by the user outside of this application.
"""

import os
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "heart_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "models", "heart_scaler.pkl")

# Feature order MUST match the order used during training
FEATURE_ORDER = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
    "thalach", "exang", "oldpeak", "slope", "ca", "thal"
]

_model = None
_scaler = None


def _load_artifacts():
    """Lazy-load the model & scaler once, then cache them in memory."""
    global _model, _scaler
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    if _scaler is None:
        _scaler = joblib.load(SCALER_PATH)
    return _model, _scaler


def validate_input(data: dict):
    """Ensure every required feature is present and numeric."""
    missing = [f for f in FEATURE_ORDER if f not in data or data[f] in (None, "")]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    cleaned = {}
    for f in FEATURE_ORDER:
        try:
            cleaned[f] = float(data[f])
        except (TypeError, ValueError):
            raise ValueError(f"Field '{f}' must be numeric.")
    return cleaned


def predict_heart(data: dict):
    """
    data: dict containing the 13 heart-disease features.
    Returns: dict with prediction (0/1), label, risk_level, confidence (%)
    """
    model, scaler = _load_artifacts()
    cleaned = validate_input(data)

    ordered_values = [cleaned[f] for f in FEATURE_ORDER]
    # Use a DataFrame so column names match what the scaler was fitted with
    # (avoids the "X does not have valid feature names" sklearn warning).
    input_df = pd.DataFrame([ordered_values], columns=FEATURE_ORDER)
    scaled_input = scaler.transform(input_df)

    prediction = int(model.predict(scaled_input)[0])

    confidence = 0.0
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(scaled_input)[0]
        confidence = round(float(np.max(proba)) * 100, 2)
    else:
        confidence = 100.0

    if prediction == 1:
        label = "Heart Disease Detected"
        risk_level = "High Risk" if confidence >= 70 else "Moderate Risk"
    else:
        label = "No Heart Disease Detected"
        risk_level = "Low Risk"

    return {
        "prediction": prediction,
        "label": label,
        "risk_level": risk_level,
        "confidence": confidence,
        "disease": "Heart Disease",
    }
