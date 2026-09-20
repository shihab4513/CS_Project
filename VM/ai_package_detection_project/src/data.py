"""Loading and validating the released static-feature dataset.

This module processes already extracted features.  It never downloads, installs,
or executes an npm or PyPI package.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


LABEL_COLUMN = "Malicious"
ECOSYSTEM_COLUMN = "Package Repository"
PACKAGE_COLUMN = "Package Name"


def load_official_dataset(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Return numeric features, package metadata, and binary labels.

    The expected CSV is ``Labelled_Dataset.csv`` released with the artifact for
    Ladisa et al.'s cross-language package-detection study.
    """
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    frame = pd.read_csv(csv_path)
    missing = {LABEL_COLUMN, ECOSYSTEM_COLUMN, PACKAGE_COLUMN}.difference(frame.columns)
    if missing:
        raise ValueError(f"The dataset is missing expected columns: {sorted(missing)}")

    labels = pd.to_numeric(frame[LABEL_COLUMN], errors="raise").astype(int)
    if not set(labels.unique()).issubset({0, 1}):
        raise ValueError("The Malicious column must contain only 0 (benign) and 1 (malicious).")

    metadata = frame[[ECOSYSTEM_COLUMN, PACKAGE_COLUMN]].copy()
    features = frame.drop(columns=[LABEL_COLUMN, ECOSYSTEM_COLUMN, PACKAGE_COLUMN]).apply(
        pd.to_numeric, errors="coerce"
    )
    # A missing static measurement is not evidence of benignness.  Median
    # imputation is performed inside the fitted model, avoiding test-set leakage.
    return features, metadata, labels
