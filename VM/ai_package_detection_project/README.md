# AI-Based Malicious Open-Source Package Detection

This is the implementation for the proposed project, **AI-Based Detection of
Malicious Open-Source Packages**. It starts from the released static feature
dataset used by the base paper, *Cross-Language Detection of Malicious Packages
in npm and PyPI*, then adds two project components:

1. an offline importer that turns separately collected sandbox telemetry into
   interpretable dynamic-behavior evidence; and
2. three evidence-fusion agents: Static Analysis, Behavior Analysis, and
   Decision. A bounded LLM review prompt is written to a text file, ready to use
   later with an approved LLM API or local model.

## Safety and scientific scope

This program **does not download, install, or execute npm/PyPI packages**. The
dynamic module reads a JSON trace produced by a separate isolated sandbox. The
provided trace is synthetic and exists only to test the importer. This lets the
project run safely in Google Colab or on a normal PC while keeping actual dynamic
execution in an offline VM or Windows Sandbox.

The static experiment uses the release CSV at:

`../RENAME_TO_YOUR_GROUP_ID/02_dataset/Labelled_Dataset.csv`

It has 1,940 package records, 140 static features after excluding the three
label/metadata columns, and the columns `Malicious`,
`Package Repository`, and `Package Name`. It is the published artifact dataset,
not generated data. The model split, seed, and every metric are saved so the
results are reproducible. Our train/test split and model hyperparameters are a
project baseline; they are not claimed to be the paper's exact reported numbers.

## Install

Use Python 3.10 to 3.12 where possible. In Google Colab, run the `pip` command
below before the experiment. XGBoost is used when installed; otherwise the code
records a Random Forest fallback in `static_metrics.json`.

```powershell
cd ai_package_detection_project
python -m pip install -r requirements.txt
```

## Run the complete prototype

From this folder, run:

```powershell
python run_project.py `
  --dataset "..\RENAME_TO_YOUR_GROUP_ID\02_dataset\Labelled_Dataset.csv" `
  --package-name "URIjs-1.16.1" `
  --trace examples\safe_trace_example.json `
  --output outputs
```

To run only the paper-dataset static baseline, omit `--trace`. To explicitly use
the tested sklearn fallback instead of XGBoost, add `--no-xgboost`.

## Result files

After a run, `outputs/` contains:

- `static/static_metrics.json`: dataset provenance, model name, split, and
  overall/per-ecosystem precision, recall, F1, accuracy, and ROC-AUC.
- `static/static_confusion_matrix.csv`: test confusion matrix.
- `static/static_feature_importance.csv`: static feature ranking.
- `static/static_model.joblib`: trained model artifact.
- `package_decision_report.json`: fused static/dynamic finding for one record.
- `llm_review_prompt.txt`: evidence-only prompt for a later LLM review agent.

## Next project modules

### 1. Scan an unpacked package without executing it

Use this only on source files that have already been downloaded and unpacked.
The scanner never installs the package or imports its code.

```powershell
python scan_source.py --source-dir "C:\path\to\unpacked-package" --output outputs\source_scan.json
```

The resulting evidence is useful for the static-analysis section of the final
project, but it is a separate lightweight scanner. Do not feed its score into
the paper-dataset XGBoost model because the feature sets differ.

### 2. Import a real trace collected in an isolated Linux VM

After you manually collect an `strace` log in a disposable Linux Mint VM, convert
it without running anything again:

```powershell
python convert_strace.py --log "C:\path\to\trace.log" --package-name "example-package" --ecosystem NPM --output outputs\imported_trace.json
```

Then pass `outputs\imported_trace.json` to `run_project.py` through `--trace`.
The converter is intentionally read-only. Do not collect traces on your main PC,
in Google Colab, or while logged in to personal accounts.

### 3. Fuse source evidence and VM trace for a new package

For a package not present in `Labelled_Dataset.csv`, combine the output of the
two modules above. This uses a transparent source-scanner score, not the trained
paper-dataset model probability.

```powershell
python fuse_source_trace.py --source-scan outputs\source_scan.json --trace outputs\imported_trace.json --package-name "example-package" --ecosystem NPM --output outputs
```

This produces `new_package_evidence_report.json` and an LLM-ready review prompt.

## Sandbox-trace format

The dynamic module accepts a JSON object. It only reads the listed observations:

```json
{
  "package_name": "observed-package",
  "ecosystem": "PyPI",
  "observed": {
    "install_hooks": ["setup.py"],
    "processes": ["python setup.py"],
    "commands": ["python setup.py"],
    "files_read": ["/sandbox/package/setup.py"],
    "files_written": ["/sandbox/tmp/build.log"],
    "network_connections": []
  }
}
```

For genuine dynamic analysis, collect this telemetry only in an isolated,
throwaway VM with no personal credentials and restricted network access. Do not
run unknown packages on the host computer, in Google Colab, or against a real
account.

## Google Colab use

Upload this entire `ai_package_detection_project` folder as a zip, upload
`Labelled_Dataset.csv`, then run inside Colab:

```python
!unzip -q ai_package_detection_project.zip -d /content
%cd /content/ai_package_detection_project
!pip -q install -r requirements.txt
!python run_project.py --dataset /content/Labelled_Dataset.csv --package-name "URIjs-1.16.1" --trace examples/safe_trace_example.json --output outputs
```

Download the `outputs` folder after completion. Colab is suitable for the static
baseline and imported-trace analysis, but not for executing untrusted packages.
