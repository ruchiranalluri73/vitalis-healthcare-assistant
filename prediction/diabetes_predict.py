"""
diabetes_predict.py
--------------------
Loads the pre-trained diabetes_model.pkl, diabetes_scaler.pkl, and the two
label encoders (le_gender.pkl, le_smoking.pkl) and exposes a single
function `predict_diabetes(input_dict)` that validates input, encodes
categorical fields, scales everything, runs the prediction, and returns
the result + confidence score.

Dataset: iammustafatz/diabetes-prediction-dataset
Real feature order (confirmed directly from the trained
diabetes_scaler.pkl's `feature_names_in_`):
    gender, age, hypertension, heart_disease, smoking_history,
    bmi, HbA1c_level, blood_glucose_level

NOTE: No training happens here. The model/scaler/encoders were already
trained and saved outside of this application (see the retraining
notebook). This module only loads and applies them.
"""

import os
import joblib
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "diabetes_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "models", "diabetes_scaler.pkl")
LE_GENDER_PATH = os.path.join(BASE_DIR, "models", "le_gender.pkl")
LE_SMOKING_PATH = os.path.join(BASE_DIR, "models", "le_smoking.pkl")

# Column order MUST exactly match diabetes_scaler.pkl's feature_names_in_
FEATURE_ORDER = [
    "gender", "age", "hypertension", "heart_disease",
    "smoking_history", "bmi", "HbA1c_level", "blood_glucose_level"
]

NUMERIC_FIELDS = ["age", "hypertension", "heart_disease", "bmi", "hba1c_level", "blood_glucose_level"]
CATEGORICAL_FIELDS = ["gender", "smoking_history"]

_model = None
_scaler = None
_le_gender = None
_le_smoking = None


def _load_artifacts():
    """Lazy-load the model, scaler, and encoders once, then cache in memory."""
    global _model, _scaler, _le_gender, _le_smoking
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    if _scaler is None:
        _scaler = joblib.load(SCALER_PATH)
    if _le_gender is None:
        _le_gender = joblib.load(LE_GENDER_PATH)
    if _le_smoking is None:
        _le_smoking = joblib.load(LE_SMOKING_PATH)
    return _model, _scaler, _le_gender, _le_smoking


def validate_input(data: dict, le_gender, le_smoking):
    """Ensure every required field is present, correctly typed, and
    that categorical values are ones the encoders were actually trained on."""
    required = NUMERIC_FIELDS + CATEGORICAL_FIELDS
    missing = [f for f in required if f not in data or data[f] in (None, "")]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    cleaned = {}

    for f in NUMERIC_FIELDS:
        try:
            cleaned[f] = float(data[f])
        except (TypeError, ValueError):
            raise ValueError(f"Field '{f}' must be numeric.")

    if data["gender"] not in le_gender.classes_:
        raise ValueError(
            f"Invalid gender '{data['gender']}'. Expected one of: {list(le_gender.classes_)}"
        )
    if data["smoking_history"] not in le_smoking.classes_:
        raise ValueError(
            f"Invalid smoking_history '{data['smoking_history']}'. "
            f"Expected one of: {list(le_smoking.classes_)}"
        )

    cleaned["gender"] = data["gender"]
    cleaned["smoking_history"] = data["smoking_history"]
    return cleaned


def predict_diabetes(data: dict):
    """
    data: dict with keys matching the diabetes.html form fields:
          gender, age, hypertension, heart_disease, smoking_history,
          bmi, hba1c_level, blood_glucose_level
    Returns: dict with prediction (0/1), label, risk_level, confidence (%)
    """
    model, scaler, le_gender, le_smoking = _load_artifacts()
    cleaned = validate_input(data, le_gender, le_smoking)

    # Encode categorical fields using the exact fitted encoders
    encoded_gender = int(le_gender.transform([cleaned["gender"]])[0])
    encoded_smoking = int(le_smoking.transform([cleaned["smoking_history"]])[0])

    row = {
        "gender": encoded_gender,
        "age": cleaned["age"],
        "hypertension": cleaned["hypertension"],
        "heart_disease": cleaned["heart_disease"],
        "smoking_history": encoded_smoking,
        "bmi": cleaned["bmi"],
        "HbA1c_level": cleaned["hba1c_level"],
        "blood_glucose_level": cleaned["blood_glucose_level"],
    }

    # DataFrame with exact column names/order the scaler was fitted with
    input_df = pd.DataFrame([row], columns=FEATURE_ORDER)
    scaled_input = scaler.transform(input_df)

    prediction = int(model.predict(scaled_input)[0])

    confidence = 0.0
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(scaled_input)[0]
        confidence = round(float(max(proba)) * 100, 2)
    else:
        confidence = 100.0

    if prediction == 1:
        label = "Diabetes Detected"
        risk_level = "High Risk" if confidence >= 70 else "Moderate Risk"
    else:
        label = "No Diabetes Detected"
        risk_level = "Low Risk"

    return {
        "prediction": prediction,
        "label": label,
        "risk_level": risk_level,
        "confidence": confidence,
        "disease": "Diabetes",
    }
