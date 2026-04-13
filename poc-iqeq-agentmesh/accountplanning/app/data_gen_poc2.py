import pandas as pd
import numpy as np

def generate_contacts(accounts, seed=42):
    np.random.seed(seed)
    contacts_data = []
    
    roles = ["CEO", "CFO", "COO", "Head of Ops", "Portfolio Manager", "Compliance", "IT", "Other"]
    seniorities = ["C-Level", "VP", "Director", "Manager", "Individual Contributor"]
    
    first_names = ["Lars", "Sofia", "Hans", "Elena", "Dieter", "Marta", "Luca", "Clara", "Sven", "Anna"]
    last_names = ["Muller", "Schmidt", "Dubois", "Lefebvre", "Rossi", "Bianchi", "Jansen", "De Vries", "Garcia", "Lopez"]
    
    for _, acc in accounts.iterrows():
        num_contacts = np.random.randint(3, 6) # 3 to 5
        for i in range(num_contacts):
            c_id = f"CNT-{acc['account_id'].split('-')[-1]}{i:02d}"
            role = np.random.choice(roles)
            # Ensure at least one C-Level or VP
            if i == 0:
                seniority = np.random.choice(["C-Level", "VP"])
            else:
                seniority = np.random.choice(seniorities)
                
            first = np.random.choice(first_names)
            last = np.random.choice(last_names)
            
            contacts_data.append({
                "contact_id": c_id,
                "account_id": acc["account_id"],
                "full_name": f"{first} {last}",
                "role": role,
                "seniority": seniority,
                "email": f"{first.lower()}.{last.lower()}@acme{c_id}.example",
                "engagement_score": round(np.random.uniform(0.1, 0.95), 2),
                "product_interests": ",".join(np.random.choice(["PROD-01", "PROD-02", "PROD-03"], size=np.random.randint(1, 3)))
            })
            
    return pd.DataFrame(contacts_data)

def generate_product_catalog():
    catalog = [
        ["PROD-01", "Fund Admin", "Mixed", "Low", 100000, "DE,FR,LU"],
        ["PROD-02", "Middle Office", "PE, RE", "High", 250000, "DE,UK,CH"],
        ["PROD-03", "ESG Reporting", "Mixed", "High", 150000, "FR,DE,NL"],
        ["PROD-04", "AIFMD", "PE, Hedge", "Medium", 120000, "LU,IE"],
        ["PROD-05", "Depositary", "PE, RE", "Medium", 180000, "LU,DE"],
        ["PROD-06", "Tax Services", "Private Client", "Medium", 80000, "CH,ES,IT"],
        ["PROD-07", "Private Client", "Private Client", "Low", 200000, "UK,CH"],
        ["PROD-08", "Transfer Agency", "Mixed", "Low", 90000, "LU,IE"]
    ]
    return pd.DataFrame(catalog, columns=["product_id", "product_line", "asset_class_fit", "expansion_potential", "typical_deal_size_eur", "region_fit"])

def generate_account_product_matrix(accounts, catalog, seed=42):
    np.random.seed(seed)
    matrix_data = []
    
    for _, acc in accounts.iterrows():
        for _, prod in catalog.iterrows():
            has_product = np.random.random() < 0.4 # 40% penetration
            current_rev = round(np.random.uniform(50000, 500000), 2) if has_product else 0.0
            potential = np.random.choice(["Low", "Medium", "High"], p=[0.3, 0.5, 0.2]) if not has_product else "None"
            priority = np.random.choice(["P1", "P2", "P3"]) if not has_product else "N/A"
            
            matrix_data.append({
                "account_id": acc["account_id"],
                "product_id": prod["product_id"],
                "has_product": has_product,
                "current_revenue_eur": current_rev,
                "potential_revenue_bucket": potential,
                "whitespace_priority": priority
            })
            
    return pd.DataFrame(matrix_data)
