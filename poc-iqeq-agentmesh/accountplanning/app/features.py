import pandas as pd
from datetime import datetime, timedelta

def compute_features(account_id: str, raw: dict) -> dict:
    """
    SINGLE SOURCE OF TRUTH: Aggregates raw 1:N data into a per-account feature vector.
    Used by both training and runtime scoring agents.
    """
    # 1. Extract account-specific subsets
    opps = raw["opportunities"][raw["opportunities"].account_id == account_id].copy()
    funds = raw["external_funds"][raw["external_funds"].account_id == account_id].copy()
    attend = raw["conference_attendance"][raw["conference_attendance"].account_id == account_id].copy()
    confs = raw["conferences"].copy()  # catalog
    
    # metrics is 1:1, get the single row
    metrics_matches = raw["snowflake_metrics"][raw["snowflake_metrics"].account_id == account_id]
    if metrics_matches.empty:
        # Fallback if metrics missing (should not happen in this prototype)
        return {f: 0.0 for f in [
            "win_rate", "avg_deal_size_eur", "open_opps_count", 
            "service_penetration", "engagement_score", "launch_indicator", 
            "tier_1_conf_count", "growth_metrics_qoq"
        ]}
    metrics = metrics_matches.iloc[0]

    # 2. Intermediate calculations
    closed = opps[opps.status.isin(["won", "lost"])]
    attended_conf_ids = attend.conference_id.unique()
    attended_confs = confs[confs.conference_id.isin(attended_conf_ids)]
    
    # Cutoff for recent launches (90 days ago from "now" / "data reference date")
    # For synthetic data, we can use a fixed reference or most recent date in data
    reference_date = datetime(2026, 4, 8) # Project logic date
    cutoff_90d = (reference_date - timedelta(days=90)).strftime('%Y-%m-%d')
    
    # Ensure fund launch_date is comparable
    if not funds.empty and 'launch_date' in funds.columns:
        launch_indicator = int((funds.launch_date >= cutoff_90d).any())
    else:
        launch_indicator = 0

    # 3. Assemble feature vector
    return {
        "win_rate":            float((closed.status == "won").sum() / max(len(closed), 1)),
        "avg_deal_size_eur":   float(opps.deal_size_eur.mean() if not opps.empty else 0.0),
        "open_opps_count":     int((opps.status == "open").sum()),
        "service_penetration": float(metrics.service_penetration),
        "engagement_score":    float(metrics.engagement_score
                               + 5 * len(attend)
                               + 10 * (attend.signal_strength == "high").sum()),
        "launch_indicator":    int(launch_indicator),
        "tier_1_conf_count":   int((attended_confs.tier == "tier_1").sum()),
        "growth_metrics_qoq":  float(metrics.growth_metrics_qoq),
    }
