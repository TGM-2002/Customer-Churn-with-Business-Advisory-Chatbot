from __future__ import annotations

from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class CustomerListItem(BaseModel):
    customer_id: UUID
    surname: str
    geography: str
    gender: str
    age: int
    tenure_months: int
    estimated_salary: float
    card_type: str
    credit_score: int
    segment: str
    lifecycle_stage: str
    # churn score
    churn_probability: Optional[float] = None
    risk_band: Optional[str] = None
    top_driver: Optional[str] = None
    # product holdings
    num_products: Optional[int] = None
    total_balance: Optional[float] = None
    is_single_product: Optional[bool] = None
    has_zero_balance: Optional[bool] = None
    # support interactions
    has_complaint: Optional[bool] = None
    satisfaction_score: Optional[int] = None
    is_high_risk_support: Optional[bool] = None
    # behavioral signals
    is_active_member: Optional[bool] = None
    activity_drop_flag: Optional[bool] = None
    points_earned: Optional[int] = None
    # computed from boolean signals
    flags: list[str] = []


class CustomerFullProfile(BaseModel):
    # core
    customer_id: UUID
    surname: str
    geography: str
    gender: str
    age: int
    tenure_months: int
    estimated_salary: float
    card_type: str
    credit_score: int
    is_active_member: bool
    has_credit_card: bool
    segment: str
    lifecycle_stage: str
    age_band: str
    salary_to_balance_ratio: Optional[float] = None
    # product_holdings
    num_products: Optional[int] = None
    total_balance: Optional[float] = None
    product_diversity_score: Optional[int] = None
    is_single_product: Optional[bool] = None
    balance_per_product: Optional[float] = None
    has_zero_balance: Optional[bool] = None
    # support_interactions
    has_complaint: Optional[bool] = None
    satisfaction_score: Optional[int] = None
    satisfaction_band: Optional[str] = None
    complaint_x_satisfaction: Optional[int] = None
    is_high_risk_support: Optional[bool] = None
    # behavioral_signals
    points_earned: Optional[int] = None
    points_per_tenure: Optional[float] = None
    card_engagement_score: Optional[float] = None
    activity_drop_flag: Optional[bool] = None
    # churn_score
    churned: Optional[bool] = None
    churn_probability: Optional[float] = None
    risk_band: Optional[str] = None
    top_churn_driver: Optional[str] = None
    model_version: Optional[str] = None
    # computed
    flags: list[str] = []


class CustomerListResponse(BaseModel):
    items: list[CustomerListItem]
    total: int
    limit: int
    offset: int
