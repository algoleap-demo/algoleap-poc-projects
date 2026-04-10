import pandas as pd
import numpy as np
from datetime import datetime, timedelta

COMPANY_NAMES = [
    "Silverstone Ventures", "Alpine Peak Capital", "Rhone Global Partners", "Luminara Equity",
    "Nordic Horizon Wealth", "Elysian Fund Mgmt", "Beacon Asset Corp", "Vertex Portfolio",
    "Aragon Strategic", "Nexus Capital EU", "Solaris Institutional", "Marathon Growth",
    "Ironclad Holdings", "Stellar Partners", "Crestview Asset", "Obsidian Capital",
    "Vanguard Legacy", "Summit Trust", "Azure Blue Fund", "Pioneer Equities"
]

CONTACT_PERSONS = [
    "Sarah Müller", "Jean-Pierre Dubois", "Elena Rossi", "Marco Moretti", "Hans Schmidt",
    "Isabelle Fournier", "Luca Bianchi", "Ana Garcia", "Robert de Jong", "Julia Weber",
    "Paolo Romano", "Marie Lefebvre", "Klaus Fischer", "Sofia Conti", "Erik Janssen"
]

def generate_accounts(n: int, seed: int, id_start: int) -> pd.DataFrame:
    np.random.seed(seed)
    account_ids = [f"ACME-EU-{i:05d}" for i in range(id_start, id_start + n)]
    countries = ["DE", "FR", "IT", "ES", "NL", "BE", "CH", "LU"]
    segments = ["FAM", "PIAO"]
    
    # Generate realistic names
    acc_names = [np.random.choice(COMPANY_NAMES) + f" ({id_start+i})" for i in range(n)] if n > len(COMPANY_NAMES) else [COMPANY_NAMES[i] for i in range(n)]
    contacts = [np.random.choice(CONTACT_PERSONS) for _ in range(n)]
    
    df = pd.DataFrame({
        "account_id": account_ids,
        "account_name": acc_names,
        "contact_person": contacts,
        "country": np.random.choice(countries, n),
        "segment": np.random.choice(segments, n),
        "fund_size_eur": np.random.uniform(1e6, 5e9, n),
        "strategic_priority_flag": np.random.choice([True, False], n, p=[0.15, 0.85])
    })
    return df

def generate_opportunities(accounts_df: pd.DataFrame, seed: int, add_label: bool = False) -> pd.DataFrame:
    np.random.seed(seed)
    n_accounts = len(accounts_df)
    n_opps = n_accounts * 4
    
    account_ids = []
    for acc_id in accounts_df.account_id:
        account_ids.extend([acc_id] * 4)
        
    opp_ids = [f"OPP-{i:07d}" for i in range(1, n_opps + 1)]
    base_date = datetime(2026, 4, 8)
    open_dates = [(base_date - timedelta(days=np.random.randint(30, 365))).strftime('%Y-%m-%d') for _ in range(n_opps)]
    
    df = pd.DataFrame({
        "opportunity_id": opp_ids,
        "account_id": account_ids,
        "deal_size_eur": np.random.uniform(50000, 2000000, n_opps),
        "open_date": open_dates,
        "status": np.random.choice(["won", "lost", "open"], n_opps, p=[0.3, 0.4, 0.3])
    })
    
    df['close_date'] = df.apply(
        lambda row: (datetime.strptime(row['open_date'], '%Y-%m-%d') + timedelta(days=np.random.randint(10, 60))).strftime('%Y-%m-%d') 
        if row['status'] != 'open' else None, axis=1
    )
    
    if add_label:
        df['won_deal'] = df['status'] == 'won'
        
    return df

def generate_snowflake_metrics(accounts_df: pd.DataFrame, seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    n = len(accounts_df)
    df = pd.DataFrame({
        "account_id": accounts_df.account_id,
        "service_penetration": np.random.uniform(0.0, 1.0, n),
        "engagement_score": np.random.uniform(0.0, 100.0, n),
        "growth_metrics_qoq": np.random.uniform(-0.5, 1.5, n),
        "revenue_concentration": np.random.uniform(0.0, 1.0, n)
    })
    return df

def generate_external_funds(accounts_df: pd.DataFrame, seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    n_with_funds = int(len(accounts_df) * 0.6)
    sampled_accounts = accounts_df.sample(n=n_with_funds).account_id.tolist()
    fund_ids = [f"FUND-{i:07d}" for i in range(1, n_with_funds + 1)]
    base_date = datetime(2026, 4, 8)
    launch_dates = [(base_date - timedelta(days=np.random.randint(10, 300))).strftime('%Y-%m-%d') for _ in range(n_with_funds)]
    
    df = pd.DataFrame({
        "fund_record_id": fund_ids,
        "account_id": sampled_accounts,
        "launch_date": launch_dates,
        "launch_size_eur": np.random.uniform(1e6, 5e8, n_with_funds)
    })
    return df

def generate_conferences(seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    n = 25
    conf_ids = [f"CONF-{i:03d}" for i in range(1, n + 1)]
    base_date = datetime(2026, 4, 8)
    df = pd.DataFrame({
        "conference_id": conf_ids,
        "conference_name": [f"Conference {i}" for i in range(1, n + 1)],
        "conference_date": [(base_date - timedelta(days=np.random.randint(10, 200))).strftime('%Y-%m-%d') for _ in range(n)],
        "location": np.random.choice(["London", "Paris", "Luxembourg", "Frankfurt", "Milan"], n),
        "tier": np.random.choice(["tier_1", "tier_2", "tier_3"], n, p=[0.2, 0.5, 0.3])
    })
    return df

def generate_conference_attendance(accounts_df: pd.DataFrame, conferences_df: pd.DataFrame, seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    attendance_data = []
    conf_ids = conferences_df.conference_id.tolist()
    for acc_id in accounts_df.account_id:
        pct = np.random.random()
        if pct < 0.30: num = 0
        elif pct < 0.70: num = np.random.randint(1, 3)
        elif pct < 0.95: num = np.random.randint(3, 7)
        else: num = np.random.randint(7, 12)
        if num > 0:
            selected_confs = np.random.choice(conf_ids, size=min(num, len(conf_ids)), replace=False)
            for cid in selected_confs:
                attendance_data.append({
                    "account_id": acc_id,
                    "conference_id": cid,
                    "signal_strength": np.random.choice(["low", "medium", "high"])
                })
    return pd.DataFrame(attendance_data)
