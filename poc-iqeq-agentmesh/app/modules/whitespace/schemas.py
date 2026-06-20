"""Pydantic schemas for POC3 whitespace API output (§08)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class WhitespaceGridSchema(BaseModel):
    countries: List[str]
    products: List[str]
    intensity_matrix: List[List[float]]


class TopAccountItem(BaseModel):
    account_id: str
    total_ws_potential_eur: float
    ws_intensity: float
    top_products: List[str] = Field(default_factory=list)
    cluster_id: int


class CampaignBriefItem(BaseModel):
    cluster_id: int
    target_account_count: int
    cluster_total_potential_eur: float
    dominant_country: str
    dominant_segment: str
    dominant_products: List[str]
    messaging_angle: str
    campaign_brief_text: str
    primary_cta: str


class ValidationFlagItem(BaseModel):
    account_id: str
    product_id: str
    flag_type: Literal["review", "warning"]
    anomaly_note: str


class WhitespaceAnalysisResponse(BaseModel):
    pipeline_run_id: str
    generated_at: datetime
    model_version: str
    total_potential_eur: float
    whitespace_grid: WhitespaceGridSchema
    top_accounts: List[TopAccountItem]
    campaign_briefs: List[CampaignBriefItem]
    validation_flags: List[ValidationFlagItem]
    export_csv_path: str
