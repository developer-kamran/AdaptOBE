"""XGBoost student-risk model with SHAP explanations (CLAUDE.md sections 5 & 9).

**Why the model is bootstrapped on synthetic data.** This deployment has no
historical labelled outcomes yet (no past cohort where we know who ultimately
struggled), so there is nothing to train a supervised model on out of the box.
Rather than ship a fake hard-coded rule dressed up as ML, this trains a *real*
XGBoost model on a synthetic sample drawn from a domain-sensible relationship
between the five features and an expected performance score. The result is a
genuine gradient-boosted model that produces genuine SHAP values; when real
outcome data accumulates, retrain on it by swapping the data source in
`_build_training_data` -- the public interface here does not change.

Imports of `xgboost`/`shap`/`numpy` are lazy (inside functions), so importing
this module -- and therefore booting the API or collecting tests -- never pays
their load cost. Training is CPU-bound and synchronous; callers offload it with
`asyncio.to_thread` via `apredict` (mirrors `app/ml/embeddings.py`).
"""

import asyncio
import threading
from dataclasses import dataclass

from app.services import risk_math

# Class label encoding shared by the classifier and the SHAP slice below.
# Kept explicit so predict_proba columns and SHAP class indices stay aligned.
_RISK_CLASSES = ["low", "medium", "high"]
_HIGH_CLASS_INDEX = _RISK_CLASSES.index("high")

# Relative weights of each feature in the synthetic performance score. These
# only shape the *training distribution*; the model learns its own splits. They
# encode the reasonable prior that a midterm and standing CLO attainment matter
# a little more than a single quiz average.
_FEATURE_WEIGHTS = {
    "attendance_percentage": 0.15,
    "quiz_average_percentage": 0.20,
    "assignment_average_percentage": 0.15,
    "midterm_score_percentage": 0.25,
    "current_avg_clo_attainment": 0.25,
}

_TRAINING_SAMPLES = 4000
_RANDOM_SEED = 42

_bundle = None
_bundle_lock = threading.Lock()


@dataclass
class FeatureContribution:
    feature: str
    value: float
    shap_value: float
    impact: str


@dataclass
class RiskPrediction:
    """Result for one student, mapping 1:1 onto the CLAUDE.md section 9 schema."""

    risk_level: str
    confidence: float
    predicted_score: float
    base_value: float
    feature_contributions: list[FeatureContribution]

    def to_shap_explanation(self) -> dict:
        """Serialise to the exact JSON shape CLAUDE.md section 9 mandates."""
        return {
            "base_value": round(self.base_value, 4),
            "predicted_risk": self.risk_level,
            "confidence": round(self.confidence, 4),
            "feature_contributions": [
                {
                    "feature": c.feature,
                    "value": round(c.value, 4),
                    "shap_value": round(c.shap_value, 4),
                    "impact": c.impact,
                }
                for c in self.feature_contributions
            ],
        }


def _build_training_data(np):
    """Synthesise (X, performance, risk_label) from a sensible latent ability.

    Each row draws a latent ability, then derives correlated features and a
    weighted performance score from it -- so the features genuinely predict the
    label, which is what makes the trained model (and its SHAP values) mean
    something. Replace this function with a real historical query to retrain on
    live outcomes without touching anything else.
    """
    rng = np.random.default_rng(_RANDOM_SEED)
    ability = rng.uniform(15.0, 100.0, size=_TRAINING_SAMPLES)

    columns = []
    for name in risk_math.FEATURE_NAMES:
        noise = rng.normal(0.0, 12.0, size=_TRAINING_SAMPLES)
        feature = np.clip(ability + noise, 0.0, 100.0)
        columns.append(feature)
    x = np.column_stack(columns)

    weights = np.array([_FEATURE_WEIGHTS[name] for name in risk_math.FEATURE_NAMES])
    performance = np.clip(
        x @ weights + rng.normal(0.0, 4.0, size=_TRAINING_SAMPLES), 0.0, 100.0
    )

    risk_label = np.array(
        [_RISK_CLASSES.index(risk_math.risk_level_from_score(p).value) for p in performance]
    )
    return x, performance, risk_label


def _train():
    import numpy as np
    from xgboost import XGBClassifier, XGBRegressor

    x, performance, risk_label = _build_training_data(np)

    regressor = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        random_state=_RANDOM_SEED,
        objective="reg:squarederror",
    )
    regressor.fit(x, performance)

    classifier = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        random_state=_RANDOM_SEED,
        objective="multi:softprob",
        num_class=len(_RISK_CLASSES),
    )
    classifier.fit(x, risk_label)

    import shap

    explainer = shap.TreeExplainer(classifier)
    return {"regressor": regressor, "classifier": classifier, "explainer": explainer}


def get_model():
    """Return the trained model bundle, training it once on first use."""
    global _bundle
    if _bundle is None:
        with _bundle_lock:
            if _bundle is None:
                _bundle = _train()
    return _bundle


def _high_class_shap(explainer, x_row, np):
    """Extract per-feature SHAP values toward the high-risk class, and the
    high-risk base value, tolerating SHAP's version-dependent output shapes."""
    raw = explainer.shap_values(x_row)
    expected = explainer.expected_value

    # Multiclass TreeExplainer returns either a list (one array per class) or a
    # single (n_samples, n_features, n_classes) array depending on version.
    if isinstance(raw, list):
        class_values = raw[_HIGH_CLASS_INDEX][0]
        base = expected[_HIGH_CLASS_INDEX]
    else:
        arr = np.asarray(raw)
        if arr.ndim == 3:
            class_values = arr[0, :, _HIGH_CLASS_INDEX]
        else:  # already reduced to a single class dimension
            class_values = arr[0]
        base = expected[_HIGH_CLASS_INDEX] if np.ndim(expected) else expected

    return [float(v) for v in class_values], float(base)


def predict(feature_rows: list[list[float]]) -> list[RiskPrediction]:
    """Predict risk for a batch of pre-assembled feature rows.

    Each row must already be the ordered, clamped 5-feature vector produced by
    `risk_math.assemble_feature_row`.
    """
    if not feature_rows:
        return []

    import numpy as np

    bundle = get_model()
    x = np.asarray(feature_rows, dtype=float)

    scores = bundle["regressor"].predict(x)
    probabilities = bundle["classifier"].predict_proba(x)

    predictions: list[RiskPrediction] = []
    for i, row in enumerate(feature_rows):
        proba = probabilities[i]
        class_index = int(np.argmax(proba))
        risk_level = _RISK_CLASSES[class_index]
        confidence = float(proba[class_index])
        predicted_score = float(np.clip(scores[i], 0.0, 100.0))

        shap_values, base_value = _high_class_shap(
            bundle["explainer"], x[i : i + 1], np
        )
        contributions = [
            FeatureContribution(
                feature=name,
                value=row[j],
                shap_value=shap_values[j],
                impact=risk_math.impact_label(shap_values[j]),
            )
            for j, name in enumerate(risk_math.FEATURE_NAMES)
        ]
        # Most influential features first, matching how the section 9 example
        # is ordered (largest-magnitude contribution at the top).
        contributions.sort(key=lambda c: abs(c.shap_value), reverse=True)

        predictions.append(
            RiskPrediction(
                risk_level=risk_level,
                confidence=confidence,
                predicted_score=predicted_score,
                base_value=base_value,
                feature_contributions=contributions,
            )
        )
    return predictions


async def apredict(feature_rows: list[list[float]]) -> list[RiskPrediction]:
    """Async wrapper offloading the CPU-bound predict off the event loop."""
    return await asyncio.to_thread(predict, feature_rows)
