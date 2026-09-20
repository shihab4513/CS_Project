"""Read-only static inspection for an unpacked npm or PyPI package.

This scanner never imports Python modules, invokes Node, runs setup scripts, or
installs dependencies. It is intended to produce explainable evidence for a
human reviewer before a package enters an isolated dynamic-analysis VM.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


TEXT_SUFFIXES = {".js", ".cjs", ".mjs", ".ts", ".py", ".json", ".toml", ".yaml", ".yml", ".txt"}
MAX_FILES = 5_000
MAX_FILE_BYTES = 2_000_000
NON_PRODUCTION_PATH_PARTS = {"test", "tests", "doc", "docs", "examples", "example", ".github", "benchmarks"}
NON_PRODUCTION_FILENAMES = {".pre-commit-config.yaml", ".readthedocs.yaml"}

RULES: dict[str, tuple[re.Pattern[str], float, str]] = {
    "install_hook": (
        re.compile(r'"(?:preinstall|install|postinstall|prepare)"\s*:', re.IGNORECASE),
        0.12,
        "Package install lifecycle hook declared.",
    ),
    "shell_execution": (
        re.compile(r"(?:child_process|subprocess\.|os\.system|shell=True|/bin/sh|powershell)", re.IGNORECASE),
        0.20,
        "Shell or child-process execution API found.",
    ),
    "network_access": (
        re.compile(r"(?:https?://|requests\.|urllib\.|fetch\s*\(|axios\.|http\.request|net\.connect)", re.IGNORECASE),
        0.12,
        "Network access indicator found.",
    ),
    "sensitive_access": (
        re.compile(r"(?:\.ssh|id_rsa|\.npmrc|NPM_TOKEN|AWS_SECRET|\.env|credential)", re.IGNORECASE),
        0.28,
        "Potential access to a credential or sensitive file found.",
    ),
    "obfuscation": (
        re.compile(r"(?:base64\.b64decode|Buffer\.from\(.+base64|fromCharCode|eval\s*\(|powershell\s+-enc)", re.IGNORECASE),
        0.18,
        "Potential obfuscation or dynamic code-evaluation indicator found.",
    ),
    "download_execute": (
        re.compile(r"(?:curl.+\|\s*(?:bash|sh)|wget.+&&|urlretrieve\(.+?/tmp)", re.IGNORECASE),
        0.30,
        "Remote download-and-execute pattern found.",
    ),
}


def _read_text(path: Path) -> str:
    """Read bounded text, replacing invalid bytes instead of executing anything."""
    return path.read_bytes()[:MAX_FILE_BYTES].decode("utf-8", errors="replace")


def scan_source_directory(directory: str | Path, include_nonproduction: bool = False) -> dict[str, Any]:
    """Inspect source files and return an explainable, non-ML risk summary."""
    root = Path(directory).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Source directory not found: {root}")

    files = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    if len(files) > MAX_FILES:
        files = files[:MAX_FILES]

    matches: Counter[str] = Counter()
    evidence: dict[str, list[str]] = {key: [] for key in RULES}
    text_files = 0
    signal_files_scanned = 0
    skipped_nonproduction_files = 0
    total_lines = 0
    total_bytes = 0
    for path in files:
        total_bytes += path.stat().st_size
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text_files += 1
        text = _read_text(path)
        total_lines += text.count("\n") + (1 if text else 0)
        relative = str(path.relative_to(root))
        is_nonproduction = (
            path.name.lower() in NON_PRODUCTION_FILENAMES
            or any(part.lower() in NON_PRODUCTION_PATH_PARTS for part in path.relative_to(root).parts)
        )
        if is_nonproduction and not include_nonproduction:
            skipped_nonproduction_files += 1
            continue
        signal_files_scanned += 1
        for name, (pattern, _, _) in RULES.items():
            count = len(pattern.findall(text))
            if count:
                matches[name] += count
                if len(evidence[name]) < 3:
                    evidence[name].append(relative)

    # Network and credential-related strings are common in legitimate clients
    # (for example, an HTTP library). Treat them as contextual evidence rather
    # than adding their full independent weights. Execution, obfuscation, and
    # download-and-execute signals remain stronger indicators.
    risk_score = sum(
        weight
        for name, (_, weight, _) in RULES.items()
        if name not in {"network_access", "sensitive_access"} and matches[name]
    )
    if matches["network_access"] and matches["sensitive_access"]:
        risk_score += 0.20
    elif matches["network_access"]:
        risk_score += 0.04
    elif matches["sensitive_access"]:
        risk_score += 0.10
    risk_score = min(1.0, risk_score)
    findings = [
        {
            "signal": name,
            "match_count": int(matches[name]),
            "files": evidence[name],
            "explanation": explanation,
        }
        for name, (_, _, explanation) in RULES.items()
        if matches[name]
    ]
    if not findings:
        findings.append(
            {
                "signal": "no_configured_signal",
                "match_count": 0,
                "files": [],
                "explanation": "No configured high-risk static indicator was found.",
            }
        )
    return {
        "scan_scope": "Read-only source inspection. No code, package script, or dependency was executed.",
        "source_directory": str(root),
        "files_seen": len(files),
        "text_files_scanned": text_files,
        "files_checked_for_risk_signals": signal_files_scanned,
        "nonproduction_files_excluded_from_risk_scoring": skipped_nonproduction_files,
        "total_lines_scanned": total_lines,
        "total_bytes_seen": total_bytes,
        "static_source_risk_score": round(float(risk_score), 4),
        "findings": findings,
        "limitation": (
            "This lightweight scanner is not the paper's 140-feature extractor and its score must not be "
            "compared directly with the trained paper-dataset model probability."
        ),
    }


def write_source_scan(
    directory: str | Path, output_path: str | Path, include_nonproduction: bool = False
) -> dict[str, Any]:
    result = scan_source_directory(directory, include_nonproduction=include_nonproduction)
    Path(output_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
