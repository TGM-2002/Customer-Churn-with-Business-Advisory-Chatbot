"""
Logistic Regression — sklearn-style implementation
Supports: binary & multiclass (OvR), L2 regularization, gradient descent solver.
"""

import numpy as np


class LogisticRegression:
    """
    Logistic Regression classifier.

    Parameters
    ----------
    C : float, default=1.0
        Inverse regularization strength (larger C → less regularization).
    max_iter : int, default=100
        Maximum number of gradient-descent iterations.
    tol : float, default=1e-4
        Convergence tolerance on the loss change.
    learning_rate : float, default=0.1
        Step size for gradient descent.
    multi_class : str, default='ovr'
        Strategy for multi-class problems. Only 'ovr' (One-vs-Rest) supported.
    fit_intercept : bool, default=True
        Whether to add a bias/intercept term.
    random_state : int or None, default=None
        Seed for reproducibility.
    verbose : bool, default=False
        Print loss every 10 iterations.
    """

    def __init__(
        self,
        C=1.0,
        max_iter=100,
        tol=1e-4,
        learning_rate=0.1,
        multi_class="ovr",
        fit_intercept=True,
        random_state=None,
        verbose=False,
    ):
        self.C = C
        self.max_iter = max_iter
        self.tol = tol
        self.learning_rate = learning_rate
        self.multi_class = multi_class
        self.fit_intercept = fit_intercept
        self.random_state = random_state
        self.verbose = verbose

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sigmoid(z):
        """Numerically stable sigmoid."""
        return np.where(
            z >= 0,
            1 / (1 + np.exp(-z)),
            np.exp(z) / (1 + np.exp(z)),
        )

    def _add_intercept(self, X):
        """Prepend a column of ones for the bias term."""
        return np.hstack([np.ones((X.shape[0], 1)), X])

    def _loss_and_grad(self, X, y, w):
        """
        Binary cross-entropy loss + L2 gradient for one weight vector.

        Parameters
        ----------
        X : (n_samples, n_features)  — already includes bias column if needed
        y : (n_samples,)             — binary labels {0, 1}
        w : (n_features,)

        Returns
        -------
        loss : float
        grad : (n_features,)
        """
        n = X.shape[0]
        z = X @ w
        p = self._sigmoid(z)

        # Clip to avoid log(0)
        eps = 1e-12
        p = np.clip(p, eps, 1 - eps)

        loss = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

        # L2 regularization (skip bias term — index 0 when fit_intercept=True)
        reg_w = w.copy()
        if self.fit_intercept:
            reg_w[0] = 0.0
        loss += (1 / (2 * self.C)) * np.dot(reg_w, reg_w)

        grad = (X.T @ (p - y)) / n + reg_w / self.C
        return loss, grad

    def _fit_binary(self, X, y, rng):
        """Fit a single binary classifier; return weight vector."""
        n_features = X.shape[1]
        w = rng.randn(n_features) * 0.01
        prev_loss = np.inf

        for i in range(self.max_iter):
            loss, grad = self._loss_and_grad(X, y, w)
            w -= self.learning_rate * grad

            if self.verbose and i % 10 == 0:
                print(f"  iter {i:4d}  loss={loss:.6f}")

            if abs(prev_loss - loss) < self.tol:
                if self.verbose:
                    print(f"  Converged at iter {i}")
                break
            prev_loss = loss

        return w

    # ------------------------------------------------------------------
    # Public sklearn-compatible API
    # ------------------------------------------------------------------

    def fit(self, X, y):
        """
        Fit the model.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
        y : array-like of shape (n_samples,)

        Returns
        -------
        self
        """
        X = np.array(X, dtype=float)
        y = np.array(y)

        self.classes_ = np.unique(y)
        n_classes = len(self.classes_)
        rng = np.random.RandomState(self.random_state)

        if self.fit_intercept:
            X = self._add_intercept(X)

        if n_classes == 2:
            # Binary classification
            y_bin = (y == self.classes_[1]).astype(float)
            w = self._fit_binary(X, y_bin, rng)
            self.coef_ = w[1:].reshape(1, -1) if self.fit_intercept else w.reshape(1, -1)
            self.intercept_ = np.array([w[0]]) if self.fit_intercept else np.array([0.0])
        else:
            # One-vs-Rest multiclass
            coefs, intercepts = [], []
            for cls in self.classes_:
                if self.verbose:
                    print(f"Fitting class '{cls}' vs rest ...")
                y_bin = (y == cls).astype(float)
                w = self._fit_binary(X, y_bin, rng)
                if self.fit_intercept:
                    intercepts.append(w[0])
                    coefs.append(w[1:])
                else:
                    intercepts.append(0.0)
                    coefs.append(w)
            self.coef_ = np.array(coefs)           # (n_classes, n_features)
            self.intercept_ = np.array(intercepts) # (n_classes,)

        return self

    def decision_function(self, X):
        """
        Compute raw decision scores.

        Returns
        -------
        scores : ndarray of shape (n_samples,) for binary,
                 (n_samples, n_classes) for multiclass
        """
        X = np.array(X, dtype=float)
        scores = X @ self.coef_.T + self.intercept_  # (n_samples, n_classes)
        if len(self.classes_) == 2:
            return scores[:, 0]                       # (n_samples,)
        return scores

    def predict_proba(self, X):
        """
        Probability estimates.

        Returns
        -------
        proba : ndarray of shape (n_samples, n_classes)
        """
        scores = self.decision_function(X)
        if len(self.classes_) == 2:
            p1 = self._sigmoid(scores)
            return np.column_stack([1 - p1, p1])
        # OvR: apply sigmoid to each score, then normalize
        p = self._sigmoid(scores)
        p /= p.sum(axis=1, keepdims=True)
        return p

    def predict_log_proba(self, X):
        """Log of probability estimates."""
        return np.log(np.clip(self.predict_proba(X), 1e-12, None))

    def predict(self, X):
        """
        Predict class labels.

        Returns
        -------
        y_pred : ndarray of shape (n_samples,)
        """
        proba = self.predict_proba(X)
        indices = np.argmax(proba, axis=1)
        return self.classes_[indices]

    def score(self, X, y):
        """Return mean accuracy."""
        return np.mean(self.predict(X) == np.array(y))

    def get_params(self, deep=True):
        """sklearn-compatible get_params."""
        return {
            "C": self.C,
            "max_iter": self.max_iter,
            "tol": self.tol,
            "learning_rate": self.learning_rate,
            "multi_class": self.multi_class,
            "fit_intercept": self.fit_intercept,
            "random_state": self.random_state,
            "verbose": self.verbose,
        }

    def set_params(self, **params):
        """sklearn-compatible set_params."""
        for k, v in params.items():
            setattr(self, k, v)
        return self

