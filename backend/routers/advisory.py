from uuid import UUID

from fastapi import APIRouter, HTTPException

from backend.schemas.advisory import (
    AdvisoryResponse,
    AdvisoryQueryRequest,
    AdvisoryQueryResponse,
)
from backend.services import advisory_service

router = APIRouter()


@router.post("/query", response_model=AdvisoryQueryResponse, summary="Ask a free-form question about a customer")
def answer_query(body: AdvisoryQueryRequest):
    try:
        answer = advisory_service.answer_query(str(body.customer_id), body.query)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return AdvisoryQueryResponse(
        customer_id=body.customer_id,
        query=body.query,
        answer=answer,
    )


@router.post("/{customer_id}", response_model=AdvisoryResponse, summary="Generate full retention advisory memo")
def generate_advisory(customer_id: UUID):
    advice = advisory_service.generate_advisory(str(customer_id))
    if advice.startswith("No data found"):
        raise HTTPException(status_code=404, detail=advice)
    if "temporarily unavailable" in advice:
        raise HTTPException(status_code=503, detail=advice)
    return AdvisoryResponse(customer_id=customer_id, advice=advice)
