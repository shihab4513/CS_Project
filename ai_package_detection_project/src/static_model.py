"""Static-model training for the released cross-language dataset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .data import ECOSYSTEM_COLUMN, load_official_dataset


def _make_classifier(random_state: int, prefer_xgboost: bool) -> tuple[Any, str]:
    """Use XGBoost when installed; retain a reproducible sklearn fallback."""
    if prefer_xgboost:
        try:
            from xgboost import XGBClassifier

            return (
                XGBClassifier(
                    n_estimators=250,
                    max_depth=5,
                    learning_rate=0.05,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    random_state=random_state,
                    n_jobs=2,
                ),
                "XGBoost",
            )
        except ImportError:
            pass

    return (
        RandomForestClassifier(
            n_estimators=350,
            class_weight="balanced_subsample",
            random_state=random_state,
            n_jobs=-1,
            min_samples_leaf=2,
        ),
        "Random Forest fallback (install xgboost for XGBoost)",
    )


def _probabilities(model: Pipeline, features: pd.DataFrame) -> np.ndarray:
    """Return probability of the malicious class even if class order changes."""
    classes = model.named_steps["classifier"].classes_
    class_index = int(np.where(classes == 1)[0][0])
    return model.predict_proba(features)[:, class_index]


def _metric_row(labels: pd.Series | np.ndarray, probabilities: np.ndarray) -> dict[str, float | int]:
    labels_array = np.asarray(labels, dtype=int)
    predictions = (probabilities >= 0.5).astype(int)
    row: dict[str, float | int] = {
        "samples": int(len(labels_array)),
        "accuracy": round(float(accuracy_score(labels_array, predictions)), 4),
        "precision": round(float(precision_score(labels_array, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(labels_array, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(labels_array, predictions, zero_division=0)), 4),
    }
    if len(np.unique(labels_array)) == 2:
        row["roc_auc"] = round(float(roc_auc_score(labels_array, probabilities)), 4)
    else:
        row["roc_auc"] = None
    return row


def train_static_model(
    dataset_path: str | Path,
    output_dir: str | Path,
    random_state: int = 42,
    prefer_xgboost: bool = True,
) -> dict[str, Any]:
    """Train, evaluate, and persist the static detector and its research outputs."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    features, metadata, labels = load_official_dataset(dataset_path)
    indices = np.arange(len(features))
    train_indices, test_indices = train_test_split(
        indices,
        test_size=0.20,
        stratify=labels,
        random_state=random_state,
    )
    classifier, model_name = _make_classifier(random_state, prefer_xgboost)
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", classifier),
        ]
    )
    model.fit(features.iloc[train_indices], labels.iloc[train_indices])

    test_probabilities = _probabilities(model, features.iloc[test_indices])
    test_labels = labels.iloc[test_indices].reset_index(drop=True)
    test_metadata = metadata.iloc[test_indices].reset_index(drop=True)
    metrics: dict[str, Any] = {"overall": _metric_row(test_labels, test_probabilities), "by_ecosystem": {}}
    for ecosystem in sorted(test_metadata[ECOSYSTEM_COLUMN].dropna().unique()):
        mask = test_metadata[ECOSYSTEM_COLUMN].eq(ecosystem).to_numpy()
        metrics["by_ecosystem"][str(ecosystem)] = _metric_row(test_labels[mask], test_probabilities[mask])

    predictions = (test_probabilities >= 0.5).astype(int)
    matrix = confusion_matrix(test_labels, predictions, labels=[0, 1])
    pd.DataFrame(
        matrix,
        index=["actual_benign", "actual_malicious"],
        columns=["predicted_benign", "predicted_malicious"],
    ).to_csv(output / "static_confusion_matrix.csv")

    fitted_classifier = model.named_steps["classifier"]
    importance = getattr(fitted_classifier, "feature_importances_", None)
    if importance is not None:
        pd.DataFrame({"feature": features.columns, "importance": importance}).sort_values(
            "importance", ascending=False
        ).to_csv(output / "static_feature_importance.csv", index=False)

    model_file = output / "static_model.joblib"
    joblib.dump({"model": model, "feature_columns": list(features.columns), "model_name": model_name}, model_file)
    summary = {
        "dataset": str(Path(dataset_path).resolve()),
        "dataset_rows": int(len(features)),
        "feature_count": int(features.shape[1]),
        "train_rows": int(len(train_indices)),
        "test_rows": int(len(test_indices)),
        "random_state": random_state,
        "model_name": model_name,
        "threshold": 0.5,
        "metrics": metrics,
        "model_file": str(model_file.resolve()),
    }
    (output / "static_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def predict_known_package(
    model_file: str | Path, dataset_path: str | Path, package_name: str
) -> dict[str, Any]:
    """Predict a named record already present in the released CSV."""
    artifact = joblib.load(model_file)
    features, metadata, labels = load_official_dataset(dataset_path)
    matches = metadata.index[metadata["Package Name"].astype(str).str.lower().eq(package_name.lower())].tolist()
    if not matches:
        raise ValueError(f"Package not present in this dataset: {package_name}")
    row = matches[0]
    model: Pipeline = artifact["model"]
    probability = float(_probabilities(model, features.iloc[[row]])[0])
    return {
        "package_name": str(metadata.iloc[row]["Package Name"]),
        "ecosystem": str(metadata.iloc[row]["Package Repository"]),
        "static_malicious_probability": round(probability, 4),
        "static_label": "malicious" if probability >= 0.5 else "benign",
        "reference_label": int(labels.iloc[row]),
        "model_name": artifact["model_name"],
    }
