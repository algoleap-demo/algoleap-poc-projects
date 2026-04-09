from app.data_gen import (
    generate_accounts, generate_opportunities, generate_snowflake_metrics,
    generate_external_funds, generate_conferences, generate_conference_attendance
)
from app.features import compute_features
import pandas as pd

def run_smoke_test():
    print("Starting Phase 1 Smoke Test...")
    seed = 42
    n = 10
    
    # 1. Generate Datasets
    accounts_df = generate_accounts(n, seed, 1)
    opps_df = generate_opportunities(accounts_df, seed, add_label=True)
    metrics_df = generate_snowflake_metrics(accounts_df, seed)
    funds_df = generate_external_funds(accounts_df, seed)
    confs_df = generate_conferences(seed)
    attendance_df = generate_conference_attendance(accounts_df, confs_df, seed)
    
    raw = {
        "accounts": accounts_df,
        "opportunities": opps_df,
        "snowflake_metrics": metrics_df,
        "external_funds": funds_df,
        "conferences": confs_df,
        "conference_attendance": attendance_df
    }
    
    print(f"Generated {len(accounts_df)} accounts and {len(opps_df)} opportunities.")
    
    # 2. Test Feature Aggregation
    account_id = accounts_df.iloc[0].account_id
    features = compute_features(account_id, raw)
    
    print(f"Features for {account_id}:")
    for k, v in features.items():
        print(f"  {k}: {v}")
        
    # 3. Simple Validations
    expected_features = [
        "win_rate", "avg_deal_size_eur", "open_opps_count", 
        "service_penetration", "engagement_score", "launch_indicator", 
        "tier_1_conf_count", "growth_metrics_qoq"
    ]
    
    for feat in expected_features:
        assert feat in features, f"Missing feature: {feat}"
        assert isinstance(features[feat], (int, float)), f"Wrong type for {feat}: {type(features[feat])}"

    print("\nSmoke Test PASSED!")

if __name__ == "__main__":
    run_smoke_test()
