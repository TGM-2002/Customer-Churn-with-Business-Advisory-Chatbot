from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func

from database.schemas import (
    Customer, ChurnScore, ChurnRiskBand,
)
from backend.schemas.dashboard import (
    DashboardSummary, RiskDistribution,
    GeographyChurnItem, SegmentChurnItem, LifecycleCountItem,
)

_AT_RISK_BANDS = [ChurnRiskBand.HIGH, ChurnRiskBand.CRITICAL]


def get_summary(session: Session) -> DashboardSummary:
    total = session.query(func.count(Customer.customer_id)).scalar() or 0

    at_risk = (
        session.query(func.count(Customer.customer_id))
        .join(ChurnScore, Customer.customer_id == ChurnScore.customer_id)
        .filter(ChurnScore.churn_risk_band.in_(_AT_RISK_BANDS))
        .scalar() or 0
    )

    total_scored = session.query(func.count(ChurnScore.score_id)).scalar() or 0
    churned_count = (
        session.query(func.count(ChurnScore.score_id))
        .filter(ChurnScore.churned.is_(True))
        .scalar() or 0
    )
    churn_rate = round(churned_count / total_scored * 100, 1) if total_scored else 0.0

    revenue_at_risk = (
        session.query(func.sum(Customer.estimated_salary))
        .join(ChurnScore, Customer.customer_id == ChurnScore.customer_id)
        .filter(ChurnScore.churn_risk_band.in_(_AT_RISK_BANDS))
        .scalar() or 0.0
    )

    return DashboardSummary(
        total_customers=total,
        at_risk_count=at_risk,
        churn_rate=churn_rate,
        revenue_at_risk=revenue_at_risk,
    )


def get_risk_distribution(session: Session) -> RiskDistribution:
    rows = (
        session.query(ChurnScore.churn_risk_band, func.count(ChurnScore.score_id))
        .filter(ChurnScore.churn_risk_band.isnot(None))
        .group_by(ChurnScore.churn_risk_band)
        .all()
    )
    counts = {band.value: count for band, count in rows}
    return RiskDistribution(
        Critical=counts.get("Critical", 0),
        High=counts.get("High", 0),
        Medium=counts.get("Medium", 0),
        Low=counts.get("Low", 0),
    )


def get_churn_by_geography(session: Session) -> list[GeographyChurnItem]:
    rows = (
        session.query(Customer.geography, func.avg(ChurnScore.churn_probability))
        .join(ChurnScore, Customer.customer_id == ChurnScore.customer_id)
        .group_by(Customer.geography)
        .order_by(func.avg(ChurnScore.churn_probability).desc())
        .all()
    )
    return [
        GeographyChurnItem(
            geography=geo.value,
            avg_churn_probability=round(avg * 100, 1),
        )
        for geo, avg in rows
        if avg is not None
    ]


def get_churn_by_segment(session: Session) -> list[SegmentChurnItem]:
    rows = (
        session.query(Customer.segment, func.avg(ChurnScore.churn_probability))
        .join(ChurnScore, Customer.customer_id == ChurnScore.customer_id)
        .group_by(Customer.segment)
        .all()
    )
    return [
        SegmentChurnItem(
            segment=seg.value,
            avg_churn_probability=round(avg * 100, 1),
        )
        for seg, avg in rows
        if avg is not None
    ]


def get_lifecycle_counts(session: Session) -> list[LifecycleCountItem]:
    rows = (
        session.query(Customer.lifecycle_stage, func.count(Customer.customer_id))
        .group_by(Customer.lifecycle_stage)
        .all()
    )
    return [
        LifecycleCountItem(lifecycle_stage=stage.value, count=count)
        for stage, count in rows
    ]
