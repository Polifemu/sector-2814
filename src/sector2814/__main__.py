"""CLI entry point: python -m sector2814 <command>."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import policy as policy_mod
from .audit import Audit
from .battery import Battery
from .config import load_config
from .guardian import Guardian
from .plugins import discover
from .ring.builtin import build_default_ring


def _config(args: argparse.Namespace):
    repo = Path(args.repo).resolve()
    home = Path(args.home).expanduser() if args.home else None
    return load_config(repo_root=repo, home=home)


def cmd_patrol(args: argparse.Namespace) -> int:
    config = _config(args)
    policy = policy_mod.load(config.book_path)
    audit = Audit(config.audit_path)
    battery = Battery(config.battery_path)
    summary = Guardian(config, policy, battery, audit).patrol(only=args.plugin)
    for line in summary["lines"]:
        print(line)
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary["severity"] in ("red", "black") else 0


def cmd_tools(args: argparse.Namespace) -> int:
    config = _config(args)
    ring = build_default_ring(Audit(config.audit_path))
    if args.action == "list":
        for tool in ring.list():
            print(f"{tool.name:18s} [{tool.action}] {tool.description}")
        return 0
    if not args.name:
        print("usage: tools run <name> [--args JSON]")
        return 2
    try:
        tool_args = json.loads(args.args) if args.args else {}
    except json.JSONDecodeError as exc:
        print(f"invalid --args JSON: {exc}")
        return 2
    print(json.dumps(ring.run(args.name, tool_args), indent=2, ensure_ascii=False))
    return 0


def cmd_findings(args: argparse.Namespace) -> int:
    config = _config(args)
    battery = Battery(config.battery_path)
    rows = battery.recent(limit=args.limit)
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    if not rows:
        print("no findings yet")
        return 0
    for row in rows:
        print(f"[{row['severity']:6s}] {row['ts']} {row['plugin']}: {row['title']}")
    return 0


def cmd_plugins(args: argparse.Namespace) -> int:
    config = _config(args)
    plugins = discover(config.plugin_dirs)
    if not plugins:
        print("no jewels found")
        return 0
    for plugin in plugins:
        print(f"{plugin.name:20s} v{plugin.version} ({plugin.kind}) {plugin.description}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print(
            "refusing to run as root: the Corps runs as the user, never root",
            file=sys.stderr,
        )
        return 2

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", default=".", help="repo root (jewels live in <repo>/plugins)")
    common.add_argument("--home", default=None, help="override home for data/config")
    common.add_argument("--json", action="store_true", help="machine-readable output")

    parser = argparse.ArgumentParser(
        prog="sector2814", description="Sector 2814 - crown of the Corps (v0)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    patrol = sub.add_parser("patrol", parents=[common], help="run a patrol round")
    patrol.add_argument("--plugin", default=None, help="run only this jewel")
    patrol.set_defaults(func=cmd_patrol)

    tools = sub.add_parser("tools", parents=[common], help="inspect the Ring")
    tools.add_argument("action", choices=["list", "run"])
    tools.add_argument("name", nargs="?", help="tool name (for run)")
    tools.add_argument("--args", default=None, help="JSON arguments (for run)")
    tools.set_defaults(func=cmd_tools)

    findings = sub.add_parser("findings", parents=[common], help="show recent findings")
    findings.add_argument("--limit", type=int, default=20)
    findings.set_defaults(func=cmd_findings)

    plugins = sub.add_parser("plugins", parents=[common], help="list discovered jewels")
    plugins.set_defaults(func=cmd_plugins)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
