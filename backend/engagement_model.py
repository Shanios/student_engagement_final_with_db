# backend/engagement_model.py
import os
import numpy as np
from pathlib import Path
from joblib import load

# ✅ CORRECTED: Find model with fallback locations
def get_model_path():
    """
    Find engagement_model.pkl in multiple locations
    """
    current_dir = Path(__file__).parent  # backend/
    
    # Try in order of likelihood
    possible_paths = [
        current_dir / "engagement" / "engagement_model.pkl",  # backend/engagement/engagement_model.pkl
        current_dir / "engagement_model.pkl",                  # backend/engagement_model.pkl
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"✅ Found model at: {path}")
            return str(path)
    
    # If not found, show helpful error
    error_msg = "Model not found. Searched:\n"
    for path in possible_paths:
        error_msg += f"  ❌ {path}\n"
    raise FileNotFoundError(error_msg)

# Load model at startup
MODEL_PATH = get_model_path()
print(f"📦 Loading model from: {MODEL_PATH}")

try:
    _model = load(MODEL_PATH)
    print(f"✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    raise


def predict_engagement(features: list[float]) -> dict:
    """
    Predict engagement from features.
    
    Args:
        features: list[float] that matches training data
        Example: [mean_ear, std_ear, blink_rate, ...]
    
    Returns:
        dict with 'label' (0 or 1) and 'probability'
    """
    X = np.array(features, dtype=float).reshape(1, -1)

    label = int(_model.predict(X)[0])

    prob = None
    if hasattr(_model, "predict_proba"):
        prob = float(_model.predict_proba(X)[0][1])

    return {
        "label": label,            # 1 = engaged, 0 = not engaged
        "probability": prob,
    }