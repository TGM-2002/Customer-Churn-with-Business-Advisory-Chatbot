# database/operations.py

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from uuid import UUID

from database.schemas import (
    Customer, ProductHolding, SupportInteraction,
    BehavioralSignal, ChurnScore,
    CustomerSegment, LifecycleStage, ChurnRiskBand,
    GeographyEnum, compute_churn_risk_band,
)
from database.connection import DatabaseConnection

db = DatabaseConnection()


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

def create_full_customer_profile(customer_data: dict, holding_data: dict,
                                  support_data: dict, signal_data: dict,
                                  score_data: dict) -> Customer:
    with db.get_db() as session:
        customer = Customer(**customer_data)
        session.add(customer)
        session.flush()
        cid = customer.customer_id

        holding_data["customer_id"] = cid
        support_data["customer_id"] = cid
        signal_data["customer_id"]  = cid
        score_data["customer_id"]   = cid

        session.add(ProductHolding(**holding_data))
        session.add(SupportInteraction(**support_data))
        session.add(BehavioralSignal(**signal_data))
        session.add(ChurnScore(**score_data))

        return customer


def create_customer(data: dict) -> Customer:
    with db.get_db() as session:
        customer = Customer(**data)
        session.add(customer)
        session.flush()
        return customer


# ---------------------------------------------------------------------------
# READ — single record
# ---------------------------------------------------------------------------

def get_customer_by_id(customer_id: UUID) -> Customer | None:
    with db.get_db() as session:
        return session.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()


def get_full_profile(customer_id: UUID) -> dict | None:
    with db.get_db() as session:
        customer = session.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        if not customer:
            return None
        return {
            "customer":    customer,
            "holding":     customer.product_holding,
            "support":     customer.support_interaction,
            "signal":      customer.behavioral_signal,
            "churn_score": customer.churn_score,
        }


def get_churn_score_by_customer(customer_id: UUID) -> ChurnScore | None:
    with db.get_db() as session:
        return session.query(ChurnScore).filter(
            ChurnScore.customer_id == customer_id
        ).first()


# ---------------------------------------------------------------------------
# READ — filtered lists
# ---------------------------------------------------------------------------

def get_customers_by_segment(segment: CustomerSegment) -> list[Customer]:
    with db.get_db() as session:
        return session.query(Customer).filter(
            Customer.segment == segment
        ).all()


def get_customers_by_lifecycle(stage: LifecycleStage) -> list[Customer]:
    with db.get_db() as session:
        return session.query(Customer).filter(
            Customer.lifecycle_stage == stage
        ).all()


def get_customers_by_geography(geography: GeographyEnum) -> list[Customer]:
    with db.get_db() as session:
        return session.query(Customer).filter(
            Customer.geography == geography
        ).all()


def get_at_risk_customers() -> list[Customer]:
    with db.get_db() as session:
        return session.query(Customer).filter(
            Customer.lifecycle_stage.in_([LifecycleStage.AT_RISK, LifecycleStage.CHURNED])
        ).all()


def get_customers_by_risk_band(band: ChurnRiskBand) -> list[Customer]:
    with db.get_db() as session:
        return (
            session.query(Customer)
            .join(ChurnScore, Customer.customer_id == ChurnScore.customer_id)
            .filter(ChurnScore.churn_risk_band == band)
            .all()
        )


def get_high_risk_support_customers() -> list[Customer]:
    with db.get_db() as session:
        return (
            session.query(Customer)
            .join(SupportInteraction, Customer.customer_id == SupportInteraction.customer_id)
            .filter(SupportInteraction.is_high_risk_support == True)
            .all()
        )


def get_zero_balance_customers() -> list[Customer]:
    with db.get_db() as session:
        return (
            session.query(Customer)
            .join(ProductHolding, Customer.customer_id == ProductHolding.customer_id)
            .filter(ProductHolding.has_zero_balance == True)
            .all()
        )


def get_disengaged_customers() -> list[Customer]:
    with db.get_db() as session:
        return (
            session.query(Customer)
            .join(BehavioralSignal, Customer.customer_id == BehavioralSignal.customer_id)
            .filter(BehavioralSignal.activity_drop_flag == True)
            .all()
        )


def get_critical_churn_candidates() -> list[Customer]:
    with db.get_db() as session:
        return (
            session.query(Customer)
            .join(ProductHolding,     Customer.customer_id == ProductHolding.customer_id)
            .join(BehavioralSignal,   Customer.customer_id == BehavioralSignal.customer_id)
            .join(SupportInteraction, Customer.customer_id == SupportInteraction.customer_id)
            .filter(
                or_(
                    and_(ProductHolding.has_zero_balance == True,     ProductHolding.is_single_product == True),
                    and_(ProductHolding.has_zero_balance == True,     BehavioralSignal.activity_drop_flag == True),
                    and_(BehavioralSignal.activity_drop_flag == True, SupportInteraction.is_high_risk_support == True),
                )
            )
            .all()
        )


def get_customers_above_churn_probability(threshold: float) -> list[Customer]:
    with db.get_db() as session:
        return (
            session.query(Customer)
            .join(ChurnScore, Customer.customer_id == ChurnScore.customer_id)
            .filter(ChurnScore.churn_probability >= threshold)
            .order_by(ChurnScore.churn_probability.desc())
            .all()
        )


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

def update_churn_score(customer_id: UUID, probability: float,
                        top_driver: str, model_version: str) -> ChurnScore | None:
    with db.get_db() as session:
        score = session.query(ChurnScore).filter(
            ChurnScore.customer_id == customer_id
        ).first()
        if not score:
            return None
        from datetime import datetime
        score.churn_probability = probability
        score.churn_risk_band   = compute_churn_risk_band(probability)
        score.top_churn_driver  = top_driver
        score.model_version     = model_version
        score.scored_at         = datetime.utcnow()
        return score


def update_customer_lifecycle(customer_id: UUID, stage: LifecycleStage) -> Customer | None:
    with db.get_db() as session:
        customer = session.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        if not customer:
            return None
        customer.lifecycle_stage = stage
        return customer


def mark_customer_churned(customer_id: UUID) -> Customer | None:
    with db.get_db() as session:
        customer = session.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        if not customer:
            return None
        customer.lifecycle_stage = LifecycleStage.CHURNED
        score = session.query(ChurnScore).filter(
            ChurnScore.customer_id == customer_id
        ).first()
        if score:
            score.churned = True
        return customer


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def delete_customer(customer_id: UUID) -> bool:
    with db.get_db() as session:
        customer = session.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        if not customer:
            return False
        session.delete(customer)
        return True


# ---------------------------------------------------------------------------
# AGGREGATES
# ---------------------------------------------------------------------------

def count_by_risk_band() -> dict:
    with db.get_db() as session:
        rows = (
            session.query(ChurnScore.churn_risk_band, func.count(ChurnScore.score_id))
            .group_by(ChurnScore.churn_risk_band)
            .all()
        )
        return {band.value: count for band, count in rows}


def count_by_lifecycle_stage() -> dict:
    with db.get_db() as session:
        rows = (
            session.query(Customer.lifecycle_stage, func.count(Customer.customer_id))
            .group_by(Customer.lifecycle_stage)
            .all()
        )
        return {stage.value: count for stage, count in rows}


def average_churn_probability_by_segment() -> dict:
    with db.get_db() as session:
        rows = (
            session.query(Customer.segment, func.avg(ChurnScore.churn_probability))
            .join(ChurnScore, Customer.customer_id == ChurnScore.customer_id)
            .group_by(Customer.segment)
            .all()
        )
        return {segment.value: round(avg, 4) for segment, avg in rows}