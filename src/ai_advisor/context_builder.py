"""
context_builder.py
-------------------
Builds a structured, LLM-ready context dictionary for a single customer.

Unlike a generic feature store lookup, this builder pulls live data directly
from the relational schema (Customer, ProductHolding, SupportInteraction,
BehavioralSignal, ChurnScore) via database.operations.get_full_profile(), and
prefers the batch-scored ChurnScore already sitting in the database over
re-running the model, since the Prediction Agent runs on its own schedule.

Responsibilities
----------------
1. Fetch the full customer profile from the database
2. Reconstruct the raw feature row in the shape the classifier was trained on
3. Use the stored ChurnScore if present, otherwise score live as a fallback
4. Compute personalised SHAP drivers for explainability
5. Package everything into a single context dict consumed by ChurnAdvisor
"""

import pandas as pd
from typing import Dict, Optional
from uuid import UUID

from loguru import logger

from database.operation import get_full_profile
from src.classifier.models import Churn_Classifier
from config.settings import MODELS_DIR


# ---------------------------------------------------------------------------
# Risk banding — mirrors database/schemas.py ChurnRiskBand thresholds
# ---------------------------------------------------------------------------

def _risk_tier(probability: float) -> str:
    if probability >= 0.8:
        return "Critical"
    elif probability >= 0.6:
        return "High"
    elif probability >= 0.3:
        return "Medium"
    return "Low"


SHAP_TOP_N = 6

# Mirrors Churn_Classifier.CLASSIFIERS keys exactly — used to pick the
# right SHAP explainer per model type.
TREE_BASED_MODEL_TYPES = ("random_forest", "gradient_boosting")


class CustomerContextBuilder:
    """
    Builds the structured context dict for one customer, combining database
    records with live model predictions and personalised SHAP explanations.
    """

    def __init__(self, model_type: str = "random_forest", shap_top_n: int = SHAP_TOP_N):
        self.model_type = model_type
        self.shap_top_n = shap_top_n

        # NOTE: Churn_Classifier.save_model() writes to
        # MODELS_DIR / f"{self.model_type}_model.joblib" — no version suffix
        # in the filename. The path here must match that exactly or
        # load_model() will always raise FileNotFoundError.
        self.model_path = MODELS_DIR / f"{model_type}_model.joblib"

        if not self.model_path.exists():
            logger.warning(
                f"Model file {self.model_path} not found. "
                f"Context builder will fall back to stored churn scores only "
                f"and SHAP drivers will be unavailable."
            )
            self.model: Optional[Churn_Classifier] = None
        else:
            self.model = Churn_Classifier.load_model(path=self.model_path)

    # ------------------------------------------------------------------
    # Feature row reconstruction
    # ------------------------------------------------------------------

    def _build_feature_row(self, profile: dict) -> pd.DataFrame:
        """
        Reconstruct a single-row DataFrame from the joined database tables.

        Churn_Classifier.prepare_data() drops RowNumber, CustomerId, Surname,
        and Exited if present, then keeps every remaining column as a
        feature. At inference time it reindexes onto self.feature_names, so
        any extra columns supplied here that the model was NOT trained on
        (e.g. CreditScore, if the training run excluded it) are silently
        dropped rather than causing an error — only genuinely MISSING
        required columns will raise.
        """
        customer = profile["customer"]
        holding  = profile["holding"]

        row = {
            "CreditScore":     customer.credit_score,
            "Geography":       customer.geography.value,
            "Gender":          customer.gender.value,
            "Age":             customer.age,
            "Tenure":          customer.tenure_months,
            "Balance":         holding.total_balance if holding.total_balance is not None else 0.0,
            "NumOfProducts":   holding.num_products,
            "HasCrCard":       int(customer.has_credit_card) if customer.has_credit_card is not None else 0,
            "IsActiveMember":  int(customer.is_active_member) if customer.is_active_member is not None else 0,
            "EstimatedSalary": customer.estimated_salary if customer.estimated_salary is not None else 0.0,
        }
        return pd.DataFrame([row])

    # ------------------------------------------------------------------
    # SHAP — personalised, per customer, not a static global table
    # ------------------------------------------------------------------

    def _top_shap_drivers(self, X_row: pd.DataFrame) -> list[dict]:
        """Compute personalised SHAP drivers for this single customer row."""
        if self.model is None:
            return []

        try:
            import shap
        except ImportError:
            logger.warning("shap not installed — skipping driver explanation. Run: pip install shap")
            return []

        X_scaled, _ = self.model.prepare_data(X_row, fit_encoders=False)

        if self.model.model_type in TREE_BASED_MODEL_TYPES:
            explainer   = shap.TreeExplainer(self.model.model)
            shap_values = explainer.shap_values(X_scaled.values)
            shap_arr    = shap_values[1] if isinstance(shap_values, list) else shap_values
        else:
            # logistic_regression — model-agnostic fallback
            explainer   = shap.KernelExplainer(self.model.model.predict_proba, X_scaled.values)
            shap_values = explainer.shap_values(X_scaled.values, nsamples=100)
            shap_arr    = shap_values[1] if isinstance(shap_values, list) else shap_values

        shap_row = pd.Series(shap_arr[0], index=X_scaled.columns)
        ranked   = shap_row.abs().sort_values(ascending=False).head(self.shap_top_n).index.tolist()

        return [
            {
                "feature":   feat,
                "value":     round(float(shap_row[feat]), 4),
                "direction": "increases churn risk" if shap_row[feat] > 0 else "decreases churn risk",
            }
            for feat in ranked
        ]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def build_context(self, customer_id: str) -> Dict:
        """
        Build the full structured context dict for one customer, ready to be
        summarised and passed to the LLM by ChurnAdvisor.
        """
        profile = get_full_profile(UUID(customer_id))

        if not profile or not all([
            profile.get("customer"), profile.get("holding"),
            profile.get("support"), profile.get("signal"),
        ]):
            logger.warning(f"No complete profile found for customer {customer_id}.")
            return {"customer_id": customer_id, "context": "No data available to build context"}

        customer = profile["customer"]
        holding  = profile["holding"]
        support  = profile["support"]
        signal   = profile["signal"]
        score    = profile.get("churn_score")

        # ── Prefer the stored batch score; fall back to a live prediction ──
        if score and score.churn_probability is not None:
            churn_probability = score.churn_probability
            risk_tier         = score.churn_risk_band.value if score.churn_risk_band else _risk_tier(churn_probability)
            top_driver_stored = score.top_churn_driver
        elif self.model is not None:
            X_row = self._build_feature_row(profile)
            X_scaled, _ = self.model.prepare_data(X_row, fit_encoders=False)
            churn_probability = float(self.model.predict_proba(X_scaled)[0, 1])
            risk_tier         = _risk_tier(churn_probability)
            top_driver_stored = None
        else:
            churn_probability = 0.0
            risk_tier         = "Unknown"
            top_driver_stored = None

        # ── Personalised SHAP drivers (live, regardless of score source) ──
        shap_drivers = []
        if self.model is not None:
            X_row = self._build_feature_row(profile)
            shap_drivers = self._top_shap_drivers(X_row)

        context = {
            "customer_id":       customer_id,
            "churn_probability": round(churn_probability, 4),
            "risk_tier":         risk_tier,
            "stored_top_driver": top_driver_stored,

            "account_info": {
                "surname":          customer.surname,
                "geography":        customer.geography.value,
                "gender":           customer.gender.value,
                "age":              customer.age,
                "tenure_months":    customer.tenure_months,
                "card_type":        customer.card_type.value,
                "credit_score":     customer.credit_score,
                "customer_segment": customer.segment.value,
                "lifecycle_stage":  customer.lifecycle_stage.value,
                "estimated_salary": customer.estimated_salary,
            },

            "product_signals": {
                "num_products":            holding.num_products,
                "total_balance":           holding.total_balance,
                "is_single_product":       holding.is_single_product,
                "has_zero_balance":        holding.has_zero_balance,
                "balance_per_product":     holding.balance_per_product,
                "product_diversity_score": holding.product_diversity_score,
            },

            "support_signals": {
                "has_complaint":            support.has_complaint,
                "satisfaction_score":       support.satisfaction_score,
                "satisfaction_band":        support.satisfaction_band.value,
                "is_high_risk_support":     support.is_high_risk_support,
                "complaint_x_satisfaction": support.complaint_x_satisfaction,
            },

            "behavioral_signals": {
                "is_active_member":     customer.is_active_member,
                "points_earned":        signal.points_earned,
                "points_per_tenure":     signal.points_per_tenure,
                "card_engagement_score": signal.card_engagement_score,
                "activity_drop_flag":    signal.activity_drop_flag,
            },

            "top_churn_drivers": shap_drivers,
        }

        logger.success(
            f"Context built for customer {customer_id} — "
            f"churn probability {churn_probability:.2%}, risk tier {risk_tier}"
        )
        return context


if __name__ == "__main__":
    builder = CustomerContextBuilder()
    context = builder.build_context("47b23f9e-906a-426f-959c-077bc762e18b")
    print(context)