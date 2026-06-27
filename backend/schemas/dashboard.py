from __future__ import annotations

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_customers: int
    at_risk_count: int
    churn_rate: float           # percentage, e.g. 15.3
    revenue_at_risk: float      # sum of estimated_salary for High+Critical customers


class RiskDistribution(BaseModel):
    Critical: int = 0
    High: int = 0
    Medium: int = 0
    Low: int = 0


class GeographyChurnItem(BaseModel):
    geography: str
    avg_churn_probability: float    # percentage


class SegmentChurnItem(BaseModel):
    segment: str
    avg_churn_probability: float    # percentage


class LifecycleCountItem(BaseModel):
    lifecycle_stage: str
    count: int
