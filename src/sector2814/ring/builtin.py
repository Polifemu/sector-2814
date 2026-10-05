"""Built-in read-only tools for the Ring."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import stat
import subprocess
from pathlib import Path

from .registry import Ring, Tool

DEFAULT_SENSITIVE_PATHS = ("~/.ssh", "~/.gnupg", "~/.config/sector2814")

DEFAULT_SECRET_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "generic-secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?([A-Za-z0-9_\-./+]{16,})"
        ),
    ),
)


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


def scan_file(args: dict) -> dict:
    raw = args.get("path")
    if not raw:
        return {"error": "missing 'path'"}
    path = Path(raw).expanduser()
    if not path.is_file():
        return {"error": f"not a file: {path}"}

    hashed = hash_file({"path": str(path)})
    if "error" in hashed:
        return hashed
    result: dict = dict(hashed)

    if shutil.which("clamscan") is None:
        result.update(
            {"engine": None, "status": "no-engine", "clean": None, "signature": None}
        )
        return result

    try:
        proc = subprocess.run(
            ["clamscan", "--no-summary", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": f"clamscan failed: {exc}", **hashed}

    result["engine"] = "clamav"
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    if proc.returncode == 0:
        result.update({"status": "clean", "clean": True, "signature": None})
    elif proc.returncode == 1 and "FOUND" in line:
        signature = line.rsplit(": ", 1)[-1].rsplit(" FOUND", 1)[0]
        result.update({"status": "infected", "clean": False, "signature": signature})
    else:
        result.update(
            {
                "status": "error",
                "clean": None,
                "signature": None,
                "detail": (proc.stderr or line).strip(),
            }
        )
    return result


def search_secrets(args: dict) -> dict:
    raw = args.get("path")
    if not raw:
        return {"error": "missing 'path'"}
    root = Path(raw).expanduser()
    if not root.exists():
        return {"error": f"not found: {root}"}

    max_files = int(args.get("max_files", 2000))
    max_file_size = int(args.get("max_file_size", 1024 * 1024))

    if root.is_file():
        files = [root]
    else:
        files = [p for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()]

    matches = []
    scanned = 0
    for path in files[:max_files]:
        try:
            if path.stat().st_size > max_file_size:
                continue
            blob = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in blob[:1024]:
            continue
        scanned += 1
        text = blob.decode("utf-8", errors="ignore")
        for name, pattern in DEFAULT_SECRET_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(1) if match.groups() else match.group(0)
                matches.append(
                    {
                        "path": str(path),
                        "pattern": name,
                        "line": text.count("\n", 0, match.start()) + 1,
                        "preview": _mask(value),
                    }
                )
    return {"path": str(root), "scanned_files": scanned, "matches": matches}


def _mask(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return value[:4] + "…"


def list_units(args: dict) -> dict:
    scope = args.get("scope", "user")
    if scope not in ("user", "system"):
        return {"error": f"unknown scope: {scope}"}
    if shutil.which("systemctl") is None:
        return {"error": "systemctl not available"}

    cmd = ["systemctl"]
    if scope == "user":
        cmd.append("--user")
    cmd += ["list-units", "--type=service,timer,socket", "--all", "--no-pager", "--output=json"]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": f"systemctl failed: {exc}"}
    if proc.returncode != 0:
        return {"error": proc.stderr.strip() or f"systemctl exit {proc.returncode}"}

    try:
        units = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return {"error": "could not parse systemctl output"}

    slim = [
        {
            "unit": unit.get("unit"),
            "load": unit.get("load"),
            "active": unit.get("active"),
            "sub": unit.get("sub"),
            "description": unit.get("description"),
        }
        for unit in units
        if isinstance(unit, dict)
    ]
    return {"scope": scope, "units": slim[:500]}


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
        Tool("scan_file", "Hash + ClamAV scan of a file", "read-only", scan_file)
    )
    ring.register(
        Tool(
            "search_secrets",
            "Regex scan for secrets, values masked",
            "read-only",
            search_secrets,
        )
    )
    ring.register(
        Tool("list_units", "systemd units (user scope by default)", "read-only", list_units)
    )
    ring.register(
        Tool("list_connections", "Active TCP/UDP connections (ss)", "read-only", list_connections)
    )
    ring.register(Tool("check_perms", "Permissions of sensitive paths", "read-only", check_perms))
    return ring
