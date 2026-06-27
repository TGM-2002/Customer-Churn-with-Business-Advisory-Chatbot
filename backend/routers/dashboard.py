from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.schemas.dashboard import (
    DashboardSummary, RiskDistribution,
    GeographyChurnItem, SegmentChurnItem, LifecycleCountItem,
)
from backend.services import dashboard_service

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary, summary="Portfolio KPIs")
def get_summary(db: Session = Depends(get_db)):
    return dashboard_service.get_summary(db)


@router.get("/risk-distribution", response_model=RiskDistribution, summary="Customer count per risk band")
def get_risk_distribution(db: Session = Depends(get_db)):
    return dashboard_service.get_risk_distribution(db)


@router.get("/churn-by-geography", response_model=list[GeographyChurnItem], summary="Avg churn probability per province")
def get_churn_by_geography(db: Session = Depends(get_db)):
    return dashboard_service.get_churn_by_geography(db)


@router.get("/churn-by-segment", response_model=list[SegmentChurnItem], summary="Avg churn probability per segment")
def get_churn_by_segment(db: Session = Depends(get_db)):
    return dashboard_service.get_churn_by_segment(db)


@router.get("/lifecycle-counts", response_model=list[LifecycleCountItem], summary="Customer count per lifecycle stage")
def get_lifecycle_counts(db: Session = Depends(get_db)):
    return dashboard_service.get_lifecycle_counts(db)
