from __future__ import annotations

from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from database.schemas import (
    Customer, ProductHolding, SupportInteraction,
    BehavioralSignal, ChurnScore,
    ChurnRiskBand, CustomerSegment,
)
from backend.schemas.customer import CustomerListItem, CustomerFullProfile, CustomerListResponse

_SORT_MAP = {
    "highest_risk": ChurnScore.churn_probability.desc().nullslast(),
    "lowest_risk":  ChurnScore.churn_probability.asc().nullsfirst(),
    "name_asc":     Customer.surname.asc(),
    "salary_desc":  Customer.estimated_salary.desc(),
}


def _compute_flags(ph: ProductHolding | None, si: SupportInteraction | None,
                   bs: BehavioralSignal | None) -> list[str]:
    flags: list[str] = []
    if bs and bs.activity_drop_flag:
        flags.append("activity_drop_flag")
    if ph and ph.has_zero_balance:
        flags.append("has_zero_balance")
    if ph and ph.is_single_product:
        flags.append("is_single_product")
    if si and si.is_high_risk_support:
        flags.append("is_high_risk_support")
    if bs and bs.points_earned is not None and bs.points_earned < 150:
        flags.append("low_points")
    return flags


def _row_to_list_item(row: tuple) -> CustomerListItem:
    c, ph, si, bs, cs = row
    return CustomerListItem(
        customer_id=c.customer_id,
        surname=c.surname or "",
        geography=c.geography.value if c.geography else "",
        gender=c.gender.value if c.gender else "",
        age=c.age or 0,
        tenure_months=c.tenure_months or 0,
        estimated_salary=c.estimated_salary or 0.0,
        card_type=c.card_type.value if c.card_type else "",
        credit_score=c.credit_score or 0,
        segment=c.segment.value if c.segment else "",
        lifecycle_stage=c.lifecycle_stage.value if c.lifecycle_stage else "",
        churn_probability=cs.churn_probability if cs else None,
        risk_band=cs.churn_risk_band.value if (cs and cs.churn_risk_band) else None,
        top_driver=cs.top_churn_driver if cs else None,
        num_products=ph.num_products if ph else None,
        total_balance=ph.total_balance if ph else None,
        is_single_product=ph.is_single_product if ph else None,
        has_zero_balance=ph.has_zero_balance if ph else None,
        has_complaint=si.has_complaint if si else None,
        satisfaction_score=si.satisfaction_score if si else None,
        is_high_risk_support=si.is_high_risk_support if si else None,
        is_active_member=bs.is_active_member if bs else None,
        activity_drop_flag=bs.activity_drop_flag if bs else None,
        points_earned=bs.points_earned if bs else None,
        flags=_compute_flags(ph, si, bs),
    )


def list_customers(
    session: Session,
    search: Optional[str] = None,
    risk_band: Optional[str] = None,
    segment: Optional[str] = None,
    sort: str = "highest_risk",
    limit: int = 50,
    offset: int = 0,
) -> CustomerListResponse:
    q = (
        session.query(Customer, ProductHolding, SupportInteraction, BehavioralSignal, ChurnScore)
        .outerjoin(ProductHolding,     Customer.customer_id == ProductHolding.customer_id)
        .outerjoin(SupportInteraction, Customer.customer_id == SupportInteraction.customer_id)
        .outerjoin(BehavioralSignal,   Customer.customer_id == BehavioralSignal.customer_id)
        .outerjoin(ChurnScore,         Customer.customer_id == ChurnScore.customer_id)
    )

    if search:
        q = q.filter(Customer.surname.ilike(f"%{search}%"))

    if risk_band:
        q = q.filter(ChurnScore.churn_risk_band == ChurnRiskBand(risk_band))

    if segment:
        q = q.filter(Customer.segment == CustomerSegment(segment))

    total: int = q.count()

    order = _SORT_MAP.get(sort, ChurnScore.churn_probability.desc().nullslast())
    rows = q.order_by(order).offset(offset).limit(limit).all()

    return CustomerListResponse(
        items=[_row_to_list_item(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_customer(session: Session, customer_id: UUID) -> CustomerFullProfile | None:
    row = (
        session.query(Customer, ProductHolding, SupportInteraction, BehavioralSignal, ChurnScore)
        .outerjoin(ProductHolding,     Customer.customer_id == ProductHolding.customer_id)
        .outerjoin(SupportInteraction, Customer.customer_id == SupportInteraction.customer_id)
        .outerjoin(BehavioralSignal,   Customer.customer_id == BehavioralSignal.customer_id)
        .outerjoin(ChurnScore,         Customer.customer_id == ChurnScore.customer_id)
        .filter(Customer.customer_id == customer_id)
        .first()
    )
    if not row:
        return None

    c, ph, si, bs, cs = row
    return CustomerFullProfile(
        customer_id=c.customer_id,
        surname=c.surname or "",
        geography=c.geography.value if c.geography else "",
        gender=c.gender.value if c.gender else "",
        age=c.age or 0,
        tenure_months=c.tenure_months or 0,
        estimated_salary=c.estimated_salary or 0.0,
        card_type=c.card_type.value if c.card_type else "",
        credit_score=c.credit_score or 0,
        is_active_member=bool(c.is_active_member),
        has_credit_card=bool(c.has_credit_card),
        segment=c.segment.value if c.segment else "",
        lifecycle_stage=c.lifecycle_stage.value if c.lifecycle_stage else "",
        age_band=c.age_band.value if c.age_band else "",
        salary_to_balance_ratio=c.salary_to_balance_ratio,
        num_products=ph.num_products if ph else None,
        total_balance=ph.total_balance if ph else None,
        product_diversity_score=ph.product_diversity_score if ph else None,
        is_single_product=ph.is_single_product if ph else None,
        balance_per_product=ph.balance_per_product if ph else None,
        has_zero_balance=ph.has_zero_balance if ph else None,
        has_complaint=si.has_complaint if si else None,
        satisfaction_score=si.satisfaction_score if si else None,
        satisfaction_band=si.satisfaction_band.value if (si and si.satisfaction_band) else None,
        complaint_x_satisfaction=si.complaint_x_satisfaction if si else None,
        is_high_risk_support=si.is_high_risk_support if si else None,
        points_earned=bs.points_earned if bs else None,
        points_per_tenure=bs.points_per_tenure if bs else None,
        card_engagement_score=bs.card_engagement_score if bs else None,
        activity_drop_flag=bs.activity_drop_flag if bs else None,
        churned=cs.churned if cs else None,
        churn_probability=cs.churn_probability if cs else None,
        risk_band=cs.churn_risk_band.value if (cs and cs.churn_risk_band) else None,
        top_churn_driver=cs.top_churn_driver if cs else None,
        model_version=cs.model_version if cs else None,
        flags=_compute_flags(ph, si, bs),
    )
