"""Offline interpretation of sandbox telemetry.

The functions in this file only inspect a JSON file produced elsewhere.  They
do not install a package, launch a shell command, or contact a network host.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


# Match credential-like path components, not arbitrary substrings.  For
# example, Python's standard ``tokenize.py`` is not a credential token.
SENSITIVE_PATH = re.compile(
    r"(?:^|[\\/])(?:\.ssh|id_rsa(?:\.pub)?|\.env(?:\.[^\\/]+)?|\.npmrc|"
    r"credentials?(?:\.[^\\/]+)?|passwords?(?:\.[^\\/]+)?|passwd|shadow)(?:$|[\\/])",
    re.IGNORECASE,
)
SUSPICIOUS_COMMAND = re.compile(r"(?:curl|wget|powershell|base64|nc\s|/bin/sh|cmd\.exe)", re.IGNORECASE)


def load_trace(path: str | Path) -> dict[str, Any]:
    trace_path = Path(path)
    if not trace_path.is_file():
        raise FileNotFoundError(f"Trace file not found: {trace_path}")
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("The trace must be one JSON object.")
    return trace


def analyse_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Convert imported sandbox observations into transparent dynamic evidence."""
    events = trace.get("observed", trace)
    if not isinstance(events, dict):
        raise ValueError("Trace observations must be a JSON object.")

    install_hooks = [str(x) for x in events.get("install_hooks", [])]
    commands = [str(x) for x in events.get("commands", [])]
    processes = [str(x) for x in events.get("processes", [])]
    files_read = [str(x) for x in events.get("files_read", [])]
    files_written = [str(x) for x in events.get("files_written", [])]
    connections = [str(x) for x in events.get("network_connections", [])]
    sensitive = [path for path in files_read + files_written if SENSITIVE_PATH.search(path)]
    suspicious_commands = [command for command in commands + processes if SUSPICIOUS_COMMAND.search(command)]

    score = min(
        1.0,
        0.12 * bool(install_hooks)
        + 0.20 * bool(connections)
        + 0.30 * bool(sensitive)
        + 0.25 * bool(suspicious_commands)
        + 0.05 * min(len(processes), 2)
        + 0.03 * min(len(files_written), 2),
    )
    evidence: list[str] = []
    if install_hooks:
        evidence.append(f"Install hook observed: {', '.join(install_hooks[:3])}.")
    if connections:
        evidence.append(f"Outbound connections observed: {len(connections)}.")
    if sensitive:
        evidence.append(f"Sensitive paths accessed: {', '.join(sensitive[:3])}.")
    if suspicious_commands:
        evidence.append(f"High-risk command/process strings observed: {', '.join(suspicious_commands[:2])}.")
    if not evidence:
        evidence.append("No configured high-risk behavior was recorded in this imported trace.")

    return {
        "dynamic_risk_score": round(float(score), 4),
        "counts": {
            "install_hooks": len(install_hooks),
            "processes": len(processes),
            "network_connections": len(connections),
            "sensitive_path_accesses": len(sensitive),
            "suspicious_commands": len(suspicious_commands),
        },
        "evidence": evidence,
        "source": "Imported sandbox telemetry; no package execution occurred in this program.",
    }
