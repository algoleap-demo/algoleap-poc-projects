# thresholds, NBA map, FEATURE_ORDER

# ML Thresholds
ML_HIGH_THRESHOLD = 0.70
ML_LOW_THRESHOLD = 0.30

# Feature Order (The exact order XGBoost expects)
FEATURE_ORDER = [
    "win_rate",
    "avg_deal_size_eur",
    "open_opps_count",
    "service_penetration",
    "engagement_score",
    "launch_indicator",
    "tier_1_conf_count",
    "growth_metrics_qoq"
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
