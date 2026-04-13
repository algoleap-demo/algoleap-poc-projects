"""Pydantic rejects malformed whitespace payloads."""

import pytest
from pydantic import ValidationError

from app.modules.whitespace.schemas import WhitespaceAnalysisResponse


def test_whitespace_response_rejects_invalid():
    with pytest.raises(ValidationError):
        WhitespaceAnalysisResponse.model_validate(
            {
                "pipeline_run_id": "x",
                "generated_at": "not-a-datetime",
                "model_version": "t",
                "total_potential_eur": "bad",
                "whitespace_grid": {},
                "top_accounts": [],
                "campaign_briefs": [],
                "validation_flags": [],
                "export_csv_path": "",
            }
        )
