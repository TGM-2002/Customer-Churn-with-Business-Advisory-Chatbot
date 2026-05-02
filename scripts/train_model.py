"""
train_pipeline.py
-----------------
End-to-end training pipeline for the churn classifier.

Flow
----
1. Pull & join all four tables from Postgres into a flat DataFrame
2. Split into train / val / test
3. Race all three classifiers with Churn_Classifier.train_models()
4. Evaluate the winner on held-out test set
5. Persist the winner (model + scaler + encoders + metadata) via save_model()

Usage
-----
    python train_pipeline.py                          # race all models
    python train_pipeline.py --model random_forest    # single model only
    python train_pipeline.py --test-size 0.15         # custom test split
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from database.connection import DatabaseConnection
from database.schemas import (
    Customer,
    ProductHolding,
    SupportInteraction,
    BehavioralSignal,
    ChurnScore,
)
from src.classifier.models import Churn_Classifier
from config.settings import MODELS_DIR, MODEL_VERSION, RANDOM_STATE

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("train_pipeline")
SEP = "=" * 65


# ==========================================================================
# 1. DATA EXTRACTION  (read-only — no DB writes)
# ==========================================================================

def load_training_data(session: Session) -> pd.DataFrame:
    """
    JOIN all five tables into one flat DataFrame, pulling every feature column.

    Excluded (model outputs / leakage risk):
        churn_scores.churn_probability  — IS the target proxy, leakage
        churn_scores.churn_risk_band    — derived from probability, leakage
        churn_scores.top_churn_driver   — post-hoc explanation, leakage

    Column groups
    -------------
    customers        : Age, Tenure, EstimatedSalary, CreditScore,
                       IsActiveMember, HasCrCard, Geography, Gender,
                       CardType, Segment, LifecycleStage, AgeBand,
                       SalaryToBalanceRatio
    product_holdings : Balance, NumOfProducts, ProductDiversityScore,
                       IsSingleProduct, BalancePerProduct, HasZeroBalance
    support          : SatisfactionScore, Complain, SatisfactionBand,
                       ComplaintXSatisfaction, IsHighRiskSupport
    behavioral       : PointEarned, PointsPerTenure, CardEngagementScore,
                       ActivityDropFlag
    churn_scores     : Exited  <- target
    """
    log.info("Querying database (read-only) ...")

    rows = (
        session.query(
            # identifiers (dropped before modelling)
            Customer.customer_id.label("CustomerId"),
            Customer.surname.label("Surname"),

            # customers: raw
            Customer.geography.label("_geography"),
            Customer.gender.label("_gender"),
            Customer.card_type.label("_card_type"),
            Customer.age.label("Age"),
            Customer.tenure_months.label("Tenure"),
            Customer.estimated_salary.label("EstimatedSalary"),
            Customer.credit_score.label("CreditScore"),
            Customer.is_active_member.label("IsActiveMember"),
            Customer.has_credit_card.label("HasCrCard"),

            # customers: derived
            Customer.segment.label("_segment"),
            Customer.lifecycle_stage.label("_lifecycle_stage"),
            Customer.age_band.label("_age_band"),
            Customer.salary_to_balance_ratio.label("SalaryToBalanceRatio"),

            # product_holdings: raw
            ProductHolding.total_balance.label("Balance"),
            ProductHolding.num_products.label("NumOfProducts"),

            # product_holdings: derived
            ProductHolding.product_diversity_score.label("ProductDiversityScore"),
            ProductHolding.is_single_product.label("IsSingleProduct"),
            ProductHolding.balance_per_product.label("BalancePerProduct"),
            ProductHolding.has_zero_balance.label("HasZeroBalance"),

            # support_interactions: raw
            SupportInteraction.satisfaction_score.label("SatisfactionScore"),
            SupportInteraction.has_complaint.label("Complain"),

            # support_interactions: derived
            SupportInteraction.satisfaction_band.label("_satisfaction_band"),
            SupportInteraction.complaint_x_satisfaction.label("ComplaintXSatisfaction"),
            SupportInteraction.is_high_risk_support.label("IsHighRiskSupport"),

            # behavioral_signals: raw
            BehavioralSignal.points_earned.label("PointEarned"),

            # behavioral_signals: derived
            BehavioralSignal.points_per_tenure.label("PointsPerTenure"),
            BehavioralSignal.card_engagement_score.label("CardEngagementScore"),
            BehavioralSignal.activity_drop_flag.label("ActivityDropFlag"),

            # target
            ChurnScore.churned.label("Exited"),
        )
        .join(ProductHolding,     Customer.customer_id == ProductHolding.customer_id)
        .join(SupportInteraction, Customer.customer_id == SupportInteraction.customer_id)
        .join(BehavioralSignal,   Customer.customer_id == BehavioralSignal.customer_id)
        .join(ChurnScore,         Customer.customer_id == ChurnScore.customer_id)
        .filter(ChurnScore.churned.isnot(None))
        .all()
    )

    if not rows:
        raise ValueError(
            "No labelled rows found. Make sure churn_scores.churned is populated."
        )

    df = pd.DataFrame(rows)

    # SQLAlchemy Enum objects -> plain strings (all categorical columns)
    enum_cols = {
        "_geography":         "Geography",
        "_gender":            "Gender",
        "_card_type":         "CardType",
        "_segment":           "Segment",
        "_lifecycle_stage":   "LifecycleStage",
        "_age_band":          "AgeBand",
        "_satisfaction_band": "SatisfactionBand",
    }
    for raw_col, clean_col in enum_cols.items():
        df[clean_col] = df[raw_col].apply(
            lambda x: x.value if hasattr(x, "value") else str(x)
        )
    df.drop(columns=list(enum_cols.keys()), inplace=True)

    # Boolean -> int
    bool_cols = (
        "IsActiveMember", "HasCrCard", "Complain", "Exited",
        "IsSingleProduct", "HasZeroBalance", "IsHighRiskSupport", "ActivityDropFlag",
    )
    for col in bool_cols:
        df[col] = df[col].astype(int)

    # Dummy RowNumber so prepare_data drop-list doesn't error
    df.insert(0, "RowNumber", range(1, len(df) + 1))

    log.info(f"Loaded {len(df):,} labelled rows  |  churn rate: {df['Exited'].mean():.2%}")
    return df


# ==========================================================================
# 2. TRAIN / VAL / TEST SPLIT
# ==========================================================================

def stratified_split(
    df: pd.DataFrame,
    val_size: float = 0.10,
    test_size: float = 0.10,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from sklearn.model_selection import train_test_split

    remaining, test_df = train_test_split(
        df, test_size=test_size, stratify=df["Exited"], random_state=random_state
    )
    adjusted_val = val_size / (1.0 - test_size)
    train_df, val_df = train_test_split(
        remaining, test_size=adjusted_val, stratify=remaining["Exited"],
        random_state=random_state,
    )

    for name, part in (("train", train_df), ("val", val_df), ("test", test_df)):
        log.info(f"  {name:>5}: {len(part):>5} rows  churn rate={part['Exited'].mean():.2%}")

    return (
        train_df.reset_index(drop=True),
        val_df.reset_index(drop=True),
        test_df.reset_index(drop=True),
    )


# ==========================================================================
# 3. MAIN PIPELINE
# ==========================================================================

def run_pipeline(
    val_size: float = 0.10,
    test_size: float = 0.10,
    single_model: str | None = None,
    save_path: Path | None = None,
) -> Churn_Classifier:

    log.info(SEP)
    log.info("  CHURN CLASSIFIER — TRAINING PIPELINE")
    log.info(f"  Version : {MODEL_VERSION}")
    log.info(f"  Started : {datetime.utcnow().isoformat(timespec='seconds')}Z")
    log.info(SEP)

    db = DatabaseConnection()

    with db.get_db() as session:

        # ── STEP 1: extract (read-only) ────────────────────────────────
        log.info(SEP)
        log.info("STEP 1 — Extract data from Postgres  [READ ONLY]")
        log.info(SEP)
        full_df = load_training_data(session)

        # ── STEP 2: split ──────────────────────────────────────────────
        log.info(SEP)
        log.info("STEP 2 — Stratified train / val / test split")
        log.info(SEP)
        train_df, val_df, test_df = stratified_split(full_df, val_size, test_size)

        # ── STEP 3: feature engineering ────────────────────────────────
        log.info(SEP)
        log.info("STEP 3 — prepare_data (fit encoders + scaler on train only)")
        log.info(SEP)
        clf = Churn_Classifier(model_name=single_model or "random_forest")

        X_train, y_train = clf.prepare_data(train_df, fit_encoders=True)
        X_val,   y_val   = clf.prepare_data(val_df,   fit_encoders=False)
        X_test,  y_test  = clf.prepare_data(test_df,  fit_encoders=False)

        log.info(f"Features ({X_train.shape[1]}): {clf.feature_names}")

        # ── STEP 4: train ──────────────────────────────────────────────
        log.info(SEP)
        if single_model:
            log.info(f"STEP 4 — Training single model: {single_model}")
            log.info(SEP)
            clf.fit(X_train, y_train)
        else:
            log.info("STEP 4 — Racing all classifiers (train_models)")
            log.info(SEP)
            clf.train_models(X_train, y_train, X_val, y_val)
            log.info(f"All accuracy scores : {clf.accurate_scores}")
            log.info(f"Winner              : {clf.model_type}")

        # ── STEP 5: evaluate on held-out test set ──────────────────────
        log.info(SEP)
        log.info("STEP 5 — Evaluate on held-out test set")
        log.info(SEP)
        metrics = clf.evaluate(X_test, y_test)
        cr = metrics["classification_report"]["1"]

        log.info(f"  Accuracy  : {metrics['accuracy']:.4f}")
        log.info(f"  ROC-AUC   : {metrics['roc_auc']:.4f}")
        log.info(f"  Precision : {cr['precision']:.4f}")
        log.info(f"  Recall    : {cr['recall']:.4f}")
        log.info(f"  F1        : {cr['f1-score']:.4f}")
        log.info(f"  Confusion matrix:\n    {np.array(metrics['confusion_matrix'])}")

        # ── STEP 6: feature importance ─────────────────────────────────
        log.info(SEP)
        log.info("STEP 6 — Feature importance")
        log.info(SEP)
        importance_df = clf.calculate_feature_importance(X_train, y_train, method="auto")
        log.info(f"\n{importance_df.to_string(index=False)}")

        # ── STEP 7: save all models, highlight winner ─────────────────
        log.info(SEP)
        log.info("STEP 7 — Saving all models + scaler + encoders")
        log.info(SEP)

        if single_model:
            # Only one model was trained — save it
            saved_paths = {}
            out_path = save_path or (MODELS_DIR / f"{clf.model_type}_{MODEL_VERSION}.joblib")
            clf.save_model(path=out_path)
            saved_paths[clf.model_type] = out_path
        else:
            # Save every trained model individually, then note the winner
            saved_paths = {}
            scores = clf.accurate_scores  # {model_name: val_accuracy}
            best_name = clf.model_type

            for model_name, trained_model in clf.models.items():
                # Temporarily swap the model on the classifier so save_model
                # serialises this model alongside the shared scaler/encoders
                clf.model      = trained_model
                clf.model_type = model_name

                model_out = MODELS_DIR / f"{model_name}_{MODEL_VERSION}.joblib"
                clf.save_model(path=model_out)
                saved_paths[model_name] = model_out

                tag = "  ★ BEST" if model_name == best_name else ""
                log.info(
                    f"  [{model_name}]  "
                    f"val_accuracy={scores[model_name]:.4f}  "
                    f"→ {model_out}{tag}"
                )

            # Restore winner as the active model
            clf.model      = clf.models[best_name]
            clf.model_type = best_name
            log.info(f"\n  Best model  : {best_name}  (val_accuracy={scores[best_name]:.4f})")

        log.info(f"  Version   : {MODEL_VERSION}")
        log.info(f"  Trained   : {clf.day_trained.isoformat(timespec='seconds')}Z")
        log.info(f"  Samples   : {clf.training_samples:,}")
        log.info(f"  Features  : {clf.feature_dim}")
        log.info(f"  Encoders  : {list(clf.label_encoders.keys())}")

        log.info(SEP)
        log.info("PIPELINE COMPLETE ✓")
        log.info(SEP)

        return clf, saved_paths


# ==========================================================================
# 4. VERIFY ROUND-TRIP LOAD
# ==========================================================================

def verify_saved_model(model_path: Path) -> None:
    log.info(SEP)
    log.info("VERIFICATION — load_model() round-trip check")
    log.info(SEP)
    loaded = Churn_Classifier.load_model(path=model_path)
    log.info(f"  model_type     : {loaded.model_type}")
    log.info(f"  feature_dim    : {loaded.feature_dim}")
    log.info(f"  feature_names  : {loaded.feature_names}")
    log.info(f"  label_encoders : {list(loaded.label_encoders.keys())}")
    log.info(f"  day_trained    : {loaded.day_trained}")
    log.info("  Round-trip load ✓")


# ==========================================================================
# 5. CLI
# ==========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Churn model training pipeline")
    parser.add_argument(
        "--model",
        choices=list(Churn_Classifier.CLASSIFIERS.keys()),
        default=None,
        help="Train a single model instead of racing all three.",
    )
    parser.add_argument(
        "--val-size", type=float, default=0.10,
        help="Fraction of data for validation (default 0.10).",
    )
    parser.add_argument(
        "--test-size", type=float, default=0.10,
        help="Fraction of data for test (default 0.10).",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Custom output path for the .joblib file.",
    )
    args = parser.parse_args()

    trained_clf, saved_paths = run_pipeline(
        val_size=args.val_size,
        test_size=args.test_size,
        single_model=args.model,
        save_path=args.out,
    )

    # Verify every saved model loads cleanly
    for model_name, path in saved_paths.items():
        verify_saved_model(path)