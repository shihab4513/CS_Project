"""Measure how many target-ecosystem labels improve static transfer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .data import ECOSYSTEM_COLUMN, load_official_dataset
from .static_model import _make_classifier


def _stratified_take(features: np.ndarray, labels: np.ndarray, count: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Sample a target-label budget while retaining both classes when possible."""
    if count <= 0:
        return np.empty((0, features.shape[1])), np.empty(0, dtype=int)
    if count >= len(labels):
        return features, labels
    positives = np.flatnonzero(labels == 1)
    negatives = np.flatnonzero(labels == 0)
    rng = np.random.default_rng(seed)
    positive_count = max(1, round(count * len(positives) / len(labels))) if count > 1 else 1
    positive_count = min(positive_count, len(positives), count - 1) if count > 1 else 1
    negative_count = min(count - positive_count, len(negatives))
    indices = np.concatenate(
        [rng.choice(positives, positive_count, replace=False), rng.choice(negatives, negative_count, replace=False)]
    )
    rng.shuffle(indices)
    return features[indices], labels[indices]


def _fit_metrics(
    train_features: np.ndarray,
    train_labels: np.ndarray,
    test_features: np.ndarray,
    test_labels: np.ndarray,
    random_state: int,
    prefer_xgboost: bool,
) -> dict[str, float] | None:
    if len(np.unique(train_labels)) < 2:
        return None
    classifier, _ = _make_classifier(random_state, prefer_xgboost)
    model = Pipeline([("imputer", SimpleImputer(strategy="median")), ("classifier", classifier)])
    model.fit(train_features, train_labels)
    probabilities = model.predict_proba(test_features)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "precision": round(float(precision_score(test_labels, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(test_labels, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(test_labels, predictions, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(test_labels, probabilities)), 4),
        "pr_auc": round(float(average_precision_score(test_labels, probabilities)), 4),
    }


def evaluate_label_efficiency(
    dataset_path: str | Path,
    output_dir: str | Path,
    budgets: Iterable[int] = (0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 200, 400),
    n_seeds: int = 8,
    pool_fraction: float = 0.65,
    random_state: int = 42,
    prefer_xgboost: bool = True,
) -> dict[str, Any]:
    """Compare source-only transfer with source-plus-target labels.

    Each direction gets a fresh target pool/holdout split per seed. The
    holdout is never used for sampling or fitting.
    """
    if not 0.0 < pool_fraction < 1.0:
        raise ValueError("pool_fraction must be between 0 and 1")
    features, metadata, labels = load_official_dataset(dataset_path)
    features = features.reindex(sorted(features.columns), axis=1).to_numpy(dtype=float)
    labels_array = labels.to_numpy(dtype=int)
    ecosystems = set(metadata[ECOSYSTEM_COLUMN].dropna().unique())
    if ecosystems != {"NPM", "PyPI"}:
        raise ValueError(f"Expected NPM and PyPI records, received: {sorted(ecosystems)}")

    budget_values = sorted({int(value) for value in budgets if int(value) >= 0})
    rows: list[dict[str, Any]] = []
    for train_ecosystem, target_ecosystem in (("NPM", "PyPI"), ("PyPI", "NPM")):
        source_mask = metadata[ECOSYSTEM_COLUMN].eq(train_ecosystem).to_numpy()
        target_mask = metadata[ECOSYSTEM_COLUMN].eq(target_ecosystem).to_numpy()
        source_features, source_labels = features[source_mask], labels_array[source_mask]
        target_features, target_labels = features[target_mask], labels_array[target_mask]
        for seed_offset in range(n_seeds):
            pool_features, holdout_features, pool_labels, holdout_labels = train_test_split(
                target_features,
                target_labels,
                train_size=pool_fraction,
                stratify=target_labels,
                random_state=random_state + seed_offset,
            )
            for budget in budget_values:
                if budget > len(pool_labels):
                    continue
                added_features, added_labels = _stratified_take(
                    pool_features, pool_labels, budget, random_state + 1000 * seed_offset + budget
                )
                combined_features = np.vstack([source_features, added_features]) if budget else source_features
                combined_labels = np.concatenate([source_labels, added_labels]) if budget else source_labels
                combined_metrics = _fit_metrics(
                    combined_features,
                    combined_labels,
                    holdout_features,
                    holdout_labels,
                    random_state + seed_offset,
                    prefer_xgboost,
                )
                if combined_metrics:
                    rows.append(
                        {
                            "seed": seed_offset,
                            "train_ecosystem": train_ecosystem,
                            "target_ecosystem": target_ecosystem,
                            "budget": budget,
                            "condition": f"{train_ecosystem} + k {target_ecosystem}",
                            **combined_metrics,
                        }
                    )
                if budget:
                    target_metrics = _fit_metrics(
                        added_features,
                        added_labels,
                        holdout_features,
                        holdout_labels,
                        random_state + seed_offset,
                        prefer_xgboost,
                    )
                    if target_metrics:
                        rows.append(
                            {
                                "seed": seed_offset,
                                "train_ecosystem": train_ecosystem,
                                "target_ecosystem": target_ecosystem,
                                "budget": budget,
                                "condition": f"k {target_ecosystem} only",
                                **target_metrics,
                            }
                        )

    raw = pd.DataFrame(rows)
    if raw.empty:
        raise ValueError("No valid label-efficiency runs were produced")
    summary = (
        raw.groupby(["train_ecosystem", "target_ecosystem", "condition", "budget"])
        .agg(
            f1_mean=("f1", "mean"),
            f1_std=("f1", "std"),
            roc_auc_mean=("roc_auc", "mean"),
            pr_auc_mean=("pr_auc", "mean"),
            runs=("f1", "size"),
        )
        .reset_index()
        .fillna(0)
        .round(4)
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output / "label_efficiency_raw.csv", index=False)
    summary.to_csv(output / "label_efficiency_table.csv", index=False)
    result = {
        "dataset": str(Path(dataset_path).resolve()),
        "purpose": "Target-ecosystem label-efficiency evaluation; not a deployment estimate.",
        "random_state": random_state,
        "n_seeds": n_seeds,
        "pool_fraction": pool_fraction,
        "budgets": budget_values,
        "model_preference": "XGBoost when installed, otherwise Random Forest fallback" if prefer_xgboost else "Random Forest fallback",
        "summary": summary.to_dict(orient="records"),
    }
    (output / "label_efficiency_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result