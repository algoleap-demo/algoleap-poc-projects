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

# Next Best Action (NBA) deterministic resolution
NBA_RESOLUTION = {
    "A": {
        "action_type": "call",
        "description": "Call this week",
        "reasoning": "Strong commercial signals paired with contextual catalysts mandate immediate direct engagement to capitalize on high propensity.",
        "due_in_days": 5
    },
    "B": {
        "action_type": "send_link",
        "description": "Send targeted product brief",
        "reasoning": "Moderate signals suggest targeted nurturing is the most efficient next step to deepen engagement before direct outreach.",
        "due_in_days": 10
    },
    "C": {
        "action_type": "schedule",
        "description": "Schedule quarterly check-in",
        "reasoning": "Low propensity and current signal volume favor long-term relationship maintenance and monitoring over immediate commercial action.",
        "due_in_days": 90
    }
}

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
