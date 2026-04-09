import joblib
import numpy as np
import pandas as pd
from app.features import compute_features
from app.constants import FEATURE_ORDER
from app.progress_tracker import tracker

def run_scoring_agent(raw_data: dict):
    tracker.emit("ag-ml", "started", message="Initializing XGBoost inference engine...")
    
    # 1. Load Model
    model_path = "models/xgb_propensity_v1.pkl"
    try:
        model_data = joblib.load(model_path)
        clf = model_data["model"]
        feature_names = model_data["feature_names"]
    except Exception as e:
        error_msg = f"Failed to load model: {str(e)}"
        tracker.emit("ag-ml", "error", message=error_msg)
        raise
        
    tracker.emit("ag-ml", "processing", message="Computing features for accounts...")
    
    # 2. Compute Features
    results = []
    accounts = raw_data["accounts"].account_id.tolist()
    
    X_list = []
    for acc_id in accounts:
        feat_dict = compute_features(acc_id, raw_data)
        X_list.append([feat_dict[f] for f in FEATURE_ORDER])
        
    X = np.array(X_list)
    
    # 3. Predict
    tracker.emit("ag-ml", "processing", message=f"Running model scoring on {len(X)} records...")
    probs = clf.predict_proba(X)[:, 1]
    
    for i, acc_id in enumerate(accounts):
        results.append({
            "account_id": acc_id,
            "propensity_score": float(probs[i]),
            "confidence_level": 0.95 # Mock confidence for POC1
        })
        
    avg_score = np.mean(probs)
    tracker.emit("ag-ml", "completed", message=f"Scoring complete. Average Propensity Score: {avg_score:.2f}")
    return results
