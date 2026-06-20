import pandas as pd
import numpy as np
import os

# --- Configurations ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data", "synthetic")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.csv")

# --- IQ-EQ Product Catalog ---
PRODUCTS = [
    {"product_id": "P-001", "product_name": "Fund Administration", "category": "Fund Services"},
    {"product_id": "P-002", "product_name": "Corporate Secretarial", "category": "Corporate Services"},
    {"product_id": "P-003", "product_name": "ESG Reporting", "category": "Compliance"},
    {"product_id": "P-004", "product_name": "Depositary Services", "category": "Fund Services"},
    {"product_id": "P-005", "product_name": "Agency & Trustee", "category": "Private Wealth"},
    {"product_id": "P-006", "product_name": "Tax Compliance", "category": "Compliance"},
    {"product_id": "P-007", "product_name": "Regulatory Reporting", "category": "Compliance"}
]

ROLES = ["GP", "CFO", "Compliance Officer", "Portfolio Manager", "Investment Director"]

def generate_poc2_data(seed: int = 42):
    np.random.seed(seed)
    
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"Error: {ACCOUNTS_FILE} not found. Run main data_gen first.")
        return

    accounts_df = pd.read_csv(ACCOUNTS_FILE)
    account_ids = accounts_df["account_id"].tolist()
    n_accounts = len(account_ids)

    # 1. Generate Product Catalog
    catalog_df = pd.DataFrame(PRODUCTS)
    catalog_df.to_csv(os.path.join(DATA_DIR, "product_catalog.csv"), index=False)
    print(f"Generated product_catalog.csv with {len(PRODUCTS)} items.")

    # 2. Generate Contacts (1:N)
    contacts_data = []
    contact_id_counter = 1
    
    from app.data_gen import CONTACT_PERSONS # Reuse existing names
    
    for acc_id in account_ids:
        # Each account has 1-3 contacts
        n_contacts = np.random.randint(1, 4)
        for _ in range(n_contacts):
            name = np.random.choice(CONTACT_PERSONS)
            role = np.random.choice(ROLES)
            email = f"{name.lower().replace(' ', '.')}@{acc_id.lower()}.com"
            contacts_data.append({
                "contact_id": f"CON-{contact_id_counter:05d}",
                "account_id": acc_id,
                "contact_name": name,
                "role": role,
                "email": email
            })
            contact_id_counter += 1
            
    pd.DataFrame(contacts_data).to_csv(os.path.join(DATA_DIR, "contacts.csv"), index=False)
    print(f"Generated contacts.csv with {len(contacts_data)} records.")

    # 3. Generate Account-Product Matrix (M:N) - The Whitespace
    matrix_data = []
    product_ids = [p["product_id"] for p in PRODUCTS]
    
    for acc_id in account_ids:
        for prod_id in product_ids:
            # Does this account currently use this product?
            is_active = np.random.choice([True, False], p=[0.3, 0.7])
            revenue = np.random.uniform(5000, 50000) if is_active else 0
            
            matrix_data.append({
                "account_id": acc_id,
                "product_id": prod_id,
                "is_active": is_active,
                "current_revenue_eur": int(revenue)
            })
            
    pd.DataFrame(matrix_data).to_csv(os.path.join(DATA_DIR, "account_product_matrix.csv"), index=False)
    print(f"Generated account_product_matrix.csv with {len(matrix_data)} combinations.")

if __name__ == "__main__":
    generate_poc2_data()
