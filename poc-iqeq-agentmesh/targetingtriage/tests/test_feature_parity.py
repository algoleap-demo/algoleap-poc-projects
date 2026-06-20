import pytest
import joblib
import pandas as pd
import os
from app.features import compute_features
from app.constants import FEATURE_ORDER

def test_feature_parity():
    """
    Verifies that the aggregate features produced by app.features
    exactly match the features the trained model expects.
    """
    # 1. Load Model Metadata
    model_path = "models/xgb_propensity_v1.pkl"
    assert os.path.exists(model_path), "Model pickle not found. Run training first."
    
    model_data = joblib.load(model_path)
    expected_features = model_data["feature_names"]
    
    # Check against constants
    assert expected_features == FEATURE_ORDER, "Model feature names mismatch with constants.FEATURE_ORDER!"
    
    # 2. Test Computation on Synthetic Sample
    data_dir = "data/synthetic"
    raw = {
        "accounts": pd.read_csv(os.path.join(data_dir, "accounts.csv")),
        "opportunities": pd.read_csv(os.path.join(data_dir, "opportunities.csv")),
        "snowflake_metrics": pd.read_csv(os.path.join(data_dir, "snowflake_metrics.csv")),
        "external_funds": pd.read_csv(os.path.join(data_dir, "external_funds.csv")),
        "conferences": pd.read_csv(os.path.join(data_dir, "conferences.csv")),
        "conference_attendance": pd.read_csv(os.path.join(data_dir, "conference_attendance.csv"))
    }
    
    acc_id = raw["accounts"].iloc[0].account_id
    features = compute_features(acc_id, raw)
    
    # Verify all expected features are present
    for feat in expected_features:
        assert feat in features, f"Feature {feat} missing from compute_features output!"
        assert isinstance(features[feat], (int, float, bool)), f"Feature {feat} is not a numeric/boolean type!"

def test_feature_stability():
    """
    Verifies that compute_features is idempotent (same input produces same output).
    """
    data_dir = "data/synthetic"
    raw = {
        "accounts": pd.read_csv(os.path.join(data_dir, "accounts.csv")),
        "opportunities": pd.read_csv(os.path.join(data_dir, "opportunities.csv")),
        "snowflake_metrics": pd.read_csv(os.path.join(data_dir, "snowflake_metrics.csv")),
        "external_funds": pd.read_csv(os.path.join(data_dir, "external_funds.csv")),
        "conferences": pd.read_csv(os.path.join(data_dir, "conferences.csv")),
        "conference_attendance": pd.read_csv(os.path.join(data_dir, "conference_attendance.csv"))
    }
    
    acc_id = raw["accounts"].iloc[1].account_id
    feat1 = compute_features(acc_id, raw)
    feat2 = compute_features(acc_id, raw)
    
    assert feat1 == feat2, "compute_features is not idempotent!"
