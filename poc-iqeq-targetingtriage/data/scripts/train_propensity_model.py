"""
IQ-EQ Targeting & Triage Agent — Feature Engineering & ML Training
===================================================================
Reads the 5 synthetic CSVs, builds per-account features, trains
Logistic Regression baseline and XGBoost propensity models, evaluates
them, and saves the best model for use by the scoring API.

Usage:
    pip install pandas numpy scikit-learn xgboost
    python train_propensity_model.py

Expects CSVs in data/synthetic_data/
Outputs model artifacts to data/model_artifacts/
"""

import os
import json
import pickle
import sqlite3
import warnings
from datetime import date

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "synthetic_data"))
MODEL_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "model_artifacts"))
DB_PATH = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "triage_poc.db"))
os.makedirs(MODEL_DIR, exist_ok=True)

TODAY = date.today()


# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────

def load_data():
    print("Loading CSVs...")
    accounts = pd.read_csv(f"{DATA_DIR}/accounts.csv")
    opportunities = pd.read_csv(f"{DATA_DIR}/opportunities.csv")
    snowflake = pd.read_csv(f"{DATA_DIR}/snowflake_metrics.csv")
    external_funds = pd.read_csv(f"{DATA_DIR}/external_funds.csv")
    conferences = pd.read_csv(f"{DATA_DIR}/conferences.csv")
    print(f"  accounts:         {len(accounts)}")
    print(f"  opportunities:    {len(opportunities)}")
    print(f"  snowflake_metrics:{len(snowflake)}")
    print(f"  external_funds:   {len(external_funds)}")
    print(f"  conferences:      {len(conferences)}")
    return accounts, opportunities, snowflake, external_funds, conferences


# ─────────────────────────────────────────────
# FEATURE ENGINEERING
# ─────────────────────────────────────────────

def build_features(accounts, opportunities, snowflake, external_funds, conferences):
    """
    Builds a per-account feature matrix.
    Features (all numeric, ready for ML):
      1. historic_win_rate        — won / total_closed
      2. avg_deal_size_eur        — mean deal size
      3. opp_count                — total opportunities
      4. revenue_concentration    — current_aum / total_fund_aum
      5. yoy_revenue_growth       — from Snowflake
      6. service_penetration_score— from Snowflake
      7. existing_middle_office   — binary flag
      8. esg_support              — binary flag
      9. upcoming_launch_flag     — any linked external fund with future launch
     10. conference_engagement    — max engagement_score across attended conferences
     11. strategic_priority_flag  — binary from accounts
     12. is_prospect              — binary (1=prospect, 0=client)
    """
    print("\nBuilding features...")

    # ── Opportunity-based features ──────────────────────────────────────────
    opp = opportunities.copy()
    opp["is_closed"] = opp["stage"].isin(["Closed Won", "Closed Lost"])
    opp["is_won"] = opp["stage"] == "Closed Won"

    opp_agg = opp.groupby("account_id").agg(
        opp_count=("opp_id", "count"),
        total_closed=("is_closed", "sum"),
        total_won=("is_won", "sum"),
        avg_deal_size_eur=("deal_size_eur", "mean"),
    ).reset_index()
    opp_agg["historic_win_rate"] = (
        opp_agg["total_won"] / opp_agg["total_closed"].replace(0, np.nan)
    ).fillna(0.0)

    # ── Upcoming launch flag ─────────────────────────────────────────────────
    ef = external_funds.copy()
    ef["has_upcoming"] = ef["next_launch_date"].apply(
        lambda d: 1 if pd.notna(d) and date.fromisoformat(str(d)) > TODAY else 0
    )
    # Match manager_name to account names (simple substring match)
    upcoming_accs = set()
    for _, row in ef[ef["has_upcoming"] == 1].iterrows():
        mgr = str(row["manager_name"]).split(" ")[0].lower()
        matches = accounts[accounts["name"].str.lower().str.startswith(mgr)]
        for acc_id in matches["account_id"].tolist():
            upcoming_accs.add(acc_id)

    # ── Conference engagement ────────────────────────────────────────────────
    conf_eng = {}
    for _, conf_row in conferences.iterrows():
        acc_list = str(conf_row["accounts_present"]).split(";")
        for acc_id in acc_list:
            acc_id = acc_id.strip()
            if acc_id:
                score = conf_row["engagement_score"]
                conf_eng[acc_id] = max(conf_eng.get(acc_id, 0.0), score)

    # ── Assemble per-account feature dataframe ───────────────────────────────
    df = accounts[["account_id", "status", "strategic_priority_flag"]].copy()
    df = df.merge(opp_agg[["account_id", "opp_count", "avg_deal_size_eur", "historic_win_rate"]], on="account_id", how="left")
    df = df.merge(snowflake[[
        "account_id", "current_aum_with_iqeq", "total_fund_aum",
        "yoy_revenue_growth", "service_penetration_score",
        "existing_middle_office_flag", "esg_policy_support_flag",
        "revenue_fund_admin", "revenue_middle_office"
    ]], on="account_id", how="left")

    df["opp_count"] = df["opp_count"].fillna(0)
    df["avg_deal_size_eur"] = df["avg_deal_size_eur"].fillna(0.0)
    df["historic_win_rate"] = df["historic_win_rate"].fillna(0.0)
    df["revenue_concentration"] = (
        df["current_aum_with_iqeq"] / df["total_fund_aum"].replace(0, np.nan)
    ).fillna(0.0)
    df["upcoming_launch_flag"] = df["account_id"].apply(lambda x: 1 if x in upcoming_accs else 0)
    df["conference_engagement"] = df["account_id"].apply(lambda x: conf_eng.get(x, 0.0))
    df["strategic_priority_flag"] = df["strategic_priority_flag"].astype(int)
    df["existing_middle_office_flag"] = df["existing_middle_office_flag"].astype(int)
    df["esg_policy_support_flag"] = df["esg_policy_support_flag"].astype(int)
    df["is_prospect"] = (df["status"] == "prospect").astype(int)

    print(f"  Feature matrix shape: {df.shape}")
    return df


# ─────────────────────────────────────────────
# DEFINE TARGET VARIABLE
# ─────────────────────────────────────────────

FEATURE_COLS = [
    "historic_win_rate",
    "avg_deal_size_eur",
    "opp_count",
    "revenue_concentration",
    "yoy_revenue_growth",
    "service_penetration_score",
    "existing_middle_office_flag",
    "esg_policy_support_flag",
    "upcoming_launch_flag",
    "conference_engagement",
    "strategic_priority_flag",
    "is_prospect",
]


def build_target(df: pd.DataFrame) -> pd.Series:
    """
    Synthetic target: high-value account if any of:
      - strategic priority AND historic_win_rate >= 0.4
      - service_penetration < 0.6 AND yoy_revenue_growth > 0.05 (whitespace + growing)
      - upcoming_launch AND no middle office (upsell opportunity)
    Adds mild noise to avoid perfect separation.
    """
    target = (
        ((df["strategic_priority_flag"] == 1) & (df["historic_win_rate"] >= 0.4)) |
        ((df["service_penetration_score"] < 0.6) & (df["yoy_revenue_growth"] > 0.05)) |
        ((df["upcoming_launch_flag"] == 1) & (df["existing_middle_office_flag"] == 0))
    ).astype(int)
    # Add 10% label noise for realism
    noise_mask = np.random.random(len(target)) < 0.10
    target[noise_mask] = 1 - target[noise_mask]
    print(f"  Target distribution - positive: {target.sum()}, negative: {(~target.astype(bool)).sum()}")
    return target


# ─────────────────────────────────────────────
# TRAIN MODELS
# ─────────────────────────────────────────────

def train_models(X_train, X_test, y_train, y_test):
    results = {}

    # ── Baseline: Logistic Regression ───────────────────────────────────────
    print("\nTraining Logistic Regression (baseline)...")
    lr_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=1.0, penalty="l2", max_iter=500, random_state=42)),
    ])
    lr_pipe.fit(X_train, y_train)
    lr_prob = lr_pipe.predict_proba(X_test)[:, 1]
    lr_auc = roc_auc_score(y_test, lr_prob)
    print(f"  LR  AUC: {lr_auc:.4f}")
    results["logistic_regression"] = {"model": lr_pipe, "auc": lr_auc, "proba": lr_prob}

    # ── Primary: XGBoost ────────────────────────────────────────────────────
    print("Training XGBoost (primary)...")
    xgb_model = XGBClassifier(
        max_depth=4,
        n_estimators=200,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    xgb_prob = xgb_model.predict_proba(X_test)[:, 1]
    xgb_auc = roc_auc_score(y_test, xgb_prob)
    print(f"  XGB AUC: {xgb_auc:.4f}")
    results["xgboost"] = {"model": xgb_model, "auc": xgb_auc, "proba": xgb_prob}

    return results


# ─────────────────────────────────────────────
# SCORE ALL ACCOUNTS & BUCKET
# ─────────────────────────────────────────────

def score_and_bucket(df: pd.DataFrame, model, feature_cols) -> pd.DataFrame:
    X_all = df[feature_cols].fillna(0.0)
    propensity = model.predict_proba(X_all)[:, 1]
    df = df.copy()
    df["buy_upsell_propensity"] = propensity

    # ICP fit score: composite (propensity + strategic_priority + upcoming_launch)
    df["ICP_fit_score"] = (
        0.5 * propensity +
        0.3 * df["strategic_priority_flag"] +
        0.2 * df["upcoming_launch_flag"]
    ).clip(0, 1)

    # Whitespace flag: low service penetration + non-zero AUM
    df["whitespace_flag"] = (
        (df["service_penetration_score"] < 0.5) & (df["current_aum_with_iqeq"] > 0)
    )

    # Priority bucket
    def bucket(p):
        if p >= 0.70:
            return "A"
        elif p >= 0.40:
            return "B"
        return "C"

    df["priority_bucket"] = df["buy_upsell_propensity"].apply(bucket)
    return df


# ─────────────────────────────────────────────
# SAVE ARTIFACTS
# ─────────────────────────────────────────────

def save_artifacts(best_model, best_name: str, scored_df, feature_cols, eval_report):
    # Pickle model (name reflects winner: logistic_regression or xgboost)
    model_path = os.path.join(MODEL_DIR, f"{best_name}_propensity.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(best_model, f)
    print(f"\n  Model saved: {model_path}")

    # Feature columns manifest
    with open(f"{MODEL_DIR}/feature_cols.json", "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"  Feature manifest: {MODEL_DIR}/feature_cols.json")

    # Scored accounts CSV
    output_cols = [
        "account_id", "status", "ICP_fit_score", "buy_upsell_propensity",
        "priority_bucket", "whitespace_flag", "upcoming_launch_flag",
        "service_penetration_score", "existing_middle_office_flag",
        "esg_policy_support_flag", "current_aum_with_iqeq", "total_fund_aum",
        "yoy_revenue_growth", "historic_win_rate", "avg_deal_size_eur",
    ]
    scored_path = f"{MODEL_DIR}/scored_accounts.csv"
    scored_df[output_cols].sort_values("buy_upsell_propensity", ascending=False).to_csv(scored_path, index=False)
    print(f"  Scored accounts:  {scored_path}")

    # Eval report
    report_path = f"{MODEL_DIR}/eval_report.json"
    with open(report_path, "w") as f:
        json.dump(eval_report, f, indent=2)
    print(f"  Eval report:      {report_path}")


def save_scores_to_sqlite(scored_df: pd.DataFrame) -> None:
    """
    Persists scored outputs into SQLite for Phase 3 API.
    The API will join `scored_accounts` with `accounts` by `account_id`.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"SQLite database not found at {DB_PATH}. Run load_to_sqlite.py first."
        )
    with sqlite3.connect(DB_PATH) as connection:
        scored_df.to_sql("scored_accounts", connection, if_exists="replace", index=False)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_scored_accounts_account_id ON scored_accounts(account_id)"
        )
        connection.commit()
    print(f"  SQLite table saved: {DB_PATH} :: scored_accounts ({len(scored_df)} rows)")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    accounts, opportunities, snowflake, external_funds, conferences = load_data()
    features_df = build_features(accounts, opportunities, snowflake, external_funds, conferences)
    target = build_target(features_df)

    X = features_df[FEATURE_COLS].fillna(0.0)
    y = target.values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"\nTrain size: {len(X_train)}, Test size: {len(X_test)}")

    results = train_models(X_train, X_test, y_train, y_test)

    best_name = max(results, key=lambda k: results[k]["auc"])
    best = results[best_name]
    print(f"\nBest model: {best_name} (AUC = {best['auc']:.4f})")

    # Print classification report for best model
    y_pred_labels = (best["proba"] >= 0.5).astype(int)
    report_str = classification_report(y_test, y_pred_labels, target_names=["Low/Med Priority", "High Priority"])
    print(f"\nClassification Report ({best_name}):\n{report_str}")

    # XGBoost feature importances
    if best_name == "xgboost":
        importances = dict(zip(FEATURE_COLS, best["model"].feature_importances_))
        importances_sorted = sorted(importances.items(), key=lambda x: x[1], reverse=True)
        print("Feature importances:")
        for feat, imp in importances_sorted:
            bar = "#" * int(imp * 50)
            print(f"  {feat:<35} {imp:.4f}  {bar}")

    # Score all accounts
    scored_df = score_and_bucket(features_df, best["model"], FEATURE_COLS)

    # Priority distribution
    print("\nPriority bucket distribution:")
    print(scored_df["priority_bucket"].value_counts().to_string())

    eval_report = {
        "best_model": best_name,
        "auc": {k: round(v["auc"], 4) for k, v in results.items()},
        "test_size": int(len(X_test)),
        "feature_cols": FEATURE_COLS,
        "priority_distribution": scored_df["priority_bucket"].value_counts().to_dict(),
        "whitespace_accounts": int(scored_df["whitespace_flag"].sum()),
        "upcoming_launch_accounts": int(scored_df["upcoming_launch_flag"].sum()),
    }

    save_artifacts(best["model"], best_name, scored_df, FEATURE_COLS, eval_report)
    save_scores_to_sqlite(scored_df)

    print("\nDone. Run scoring_api.py to serve the model.")


if __name__ == "__main__":
    main()
