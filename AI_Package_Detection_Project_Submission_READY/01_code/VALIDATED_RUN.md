# Verified Local Run

The project was tested on 16 September 2026 using the released
`Labelled_Dataset.csv` file, the deterministic split seed `42`, and the
scikit-learn Random Forest fallback. The fallback was used because XGBoost was
not installed in the local test environment. Google Colab will use XGBoost after
`pip install -r requirements.txt`.

## Data and Configuration

| Item | Value |
| --- | --- |
| Dataset | Released `Labelled_Dataset.csv` from the base paper artifact |
| Records | 1,940 |
| Static input features | 140 |
| Train/test split | 1,552 / 388, stratified on `Malicious` |
| Seed | 42 |
| Dynamic trace | `examples/safe_trace_example.json` (synthetic importer test only) |

## Static-Test Results

| Scope | Accuracy | Precision | Recall | F1 | ROC-AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overall | 0.9639 | 0.8788 | 0.7436 | 0.8056 | 0.9569 |
| NPM | 0.9730 | 0.9231 | 0.7500 | 0.8276 | 0.9760 |
| PyPI | 0.9557 | 0.8500 | 0.7391 | 0.7907 | 0.9459 |

These are **this project's baseline results**, not a claim that they exactly
reproduce the numerical results in the paper. Exact replication can differ due
to model configuration, package-level split protocol, preprocessing, and the
runtime/library versions. The program writes the corresponding JSON and CSV
result files on every run.

The test also used the provided synthetic trace: it generated an imported-trace
dynamic risk score of 0.2000 and a fused risk score of 0.0893 for the benign
`URIjs-1.16.1` dataset record. No package was executed during this verification.
