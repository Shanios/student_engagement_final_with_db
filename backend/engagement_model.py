# backend/engagement_model.py
import os
import numpy as np
from joblib import load

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "engagement_model.pkl")

# load once at import
_model = load(MODEL_PATH)


def predict_engagement(features: list[float]) -> dict:
    """
    features -> list[float] that matches what you trained on.
    Example: [mean_ear, std_ear, blink_rate, ...]
    """
    X = np.array(features, dtype=float).reshape(1, -1)

    label = int(_model.predict(X)[0])

    prob = None
    if hasattr(_model, "predict_proba"):
        prob = float(_model.predict_proba(X)[0][1])

    return {
        "label": label,            # 1 = engaged, 0 = not engaged (your convention)
        "probability": prob,
    }
