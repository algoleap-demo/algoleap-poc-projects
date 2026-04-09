"""
IQ-EQ Targeting & Triage Agent - SQLite Loader
==============================================
Loads synthetic CSV datasets into a local SQLite database.

Usage:
    python load_to_sqlite.py
"""

import os
import sqlite3
from typing import Dict

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "synthetic_data"))
DB_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "triage_poc.db"))

TABLE_FILE_MAP: Dict[str, str] = {
    "accounts": "accounts.csv",
    "opportunities": "opportunities.csv",
    "snowflake_metrics": "snowflake_metrics.csv",
    "external_funds": "external_funds.csv",
    "conferences": "conferences.csv",
}


def read_csv_tables() -> Dict[str, pd.DataFrame]:
    tables: Dict[str, pd.DataFrame] = {}
    for table, file_name in TABLE_FILE_MAP.items():
        path = os.path.join(DATA_DIR, file_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing CSV for table '{table}': {path}")
        tables[table] = pd.read_csv(path)
    return tables


def write_tables_to_sqlite(tables: Dict[str, pd.DataFrame]) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        for table, df in tables.items():
            df.to_sql(table, connection, if_exists="replace", index=False)
        # Add basic indexes to keep filter/query operations responsive in POC demos.
        connection.execute("CREATE INDEX IF NOT EXISTS idx_accounts_account_id ON accounts(account_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_account_id ON opportunities(account_id)")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_snowflake_metrics_account_id ON snowflake_metrics(account_id)"
        )
        connection.commit()


def validate_row_counts(tables: Dict[str, pd.DataFrame]) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        for table, df in tables.items():
            db_count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if db_count != len(df):
                raise ValueError(
                    f"Row count mismatch for {table}: sqlite={db_count}, csv={len(df)}"
                )


def main() -> None:
    print(f"Reading CSVs from: {DATA_DIR}")
    tables = read_csv_tables()
    print(f"Writing SQLite DB: {DB_PATH}")
    write_tables_to_sqlite(tables)
    validate_row_counts(tables)
    print("SQLite load complete. Row count validation passed.")
    for table, df in tables.items():
        print(f"  - {table}: {len(df)} rows")


if __name__ == "__main__":
    main()
