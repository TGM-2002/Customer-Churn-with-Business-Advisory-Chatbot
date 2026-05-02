"""
evaluate.py
-----------
Load a saved churn model and evaluate it against dummy data that mirrors
the full feature set pulled by the training pipeline.

Usage
-----
    # evaluate the best model (auto-detects from MODELS_DIR)
    python evaluate.py

    # evaluate a specific .joblib file
    python evaluate.py --model-path models/random_forest_v1.0.0.joblib

    # control how many dummy rows to generate
    python evaluate.py --n-samples 500

    # show per-row prediction table
    python evaluate.py --show-predictions
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

from src.classifier.models import Churn_Classifier
from config.settings import MODELS_DIR, MODEL_VERSION, RANDOM_STATE

# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("evaluate")
SEP = "=" * 65


# ==========================================================================
# DUMMY DATA  — mirrors every column pulled by load_training_data()
# ==========================================================================

def make_dummy_df(n: int = 200, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """
    Generate synthetic rows that exactly mirror what the seed script writes
    to the database:

    Key differences vs naive dummy data
    ------------------------------------
    Geography  : stored as enum .value strings — "gauteng", "western_cape", etc.
                 NOT the original CSV strings "France", "Germany", "Spain"
    Salary     : ZAR (seed converts USD → ZAR at ~18.5x before storing)
                 Range: ~370k – 3.7M ZAR  (was 20k–200k USD)
    Balance    : ZAR (same conversion)
                 Range: 0 or ~18k – 4.6M ZAR
    Tenure     : raw CSV value 0-10 (seed stores int(r["Tenure"]) directly,
                 column is named tenure_months but holds the 0-10 year value)
    Segments   : "Affluent", "Mid", "Mass"  — computed from USD thresholds
                 in compute_customer_customs() before ZAR conversion, so
                 most ZAR salaries map to Affluent/Mid
    Enums      : all string values match the exact .value of each Enum class
    """
    rng = np.random.default_rng(seed)

    # Approximate exchange rate used by the seed script
    USD_TO_ZAR = 18.50

    # ── raw fields — matching DB ranges ───────────────────────────────────
    age          = rng.integers(18, 75, n)
    tenure       = rng.integers(0, 11, n)            # 0-10, stored as tenure_months
    salary_usd   = rng.uniform(20_000, 200_000, n)   # original USD (for segment logic)
    salary_zar   = np.round(salary_usd * USD_TO_ZAR, 2)
    credit_score = rng.integers(300, 851, n)
    is_active    = rng.integers(0, 2, n)
    has_cc       = rng.integers(0, 2, n)
    balance_usd  = np.where(
        rng.random(n) < 0.25, 0.0,
        rng.uniform(1_000, 250_000, n)
    )
    balance_zar  = np.round(balance_usd * USD_TO_ZAR, 2)
    num_products = rng.integers(1, 5, n)
    sat_score    = rng.integers(1, 6, n)
    complain     = rng.integers(0, 2, n)
    points       = rng.integers(100, 1001, n)

    # Geography: exact enum .value strings stored by the seed
    geography = rng.choice(
        ["gauteng", "western_cape", "limpopo"   # mapped from France/Germany/Spai
         ], n
    )
    gender    = rng.choice(["Male", "Female"], n)
    card_type = rng.choice(["DIAMOND", "GOLD", "SILVER", "PLATINUM"], n)

    # ── derived: customers ────────────────────────────────────────────────
    # Segment is computed from USD salary (matches compute_customer_customs)
    def get_segment(s_usd, c):
        if s_usd > 150_000 and c > 700: return "Affluent"
        if s_usd >= 75_000 or c >= 500: return "Mid"
        return "Mass"

    # Lifecycle uses raw tenure (0-10) — matches seed behaviour
    def get_lifecycle(t, a, e):
        if e:              return "Churned"
        if t < 12:         return "New"      # almost all rows since tenure 0-10
        if not a and t > 24: return "At-Risk"
        return "Growing"

    def get_age_band(a):
        if a <= 30: return "Young Adult"
        if a <= 50: return "Mid"
        return "Senior"

    # Target first — lifecycle references it
    churn_prob = (
        0.05
        + 0.30 * (age > 50).astype(float)
        + 0.20 * (is_active == 0).astype(float)
        + 0.15 * (balance_zar == 0).astype(float)
        + 0.10 * (num_products > 2).astype(float)
        + 0.10 * (complain == 1).astype(float)
    ).clip(0, 1)
    exited = rng.binomial(1, churn_prob).astype(int)

    segment   = [get_segment(s, c) for s, c in zip(salary_usd, credit_score)]
    lifecycle = [get_lifecycle(t, a, e) for t, a, e in zip(tenure, is_active, exited)]
    age_band  = [get_age_band(a) for a in age]

    # salary_to_balance_ratio uses ZAR/ZAR (consistent units)
    sal_bal_ratio = np.where(
        salary_zar > 0,
        np.round(balance_zar / salary_zar, 4),
        0.0,
    )

    # ── derived: product_holdings ─────────────────────────────────────────
    prod_diversity   = np.minimum(num_products + has_cc, 3)
    is_single        = (num_products == 1).astype(int)
    bal_per_product  = np.where(
        num_products > 0,
        np.round(balance_zar / num_products, 2),
        0.0,
    )
    has_zero_balance = (balance_zar == 0).astype(int)

    # ── derived: support_interactions ─────────────────────────────────────
    def get_sat_band(s):
        if s <= 2: return "Dissatisfied"
        if s == 3: return "Neutral"
        return "Satisfied"

    sat_band             = [get_sat_band(s) for s in sat_score]
    complaint_x_sat      = complain * (5 - sat_score)
    is_high_risk_support = ((complain == 1) & (sat_score <= 2)).astype(int)

    # ── derived: behavioral_signals ───────────────────────────────────────
    CARD_WEIGHTS = {"DIAMOND": 4, "GOLD": 3, "SILVER": 2, "PLATINUM": 1}
    MAX_POINTS   = 1000

    points_per_tenure = np.round(points / np.maximum(tenure, 1), 2)
    card_engagement   = np.array([
        round(CARD_WEIGHTS[c] * (p / MAX_POINTS), 4)
        for c, p in zip(card_type, points)
    ])
    activity_drop = ((is_active == 0) & (tenure > 24)).astype(int)

    df = pd.DataFrame({
        # identifiers
        "RowNumber":              np.arange(1, n + 1),
        "CustomerId":             rng.integers(10_000_000, 20_000_000, n),
        "Surname":                rng.choice(
            ["Dlamini", "Nkosi", "Mokoena", "Van der Merwe", "Sithole"], n
        ),
        # raw
        "Geography":              geography,
        "Gender":                 gender,
        "CardType":               card_type,
        "Age":                    age,
        "Tenure":                 tenure,
        "EstimatedSalary":        salary_zar,   # ZAR
        "CreditScore":            credit_score,
        "IsActiveMember":         is_active,
        "HasCrCard":              has_cc,
        "Balance":                balance_zar,  # ZAR
        "NumOfProducts":          num_products,
        "SatisfactionScore":      sat_score,
        "Complain":               complain,
        "PointEarned":            points,
        # derived: customers
        "Segment":                segment,
        "LifecycleStage":         lifecycle,
        "AgeBand":                age_band,
        "SalaryToBalanceRatio":   sal_bal_ratio,
        # derived: product_holdings
        "ProductDiversityScore":  prod_diversity,
        "IsSingleProduct":        is_single,
        "BalancePerProduct":      bal_per_product,
        "HasZeroBalance":         has_zero_balance,
        # derived: support_interactions
        "SatisfactionBand":       sat_band,
        "ComplaintXSatisfaction": complaint_x_sat,
        "IsHighRiskSupport":      is_high_risk_support,
        # derived: behavioral_signals
        "PointsPerTenure":        points_per_tenure,
        "CardEngagementScore":    card_engagement,
        "ActivityDropFlag":       activity_drop,
        # target
        "Exited":                 exited,
    })

    log.info(f"Generated {n} dummy rows  |  churn rate: {df['Exited'].mean():.2%}")
    log.info(f"  Salary range (ZAR) : R{salary_zar.min():,.0f} – R{salary_zar.max():,.0f}")
    log.info(f"  Balance range (ZAR): R{balance_zar.min():,.0f} – R{balance_zar.max():,.0f}")
    log.info(f"  Tenure range       : {tenure.min()} – {tenure.max()} (raw CSV units)")
    log.info(f"  Geography values   : {sorted(set(geography))}")
    return df


# ==========================================================================
# FIND LATEST MODEL  (fallback when no --model-path given)
# ==========================================================================

def find_model(models_dir: Path, model_name: str = "gradient_boosting") -> Path:
    """Return the saved model for the given model_name."""
    preferred = models_dir / f"{model_name}_{MODEL_VERSION}.joblib"
    if preferred.exists():
        log.info(f"Auto-selected model: {preferred}")
        return preferred

    # Fallback: pick the most recently modified .joblib
    candidates = sorted(models_dir.glob("*.joblib"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No .joblib files found in {models_dir}")
    latest = candidates[-1]
    log.warning(f"{model_name} model not found, falling back to: {latest}")
    return latest
# ==========================================================================
# EVALUATION
# ==========================================================================

def evaluate_model(model_path: Path, n_samples: int, show_predictions: bool) -> None:

    log.info(SEP)
    log.info("  CHURN MODEL — EVALUATION SCRIPT")
    log.info(SEP)

    # ── STEP 1: load ──────────────────────────────────────────────────────
    log.info(SEP)
    log.info("STEP 1 — Loading model")
    log.info(SEP)

    clf = Churn_Classifier.load_model(path=model_path)

    log.info(f"  Model type     : {clf.model_type}")
    log.info(f"  Model version  : {clf.day_trained}")
    log.info(f"  Feature count  : {clf.feature_dim}")
    log.info(f"  Feature names  : {clf.feature_names}")
    log.info(f"  Encoders       : {list(clf.label_encoders.keys())}")
    log.info(f"  Trained on     : {clf.training_samples:,} samples")

    # ── STEP 2: generate dummy data ───────────────────────────────────────
    log.info(SEP)
    log.info(f"STEP 2 — Generating {n_samples} dummy rows")
    log.info(SEP)

    dummy_df = make_dummy_df(n=n_samples)

    # ── STEP 3: prepare features ──────────────────────────────────────────
    log.info(SEP)
    log.info("STEP 3 — Preparing features (inference mode — no refitting)")
    log.info(SEP)

    X, y = clf.prepare_data(dummy_df, fit_encoders=False)
    log.info(f"  Feature matrix shape : {X.shape}")
    log.info(f"  Target distribution  : {dict(y.value_counts().sort_index())}")

    # ── STEP 4: predict ───────────────────────────────────────────────────
    log.info(SEP)
    log.info("STEP 4 — Running predictions")
    log.info(SEP)

    preds  = clf.predict(X)
    probas = clf.predict_proba(X)[:, 1]

    log.info(f"  Predicted churn count : {preds.sum()} / {len(preds)}")
    log.info(f"  Avg churn probability : {probas.mean():.4f}")
    log.info(f"  Min / Max probability : {probas.min():.4f} / {probas.max():.4f}")

    # ── STEP 5: metrics ───────────────────────────────────────────────────
    log.info(SEP)
    log.info("STEP 5 — Metrics")
    log.info(SEP)

    acc = accuracy_score(y, preds)
    auc = roc_auc_score(y, probas)
    cm  = confusion_matrix(y, preds)
    cr  = classification_report(y, preds, target_names=["Retained", "Churned"])

    tn, fp, fn, tp = cm.ravel()

    log.info(f"  Accuracy          : {acc:.4f}")
    log.info(f"  ROC-AUC           : {auc:.4f}")
    log.info(f"  True  Positives   : {tp}   (correctly predicted churners)")
    log.info(f"  False Positives   : {fp}   (falsely flagged as churners)")
    log.info(f"  True  Negatives   : {tn}   (correctly predicted retained)")
    log.info(f"  False Negatives   : {fn}   (missed churners)")
    log.info(f"\n  Classification report:\n{cr}")
    log.info(f"  Confusion matrix:\n{cm}")

    # ── STEP 6: risk band breakdown ───────────────────────────────────────
    log.info(SEP)
    log.info("STEP 6 — Churn risk band breakdown")
    log.info(SEP)

    bands = pd.cut(
        probas,
        bins=[0.0, 0.3, 0.6, 0.8, 1.0],
        labels=["LOW (<30%)", "MEDIUM (30-60%)", "HIGH (60-80%)", "CRITICAL (>80%)"],
        include_lowest=True,
    )
    band_counts = bands.value_counts().sort_index()
    for band, count in band_counts.items():
        pct = count / len(probas) * 100
        log.info(f"  {band:<20}: {count:>4} customers  ({pct:.1f}%)")

    # ── STEP 7: optional per-row table ────────────────────────────────────
    if show_predictions:
        log.info(SEP)
        log.info("STEP 7 — Per-row prediction table (first 20 rows)")
        log.info(SEP)

        preview = pd.DataFrame({
            "ActualChurn":    y.values[:20],
            "PredictedChurn": preds[:20],
            "ChurnProb":      probas[:20].round(4),
            "RiskBand":       bands.values[:20],
        })
        log.info(f"\n{preview.to_string(index=True)}")

    log.info(SEP)
    log.info("EVALUATION COMPLETE ✓")
    log.info(SEP)


# ==========================================================================
# CLI
# ==========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a saved churn model")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Path to a .joblib model file. Defaults to the latest in MODELS_DIR.",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=200,
        help="Number of dummy rows to generate (default 200).",
    )
    parser.add_argument(
        "--show-predictions",
        action="store_true",
        help="Print a per-row prediction table for the first 20 rows.",
    )
    args = parser.parse_args()

    model_path = args.model_path or find_model(MODELS_DIR)
    evaluate_model(
        model_path=model_path,
        n_samples=args.n_samples,
        show_predictions=args.show_predictions,
    )