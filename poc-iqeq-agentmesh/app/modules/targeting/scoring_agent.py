import joblib
import numpy as np
import pandas as pd
from app.core.features import compute_features
from app.core.constants import FEATURE_ORDER
from app.core.paths import MODELS_DIR
from app.core.progress_tracker import tracker

def run_scoring_agent(raw_data: dict, trace_id: str = None):
    tracker.emit("ag-ml", "started", message="Initializing XGBoost inference engine...", trace_id=trace_id)
    
    # 1. Load Model
    model_path = MODELS_DIR / "xgb_propensity_v1.pkl"
    try:
        model_data = joblib.load(model_path)
        clf = model_data["model"]
        feature_names = model_data["feature_names"]
    except Exception as e:
        error_msg = f"Failed to load model: {str(e)}"
        tracker.emit("ag-ml", "error", message=error_msg, trace_id=trace_id)
        raise
        
    tracker.emit("ag-ml", "processing", message="Computing features for accounts...", trace_id=trace_id)
    
    # 2. Compute Features
    results = []
    accounts = raw_data["accounts"].account_id.tolist()
    
    X_list = []
    for acc_id in accounts:
        feat_dict = compute_features(acc_id, raw_data)
        X_list.append([feat_dict[f] for f in FEATURE_ORDER])
        
    X = np.array(X_list)
    
    # 3. Predict
    tracker.emit("ag-ml", "processing", message=f"Running model scoring on {len(X)} records...", trace_id=trace_id)
    probs = clf.predict_proba(X)[:, 1]
    for i, acc_id in enumerate(accounts):
        # Calculate dynamic confidence based on distance from decision boundary (0.5)
        # Prob close to 0 or 1 = High Confidence; Prob close to 0.5 = Low Confidence
        raw_prob = float(probs[i])
        confidence = min(0.98, (abs(raw_prob - 0.5) / 0.5) * 0.4 + 0.55) 
        
        results.append({
            "account_id": acc_id,
            "propensity_score": raw_prob,
            "confidence_level": confidence
        })
        
    avg_score = np.mean(probs)
    tracker.emit("ag-ml", "completed", message=f"Scoring complete. Average Propensity Score: {avg_score:.2f}", trace_id=trace_id)
    return results
