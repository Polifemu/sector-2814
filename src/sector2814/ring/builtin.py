"""Built-in read-only tools for the Ring v0."""

from __future__ import annotations

import hashlib
import shutil
import stat
import subprocess
from pathlib import Path

from .registry import Ring, Tool

DEFAULT_SENSITIVE_PATHS = ("~/.ssh", "~/.gnupg", "~/.config/sector2814")


def hash_file(args: dict) -> dict:
    raw = args.get("path")
    if not raw:
        return {"error": "missing 'path'"}
    path = Path(raw).expanduser()
    if not path.is_file():
        return {"error": f"not a file: {path}"}

    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "size": size}


def list_connections(args: dict) -> dict:
    if shutil.which("ss") is None:
        return {"error": "ss not available"}
    try:
        proc = subprocess.run(
            ["ss", "-tunapH"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": f"ss failed: {exc}"}
    if proc.returncode != 0:
        return {"error": proc.stderr.strip() or f"ss exit {proc.returncode}"}

    connections = []
    for line in proc.stdout.splitlines():
        parts = line.split(maxsplit=6)
        if len(parts) < 6:
            continue
        netid, state, recvq, sendq, local, peer = parts[:6]
        connections.append(
            {
                "netid": netid,
                "state": state,
                "recvq": recvq,
                "sendq": sendq,
                "local": local,
                "peer": peer,
                "process": parts[6] if len(parts) > 6 else "",
            }
        )
    return {"connections": connections}


def check_perms(args: dict) -> dict:
    raw_paths = args.get("paths") or list(DEFAULT_SENSITIVE_PATHS)
    results = []
    for raw in raw_paths:
        path = Path(raw).expanduser()
        if not path.exists():
            results.append({"path": str(path), "exists": False})
            continue
        mode = stat.S_IMODE(path.stat().st_mode)
        results.append(
            {
                "path": str(path),
                "exists": True,
                "mode": oct(mode),
                "world_readable": bool(mode & 0o004),
                "world_writable": bool(mode & 0o002),
                "group_writable": bool(mode & 0o020),
            }
        )
    return {"paths": results}


def build_default_ring(audit=None) -> Ring:
    ring = Ring(audit=audit)
    ring.register(Tool("hash_file", "SHA-256 of a file", "read-only", hash_file))
    ring.register(
        Tool("list_connections", "Active TCP/UDP connections (ss)", "read-only", list_connections)
    )
    ring.register(
        Tool("check_perms", "Permissions of sensitive paths", "read-only", check_perms)
    )
    return ring
