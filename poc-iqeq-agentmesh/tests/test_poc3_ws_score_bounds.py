"""POC3: ws_score in [0, 1] for whitespace cells."""

import pandas as pd

from app.modules.whitespace.scoring import compute_ws_cell


def test_ws_score_bounds():
    account = pd.Series({"strategic_priority_flag": False})
    product = pd.Series(
        {"product_id": "P-ESG", "expansion_potential": "High", "product_line": "ESG"}
    )
    cell = pd.Series(
        {
            "is_active": False,
            "potential_revenue_bucket": "High",
        }
    )
    out = compute_ws_cell(account, product, cell)
    assert out["whitespace_flag"] == 1
    assert 0 <= out["ws_score"] <= 1

    cell_owned = pd.Series({"is_active": True, "potential_revenue_bucket": "High"})
    out2 = compute_ws_cell(account, product, cell_owned)
    assert out2["ws_score"] == 0.0
