#!/usr/bin/env python3
"""Example jewel: flags world-writable files in a directory.

Contract:
- reads one JSON payload from stdin (protocol, round_id, config, policy)
- writes one JSON object to stdout: {"findings": [...]}

Read-only by construction: it opens nothing for writing.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path


def main() -> int:
    payload = json.load(sys.stdin)
    config = payload.get("config", {})
    directory = Path(config.get("directory", "~/Downloads")).expanduser()
    max_files = int(config.get("max_files", 500))

    findings = []
    checked = 0

    if directory.is_dir():
        for entry in sorted(directory.iterdir()):
            checked += 1
            if checked > max_files:
                break
            if not entry.is_file():
                continue
            try:
                mode = stat.S_IMODE(entry.stat().st_mode)
            except OSError:
                continue
            if mode & 0o002:
                findings.append(
                    {
                        "severity": "yellow",
                        "title": f"world-writable file: {entry.name}",
                        "detail": "Any local user can modify this file.",
                        "subject": {"type": "file", "value": str(entry)},
                        "evidence": {"mode": oct(mode)},
                    }
                )

    json.dump({"findings": findings, "checked": checked}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
