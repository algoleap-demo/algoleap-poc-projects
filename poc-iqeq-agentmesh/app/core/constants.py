# thresholds, NBA map, FEATURE_ORDER

# ML Thresholds
ML_HIGH_THRESHOLD = 0.70
ML_LOW_THRESHOLD = 0.30

# LLM Model Defaults
GEMINI_MODEL = "gemini-2.0-flash"
OPENAI_MODEL = "gpt-4o-mini"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Feature Order (The exact order XGBoost expects)
FEATURE_ORDER = [
    "win_rate",
    "avg_deal_size_eur",
    "open_opps_count",
    "service_penetration",
    "engagement_score",
    "launch_indicator",
    "tier_1_conf_count",
    "growth_metrics_qoq",
    "revenue_concentration"
]

# Country Enums
COUNTRIES = ["DE", "FR", "IT", "ES", "NL", "BE", "CH", "LU"]

# Segment Enums
SEGMENTS = ["FAM", "PIAO"]

# LLM Bucket Levels
LLM_BUCKET_TO_LEVEL = {
    "A": "High",
    "B": "Medium",
    "C": "Low"
}

# Deterministic NBA Resolution (Section 07.3 of Requirements)
NBA_RESOLUTION = {
    "A": {"action_type": "call", "description": "Call this week", "due_in_days": 5},
    "B": {"action_type": "send_link", "description": "Send targeted product brief", "due_in_days": 10},
    "C": {"action_type": "schedule", "description": "Schedule quarterly check-in", "due_in_days": 90}
}

# --- POC2 v3 (Account Planning) — locked tables / thresholds ---
ROLE_WEIGHTS = {
    "CEO": 1.0,
    "CFO": 0.95,
    "COO": 0.9,
    "Head of Ops": 0.8,
    "Portfolio Manager": 0.75,
    "Compliance": 0.6,
    "IT": 0.5,
    "Other": 0.3,
}

SENIORITY_WEIGHTS = {
    "C-Level": 1.0,
    "VP": 0.85,
    "Director": 0.7,
    "Manager": 0.5,
    "Individual Contributor": 0.3,
}

EXPECTED_REVENUE_MAP = {"Low": 50_000, "Medium": 150_000, "High": 300_000}

API_SCORE_WEIGHTS = {"propensity": 0.5, "whitespace": 0.3, "strategic": 0.2}

# Validation conflict thresholds (§06.1)
CONFLICT_HIGH_PROPENSITY_WS_MAX = 50_000
CONFLICT_LOW_PROPENSITY_WS_MIN = 500_000

MODEL_VERSION_POC2 = "xgb_propensity_v1+router_v1+poc2_v1"

