"""POC3 whitespace scoring and clustering constants (POC3_Requirements_v3 §05)."""

from app.core.constants import EXPECTED_REVENUE_MAP

EXPANSION_WEIGHT = {"Low": 0.3, "Medium": 0.6, "High": 1.0}

WS_SCORE_WEIGHTS = {"revenue": 0.5, "expansion": 0.3, "strategic": 0.2}

WS_HIGH_THRESHOLD = 0.7

KMEANS_K = 5
KMEANS_RANDOM_STATE = 42
KMEANS_N_INIT = 10

MODEL_VERSION_POC3 = "poc3_v1+router_v1"

__all__ = [
    "EXPECTED_REVENUE_MAP",
    "EXPANSION_WEIGHT",
    "WS_SCORE_WEIGHTS",
    "WS_HIGH_THRESHOLD",
    "KMEANS_K",
    "KMEANS_RANDOM_STATE",
    "KMEANS_N_INIT",
    "MODEL_VERSION_POC3",
]
