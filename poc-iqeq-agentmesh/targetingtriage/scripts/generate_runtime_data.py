import os
import pandas as pd
import numpy as np
from datetime import datetime
from targetingtriage.app.data_gen import (
    generate_accounts, 
    generate_opportunities, 
    generate_snowflake_metrics, 
    generate_external_funds, 
    generate_conferences, 
    generate_conference_attendance
)

def main():
    print("Starting runtime data generation (n=50)...")
    seed = 43
    n_accounts = 50
    id_start = 90001
    
    # 1. Generate Base Data
    accounts = generate_accounts(n_accounts, seed, id_start)
    opps = generate_opportunities(accounts, seed)
    metrics = generate_snowflake_metrics(accounts, seed)
    funds = generate_external_funds(accounts, seed)
    confs = generate_conferences(seed)
    attendance = generate_conference_attendance(accounts, confs, seed)
    
    # 2. Hand-Engineering Special Demo Accounts
    
    print("Hand-engineering special demo accounts...")
    
    # ACME-EU-90001: Golden Path -> Bucket A
    # 4 won opps, 5 tier-1 conferences, 2 recent fund launches
    acc_1 = "ACME-EU-90001"
    opps.loc[opps.account_id == acc_1, "status"] = "won"
    metrics.loc[metrics.account_id == acc_1, ["service_penetration", "engagement_score"]] = [0.85, 90.0]
    
    # Ensure 5 tier-1 conferences
    t1_confs = confs[confs.tier == "tier_1"].conference_id.tolist()
    # Clear existing attendance for this account
    attendance = attendance[attendance.account_id != acc_1]
    # Add new attendance
    new_attendance = []
    for cid in t1_confs[:5]:
        new_attendance.append({"account_id": acc_1, "conference_id": cid, "signal_strength": "high"})
    attendance = pd.concat([attendance, pd.DataFrame(new_attendance)], ignore_index=True)
    
    # Ensure 2 recent fund launches
    funds = funds[funds.account_id != acc_1]
    new_funds = [
        {"fund_record_id": "FUND-G1", "account_id": acc_1, "launch_date": "2026-03-15", "launch_size_eur": 500000000},
        {"fund_record_id": "FUND-G2", "account_id": acc_1, "launch_date": "2026-02-20", "launch_size_eur": 250000000}
    ]
    funds = pd.concat([funds, pd.DataFrame(new_funds)], ignore_index=True)
    
    # ACME-EU-90002 to 90004: Engineered Conflicts
    # 90002: High ML (all won) but Zero Context (no funds, no conferences) -> ML High / LLM Low or Med
    acc_2 = "ACME-EU-90002"
    opps.loc[opps.account_id == acc_2, "status"] = "won"
    funds = funds[funds.account_id != acc_2]
    attendance = attendance[attendance.account_id != acc_2]
    metrics.loc[metrics.account_id == acc_2, "service_penetration"] = 0.9
    
    # 90003: Low ML (all lost) but High Context (3 t1 confs, 2 recent funds) -> ML Low / LLM High or Med
    acc_3 = "ACME-EU-90003"
    opps.loc[opps.account_id == acc_3, "status"] = "lost"
    metrics.loc[metrics.account_id == acc_3, "service_penetration"] = 0.1
    new_attendance = []
    for cid in t1_confs[:3]:
        new_attendance.append({"account_id": acc_3, "conference_id": cid, "signal_strength": "high"})
    attendance = pd.concat([attendance, pd.DataFrame(new_attendance)], ignore_index=True)
    new_funds = [
        {"fund_record_id": "FUND-C1", "account_id": acc_3, "launch_date": "2026-03-10", "launch_size_eur": 100000000},
        {"fund_record_id": "FUND-C2", "account_id": acc_3, "launch_date": "2026-03-20", "launch_size_eur": 150000000}
    ]
    funds = pd.concat([funds, pd.DataFrame(new_funds)], ignore_index=True)

    # ACME-EU-90005 to 90009: Clear Bucket C
    for acc_id in [f"ACME-EU-{i:05d}" for i in range(90005, 90010)]:
        opps.loc[opps.account_id == acc_id, "status"] = "lost"
        metrics.loc[metrics.account_id == acc_id, ["service_penetration", "engagement_score"]] = [0.1, 10.0]
        funds = funds[funds.account_id != acc_id]
        attendance = attendance[attendance.account_id != acc_id]

    # 3. Save to data/raw/
    output_dir = "data/raw"
    os.makedirs(output_dir, exist_ok=True)
    
    accounts.to_csv(os.path.join(output_dir, "accounts.csv"), index=False)
    opps.to_csv(os.path.join(output_dir, "opportunities.csv"), index=False)
    metrics.to_csv(os.path.join(output_dir, "snowflake_metrics.csv"), index=False)
    funds.to_csv(os.path.join(output_dir, "external_funds.csv"), index=False)
    confs.to_csv(os.path.join(output_dir, "conferences.csv"), index=False)
    attendance.to_csv(os.path.join(output_dir, "conference_attendance.csv"), index=False)
    
    print(f"Runtime data generation complete. Files saved to {output_dir}")

if __name__ == "__main__":
    main()
