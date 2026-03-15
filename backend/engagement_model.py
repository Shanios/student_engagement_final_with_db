# backend/engagement_model.py
# ✅ PRODUCTION-SAFE: Lazy loading, graceful fallback, better logging

import os
import numpy as np
from pathlib import Path
from joblib import load
import logging

logger = logging.getLogger(__name__)

# ========================================================
# MODEL LOADER (Lazy Loading Pattern)
# ========================================================

class EngagementModelLoader:
    """
    Lazy loads the engagement model on first use.
    If model is missing, gracefully falls back to dummy predictions.
    """
    
    def __init__(self):
        self._model = None
        self._model_loaded = False
        self._model_available = False
        self.model_path = None
    
    def find_model_path(self):
        """Find engagement_model.pkl in multiple locations"""
        current_dir = Path(__file__).parent  # backend/
        
        possible_paths = [
            current_dir / "engagement" / "engagement_model.pkl",  # backend/engagement/engagement_model.pkl
            current_dir / "engagement_model.pkl",                  # backend/engagement_model.pkl
            Path.cwd() / "engagement_model.pkl",                   # Current working directory
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"✅ Found model at: {path}")
                return str(path)
        
        logger.warning(f"⚠️  Model not found. Searched {len(possible_paths)} locations")
        return None
    
    def load_model(self):
        """Load model from disk (only called once, on first use)"""
        if self._model_loaded:
            return self._model
        
        self._model_loaded = True
        
        self.model_path = self.find_model_path()
        
        if self.model_path is None:
            logger.error("❌ engagement_model.pkl not found anywhere!")
            logger.error("    Place model at: backend/engagement/engagement_model.pkl")
            self._model_available = False
            return None
        
        try:
            logger.info(f"📦 Loading model from: {self.model_path}")
            self._model = load(self.model_path)
            logger.info("✅ Model loaded successfully!")
            self._model_available = True
            return self._model
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            self._model_available = False
            return None
    
    def is_available(self):
        """Check if model is available (lazy loads if needed)"""
        if not self._model_loaded:
            self.load_model()
        return self._model_available
    
    def get_model(self):
        """Get model instance (lazy loads if needed)"""
        if not self._model_loaded:
            self.load_model()
        return self._model


# Global instance
_model_loader = EngagementModelLoader()


# ========================================================
# PREDICTION FUNCTION
# ========================================================

def predict_engagement(features: list[float]) -> dict:
    """
    Predict engagement from features.
    
    Args:
        features: list[float] that matches training data
        Example: [mean_ear, std_ear, blink_rate, ...]
    
    Returns:
        dict with 'label' (0 or 1), 'probability', and 'model_available'
    
    Falls back to dummy prediction if model is not available.
    """
    
    # Convert to numpy array
    try:
        X = np.array(features, dtype=float).reshape(1, -1)
    except Exception as e:
        logger.error(f"❌ Invalid features: {e}")
        return {
            "label": 0,
            "probability": 0.5,
            "model_available": False,
            "error": str(e)
        }
    
    # Check if model is available
    model = _model_loader.get_model()
    
    if model is None:
        logger.warning("⚠️  Model unavailable, using fallback prediction")
        # Fallback: simple heuristic based on mean_ear
        mean_ear = features[0] if len(features) > 0 else 0.3
        prob = max(0.1, min(0.9, mean_ear * 2))  # Simple scaling
        
        return {
            "label": 1 if prob > 0.5 else 0,
            "probability": float(prob),
            "model_available": False,
            "fallback": True
        }
    
    # Use actual model
    try:
        label = int(model.predict(X)[0])
        
        # Get probability if available
        prob = None
        if hasattr(model, "predict_proba"):
            proba_array = model.predict_proba(X)[0]
            # Assume: class 0 = not engaged, class 1 = engaged
            prob = float(proba_array[1]) if len(proba_array) > 1 else float(proba_array[0])
        else:
            # Fallback if model doesn't have predict_proba
            prob = float(label)
        
        return {
            "label": label,
            "probability": prob,
            "model_available": True,
            "fallback": False
        }
    
    except Exception as e:
        logger.error(f"❌ Prediction failed: {e}")
        return {
            "label": 0,
            "probability": 0.5,
            "model_available": True,
            "error": str(e)
        }


# ========================================================
# HEALTH CHECK
# ========================================================

def get_model_status() -> dict:
    """Get model status for debugging/health checks"""
    return {
        "model_available": _model_loader.is_available(),
        "model_path": _model_loader.model_path,
        "loaded": _model_loader._model_loaded,
    }


# ========================================================
# INITIALIZATION (called on app startup)
# ========================================================

def init_model():
    """Pre-load model on app startup (optional, for better UX)"""
    logger.info("🚀 Initializing engagement model...")
    if _model_loader.is_available():
        logger.info("✅ Model ready!")
    else:
        logger.warning("⚠️  Model will use fallback predictions (not production-ready)")