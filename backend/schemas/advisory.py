from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel


class AdvisoryResponse(BaseModel):
    customer_id: UUID
    advice: str


class AdvisoryQueryRequest(BaseModel):
    customer_id: UUID
    query: str


class AdvisoryQueryResponse(BaseModel):
    customer_id: UUID
    query: str
    answer: str
