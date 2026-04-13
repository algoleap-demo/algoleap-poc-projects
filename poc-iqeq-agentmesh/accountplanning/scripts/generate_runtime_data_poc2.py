import os
import sys
import pandas as pd

# Add the root and app directories to path to import dependencies
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "accountplanning"))

from accountplanning.app.data_gen_poc2 import (
    generate_contacts,
    generate_product_catalog,
    generate_account_product_matrix
)

def main():
    print("Starting POC 2 runtime data generation...")
    output_dir = "accountplanning/data/synthetic"
    os.makedirs(output_dir, exist_ok=True)
    
    # Load base accounts from Targeting POC
    base_data_path = "targetingtriage/data/synthetic/accounts.csv"
    if not os.path.exists(base_data_path):
        print(f"Error: Base accounts not found at {base_data_path}. Run POC 1 data gen first.")
        return
    
    accounts = pd.read_csv(base_data_path)
    seed = 44 # Different seed for POC 2
    
    # 1. Generate POC 2 files
    print("Generating contacts...")
    contacts = generate_contacts(accounts, seed)
    
    print("Generating product catalog...")
    catalog = generate_product_catalog()
    
    print("Generating account-product matrix...")
    matrix = generate_account_product_matrix(accounts, catalog, seed)
    
    # 2. Hand-Engineering for Golden Path (ACME-EU-90001)
    # Target: High API score (Propensity 0.84 + WS Potential High + Strategic)
    acc_1 = "ACME-EU-90001"
    
    # Ensure 5 contacts, 2 C-Level
    # (Already handled by data_gen_poc2 logic for account_id end in '1')
    
    # Ensure high whitespace potential
    # Set 4 products to has_product=False and potential=High
    ws_products = ["PROD-02", "PROD-03", "PROD-04", "PROD-05"]
    for p_id in ws_products:
        matrix.loc[(matrix.account_id == acc_1) & (matrix.product_id == p_id), ["has_product", "potential_revenue_bucket", "current_revenue_eur"]] = [False, "High", 0.0]

    # 3. Hand-Engineering Conflicts
    # 90002: High Propensity + Zero Whitespace
    acc_2 = "ACME-EU-90002"
    matrix.loc[matrix.account_id == acc_2, "has_product"] = True
    matrix.loc[matrix.account_id == acc_2, "potential_revenue_bucket"] = "None"
    
    # 90003: Low Propensity + Huge Whitespace
    acc_3 = "ACME-EU-90003"
    matrix.loc[matrix.account_id == acc_3, "has_product"] = False
    matrix.loc[matrix.account_id == acc_3, "potential_revenue_bucket"] = "High"

    # 4. Save files
    contacts.to_csv(os.path.join(output_dir, "contacts.csv"), index=False)
    catalog.to_csv(os.path.join(output_dir, "product_catalog.csv"), index=False)
    matrix.to_csv(os.path.join(output_dir, "account_product_matrix.csv"), index=False)
    
    print(f"POC 2 data generation complete. Files saved to {output_dir}")

if __name__ == "__main__":
    main()
