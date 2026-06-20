import os
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from datetime import datetime
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, confusion_matrix, classification_report
from sklearn.calibration import CalibratedClassifierCV

from app.core.features import compute_features
from app.core.constants import FEATURE_ORDER

def main():
    print("Starting Phase 3: Model Training...")
    
    # 1. Load Data
    data_dir = "data/training"
    raw_data = {
        "accounts": pd.read_csv(os.path.join(data_dir, "accounts.csv")),
        "opportunities": pd.read_csv(os.path.join(data_dir, "opportunities.csv")),
        "snowflake_metrics": pd.read_csv(os.path.join(data_dir, "snowflake_metrics.csv")),
        "external_funds": pd.read_csv(os.path.join(data_dir, "external_funds.csv")),
        "conferences": pd.read_csv(os.path.join(data_dir, "conferences.csv")),
        "conference_attendance": pd.read_csv(os.path.join(data_dir, "conference_attendance.csv"))
    }
    
    # 2. Extract Features and Labels
    print("Aggregating features for 2,500 accounts...")
    X_list = []
    y_list = []
    
    for acc_id in raw_data["accounts"].account_id:
        # Features
        feat_dict = compute_features(acc_id, raw_data)
        X_list.append([feat_dict[f] for f in FEATURE_ORDER])
        
        # Label: Probabilistic success (avoids binary separation)
        # We use win_rate as a base probability, clamped between 0.1 and 0.9
        base_prob = 0.1 + (min(max(feat_dict["win_rate"], 0), 1) * 0.8)
        y_list.append(1 if np.random.random() < base_prob else 0)
        
    X = np.array(X_list)
    y = np.array(y_list)
    
    print(f"Feature matrix shape: {X.shape}")
    print(f"Positive class rate: {y.mean():.2%}")
    
    # 3. Train/Val/Test Split (70/15/15)
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)
    
    # 4. Train XGBoost with higher regularization
    print("Training XGBoost Classifier...")
    xgb = XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        reg_lambda=10, # Higher L2 regularization
        gamma=5,       # Higher minimum loss reduction
        random_state=42,
        eval_metric="logloss"
    )
    
    # 5. Calibration (Essential for conflict detection logic)
    print("Calibrating probabilities (isotonic regression)...")
    calibrated_model = CalibratedClassifierCV(xgb, method="isotonic", cv=3)
    calibrated_model.fit(X_train, y_train)
    
    # 6. Evaluation
    y_prob = calibrated_model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    print(f"Training Complete. Test AUC: {auc:.4f}")
    
    if auc < 0.75:
        print("WARNING: AUC is below target threshold of 0.75!")
    
    # 7. Viz - Score Distribution
    plt.figure(figsize=(10, 6))
    plt.hist(y_prob, bins=25, color='teal', edgecolor='black', alpha=0.7)
    plt.title(f"Propensity Score Distribution (Test Set)\nAUC: {auc:.4f}")
    plt.xlabel("Propensity Score")
    plt.ylabel("Frequency")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    os.makedirs("models", exist_ok=True)
    plt.savefig("models/score_distribution.png")
    print("Histogram saved to models/score_distribution.png")
    
    # 8. Export Pickle
    model_path = "models/xgb_propensity_v1.pkl"
    export_data = {
        "model": calibrated_model,
        "feature_names": FEATURE_ORDER,
        "model_version": "xgb_propensity_v1",
        "trained_at": datetime.utcnow().isoformat(),
        "test_auc": float(auc),
        "training_size": len(X_train)
    }
    joblib.dump(export_data, model_path)
    print(f"Model exported to {model_path}")

if __name__ == "__main__":
    main()
