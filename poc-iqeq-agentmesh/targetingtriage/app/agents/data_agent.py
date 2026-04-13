import os
import pandas as pd
from app.progress_tracker import tracker

def run_data_agent():
    tracker.emit("ag-data", "started", message="Loading synthetic datasets from data/synthetic/...")
    
    data_dir = "data/synthetic"
    tables = [
        "accounts", "opportunities", "snowflake_metrics", 
        "external_funds", "conferences", "conference_attendance",
        "contacts", "product_catalog", "account_product_matrix"
    ]
    
    raw_data = {}
    for table in tables:
        path = os.path.join(data_dir, f"{table}.csv")
        if not os.path.exists(path):
            error_msg = f"Missing required data file: {path}"
            tracker.emit("ag-data", "error", error_msg)
            raise FileNotFoundError(error_msg)
        
        raw_data[table] = pd.read_csv(path)
    
    # Validation: Referential Integrity
    tracker.emit("ag-data", "processing", message="Validating referential integrity...")
    account_ids = set(raw_data["accounts"].account_id)
    
    # Shared check for all account-mapped tables
    acc_mapped_tables = [
        "opportunities", "snowflake_metrics", "external_funds", 
        "conference_attendance", "contacts", "account_product_matrix"
    ]
    
    for table in acc_mapped_tables:
        orphans = raw_data[table][~raw_data[table].account_id.isin(account_ids)]
        if not orphans.empty:
            error_msg = f"Data Integrity Error: {len(orphans)} orphaned records in {table}"
            tracker.emit("ag-data", "error", error_msg)
            raise ValueError(error_msg)
            
    tracker.emit("ag-data", "completed", message=f"Data Agent successfully loaded {len(raw_data['accounts'])} accounts.")
    return raw_data
