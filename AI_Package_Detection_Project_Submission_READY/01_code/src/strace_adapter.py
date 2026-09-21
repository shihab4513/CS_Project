"""Convert an existing Linux strace log into the project trace JSON format.

It parses a log already collected in an isolated VM. It does not launch strace
or start a package installation command.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


QUOTED = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')


def _quoted_values(line: str) -> list[str]:
    return [value.replace('\\"', '"') for value in QUOTED.findall(line)]


def convert_strace_log(log_path: str | Path, package_name: str, ecosystem: str) -> dict[str, Any]:
    """Extract process, file, and connection observations from a bounded log."""
    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"strace log not found: {path}")
    observed: dict[str, list[str]] = {
        "install_hooks": [],
        "processes": [],
        "commands": [],
        "files_read": [],
        "files_written": [],
        "network_connections": [],
    }
    with path.open("r", encoding="utf-8", errors="replace") as log_file:
        for index, line in enumerate(log_file):
            if index >= 200_000:
                break
            values = _quoted_values(line)
            if "execve(" in line and values:
                observed["processes"].append(values[0])
                observed["commands"].append(values[0])
            elif "connect(" in line:
                observed["network_connections"].append(values[0] if values else "network connection")
            elif ("openat(" in line or "open(" in line) and values:
                target = values[-1]
                if "O_WRONLY" in line or "O_RDWR" in line or "O_CREAT" in line:
                    observed["files_written"].append(target)
                else:
                    observed["files_read"].append(target)

    # Keep reports usable if an application created a noisy trace.
    for key in observed:
        observed[key] = list(dict.fromkeys(observed[key]))[:200]
    return {
        "package_name": package_name,
        "ecosystem": ecosystem,
        "collection_note": "Converted from an existing Linux strace log. This converter did not execute a package.",
        "observed": observed,
    }


def write_trace(log_path: str | Path, package_name: str, ecosystem: str, output_path: str | Path) -> dict[str, Any]:
    trace = convert_strace_log(log_path, package_name, ecosystem)
    Path(output_path).write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return trace
