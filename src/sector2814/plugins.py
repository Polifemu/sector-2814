"""Jewels: plugin discovery and the JSON-over-stdio protocol.

A jewel is a directory with a ``plugin.toml`` manifest and an executable
entry point. The crown runs the entry point, writes one JSON payload to
stdin, and reads one JSON object from stdout. Any language works.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class Plugin:
    name: str
    version: str
    kind: str
    entry: Path
    root: Path
    actions: tuple[str, ...] = ("read-only",)
    description: str = ""
    schedule: str = "manual"
    config: dict[str, Any] = field(default_factory=dict)
    timeout: int = 60


def discover(plugin_dirs: Iterable[Path]) -> list[Plugin]:
    found: dict[str, Plugin] = {}
    for base in plugin_dirs:
        base = Path(base)
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            manifest = child / "plugin.toml"
            if not child.is_dir() or not manifest.is_file():
                continue
            try:
                plugin = _load_manifest(manifest, child)
            except ValueError:
                continue
            found.setdefault(plugin.name, plugin)
    return sorted(found.values(), key=lambda p: p.name)


def _load_manifest(manifest: Path, root: Path) -> Plugin:
    with manifest.open("rb") as fh:
        data = tomllib.load(fh)

    section = data.get("plugin", data)
    safety = data.get("safety", {})

    name = section.get("name")
    kind = section.get("kind")
    entry = section.get("entry")
    if not name or not kind or not entry:
        raise ValueError(f"{manifest}: 'name', 'kind' and 'entry' are required")

    entry_path = (root / entry).resolve()
    root_resolved = root.resolve()
    if root_resolved != entry_path and root_resolved not in entry_path.parents:
        raise ValueError(f"{manifest}: entry escapes the plugin directory")
    if not entry_path.is_file():
        raise ValueError(f"{manifest}: entry not found: {entry}")

    return Plugin(
        name=str(name),
        version=str(section.get("version", "0.0.0")),
        kind=str(kind),
        entry=entry_path,
        root=root_resolved,
        actions=tuple(safety.get("actions", ["read-only"])),
        description=str(section.get("description", "")),
        schedule=str(section.get("schedule", "manual")),
        config=dict(data.get("config", {})),
        timeout=int(section.get("timeout", 60)),
    )


def run(plugin: Plugin, payload: dict[str, Any]) -> dict[str, Any]:
    if plugin.entry.suffix == ".py":
        cmd = [sys.executable, str(plugin.entry)]
    else:
        cmd = [str(plugin.entry)]

    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=plugin.timeout,
            cwd=str(plugin.root),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"plugin timed out after {plugin.timeout}s", "stderr": ""}
    except OSError as exc:
        return {"error": f"could not run plugin: {exc}", "stderr": ""}

    stderr = proc.stderr.strip()
    if proc.returncode != 0:
        return {"error": f"plugin exited with code {proc.returncode}", "stderr": stderr}

    try:
        out = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {"error": f"invalid JSON output: {exc}", "stderr": stderr}

    if not isinstance(out, dict):
        return {"error": "plugin output must be a JSON object", "stderr": stderr}

    out.setdefault("stderr", stderr)
    return out
