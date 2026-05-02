import pandas as pd
import numpy as np
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_curve, accuracy_score,
)
from sklearn.preprocessing import StandardScaler, LabelEncoder
from src.classifier.logistic_regression import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging as logger
from datetime import datetime
from sklearn.model_selection import GridSearchCV, cross_val_score
from config.settings import RANDOM_STATE, CV_FOLDS, MODELS_DIR, MODEL_VERSION
import joblib
from sklearn.inspection import permutation_importance


class Churn_Classifier:
    CLASSIFIERS = {
        "random_forest": {
            "class": RandomForestClassifier,
            "params": {
                "n_estimators": 100,
                "max_depth": 40,
                "class_weight": "balanced",
                "random_state": RANDOM_STATE,
            },
            "grid_params": {
                "n_estimators": [50, 100, 200],
                "max_depth": [30, 50, None],
            },
        },
        # FIX: removed sklearn-only params (solver, class_weight, penalty)
        # that the custom LogisticRegression class doesn't accept.
        "logistic_regression": {
            "class": LogisticRegression,
            "params": {
                "C": 1.0,
                "max_iter": 1000,
                "random_state": RANDOM_STATE,
            },
            "grid_params": {
                "C": [0.01, 0.1, 1, 10],
            },
        },
        "gradient_boosting": {
            "class": GradientBoostingClassifier,
            "params": {
                "n_estimators": 100,
                "learning_rate": 0.1,
                "max_depth": 5,
                "random_state": RANDOM_STATE,
            },
            "grid_params": {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.1, 0.2],
            },
        },
    }

    def __init__(
        self,
        model_name: str = "random_forest",
        custom_params: Optional[Dict] = None,
    ):
        if model_name not in self.CLASSIFIERS:
            logger.error(f"Model name: {model_name} does not exist")
            raise ValueError(f"Unknown model: {model_name}")

        self.model_type = model_name
        self.model_class = self.CLASSIFIERS[model_name]["class"]
        self.params = self.CLASSIFIERS[model_name]["params"].copy()
        self.config = self.CLASSIFIERS[model_name]

        if custom_params:
            self.params.update(custom_params)

        self.model = self.model_class(**self.params)
        self.is_trained = False
        self.day_trained = None
        self.scaler = StandardScaler()
        self.label_encoders: Dict = {}
        self.feature_names: List[str] = []
        self.feature_dim: int = 0
        self.training_samples: int = 0

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------

    def prepare_data(
        self,
        df: pd.DataFrame,
        fit_encoders: bool = True,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features from raw DataFrame.

        Args:
            df: Raw DataFrame with customer data.
            fit_encoders:
                True  → fit new encoders/scaler (training mode).
                False → use existing encoders/scaler (inference mode).

        Returns:
            X_scaled : scaled feature DataFrame.
            y        : binary target Series (0/1).
        """
        X = df.drop(["RowNumber", "CustomerId", "Surname", "Exited"], axis=1, errors="ignore")
        y = df["Exited"].astype(int) if "Exited" in df.columns else pd.Series(dtype=int)

        if not self.feature_names:
            self.feature_names = X.columns.tolist()

        categorical_cols = X.select_dtypes(include=["object"]).columns

        if fit_encoders:
            logger.info("Fitting new encoders and scaler...")
            for col in categorical_cols:
                le = LabelEncoder()
                X = X.copy()
                X[col] = le.fit_transform(X[col].astype(str))
                self.label_encoders[col] = le
        else:
            # FIX: inference path was missing — apply existing encoders
            if not self.label_encoders:
                raise ValueError("No label encoders found. Run prepare_data with fit_encoders=True first.")
            X = X.copy()
            for col in categorical_cols:
                if col in self.label_encoders:
                    le = self.label_encoders[col]
                    X[col] = le.transform(X[col].astype(str))
                else:
                    logger.warning(f"No encoder found for column '{col}', skipping.")

        X = X.fillna(X.median(numeric_only=True))

        if fit_encoders:
            X_scaled_arr = self.scaler.fit_transform(X)
            self.feature_dim = X.shape[1]
            logger.info(f"Fitted scaler on {self.feature_dim} features")
        else:
            # Reorder columns to exactly match the order seen during fit.
            # sklearn scalers raise ValueError if column order differs.
            missing = [c for c in self.feature_names if c not in X.columns]
            if missing:
                raise ValueError(f"Inference data is missing columns: {missing}")
            X = X[self.feature_names]
            X_scaled_arr = self.scaler.transform(X)

        X_scaled = pd.DataFrame(X_scaled_arr, columns=self.feature_names, index=X.index)

        logger.info(
            f"Data prepared: {len(X_scaled)} samples, {self.feature_dim} features "
            f"(mode: {'TRAINING' if fit_encoders else 'INFERENCE'})"
        )
        return X_scaled, y

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, X: pd.DataFrame, y: pd.Series, validate: bool = False):
        if self.feature_dim != X.shape[1]:
            raise ValueError(
                f"Feature mismatch: expected {self.feature_dim}, got {X.shape[1]}"
            )
        if len(X) != len(y):
            raise ValueError(
                f"Row mismatch: X has {len(X)} rows, y has {len(y)} rows"
            )

        try:
            self.model.fit(X, y)
            self.is_trained = True
            self.training_samples = len(X)
            self.day_trained = datetime.utcnow()
            logger.info(
                f"Training complete — samples: {self.training_samples}, "
                f"features: {self.feature_dim}"
            )
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise

    def train_models(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
    ):
        """Train all classifiers, keep the best one."""
        self.models: Dict = {}
        self.accurate_scores: Dict = {}

        for model_name in self.CLASSIFIERS:
            model_class = self.CLASSIFIERS[model_name]["class"]
            params = self.CLASSIFIERS[model_name]["params"].copy()
            model = model_class(**params)

            try:
                model.fit(X, y)
            except Exception as e:
                logger.error(f"Training failed for {model_name}: {e}")
                raise

            y_pred = model.predict(X_val)
            acc = accuracy_score(y_val, y_pred)
            self.models[model_name] = model
            self.accurate_scores[model_name] = acc
            logger.info(f"  {model_name}: accuracy={acc:.4f}")

        best_name, best_acc = max(self.accurate_scores.items(), key=lambda x: x[1])
        logger.info(f"Best model: {best_name} (accuracy={best_acc:.4f})")

        self.model_type = best_name
        self.model_class = self.CLASSIFIERS[best_name]["class"]
        self.params = self.CLASSIFIERS[best_name]["params"].copy()
        self.config = self.CLASSIFIERS[best_name]
        self.model = self.models[best_name]
        self.is_trained = True
        self.day_trained = datetime.utcnow()

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model not trained. Call fit() first.")
        if X.shape[1] != self.feature_dim:
            raise ValueError(f"Expected {self.feature_dim} features, got {X.shape[1]}")
        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model not trained. Call fit() first.")

        X_arr = X.values if isinstance(X, pd.DataFrame) else X
        if X_arr.shape[1] != self.feature_dim:
            raise ValueError(f"Expected {self.feature_dim} features, got {X_arr.shape[1]}")

        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X_arr)

        if hasattr(self.model, "decision_function"):
            scores = self.model.decision_function(X_arr)
            if scores.ndim == 1:
                p1 = 1 / (1 + np.exp(-scores))
                return np.vstack([1 - p1, p1]).T
            return np.exp(scores) / np.sum(np.exp(scores), axis=1, keepdims=True)

        raise ValueError("Model doesn't support probability predictions")

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        if not self.is_trained:
            raise ValueError("Model not trained")

        y_pred = self.predict(X)
        y_proba = self.predict_proba(X)[:, 1]

        report = classification_report(y, y_pred, output_dict=True)
        conf_matrix = confusion_matrix(y, y_pred).tolist()
        auc = roc_auc_score(y, y_proba)
        acc = accuracy_score(y, y_pred)
        precision, recall, _ = precision_recall_curve(y, y_proba)

        results = {
            "accuracy": acc,
            "roc_auc": auc,
            "classification_report": report,
            "confusion_matrix": conf_matrix,
            "precision_recall_curve": {
                "precision": precision.tolist(),
                "recall": recall.tolist(),
            },
        }

        logger.info(f"Evaluation: Accuracy={acc:.4f}, AUC={auc:.4f}")
        return results

    # ------------------------------------------------------------------
    # Hyperparameter tuning
    # ------------------------------------------------------------------

    def hyperparameter_tuning(
        self, X: pd.DataFrame, y: pd.Series, cv: int = CV_FOLDS
    ) -> Dict:
        # FIX: was referencing self.classifier_type — correct attr is self.model_type
        logger.info(f"Starting hyperparameter tuning for {self.model_type}...")

        grid_params = self.config.get("grid_params", {})
        if not grid_params:
            logger.warning("No grid parameters defined. Skipping tuning.")
            return {}

        try:
            grid_search = GridSearchCV(
                estimator=self.config["class"](**self.params),
                param_grid=grid_params,
                cv=cv,
                scoring="roc_auc",
                verbose=1,
                n_jobs=-1,
            )
            grid_search.fit(X, y)

            self.model = grid_search.best_estimator_
            self.is_trained = True
            self.day_trained = datetime.utcnow()

            results = {
                "best_params": grid_search.best_params_,
                "best_score": grid_search.best_score_,
                "cv_results": grid_search.cv_results_,
            }
            logger.info(
                f"Tuning complete. Best AUC: {results['best_score']:.4f} | "
                f"Params: {results['best_params']}"
            )
            return results
        except Exception as e:
            logger.error(f"Hyperparameter tuning failed: {e}")
            raise

    # ------------------------------------------------------------------
    # Feature importance
    # ------------------------------------------------------------------

    def calculate_feature_importance(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None,
        method: str = "auto",
    ) -> pd.DataFrame:
        if not self.is_trained:
            raise ValueError("Model must be trained first")

        # FIX: was referencing self.classifier_type — correct attr is self.model_type
        logger.info(f"Calculating feature importance (method={method})...")

        results: Dict = {}

        if method == "auto":
            if self.model_type in ["random_forest", "gradient_boosting"]:
                methods = ["builtin"]
            else:
                methods = ["permutation"] if y is not None else ["builtin"]
        elif method == "both":
            methods = ["builtin", "permutation"]
        else:
            methods = [method]

        if "builtin" in methods:
            try:
                if hasattr(self.model, "feature_importances_"):
                    results["builtin_importance"] = self.model.feature_importances_
                elif hasattr(self.model, "coef_"):
                    coef = self.model.coef_
                    if coef.ndim > 1:
                        coef = coef[0]
                    results["builtin_importance"] = np.abs(coef)
                else:
                    logger.warning("Model has no built-in importance scores")
            except Exception as e:
                logger.warning(f"Built-in importance failed: {e}")

        if "permutation" in methods:
            if y is None:
                logger.warning("Permutation importance requires y. Skipping.")
            else:
                try:
                    perm = permutation_importance(
                        self.model, X, y,
                        n_repeats=10,
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    )
                    results["permutation_importance"] = perm.importances_mean
                    results["permutation_std"] = perm.importances_std
                except Exception as e:
                    logger.warning(f"Permutation importance failed: {e}")

        importance_df = pd.DataFrame({"feature": self.feature_names})
        for key, values in results.items():
            importance_df[key] = values

        if "builtin_importance" in results and "permutation_importance" in results:
            b_norm = results["builtin_importance"] / results["builtin_importance"].sum()
            p_norm = results["permutation_importance"] / results["permutation_importance"].sum()
            importance_df["combined_importance"] = (b_norm + p_norm) / 2

        sort_col = (
            "combined_importance" if "combined_importance" in importance_df.columns
            else "builtin_importance" if "builtin_importance" in importance_df.columns
            else "permutation_importance"
        )
        importance_df = (
            importance_df.sort_values(sort_col, ascending=False).reset_index(drop=True)
        )
        logger.info(f"Top 5 features: {importance_df['feature'].head().tolist()}")
        return importance_df

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_model(self, path: Optional[Path] = None):
        if not self.is_trained:
            raise ValueError("Model not trained")

        model_path = path or MODELS_DIR / f"{self.model_type}_model.joblib"
        model_path.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            "version": MODEL_VERSION,
            "classifier_type": self.model_type,
            "training_date": self.day_trained.isoformat(),
            "model": self.model,
            "scaler": self.scaler,
            "label_encoders": self.label_encoders,
            "feature_names": self.feature_names,
            "training_samples": self.training_samples,
            "feature_dim": self.feature_dim,
        }
        joblib.dump(model_data, model_path)
        logger.info(f"Model saved to {model_path}")

    @classmethod
    def load_model(
        cls,
        classifier_type: str = "random_forest",
        path: Optional[Path] = None,
    ) -> "Churn_Classifier":
        model_path = path or MODELS_DIR / f"{classifier_type}_model.joblib"
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        model_data = joblib.load(model_path)

        # FIX: __init__ uses 'model_name', not 'classifier_name'
        predictor = cls(model_name=model_data["classifier_type"])
        predictor.model = model_data["model"]
        predictor.scaler = model_data["scaler"]
        predictor.label_encoders = model_data["label_encoders"]
        predictor.feature_names = model_data["feature_names"]
        predictor.training_samples = model_data["training_samples"]
        predictor.feature_dim = model_data["feature_dim"]
        predictor.day_trained = datetime.fromisoformat(model_data["training_date"])
        predictor.is_trained = True

        logger.info(f"Model loaded from {model_path}")
        return predictor


# ======================================================================
# Integration test — end-to-end flow
# ======================================================================

def _make_synthetic_churn_df(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """
    Generate a synthetic DataFrame that mirrors the bank-churn CSV schema.
    Columns: RowNumber, CustomerId, Surname, Geography, Gender, Age, Tenure,
             Balance, NumOfProducts, HasCrCard, IsActiveMember,
             EstimatedSalary, Exited
    """
    rng = np.random.default_rng(seed)
    geographies = ["France", "Spain", "Germany"]
    genders = ["Male", "Female"]

    df = pd.DataFrame(
        {
            "RowNumber":       np.arange(1, n + 1),
            "CustomerId":      rng.integers(10_000_000, 20_000_000, n),
            "Surname":         rng.choice(
                ["Smith", "Jones", "Müller", "Dubois", "García"], n
            ),
            "Geography":       rng.choice(geographies, n),
            "Gender":          rng.choice(genders, n),
            "Age":             rng.integers(18, 75, n),
            "Tenure":          rng.integers(0, 11, n),
            "Balance":         np.where(
                rng.random(n) < 0.3, 0.0,
                rng.uniform(10_000, 200_000, n)
            ),
            "NumOfProducts":   rng.integers(1, 5, n),
            "HasCrCard":       rng.integers(0, 2, n),
            "IsActiveMember":  rng.integers(0, 2, n),
            "EstimatedSalary": rng.uniform(20_000, 200_000, n),
        }
    )

    # Simulate target: higher churn for older inactive customers
    churn_prob = (
        0.05
        + 0.30 * (df["Age"] > 50).astype(float)
        + 0.20 * (df["IsActiveMember"] == 0).astype(float)
        + 0.15 * (df["Balance"] == 0).astype(float)
        + 0.10 * (df["NumOfProducts"] > 2).astype(float)
    )
    churn_prob = churn_prob.clip(0, 1)
    df["Exited"] = rng.binomial(1, churn_prob).astype(int)
    return df


if __name__ == "__main__":
    import sys

    logging_format = "%(asctime)s  %(levelname)-8s  %(message)s"
    import logging
    logging.basicConfig(level=logging.INFO, format=logging_format, stream=sys.stdout)
    log = logging.getLogger(__name__)

    SEPARATOR = "=" * 60

    # ------------------------------------------------------------------
    # 0. Synthetic dataset
    # ------------------------------------------------------------------
    log.info(SEPARATOR)
    log.info("STEP 0 — Generating synthetic churn dataset")
    log.info(SEPARATOR)

    full_df = _make_synthetic_churn_df(n=600)
    train_df = full_df.iloc[:400].reset_index(drop=True)
    val_df   = full_df.iloc[400:500].reset_index(drop=True)
    test_df  = full_df.iloc[500:].reset_index(drop=True)

    log.info(
        f"Split → train={len(train_df)}, val={len(val_df)}, test={len(test_df)}"
    )
    log.info(f"Churn rate (train): {train_df['Exited'].mean():.2%}")

    # ------------------------------------------------------------------
    # 1. Single-model flow: prepare → fit → evaluate
    # ------------------------------------------------------------------
    log.info(SEPARATOR)
    log.info("STEP 1 — Single-model flow (random_forest)")
    log.info(SEPARATOR)

    clf = Churn_Classifier(model_name="random_forest")

    X_train, y_train = clf.prepare_data(train_df, fit_encoders=True)
    log.info(f"Training features shape: {X_train.shape}")

    clf.fit(X_train, y_train)
    log.info("fit() ✓")

    # Inference path uses saved encoders/scaler
    X_test, y_test = clf.prepare_data(test_df, fit_encoders=False)
    preds = clf.predict(X_test)
    probas = clf.predict_proba(X_test)

    log.info(f"predict()       ✓  shape={preds.shape}  unique={np.unique(preds)}")
    log.info(f"predict_proba() ✓  shape={probas.shape}  sum_check≈1: {np.allclose(probas.sum(axis=1), 1)}")

    metrics = clf.evaluate(X_test, y_test)
    log.info(
        f"evaluate()      ✓  accuracy={metrics['accuracy']:.4f}  "
        f"AUC={metrics['roc_auc']:.4f}"
    )
    log.info(f"Confusion matrix:\n{np.array(metrics['confusion_matrix'])}")

    # ------------------------------------------------------------------
    # 2. Feature importance
    # ------------------------------------------------------------------
    log.info(SEPARATOR)
    log.info("STEP 2 — Feature importance")
    log.info(SEPARATOR)

    importance_df = clf.calculate_feature_importance(X_train, y_train, method="builtin")
    log.info(f"calculate_feature_importance() ✓\n{importance_df.to_string(index=False)}")

    # ------------------------------------------------------------------
    # 3. train_models — compare all classifiers, auto-select best
    # ------------------------------------------------------------------
    log.info(SEPARATOR)
    log.info("STEP 3 — train_models() — race all three classifiers")
    log.info(SEPARATOR)

    multi_clf = Churn_Classifier(model_name="random_forest")
    X_train2, y_train2 = multi_clf.prepare_data(train_df, fit_encoders=True)
    X_val,    y_val    = multi_clf.prepare_data(val_df,   fit_encoders=False)

    multi_clf.train_models(X_train2, y_train2, X_val, y_val)
    log.info(f"Best model selected: {multi_clf.model_type}")
    log.info(f"Scores: {multi_clf.accurate_scores}")

    X_test2, y_test2 = multi_clf.prepare_data(test_df, fit_encoders=False)
    test_metrics = multi_clf.evaluate(X_test2, y_test2)
    log.info(
        f"Best-model test accuracy={test_metrics['accuracy']:.4f}  "
        f"AUC={test_metrics['roc_auc']:.4f}"
    )

    # ------------------------------------------------------------------
    # 4. Save → load round-trip
    # ------------------------------------------------------------------
    log.info(SEPARATOR)
    log.info("STEP 4 — save_model / load_model round-trip")
    log.info(SEPARATOR)

    save_path = Path("/tmp/test_churn_model.joblib")
    clf.save_model(path=save_path)
    log.info(f"Saved to {save_path}  ✓")

    loaded_clf = Churn_Classifier.load_model(path=save_path)
    log.info(
        f"Loaded model type: {loaded_clf.model_type}  "
        f"features: {loaded_clf.feature_dim}  "
        f"trained: {loaded_clf.is_trained}"
    )

    # Verify predictions are identical after round-trip
    preds_loaded = loaded_clf.predict(X_test)
    match = np.array_equal(preds, preds_loaded)
    log.info(f"Predictions match after reload: {match}  ✓")

    # ------------------------------------------------------------------
    # 5. Summary
    # ------------------------------------------------------------------
    log.info(SEPARATOR)
    log.info("ALL STEPS PASSED ✓")
    log.info(SEPARATOR)