from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.schemas.customer import CustomerListResponse, CustomerFullProfile
from backend.services import customer_service

router = APIRouter()

_VALID_SORT = {"highest_risk", "lowest_risk", "name_asc", "salary_desc"}
_VALID_RISK_BANDS = {"Critical", "High", "Medium", "Low"}
_VALID_SEGMENTS = {"Affluent", "Mid", "Mass"}


@router.get("/", response_model=CustomerListResponse, summary="List customers")
def list_customers(
    search: Optional[str] = Query(None, description="Search by surname"),
    risk_band: Optional[str] = Query(None, description="Filter by risk band: Critical|High|Medium|Low"),
    segment: Optional[str] = Query(None, description="Filter by segment: Affluent|Mid|Mass"),
    sort: str = Query("highest_risk", description="Sort order: highest_risk|lowest_risk|name_asc|salary_desc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    if risk_band and risk_band not in _VALID_RISK_BANDS:
        raise HTTPException(status_code=422, detail=f"Invalid risk_band. Choose from {_VALID_RISK_BANDS}")
    if segment and segment not in _VALID_SEGMENTS:
        raise HTTPException(status_code=422, detail=f"Invalid segment. Choose from {_VALID_SEGMENTS}")
    if sort not in _VALID_SORT:
        raise HTTPException(status_code=422, detail=f"Invalid sort. Choose from {_VALID_SORT}")

    return customer_service.list_customers(
        session=db,
        search=search,
        risk_band=risk_band,
        segment=segment,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/{customer_id}", response_model=CustomerFullProfile, summary="Get full customer profile")
def get_customer(customer_id: UUID, db: Session = Depends(get_db)):
    profile = customer_service.get_customer(session=db, customer_id=customer_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Customer not found")
    return profile
