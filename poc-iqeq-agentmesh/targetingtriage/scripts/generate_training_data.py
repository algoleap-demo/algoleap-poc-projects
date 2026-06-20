import os
import pandas as pd
import numpy as np
from targetingtriage.app.data_gen import (
    generate_accounts, 
    generate_opportunities, 
    generate_snowflake_metrics, 
    generate_external_funds, 
    generate_conferences, 
    generate_conference_attendance
)
from app.core.features import compute_features

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def main():
    print("Starting training data generation (n=2500)...")
    seed = 42
    n_accounts = 2500
    
    # 1. Generate Raw Data
    accounts = generate_accounts(n_accounts, seed, 1)
    opps = generate_opportunities(accounts, seed)
    metrics = generate_snowflake_metrics(accounts, seed)
    funds = generate_external_funds(accounts, seed)
    confs = generate_conferences(seed)
    attendance = generate_conference_attendance(accounts, confs, seed)
    
    # Pack for compute_features
    raw_data = {
        "accounts": accounts,
        "opportunities": opps,
        "snowflake_metrics": metrics,
        "external_funds": funds,
        "conferences": confs,
        "conference_attendance": attendance
    }
    
    # 2. Apply Hidden Label Function to Opportunities
    # To do this realistically, we compute "contextual" features for each account first
    # then used those to bias the opportunity outcomes.
    
    print("Applying hidden label function to bias outcomes...")
    
    account_outcome_probs = {}
    for acc_id in accounts.account_id:
        # Get contextual features (avoiding outcome-based features like win_rate for now)
        feat = compute_features(acc_id, raw_data)
        
        # Hidden Signal Logic
        # true_prob = sigmoid(1.5*SP + 1.0*(ES/100) + 0.8*Launch + 0.6*T1Conf + 0.5*SPF - 1.0)
        logit = (
            1.5 * feat["service_penetration"]
            + 1.0 * (feat["engagement_score"] / 100.0)
            + 0.8 * feat["launch_indicator"]
            + 0.6 * (feat["tier_1_conf_count"] / 3.0) # normalized roughly
            + 0.5 * accounts[accounts.account_id == acc_id].strategic_priority_flag.iloc[0]
            - 2.3 # adjust bias for ~35% win rate
        )
        account_outcome_probs[acc_id] = sigmoid(logit)
    
    # Update Opportunity Status based on account-level probability
    def assign_status(row):
        prob = account_outcome_probs[row['account_id']]
        if np.random.random() < prob:
            return "won"
        else:
            return "lost"
            
    # For training, we only care about closed deals for the label
    # We overwrite the random status from generate_opportunities
    opps['status'] = opps.apply(assign_status, axis=1)
    
    # 3. Save to data/training/
    output_dir = "data/training"
    os.makedirs(output_dir, exist_ok=True)
    
    accounts.to_csv(os.path.join(output_dir, "accounts.csv"), index=False)
    opps.to_csv(os.path.join(output_dir, "opportunities.csv"), index=False)
    metrics.to_csv(os.path.join(output_dir, "snowflake_metrics.csv"), index=False)
    funds.to_csv(os.path.join(output_dir, "external_funds.csv"), index=False)
    confs.to_csv(os.path.join(output_dir, "conferences.csv"), index=False)
    attendance.to_csv(os.path.join(output_dir, "conference_attendance.csv"), index=False)
    
    print(f"Data generation complete. Files saved to {output_dir}")
    print(f"Overall Win Rate: {len(opps[opps.status == 'won']) / len(opps):.2%}")

if __name__ == "__main__":
    main()
