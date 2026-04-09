"""
IQ-EQ Targeting & Triage Agent — Synthetic Data Generator
==========================================================
Generates 5 fully synthetic, referentially consistent CSV datasets:
  - accounts.csv
  - opportunities.csv
  - snowflake_metrics.csv
  - external_funds.csv
  - conferences.csv

Usage:
    pip install pandas faker numpy
    python generate_synthetic_data.py

Outputs all CSVs into data/synthetic_data/ (relative to repo root).
"""

import os
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

random.seed(42)
np.random.seed(42)
fake = Faker("en_GB")
Faker.seed(42)

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "synthetic_data"))
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def rand_date(start: str, end: str) -> date:
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    return s + timedelta(days=random.randint(0, (e - s).days))


def maybe(value, probability=0.8):
    """Return value with given probability, else None."""
    return value if random.random() < probability else None


def rand_id(prefix: str, num: int, zfill: int = 4) -> str:
    return f"{prefix}{str(num).zfill(zfill)}"


# ─────────────────────────────────────────────
# STEP 1: CONFERENCES (20 rows)
# ─────────────────────────────────────────────

def generate_conferences(n: int = 20) -> pd.DataFrame:
    themes = [
        "ESG Integration in Private Equity",
        "T+1 Settlement Readiness",
        "Private Debt Structures",
        "AIFMD II Compliance",
        "Operational Alpha in Fund Admin",
        "Digital Transformation in Asset Management",
        "Depositary Governance",
        "Middle Office Automation",
        "Regulatory Reporting & SFDR",
        "Cross-border Fund Distribution",
    ]
    cities = {
        "LU": "Luxembourg City",
        "NL": "Amsterdam",
        "FR": "Paris",
        "IT": "Milan",
    }
    conference_names = [
        "IQ-EQ Lux Funds Summit",
        "Amsterdam Asset Owners Forum",
        "Paris Private Capital Conference",
        "Milan Alternatives Congress",
        "LPEA Annual Congress",
        "ALFI Global Distribution Conference",
        "Private Equity Netherlands Summit",
        "Fund Finance Forum Europe",
        "ESG in Finance Brussels",
        "AIC Annual Conference London",
        "Europlace Finance Forum",
        "Funds Europe Awards",
        "Private Debt Investor Europe",
        "Real Assets Europe",
        "Infra Investor Global Summit",
        "IQ-EQ NL Roundtable",
        "IQ-EQ FR Client Day",
        "KPMG Funds Tax Summit LU",
        "Intertrust PIAO Forum",
        "Caceis Fund Administration Summit",
    ]
    rows = []
    for i in range(1, n + 1):
        country_code = random.choice(list(cities.keys()))
        year = random.choice([2024, 2025, 2026])
        conf_date = rand_date(f"{year}-01-01", f"{year}-03-01" if year == 2026 else f"{year}-12-31")
        rows.append({
            "conference_id": f"CONF_{country_code}_{year}_{i:02d}",
            "name": f"{conference_names[i - 1]} {year}",
            "date": conf_date.isoformat(),
            "location": f"{cities[country_code]}, {country_code}",
            "theme": themes[(i - 1) % len(themes)],
            "accounts_present": "",  # filled after accounts are generated
            "engagement_score": round(random.uniform(0.3, 1.0), 2),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# STEP 2: ACCOUNTS (150 rows)
# ─────────────────────────────────────────────

FUND_PREFIXES = {
    "LU": ["Lux", "Grand Duchy", "Europa", "Luxembourg"],
    "NL": ["Amsterdam", "Dutch", "Holland", "NL"],
    "FR": ["Paris", "Seine", "Gallic", "FR"],
    "IT": ["Milan", "Adriatic", "Italian", "IT"],
}
FUND_TYPES = ["PE Fund", "Infra Fund", "Real Estate Fund", "Private Debt Fund", "Mid-Market Fund", "Growth Fund"]
LEGAL_SUFFIXES = {
    "LU": ["SCSp", "SCA", "SICAV", "SICAR"],
    "NL": ["BV", "CV", "NV", "FGR"],
    "FR": ["SAS", "FPCI", "SCPI", "SA"],
    "IT": ["SpA", "SRL", "FIA", "FP"],
}


def fund_name(country: str, idx: int) -> str:
    prefix = random.choice(FUND_PREFIXES[country])
    ftype = random.choice(FUND_TYPES)
    # POC: ESG names more likely to get esg_policy_support_flag in snowflake_metrics
    if random.random() < 0.22:
        ftype = random.choice(["Green " + ftype, "ESG " + ftype, "Sustainable " + ftype])
    roman = ["I", "II", "III", "IV", "V"][idx % 5]
    suffix = random.choice(LEGAL_SUFFIXES[country])
    return f"{prefix} {ftype} {roman} {suffix}"


def generate_accounts(conferences_df: pd.DataFrame, n: int = 150) -> pd.DataFrame:
    conf_ids = conferences_df["conference_id"].tolist()

    # Country distribution: ~60% LU/NL, ~40% FR/IT
    countries = (
        ["LU"] * 45 + ["NL"] * 45 + ["FR"] * 30 + ["IT"] * 30
    )
    random.shuffle(countries)
    countries = countries[:n]

    rows = []
    for i, country in enumerate(countries, 1):
        acc_id = f"ACC_{country}_{i:04d}"
        status = "client" if random.random() < 0.60 else "prospect"
        segment = "FAM" if random.random() < 0.55 else "PIAO"
        rel_start = maybe(rand_date("2017-01-01", "2025-12-31").isoformat(), 1.0 if status == "client" else 0.0)
        last_contact = maybe(rand_date("2025-01-01", "2026-03-01").isoformat(), 0.75)
        conf = maybe(random.choice(conf_ids), 0.5)
        rows.append({
            "account_id": acc_id,
            "name": fund_name(country, i),
            "country": country,
            "segment": segment,
            "status": status,
            "key_contact": fake.email(),
            "iqeq_relationship_start_date": rel_start if status == "client" else None,
            "last_contact_date": last_contact,
            "associated_conference_id": conf,
            "strategic_priority_flag": random.random() < 0.40,
        })

    df = pd.DataFrame(rows)

    # Back-fill conference.accounts_present
    for conf_id in conf_ids:
        members = df[df["associated_conference_id"] == conf_id]["account_id"].tolist()
        conferences_df.loc[conferences_df["conference_id"] == conf_id, "accounts_present"] = ";".join(members)

    return df


# ─────────────────────────────────────────────
# STEP 3: OPPORTUNITIES (~800 rows)
# ─────────────────────────────────────────────

PRODUCT_LINES = ["Fund Admin", "AIFM", "Depositary", "Middle Office", "ESG Reporting", "Regulatory"]
STAGES_OPEN = ["Prospecting", "Proposal", "Negotiation"]
COMPETITORS = ["Competitor A", "Competitor B", "Competitor C", ""]
WIN_LOSS_CODES = ["PRICE", "ONBOARDING_SPEED", "COVERAGE", "COMPETITOR_RELATIONSHIP", "OTHER"]
WIN_NOTES = {
    "PRICE": "Client confirmed our pricing was competitive and within the approved budget envelope.",
    "ONBOARDING_SPEED": "Our rapid onboarding capability was a decisive factor in the client's selection.",
    "COVERAGE": "Our broad coverage across the required jurisdictions exceeded all other proposals.",
    "COMPETITOR_RELATIONSHIP": "Existing long-term relationship with IQ-EQ team outweighed competitor's lower price.",
    "OTHER": "A combination of service quality and responsiveness led to a successful close.",
}
LOSS_NOTES = {
    "PRICE": "Client selected a competitor offering a lower fee structure for the same service scope.",
    "ONBOARDING_SPEED": "Competitor promised a faster go-live timeline which was critical for the fund launch.",
    "COVERAGE": "Our current coverage in the required domicile was insufficient for the mandate.",
    "COMPETITOR_RELATIONSHIP": "Incumbent provider retained mandate due to entrenched relationship with CFO.",
    "OTHER": "Deal stalled due to internal restructuring at the client; no clear next steps.",
}


def generate_opportunities(accounts_df: pd.DataFrame, target: int = 800) -> pd.DataFrame:
    account_ids = accounts_df["account_id"].tolist()
    # Large funds (PE/Infra) get larger deals
    large_keywords = ["PE Fund", "Infra Fund", "Private Debt"]

    rows = []
    opp_num = 1
    while len(rows) < target:
        acc_id = random.choice(account_ids)
        acc_name = accounts_df[accounts_df["account_id"] == acc_id]["name"].values[0]
        is_large = any(kw in acc_name for kw in large_keywords)
        close_date = rand_date("2022-01-01", "2026-03-01")
        stage = random.choices(
            STAGES_OPEN + ["Closed Won", "Closed Lost"],
            weights=[5, 5, 3, 10, 10], k=1
        )[0]
        # POC: status is won/lost; must align when stage is Closed Won/Lost; open pipeline uses stage
        if stage == "Closed Won":
            status = "won"
            wl_code = random.choice(WIN_LOSS_CODES)
            wl_note = WIN_NOTES.get(wl_code, "")
        elif stage == "Closed Lost":
            status = "lost"
            wl_code = random.choice(WIN_LOSS_CODES)
            wl_note = LOSS_NOTES.get(wl_code, "")
        else:
            status = ""
            wl_code = ""
            wl_note = ""

        rows.append({
            "opp_id": f"OPP_{opp_num:06d}",
            "account_id": acc_id,
            "close_date": close_date.isoformat(),
            "stage": stage,
            "status": status,
            "product_line": random.choice(PRODUCT_LINES),
            "deal_size_eur": int(
                random.uniform(500_000, 5_000_000) if is_large else random.uniform(50_000, 1_500_000)
            ),
            "competitor": random.choice(COMPETITORS),
            "win_loss_reason_code": wl_code,
            "win_loss_notes": wl_note,
        })
        opp_num += 1

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# STEP 4: SNOWFLAKE METRICS (one per account)
# ─────────────────────────────────────────────

def generate_snowflake_metrics(accounts_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, acc in accounts_df.iterrows():
        total_fund_aum = int(random.uniform(100_000_000, 3_000_000_000))
        current_aum = 0 if acc["status"] == "prospect" else int(random.uniform(0, total_fund_aum))
        rev_fa = int(random.uniform(0, 600_000)) if current_aum > 0 else 0
        rev_mo = int(random.uniform(0, 400_000)) if (current_aum > 0 and random.random() < 0.45) else 0
        has_esg = any(kw in acc["name"] for kw in ["Green", "ESG", "Sustainable"])
        rows.append({
            "account_id": acc["account_id"],
            "current_aum_with_iqeq": current_aum,
            "total_fund_aum": total_fund_aum,
            "revenue_fund_admin": rev_fa,
            "revenue_middle_office": rev_mo,
            "yoy_revenue_growth": round(random.uniform(-0.2, 0.3), 3),
            "service_penetration_score": round(current_aum / total_fund_aum, 3) if total_fund_aum > 0 else 0.0,
            "existing_middle_office_flag": rev_mo > 0,
            "esg_policy_support_flag": has_esg or random.random() < 0.35,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# STEP 5: EXTERNAL FUNDS (200 rows)
# ─────────────────────────────────────────────

ASSET_CLASSES = ["PE", "RE", "Infra", "Private Debt"]
STRATEGY_MAP = {
    "PE": ["Buyout", "Mid-market", "Growth", "Venture", "Distressed"],
    "RE": ["Core", "Value-Add", "Opportunistic", "Logistics", "Residential"],
    "Infra": ["Renewables", "Transportation", "Digital Infra", "Social Infra"],
    "Private Debt": ["Senior Secured", "Mezzanine", "Direct Lending", "Unitranche"],
}
REGIONS = ["Europe", "Western Europe", "Global", "Pan-European"]


def _account_name_prefix(account_name: str) -> str:
    # Training matches external_funds.manager_name first token to account name start
    return account_name.split()[0]


def generate_external_funds(accounts_df: pd.DataFrame, n: int = 200) -> pd.DataFrame:
    countries = ["LU", "NL", "FR", "IT"]
    rows = []
    fund_seq = 0

    # POC: ≥20 accounts with an upcoming launch — tie funds to name prefix match used in ML join
    launch_accounts = accounts_df.sample(n=min(24, len(accounts_df)), random_state=42)
    for _, acc in launch_accounts.iterrows():
        fund_seq += 1
        country = acc["country"]
        asset_class = random.choice(ASSET_CLASSES)
        strategies = random.sample(STRATEGY_MAP[asset_class], k=random.randint(1, 3))
        prefix = _account_name_prefix(acc["name"])
        rows.append({
            "fund_id": f"FUND_{country}_{9000 + fund_seq}",
            "manager_name": f"{prefix} Capital Partners",
            "domicile": country,
            "asset_class": asset_class,
            "aum_eur": int(random.uniform(100_000_000, 3_000_000_000)),
            "next_launch_date": rand_date("2026-04-01", "2027-12-31").isoformat(),
            "last_launch_date": maybe(rand_date("2022-01-01", "2024-12-31").isoformat(), 0.7),
            "strategy_tags": "; ".join(strategies),
            "launch_region_focus": random.choice(REGIONS),
        })

    while len(rows) < n:
        fund_seq += 1
        country = random.choices(countries, weights=[40, 25, 20, 15])[0]
        asset_class = random.choice(ASSET_CLASSES)
        strategies = random.sample(STRATEGY_MAP[asset_class], k=random.randint(1, 3))
        linked_name = None
        if random.random() < 0.6:
            sample = accounts_df[accounts_df["country"] == country]
            if not sample.empty:
                linked_name = f"{_account_name_prefix(sample.sample(1, random_state=fund_seq).iloc[0]['name'])} Capital"

        next_launch = maybe(rand_date("2026-01-01", "2027-12-31").isoformat(), 0.30)
        last_launch = maybe(rand_date("2022-01-01", "2024-12-31").isoformat(), 0.60)
        rows.append({
            "fund_id": f"FUND_{country}_{9000 + fund_seq}",
            "manager_name": linked_name or fake.company(),
            "domicile": country,
            "asset_class": asset_class,
            "aum_eur": int(random.uniform(100_000_000, 3_000_000_000)),
            "next_launch_date": next_launch,
            "last_launch_date": last_launch,
            "strategy_tags": "; ".join(strategies),
            "launch_region_focus": random.choice(REGIONS),
        })

    df = pd.DataFrame(rows)
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


# ─────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────

def validate(accounts, opportunities, snowflake, conferences, external_funds):
    errors = []
    acc_ids = set(accounts["account_id"])
    ref_today = date.today()

    opp_fk = set(opportunities["account_id"]) - acc_ids
    if opp_fk:
        errors.append(f"Orphan account_ids in opportunities: {opp_fk}")

    snow_fk = set(snowflake["account_id"]) - acc_ids
    if snow_fk:
        errors.append(f"Orphan account_ids in snowflake_metrics: {snow_fk}")

    if len(snowflake) != len(accounts):
        errors.append(f"snowflake_metrics row count {len(snowflake)} != accounts {len(accounts)}")

    invalid_aum = snowflake[snowflake["current_aum_with_iqeq"] > snowflake["total_fund_aum"]]
    if not invalid_aum.empty:
        errors.append(f"{len(invalid_aum)} rows where current_aum > total_aum")

    # Closed stage vs status (POC alignment)
    closed = opportunities[opportunities["stage"].isin(["Closed Won", "Closed Lost"])]
    bad_status = closed[
        ((closed["stage"] == "Closed Won") & (closed["status"] != "won"))
        | ((closed["stage"] == "Closed Lost") & (closed["status"] != "lost"))
    ]
    if not bad_status.empty:
        errors.append(f"{len(bad_status)} opportunities with stage/status mismatch")

    # POC: ≥20 accounts with future next_launch_date on linked external_funds (same rule as train_propensity_model)
    upcoming_accs = set()
    for _, row in external_funds.iterrows():
        if pd.isna(row.get("next_launch_date")):
            continue
        try:
            nd = date.fromisoformat(str(row["next_launch_date"])[:10])
        except ValueError:
            continue
        if nd <= ref_today:
            continue
        mgr = str(row["manager_name"]).split(" ")[0].lower()
        matches = accounts[accounts["name"].str.lower().str.startswith(mgr)]
        for aid in matches["account_id"].tolist():
            upcoming_accs.add(aid)
    if len(upcoming_accs) < 20:
        errors.append(
            f"Only {len(upcoming_accs)} accounts linked to future launches (need ≥20 per POC)"
        )

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(f"  [FAIL] {e}")
    else:
        print("[OK] All validation checks passed.")
    return len(errors) == 0


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("Generating conferences...")
    conferences = generate_conferences(20)

    print("Generating accounts...")
    accounts = generate_accounts(conferences, 150)

    print("Generating opportunities...")
    opportunities = generate_opportunities(accounts, 800)

    print("Generating snowflake_metrics...")
    snowflake = generate_snowflake_metrics(accounts)

    print("Generating external_funds...")
    external_funds = generate_external_funds(accounts, 200)

    print("\nRunning validation...")
    valid = validate(accounts, opportunities, snowflake, conferences, external_funds)

    if valid:
        for name, df in [
            ("accounts", accounts),
            ("opportunities", opportunities),
            ("snowflake_metrics", snowflake),
            ("external_funds", external_funds),
            ("conferences", conferences),
        ]:
            path = os.path.join(OUTPUT_DIR, f"{name}.csv")
            df.to_csv(path, index=False)
            print(f"  Saved {path}  ({len(df)} rows)")

        print(f"\nAll 5 CSVs written to {OUTPUT_DIR}/")
        print("\nDataset summary:")
        print(f"  accounts:         {len(accounts)} rows   (clients: {(accounts['status']=='client').sum()}, prospects: {(accounts['status']=='prospect').sum()})")
        print(f"  opportunities:    {len(opportunities)} rows")
        print(f"  snowflake_metrics:{len(snowflake)} rows")
        print(f"  external_funds:   {len(external_funds)} rows  (upcoming launches: {external_funds['next_launch_date'].notna().sum()})")
        print(f"  conferences:      {len(conferences)} rows")
    else:
        print("\nERROR: Validation failed. CSVs not saved. Review errors above.")


if __name__ == "__main__":
    main()
