import pandas as pd
import numpy as np
import os

# Seed for reproducibility
np.random.seed(42)

def generate_poc2_data():
    print("Initiating POC 2 Data Generation...")
    
    # 1. Load Core Accounts
    accounts_path = "data/raw/accounts.csv"
    if not os.path.exists(accounts_path):
        print(f"Error: {accounts_path} not found. Please run POC 1 data gen first.")
        return
    
    accounts_df = pd.read_csv(accounts_path)
    account_ids = accounts_df['account_id'].tolist()
    
    output_dir = "data/raw"
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Generate Contacts
    print("Generating Contacts...")
    roles = ["Chief Financial Officer", "General Counsel", "Head of Fund Operations", "Investment Director", "Compliance Officer"]
    contacts_data = []
    
    for acc_id in account_ids:
        # Generate 2-4 contacts per account
        num_contacts = np.random.randint(2, 5)
        for _ in range(num_contacts):
            role = np.random.choice(roles)
            first_name = np.random.choice(["James", "Anne", "Thomas", "Sarah", "Philip", "Elena", "Marcus", "Sophie"])
            last_name = np.random.choice(["Smith", "Müller", "Dupont", "Rossi", "Vermeulen", "Schmidt", "Lefebvre"])
            
            contacts_data.append({
                "contact_id": f"CON-{np.random.randint(10000, 99999)}",
                "account_id": acc_id,
                "name": f"{first_name} {last_name}",
                "role": role,
                "email": f"{first_name.lower()}.{last_name.lower()}@external.com",
                "is_primary": False
            })
            
    contacts_df = pd.DataFrame(contacts_data)
    # Ensure one primary contact per account
    for acc_id in account_ids:
        contacts_df.loc[contacts_df[contacts_df.account_id == acc_id].index[0], "is_primary"] = True
        
    contacts_df.to_csv(os.path.join(output_dir, "contacts.csv"), index=False)
    print(f"Saved contacts.csv ({len(contacts_df)} records)")
    
    # 3. Generate Product Matrix (Whitespace)
    print("Generating Account-Product Matrix...")
    products = [
        {"product_id": "P-FA", "product_name": "Fund Administration"},
        {"product_id": "P-DEP", "product_name": "Depositary Services"},
        {"product_id": "P-GRC", "product_name": "Governance, Risk & Compliance"},
        {"product_id": "P-KYC", "product_name": "KYC/AML Outsourcing"},
        {"product_id": "P-ESG", "product_name": "ESG Reporting"},
        {"product_id": "P-CORP", "product_name": "Corporate Secretarial"}
    ]
    
    matrix_data = []
    product_catalog = []
    
    for p in products:
        product_catalog.append(p)
    
    for acc_id in account_ids:
        # Randomly assign 1-3 active products
        num_active = np.random.randint(1, 4)
        active_indices = np.random.choice(len(products), num_active, replace=False)
        
        for i, p in enumerate(products):
            is_active = i in active_indices
            matrix_data.append({
                "account_id": acc_id,
                "product_id": p["product_id"],
                "is_active": is_active,
                "current_revenue_eur": np.random.randint(5000, 50000) if is_active else 0,
                "last_review_date": "2024-01-15" if is_active else None
            })
            
    matrix_df = pd.DataFrame(matrix_data)
    matrix_df.to_csv(os.path.join(output_dir, "account_product_matrix.csv"), index=False)
    
    catalog_df = pd.DataFrame(product_catalog)
    catalog_df.to_csv(os.path.join(output_dir, "product_catalog.csv"), index=False)
    
    print(f"Saved account_product_matrix.csv ({len(matrix_df)} records)")
    print(f"Saved product_catalog.csv ({len(catalog_df)} records)")
    print("POC 2 Data Generation Complete.")

if __name__ == "__main__":
    generate_poc2_data()
