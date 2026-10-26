"""Bounded model catalogue for classification and regression."""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC, SVR
from xgboost import XGBClassifier, XGBRegressor

from shared.features import build_feature_pipeline


class EncodedClassifier(ClassifierMixin, BaseEstimator):
    """XGBoost requires integer labels; expose the original classes to all callers."""
    def __init__(self, estimator):
        self.estimator = estimator

    def fit(self, X, y):
        self.encoder_ = LabelEncoder().fit(y)
        self.classes_ = self.encoder_.classes_
        self.estimator_ = clone(self.estimator).fit(X, self.encoder_.transform(y))
        self.n_features_in_ = self.estimator_.n_features_in_
        return self

    def predict(self, X):
        return self.encoder_.inverse_transform(np.asarray(self.estimator_.predict(X), dtype=int))

    def predict_proba(self, X):
        return self.estimator_.predict_proba(X)


def candidates(plan, seed, attempt):
    classification = plan.task_type == "classification"
    weight = "balanced" if plan.balance_classes else None
    if classification:
        choices = {
            "baseline": (DummyClassifier(strategy="most_frequent"), {}),
            "linear": (LogisticRegression(max_iter=1500, class_weight=weight, random_state=seed), {"model__C": [0.1, 1.0] if attempt == 0 else [0.01, 10.0]}),
            "random_forest": (RandomForestClassifier(n_estimators=100, n_jobs=1, class_weight=weight, random_state=seed), {"model__max_depth": [6, None] if attempt == 0 else [3, 12], "model__min_samples_leaf": [1] if attempt == 0 else [3]}),
            "svm": (SVC(probability=True, class_weight=weight, random_state=seed), {"model__C": [0.5, 2.0] if attempt == 0 else [0.1, 10.0]}),
            "gradient_boosting": (GradientBoostingClassifier(n_estimators=100, random_state=seed), {"model__max_depth": [2, 3] if attempt == 0 else [1, 4]}),
            "xgboost": (EncodedClassifier(XGBClassifier(n_estimators=100, n_jobs=1, tree_method="hist", random_state=seed)), {"model__estimator__max_depth": [3, 6] if attempt == 0 else [2, 4]}),
        }
    else:
        choices = {
            "baseline": (DummyRegressor(strategy="mean"), {}),
            "linear": (Ridge(), {"model__alpha": [0.1, 1.0] if attempt == 0 else [10.0, 100.0]}),
            "random_forest": (RandomForestRegressor(n_estimators=100, n_jobs=1, random_state=seed), {"model__max_depth": [6, None] if attempt == 0 else [3, 12], "model__min_samples_leaf": [1] if attempt == 0 else [3]}),
            "svm": (SVR(), {"model__C": [1.0, 10.0] if attempt == 0 else [0.1, 100.0]}),
            "gradient_boosting": (GradientBoostingRegressor(n_estimators=100, random_state=seed), {"model__max_depth": [2, 3] if attempt == 0 else [1, 4]}),
            "xgboost": (XGBRegressor(n_estimators=100, n_jobs=1, tree_method="hist", random_state=seed), {"model__max_depth": [3, 6] if attempt == 0 else [2, 4]}),
        }
    for name in ["baseline", *plan.models]:
        model, grid = choices[name]
        if attempt > 1:
            # A second retry changes regularization rather than repeating round one.
            if name == "linear":
                grid = {"model__C": [0.03, 3.0]} if classification else {"model__alpha": [0.01, 30.0]}
            elif name == "svm":
                grid = {"model__C": [0.03, 30.0]}
            elif name == "random_forest":
                grid = {"model__max_depth": [4, 10], "model__min_samples_leaf": [5]}
            elif name == "gradient_boosting":
                grid = {"model__learning_rate": [0.03, 0.2]}
            elif name == "xgboost":
                grid = {("model__estimator__learning_rate" if classification else "model__learning_rate"): [0.03, 0.2]}
        yield name, Pipeline([("features", build_feature_pipeline(plan)), ("model", model)]), grid
