"""Cross-ecosystem static evaluation for npm and PyPI.

This experiment trains on one ecosystem and evaluates on the other. It exposes
transfer failure rather than hiding it behind a single combined score.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline

from .data import ECOSYSTEM_COLUMN, load_official_dataset
from .static_model import _make_classifier


def _scores(labels: pd.Series, probabilities: np.ndarray) -> dict[str, float | int | None]:
    predictions = (probabilities >= 0.5).astype(int)
    result: dict[str, float | int | None] = {
        "samples": int(len(labels)),
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "precision": round(float(precision_score(labels, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, predictions, zero_division=0)), 4),
    }
    result["roc_auc"] = round(float(roc_auc_score(labels, probabilities)), 4) if labels.nunique() == 2 else None
    return result


def evaluate_leave_one_ecosystem_out(
    dataset_path: str | Path, output_path: str | Path, random_state: int = 42, prefer_xgboost: bool = True
) -> dict[str, Any]:
    """Train NPM-to-PyPI and PyPI-to-NPM models using a shared static feature space."""
    features, metadata, labels = load_official_dataset(dataset_path)
    ecosystems = sorted(metadata[ECOSYSTEM_COLUMN].dropna().unique())
    if set(ecosystems) != {"NPM", "PyPI"}:
        raise ValueError(f"Expected NPM and PyPI records, received: {ecosystems}")

    experiments: dict[str, Any] = {}
    for train_ecosystem, test_ecosystem in [("NPM", "PyPI"), ("PyPI", "NPM")]:
        train_mask = metadata[ECOSYSTEM_COLUMN].eq(train_ecosystem)
        test_mask = metadata[ECOSYSTEM_COLUMN].eq(test_ecosystem)
        classifier, model_name = _make_classifier(random_state, prefer_xgboost)
        model = Pipeline([("imputer", SimpleImputer(strategy="median")), ("classifier", classifier)])
        model.fit(features.loc[train_mask], labels.loc[train_mask])
        classes = model.named_steps["classifier"].classes_
        positive_index = int(np.where(classes == 1)[0][0])
        probabilities = model.predict_proba(features.loc[test_mask])[:, positive_index]
        experiments[f"{train_ecosystem}_to_{test_ecosystem}"] = {
            "train_ecosystem": train_ecosystem,
            "test_ecosystem": test_ecosystem,
            "model_name": model_name,
            "metrics": _scores(labels.loc[test_mask], probabilities),
        }

    result = {
        "dataset": str(Path(dataset_path).resolve()),
        "purpose": "Leave-one-ecosystem-out static transfer evaluation, not a deployment estimate.",
        "random_state": random_state,
        "experiments": experiments,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
