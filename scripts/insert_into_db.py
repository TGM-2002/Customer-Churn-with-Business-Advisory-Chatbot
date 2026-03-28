import uuid
import logging
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

from database.schemas import (
    Customer, ProductHolding, SupportInteraction, BehavioralSignal, ChurnScore,
    GeographyEnum, Gender, CardType,
    CustomerSegment, LifecycleStage, AgeBand, SatisfactionBand, ChurnRiskBand,
    compute_customer_customs, compute_support_customs,
    compute_behavioral_customs, compute_churn_risk_band,
)
from database.connection import DatabaseConnection
from config.settings import RAW_DATA_DIR
load_dotenv()

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CSV_PATH   = RAW_DATA_DIR /"Bank-Customer-Attrition-Insights-Data.csv"
BATCH_SIZE = 500

GEOGRAPHY_MAP = {
    "France":  GeographyEnum.GAUTENG,
    "Germany": GeographyEnum.WESTERN_CAPE,
    "Spain":   GeographyEnum.LIMPOPO,
}


# ---------------------------------------------------------------------------
# Currency conversion — USD -> ZAR
# ---------------------------------------------------------------------------

def get_usd_to_zar_rate() -> float:
    log.info("Fetching live USD -> ZAR exchange rate...")
    try:
        response = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=5
        )
        response.raise_for_status()
        rate = float(response.json()["rates"]["ZAR"])
        log.info(f"Live rate fetched successfully: 1 USD = {rate:.4f} ZAR")
        return rate
    except Exception as e:
        fallback = 18.50
        log.warning(f"Failed to fetch live rate: {e}")
        log.warning(f"Falling back to hardcoded rate: 1 USD = {fallback} ZAR")
        return fallback


USD_TO_ZAR = get_usd_to_zar_rate()


def to_zar(usd_amount: float) -> float:
    return round(float(usd_amount) * USD_TO_ZAR, 2)


# ---------------------------------------------------------------------------
# Row -> ORM objects
# ---------------------------------------------------------------------------

def row_to_customer(r: dict, cid: uuid.UUID) -> Customer:
    raw_geo  = str(r.get("Geography", "France")).strip()
    raw_gen  = str(r.get("Gender", "Male")).strip().capitalize()
    raw_card = str(r.get("Card Type", "SILVER")).strip().upper()

    geography = GEOGRAPHY_MAP.get(raw_geo, GeographyEnum.GAUTENG)
    gender    = Gender(raw_gen)
    card_type = CardType(raw_card)
    customs   = compute_customer_customs(r)

    salary_usd = float(r["EstimatedSalary"])
    salary_zar = to_zar(salary_usd)
    log.debug(
        f"Customer {r.get('Surname')} | salary: R{salary_zar:,.2f} "
        f"(was ${salary_usd:,.2f}) | segment: {customs['segment'].value} "
        f"| lifecycle: {customs['lifecycle_stage'].value}"
    )

    return Customer(
        customer_id=cid,
        surname=str(r.get("Surname", "")),
        geography=geography,
        gender=gender,
        age=int(r["Age"]),
        tenure_months=int(r["Tenure"]),
        estimated_salary=salary_zar,
        card_type=card_type,
        credit_score=int(r["CreditScore"]),
        is_active_member=bool(int(r["IsActiveMember"])),
        has_credit_card=bool(int(r["HasCrCard"])),
        **customs,
    )


def row_to_product_holding(r: dict, cid: uuid.UUID) -> ProductHolding:
    balance_usd = float(r["Balance"])
    balance_zar = to_zar(balance_usd)
    n           = int(r["NumOfProducts"])
    has_cc      = int(r.get("HasCrCard", 0))

    log.debug(
        f"ProductHolding | balance: R{balance_zar:,.2f} "
        f"(was ${balance_usd:,.2f}) | products: {n} | zero_balance: {balance_zar == 0.0}"
    )

    return ProductHolding(
        customer_id=cid,
        num_products=n,
        total_balance=balance_zar,
        product_diversity_score=min(n + has_cc, 3),
        is_single_product=(n == 1),
        balance_per_product=round(balance_zar / n, 2) if n else 0.0,
        has_zero_balance=(balance_zar == 0.0),
    )


def row_to_support_interaction(r: dict, cid: uuid.UUID) -> SupportInteraction:
    customs = compute_support_customs(r)
    log.debug(
        f"SupportInteraction | complaint: {bool(int(r.get('Complain', 0)))} "
        f"| satisfaction: {r.get('Satisfaction Score')} "
        f"| band: {customs['satisfaction_band'].value} "
        f"| high_risk: {customs['is_high_risk_support']}"
    )
    return SupportInteraction(
        customer_id=cid,
        has_complaint=bool(int(r["Complain"])),
        satisfaction_score=int(r["Satisfaction Score"]),
        **customs,
    )


def row_to_behavioral_signal(r: dict, cid: uuid.UUID) -> BehavioralSignal:
    customs = compute_behavioral_customs(r)
    log.debug(
        f"BehavioralSignal | points: {r.get('Point Earned')} "
        f"| active: {bool(int(r.get('IsActiveMember', 1)))} "
        f"| activity_drop: {customs['activity_drop_flag']} "
        f"| engagement_score: {customs['card_engagement_score']}"
    )
    return BehavioralSignal(
        customer_id=cid,
        points_earned=int(r["Point Earned"]),
        is_active_member=bool(int(r["IsActiveMember"])),
        **customs,
    )


def row_to_churn_score(r: dict, cid: uuid.UUID) -> ChurnScore:
    churned = bool(int(r["Exited"]))
    prob    = _heuristic_churn_probability(r)
    band    = compute_churn_risk_band(prob)
    driver  = _top_driver(r)

    log.debug(
        f"ChurnScore | churned: {churned} | prob: {prob:.4f} "
        f"| band: {band.value} | driver: {driver}"
    )

    return ChurnScore(
        customer_id=cid,
        churned=churned,
        churn_probability=prob,
        churn_risk_band=band,
        top_churn_driver=driver,
        model_version="v0.0-seed",
    )


# ---------------------------------------------------------------------------
# Heuristic helpers
# ---------------------------------------------------------------------------

def _heuristic_churn_probability(r: dict) -> float:
    score = 0.0
    if float(r.get("Balance", 0)) == 0:
        score += 0.30
    if int(r.get("NumOfProducts", 1)) == 1:
        score += 0.20
    if not bool(int(r.get("IsActiveMember", 1))):
        score += 0.20
    if bool(int(r.get("Complain", 0))) and int(r.get("Satisfaction Score", 5)) <= 2:
        score += 0.20
    if not bool(int(r.get("IsActiveMember", 1))) and int(r.get("Tenure", 0)) > 24:
        score += 0.10
    return round(min(score, 1.0), 4)


def _top_driver(r: dict) -> str:
    if float(r.get("Balance", 0)) == 0:
        return "has_zero_balance"
    if bool(int(r.get("Complain", 0))) and int(r.get("Satisfaction Score", 5)) <= 2:
        return "is_high_risk_support"
    if not bool(int(r.get("IsActiveMember", 1))) and int(r.get("Tenure", 0)) > 24:
        return "activity_drop_flag"
    if int(r.get("NumOfProducts", 1)) == 1:
        return "is_single_product"
    return "low_engagement_score"


# ---------------------------------------------------------------------------
# Main ETL
# ---------------------------------------------------------------------------

def seed_database(csv_path: str = CSV_PATH):
    log.info("=" * 60)
    log.info("Starting ETL: Bank Customer Churn Seed")
    log.info("=" * 60)

    log.info(f"Reading CSV: {csv_path}")
    df    = pd.read_csv(csv_path)
    total = len(df)
    log.info(f"Loaded {total} rows | columns: {list(df.columns)}")
    log.info(f"Batch size: {BATCH_SIZE} | Total batches: {-(-total // BATCH_SIZE)}")
    log.info(f"Exchange rate: 1 USD = {USD_TO_ZAR:.4f} ZAR")
    log.info("-" * 60)

    db        = DatabaseConnection()
    inserted  = 0
    skipped   = 0
    batch_num = 0
    start_time = datetime.now()

    rows    = df.to_dict(orient="records")
    batches = [rows[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    for batch in batches:
        batch_num  += 1
        batch_start = datetime.now()
        batch_inserted = 0
        batch_skipped  = 0

        log.info(f"Processing batch {batch_num}/{len(batches)} ({len(batch)} rows)...")

        with db.get_db() as session:
            for r in batch:
                try:
                    cid = uuid.uuid4()

                    session.add(row_to_customer(r, cid))
                    session.flush()

                    session.add(row_to_product_holding(r, cid))
                    session.add(row_to_support_interaction(r, cid))
                    session.add(row_to_behavioral_signal(r, cid))
                    session.add(row_to_churn_score(r, cid))

                    inserted       += 1
                    batch_inserted += 1

                except Exception as e:
                    skipped       += 1
                    batch_skipped += 1
                    log.error(
                        f"Skipped row | CustomerId={r.get('CustomerId')} "
                        f"Surname={r.get('Surname')} | Reason: {e}"
                    )

        elapsed = (datetime.now() - batch_start).total_seconds()
        log.info(
            f"Batch {batch_num} committed | "
            f"inserted: {batch_inserted} | skipped: {batch_skipped} | "
            f"time: {elapsed:.2f}s | total so far: {inserted}/{total}"
        )

    total_elapsed = (datetime.now() - start_time).total_seconds()

    log.info("-" * 60)
    log.info("ETL Complete")
    log.info(f"  Total inserted : {inserted}")
    log.info(f"  Total skipped  : {skipped}")
    log.info(f"  Success rate   : {inserted / total * 100:.1f}%")
    log.info(f"  Total time     : {total_elapsed:.2f}s")
    log.info(f"  Avg per row    : {total_elapsed / total * 1000:.2f}ms")
    log.info(f"  Exchange rate  : 1 USD = {USD_TO_ZAR:.4f} ZAR")
    log.info("=" * 60)


if __name__ == "__main__":
    seed_database(CSV_PATH)