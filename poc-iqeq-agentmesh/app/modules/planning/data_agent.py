import pandas as pd
from app.core.paths import DATA_RAW
from app.core.progress_tracker import tracker

def run_data_agent(trace_id: str = None):
    tracker.emit("ag-data", "started", message="Loading synthetic datasets from data/raw/...", trace_id=trace_id)
    
    tables = [
        "accounts", "opportunities", "snowflake_metrics", 
        "external_funds", "conferences", "conference_attendance",
        "contacts", "account_product_matrix", "product_catalog"
    ]
    
    raw_data = {}
    for table in tables:
        path = DATA_RAW / f"{table}.csv"
        if not path.exists():
            error_msg = f"Missing required data file: {path}"
            tracker.emit("ag-data", "error", error_msg, trace_id=trace_id)
            raise FileNotFoundError(error_msg)
        
        raw_data[table] = pd.read_csv(path)
    
    # Validation: Referential Integrity
    tracker.emit("ag-data", "processing", message="Validating referential integrity...", trace_id=trace_id)
    account_ids = set(raw_data["accounts"].account_id)
    
    for table in [
        "opportunities",
        "snowflake_metrics",
        "external_funds",
        "conference_attendance",
        "contacts",
        "account_product_matrix",
    ]:
        orphans = raw_data[table][~raw_data[table].account_id.isin(account_ids)]
        if not orphans.empty:
            error_msg = f"Data Integrity Error: {len(orphans)} orphaned records in {table}"
            tracker.emit("ag-data", "error", error_msg, trace_id=trace_id)
            raise ValueError(error_msg)

    cat_ids = set(raw_data["product_catalog"].product_id)
    bad_p = raw_data["account_product_matrix"][
        ~raw_data["account_product_matrix"].product_id.isin(cat_ids)
    ]
    if not bad_p.empty:
        error_msg = f"Data Integrity Error: {len(bad_p)} matrix rows with unknown product_id"
        tracker.emit("ag-data", "error", error_msg, trace_id=trace_id)
        raise ValueError(error_msg)
            
    tracker.emit("ag-data", "completed", message=f"Data Agent successfully loaded {len(raw_data['accounts'])} accounts.", trace_id=trace_id)
    return raw_data
