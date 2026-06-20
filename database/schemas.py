#database/schemas.py
import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float,
    Boolean, DateTime, ForeignKey, CheckConstraint, Enum,Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from dotenv import load_dotenv
import os

load_dotenv()

database_url=os.getenv("DATABASE_URL")
Base = declarative_base()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GeographyEnum(str, enum.Enum):
  
    WESTERN_CAPE="western_cape"
    GAUTENG="gauteng"
    FREE_STATE="free_state"
    NORTHERN_CAPE="northern_cape"
    LIMPOPO="limpopo"
    MPUMALANGA="mpumalanga"
    


class Gender(str, enum.Enum):
    MALE   = "Male"
    FEMALE = "Female"
    


class CardType(str, enum.Enum):
    DIAMOND  = "DIAMOND"
    GOLD     = "GOLD"
    SILVER   = "SILVER"
    PLATINUM = "PLATINUM"


class CustomerSegment(str, enum.Enum):
    """
    Derived from EstimatedSalary + CreditScore.
    AFFLUENT : salary > 150000 AND credit_score > 700
    MID      : salary 75000-150000 OR credit_score 500-700
    MASS     : everything else
    """
    AFFLUENT = "Affluent"
    MID      = "Mid"
    MASS     = "Mass"


class LifecycleStage(str, enum.Enum):
    """
    Derived from Tenure + IsActiveMember + Exited.
    NEW      : tenure < 12
    GROWING  : tenure 12-60 AND is_active = true
    AT_RISK  : is_active = false AND tenure > 24
    CHURNED  : exited = true
    """
    NEW      = "New"
    GROWING  = "Growing"
    AT_RISK  = "At-Risk"
    CHURNED  = "Churned"


class AgeBand(str, enum.Enum):
    """
    Derived from Age.
    YOUNG_ADULT : 18-30
    MID         : 31-50
    SENIOR      : 51+
    """
    YOUNG_ADULT = "Young Adult"
    MID         = "Mid"
    SENIOR      = "Senior"


class SatisfactionBand(str, enum.Enum):
    """
    Derived from Satisfaction Score.
    DISSATISFIED : 1-2
    NEUTRAL      : 3
    SATISFIED    : 4-5
    """
    DISSATISFIED = "Dissatisfied"
    NEUTRAL      = "Neutral"
    SATISFIED    = "Satisfied"


class ChurnRiskBand(str, enum.Enum):
    """
    Derived from churn_probability (model output).
    LOW      : < 0.3
    MEDIUM   : 0.3-0.6
    HIGH     : 0.6-0.8
    CRITICAL : > 0.8
    """
    LOW      = "Low"
    MEDIUM   = "Medium"
    HIGH     = "High"
    CRITICAL = "Critical"


# ---------------------------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    customer_id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    surname          = Column(String(100))
    geography        = Column(Enum(GeographyEnum,name="geography_enum"),  nullable=False,default="limpopo")
    gender           = Column(Enum(Gender,name="gender_enum"),     nullable=False)
    age              = Column(Integer)
    tenure_months    = Column(Integer)
    estimated_salary = Column(Float)
    card_type        = Column(Enum(CardType,name="cardtype_name"),   nullable=False)
    credit_score     = Column(Integer)
    is_active_member = Column(Boolean)
    has_credit_card  = Column(Boolean)

    # custom: EstimatedSalary + CreditScore bucketing
    segment = Column(
        Enum(CustomerSegment),
        nullable=False,
        comment="Derived: EstimatedSalary + CreditScore bucketing"
    )

    # custom: Tenure + IsActiveMember + Exited
    lifecycle_stage = Column(
        Enum(LifecycleStage),
        nullable=False,
        comment="Derived: Tenure + IsActiveMember + Exited"
    )

    # custom: Age bucket
    age_band = Column(
        Enum(AgeBand),
        nullable=False,
        comment="Derived: Age bucket"
    )

    # custom: Balance / EstimatedSalary
    salary_to_balance_ratio = Column(
        Float,
        comment="Derived: Balance / EstimatedSalary"
    )

    __table_args__ = (
        CheckConstraint("credit_score BETWEEN 300 AND 850", name="ck_credit_score_range"),
        CheckConstraint("age >= 18",                        name="ck_min_age"),
 
        # filter/group by segment for cohort churn analysis
        Index("ix_customers_segment",           "segment"),
        # filter by lifecycle stage — most common operational query
        Index("ix_customers_lifecycle_stage",   "lifecycle_stage"),
        # geography-level reporting and regional cohort queries
        Index("ix_customers_geography",         "geography"),
        # active/inactive filters used throughout feature engineering
        Index("ix_customers_is_active",         "is_active_member"),
        # composite: segment + lifecycle used together in risk dashboards
        Index("ix_customers_segment_lifecycle", "segment", "lifecycle_stage"),
        # composite: geography + segment for regional segmentation queries
        Index("ix_customers_geo_segment",       "geography", "segment"),
    )

    # relationships
    product_holding     = relationship("ProductHolding",     back_populates="customer", uselist=False)
    support_interaction = relationship("SupportInteraction", back_populates="customer", uselist=False)
    behavioral_signal   = relationship("BehavioralSignal",   back_populates="customer", uselist=False)
    churn_score         = relationship("ChurnScore",         back_populates="customer", uselist=False)

    def __repr__(self):
        return f"<Customer id={self.customer_id} segment={self.segment}>"


# ---------------------------------------------------------------------------
# PRODUCT HOLDINGS
# ---------------------------------------------------------------------------

class ProductHolding(Base):
    __tablename__ = "product_holdings"

    holding_id  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)

    num_products  = Column(Integer)  # original: NumOfProducts
    total_balance = Column(Float)    # original: Balance

    # custom: NumOfProducts + HasCrCard (0-3 scale)
    product_diversity_score = Column(
        Integer,
        comment="Derived: NumOfProducts + HasCrCard (0-3 scale)"
    )

    # custom: NumOfProducts == 1
    is_single_product = Column(
        Boolean,
        comment="Derived: NumOfProducts == 1"
    )

    # custom: Balance / NumOfProducts
    balance_per_product = Column(
        Float,
        comment="Derived: Balance / NumOfProducts"
    )

    # custom: Balance == 0
    has_zero_balance = Column(
        Boolean,
        comment="Derived: Balance == 0"
    )

    __table_args__ = (
        CheckConstraint("num_products >= 1",  name="ck_min_products"),
        CheckConstraint("total_balance >= 0", name="ck_non_negative_balance"),
        CheckConstraint(
            "product_diversity_score BETWEEN 0 AND 3",
            name="ck_diversity_score_range"
        ),
 
        # FK lookup — join from customers to product_holdings
        Index("ix_product_holdings_customer_id",    "customer_id"),
        # fast retrieval of single-product customers (high churn risk cohort)
        Index("ix_product_holdings_single_product", "is_single_product"),
        # zero-balance filter — one of the strongest churn signals
        Index("ix_product_holdings_zero_balance",   "has_zero_balance"),
        # composite: single product + zero balance — critical churn risk combo
        Index("ix_product_holdings_risk_combo",     "is_single_product", "has_zero_balance"),
    )

    customer = relationship("Customer", back_populates="product_holding")

    def __repr__(self):
        return f"<ProductHolding customer={self.customer_id} products={self.num_products}>"


# ---------------------------------------------------------------------------
# SUPPORT INTERACTIONS
# ---------------------------------------------------------------------------

class SupportInteraction(Base):
    __tablename__ = "support_interactions"

    interaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id    = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)

    has_complaint      = Column(Boolean)  # original: Complain
    satisfaction_score = Column(Integer)  # original: Satisfaction Score

    # custom: Satisfaction Score bucketed
    satisfaction_band = Column(
        Enum(SatisfactionBand),
        nullable=False,
        comment="Derived: Satisfaction Score bucketed"
    )

    # custom: Complain * (5 - Satisfaction Score)
    complaint_x_satisfaction = Column(
        Integer,
        comment="Derived: Complain * (5 - Satisfaction Score)"
    )

    # custom: Complain == 1 AND Satisfaction Score <= 2
    is_high_risk_support = Column(
        Boolean,
        comment="Derived: Complain == 1 AND Satisfaction Score <= 2"
    )

    __table_args__ = (
        CheckConstraint("satisfaction_score BETWEEN 1 AND 5", name="ck_satisfaction_range"),
        CheckConstraint(
            "complaint_x_satisfaction BETWEEN 0 AND 4",
            name="ck_friction_score_range"
        ),
 
        # FK lookup — join from customers to support_interactions
        Index("ix_support_customer_id",       "customer_id"),
        # filter all high-risk support cases in one scan
        Index("ix_support_high_risk",         "is_high_risk_support"),
        # filter/group by satisfaction band for reporting
        Index("ix_support_satisfaction_band", "satisfaction_band"),
        # composite: complaint + satisfaction band — complaint triage queries
        Index("ix_support_complaint_band",    "has_complaint", "satisfaction_band"),
    )

    customer = relationship("Customer", back_populates="support_interaction")

    def __repr__(self):
        return f"<SupportInteraction customer={self.customer_id} risk={self.is_high_risk_support}>"


# ---------------------------------------------------------------------------
# BEHAVIORAL SIGNALS
# ---------------------------------------------------------------------------

class BehavioralSignal(Base):
    __tablename__ = "behavioral_signals"

    signal_id   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)

    points_earned    = Column(Integer)  # original: Point Earned
    is_active_member = Column(Boolean)  # original: IsActiveMember

    # custom: Point Earned / Tenure
    points_per_tenure = Column(
        Float,
        comment="Derived: Point Earned / Tenure"
    )

    # custom: card_type_weight * (Point Earned / max_points)
    # DIAMOND=4, GOLD=3, SILVER=2, PLATINUM=1
    card_engagement_score = Column(
        Float,
        comment="Derived: card_type_weight * (Point Earned / max_points)"
    )

    # custom: IsActiveMember == 0 AND Tenure > 24
    activity_drop_flag = Column(
        Boolean,
        comment="Derived: IsActiveMember == 0 AND Tenure > 24"
    )

    __table_args__ = (
        CheckConstraint("points_earned >= 0",         name="ck_non_negative_points"),
        CheckConstraint("card_engagement_score >= 0", name="ck_non_negative_engagement"),
 
        # FK lookup — join from customers to behavioral_signals
        Index("ix_behavioral_customer_id",      "customer_id"),
        # filter disengaged long-tenure customers — key churn predictor
        Index("ix_behavioral_activity_drop",    "activity_drop_flag"),
        # filter inactive members for targeted re-engagement campaigns
        Index("ix_behavioral_is_active",        "is_active_member"),
        # composite: activity drop + inactive — strongest disengagement combo
        Index("ix_behavioral_disengagement",    "activity_drop_flag", "is_active_member"),
    )

    customer = relationship("Customer", back_populates="behavioral_signal")

    def __repr__(self):
        return f"<BehavioralSignal customer={self.customer_id} active={self.is_active_member}>"


# ---------------------------------------------------------------------------
# CHURN SCORES  (ML pipeline output)
# ---------------------------------------------------------------------------

class ChurnScore(Base):
    __tablename__ = "churn_scores"

    score_id    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)

    churned = Column(Boolean)  # original: Exited

    # custom: model output probability (0-1)
    churn_probability = Column(
        Float,
        comment="Model output: probability of churn (0.0-1.0)"
    )

    # custom: bucketed from churn_probability — null until ML pipeline runs
    churn_risk_band = Column(
        Enum(ChurnRiskBand),
        nullable=True,
        comment="Derived: churn_probability bucketed into risk band"
    )

    # custom: SHAP/LIME top contributing feature per customer
    # e.g. "has_zero_balance", "activity_drop_flag", "is_single_product"
    top_churn_driver = Column(
        String(100),
        comment="SHAP/LIME: top contributing feature for this customer's score"
    )

    scored_at     = Column(DateTime, default=datetime.utcnow, comment="Pipeline run timestamp")
    model_version = Column(String(50), comment="Model registry tag, e.g. v1.3.0")

    __table_args__ = (
        CheckConstraint(
            "churn_probability BETWEEN 0.0 AND 1.0",
            name="ck_probability_range"
        ),
 
        # FK lookup — join from customers to churn_scores
        Index("ix_churn_scores_customer_id",    "customer_id"),
        # filter by risk band — primary query for intervention workflows
        Index("ix_churn_scores_risk_band",      "churn_risk_band"),
        # filter confirmed churned customers for retrospective analysis
        Index("ix_churn_scores_churned",        "churned"),
        # range queries on probability score (e.g. prob > 0.7)
        Index("ix_churn_scores_probability",    "churn_probability"),
        # group by top driver — identifies systemic churn causes
        Index("ix_churn_scores_top_driver",     "top_churn_driver"),
        # filter scores by pipeline run — used for model drift monitoring
        Index("ix_churn_scores_scored_at",      "scored_at"),
        # composite: risk band + churned — confirmed vs predicted comparison
        Index("ix_churn_scores_band_churned",   "churn_risk_band", "churned"),
        # composite: model version + scored_at — per-run performance tracking
        Index("ix_churn_scores_version_date",   "model_version", "scored_at"),
    )

    customer = relationship("Customer", back_populates="churn_score")

    def __repr__(self):
        return (
            f"<ChurnScore customer={self.customer_id} "
            f"band={self.churn_risk_band} prob={self.churn_probability}>"
        )


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def get_engine(db_url: str = "postgresql+psycopg2://user:password@localhost:5432/churn_db"):
    return create_engine(db_url, echo=True)


def create_all_tables(engine):
    Base.metadata.create_all(engine)


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


# ---------------------------------------------------------------------------
# Derivation helpers  (raw CSV row dict -> enum instances + computed values)
# ---------------------------------------------------------------------------

CARD_TYPE_WEIGHTS: dict = {
    CardType.DIAMOND:  4,
    CardType.GOLD:     3,
    CardType.SILVER:   2,
    CardType.PLATINUM: 1,
}

MAX_POINTS = 1000  # adjust to your dataset's observed max


def compute_customer_customs(row: dict) -> dict:
    salary  = row.get("EstimatedSalary", 0) or 0
    credit  = row.get("CreditScore", 0)
    tenure  = row.get("Tenure", 1) or 1
    age     = row.get("Age", 0)
    active  = row.get("IsActiveMember", 0)
    exited  = row.get("Exited", 0)
    balance = row.get("Balance", 0)

    if salary > 150_000 and credit > 700:
        segment = CustomerSegment.AFFLUENT
    elif salary >= 75_000 or credit >= 500:
        segment = CustomerSegment.MID
    else:
        segment = CustomerSegment.MASS

    if exited:
        lifecycle_stage = LifecycleStage.CHURNED
    elif tenure < 12:
        lifecycle_stage = LifecycleStage.NEW
    elif not active and tenure > 24:
        lifecycle_stage = LifecycleStage.AT_RISK
    else:
        lifecycle_stage = LifecycleStage.GROWING

    if age <= 30:
        age_band = AgeBand.YOUNG_ADULT
    elif age <= 50:
        age_band = AgeBand.MID
    else:
        age_band = AgeBand.SENIOR

    salary_to_balance_ratio = round(balance / salary, 4) if salary else 0.0

    return dict(
        segment=segment,
        lifecycle_stage=lifecycle_stage,
        age_band=age_band,
        salary_to_balance_ratio=salary_to_balance_ratio,
    )


def compute_product_customs(row: dict) -> dict:
    n       = row.get("NumOfProducts", 1)
    balance = row.get("Balance", 0)
    has_cc  = row.get("HasCrCard", 0)

    return dict(
        product_diversity_score=min(n + has_cc, 3),
        is_single_product=(n == 1),
        balance_per_product=round(balance / n, 2) if n else 0.0,
        has_zero_balance=(balance == 0),
    )


def compute_support_customs(row: dict) -> dict:
    complaint = row.get("Complain", 0)
    score     = row.get("Satisfaction Score", 3)

    if score <= 2:
        band = SatisfactionBand.DISSATISFIED
    elif score == 3:
        band = SatisfactionBand.NEUTRAL
    else:
        band = SatisfactionBand.SATISFIED

    return dict(
        satisfaction_band=band,
        complaint_x_satisfaction=complaint * (5 - score),
        is_high_risk_support=(complaint == 1 and score <= 2),
    )


def compute_behavioral_customs(row: dict, max_points: int = MAX_POINTS) -> dict:
    points = row.get("Point Earned", 0)
    tenure = row.get("Tenure", 1) or 1
    active = row.get("IsActiveMember", 0)
    card   = CardType(row.get("Card Type", "SILVER").upper())
    weight = CARD_TYPE_WEIGHTS.get(card, 1)

    return dict(
        points_per_tenure=round(points / tenure, 2),
        card_engagement_score=round(weight * (points / max_points), 4),
        activity_drop_flag=(not active and tenure > 24),
    )


def compute_churn_risk_band(probability: float) -> ChurnRiskBand:
    """Call this when updating ChurnScore after the ML pipeline runs."""
    if probability < 0.3:
        return ChurnRiskBand.LOW
    elif probability < 0.6:
        return ChurnRiskBand.MEDIUM
    elif probability < 0.8:
        return ChurnRiskBand.HIGH
    else:
        return ChurnRiskBand.CRITICAL


# ---------------------------------------------------------------------------
# Example: load from CSV and populate all tables
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@localhost:5432/churn_db")

    engine  = get_engine(db_url)
    create_all_tables(engine)
    session = get_session(engine)

    dummy_customers = [
        {
            "customer_id": uuid.uuid4(), "surname": "Dlamini",
            "geography": GeographyEnum.GAUTENG, "gender": Gender.MALE,
            "age": 45, "tenure_months": 36, "estimated_salary": 180_000.0,
            "card_type": CardType.DIAMOND, "credit_score": 750,
            "is_active_member": True, "has_credit_card": True,
            "segment": CustomerSegment.AFFLUENT, "lifecycle_stage": LifecycleStage.GROWING,
            "age_band": AgeBand.MID, "salary_to_balance_ratio": 0.42,
        },
        {
            "customer_id": uuid.uuid4(), "surname": "Nkosi",
            "geography": GeographyEnum.LIMPOPO, "gender": Gender.FEMALE,
            "age": 33, "tenure_months": 8, "estimated_salary": 55_000.0,
            "card_type": CardType.SILVER, "credit_score": 480,
            "is_active_member": False, "has_credit_card": False,
            "segment": CustomerSegment.MASS, "lifecycle_stage": LifecycleStage.NEW,
            "age_band": AgeBand.MID, "salary_to_balance_ratio": 0.0,
        },
        {
            "customer_id": uuid.uuid4(), "surname": "Van der Merwe",
            "geography": GeographyEnum.WESTERN_CAPE, "gender": Gender.MALE,
            "age": 58, "tenure_months": 60, "estimated_salary": 120_000.0,
            "card_type": CardType.GOLD, "credit_score": 610,
            "is_active_member": False, "has_credit_card": True,
            "segment": CustomerSegment.MID, "lifecycle_stage": LifecycleStage.AT_RISK,
            "age_band": AgeBand.SENIOR, "salary_to_balance_ratio": 0.19,
        },
        {
            "customer_id": uuid.uuid4(), "surname": "Mokoena",
            "geography": GeographyEnum.MPUMALANGA, "gender": Gender.FEMALE,
            "age": 27, "tenure_months": 14, "estimated_salary": 85_000.0,
            "card_type": CardType.PLATINUM, "credit_score": 540,
            "is_active_member": True, "has_credit_card": True,
            "segment": CustomerSegment.MID, "lifecycle_stage": LifecycleStage.GROWING,
            "age_band": AgeBand.YOUNG_ADULT, "salary_to_balance_ratio": 0.55,
        },
    ]

    for d in dummy_customers:
        cid = d["customer_id"]

        session.add(Customer(**{k: v for k, v in d.items()}))

        session.add(ProductHolding(
            customer_id=cid, num_products=2, total_balance=45_000.0,
            product_diversity_score=2, is_single_product=False,
            balance_per_product=22_500.0, has_zero_balance=False,
        ))

        session.add(SupportInteraction(
            customer_id=cid, has_complaint=False, satisfaction_score=4,
            satisfaction_band=SatisfactionBand.SATISFIED,
            complaint_x_satisfaction=0, is_high_risk_support=False,
        ))

        session.add(BehavioralSignal(
            customer_id=cid, points_earned=400, is_active_member=d["is_active_member"],
            points_per_tenure=round(400 / (d["tenure_months"] or 1), 2),
            card_engagement_score=1.6, activity_drop_flag=not d["is_active_member"] and d["tenure_months"] > 24,
        ))

        session.add(ChurnScore(
            customer_id=cid, churned=False, churn_probability=0.25,
            churn_risk_band=ChurnRiskBand.LOW, top_churn_driver="low_engagement_score",
            model_version="v0.0-dummy",
        ))

    session.commit()
    session.close()
    print("4 dummy customers inserted successfully.")