"""Load POC1 + POC2 CSVs from repo `data/raw` (paths relative to this package)."""
from pathlib import Path

import pandas as pd

from app.progress_tracker import tracker

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_RAW = REPO_ROOT / "data" / "raw"


def run_data_agent():
    tracker.emit("ag-data", "started", message=f"Loading datasets from {DATA_RAW}...")

    tables = [
        "accounts",
        "opportunities",
        "snowflake_metrics",
        "external_funds",
        "conferences",
        "conference_attendance",
        "contacts",
        "account_product_matrix",
        "product_catalog",
    ]

    raw_data = {}
    for table in tables:
        path = DATA_RAW / f"{table}.csv"
        if not path.exists():
            msg = f"Missing required data file: {path}"
            tracker.emit("ag-data", "error", msg)
            raise FileNotFoundError(msg)
        raw_data[table] = pd.read_csv(path)

    tracker.emit("ag-data", "processing", message="Validating referential integrity...")
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
            msg = f"Data Integrity Error: {len(orphans)} orphaned records in {table}"
            tracker.emit("ag-data", "error", msg)
            raise ValueError(msg)

    cat_ids = set(raw_data["product_catalog"].product_id)
    bad_p = raw_data["account_product_matrix"][
        ~raw_data["account_product_matrix"].product_id.isin(cat_ids)
    ]
    if not bad_p.empty:
        msg = f"Data Integrity Error: {len(bad_p)} matrix rows with unknown product_id"
        tracker.emit("ag-data", "error", msg)
        raise ValueError(msg)

    tracker.emit(
        "ag-data",
        "completed",
        message=f"Data Agent loaded {len(raw_data['accounts'])} accounts.",
    )
    return raw_data
