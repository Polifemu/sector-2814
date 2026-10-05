"""The Guardian: runs a round, enforces policy, collects findings."""

from __future__ import annotations

import uuid
from typing import Any

from .battery import Battery, Finding, SEVERITIES
from .config import Config
from .plugins import discover, run

SEVERITY_ORDER = {level: index for index, level in enumerate(SEVERITIES)}


class Guardian:
    def __init__(self, config: Config, policy: Any, battery: Battery, audit: Any) -> None:
        self.config = config
        self.policy = policy
        self.battery = battery
        self.audit = audit

    def patrol(self, only: str | None = None) -> dict[str, Any]:
        round_id = uuid.uuid4().hex[:12]
        self.battery.start_round(round_id)
        self.audit.log("round.start", round_id=round_id, only=only)

        lines: list[str] = [f"round {round_id}"]
        worst = "green"

        plugins = [p for p in discover(self.config.plugin_dirs) if p.kind == "detector"]
        if only:
            plugins = [p for p in plugins if p.name == only]
        if not plugins:
            lines.append("no detector jewels found")

        for plugin in plugins:
            allowed, reason = self.policy.allows_actions(list(plugin.actions))
            if not allowed:
                self.audit.log("plugin.blocked", plugin=plugin.name, reason=reason)
                lines.append(f"blocked {plugin.name}: {reason}")
                continue

            payload = {
                "protocol": 1,
                "round_id": round_id,
                "plugin": plugin.name,
                "config": plugin.config,
                "policy": {
                    "actions": {
                        "read_only": self.policy.read_only,
                        "reversible": self.policy.reversible,
                        "destructive": self.policy.destructive,
                    },
                    "escalate_at": self.policy.escalate_at,
                },
            }
            result = run(plugin, payload)
            findings = result.get("findings", [])
            self.audit.log(
                "plugin.run",
                plugin=plugin.name,
                error=result.get("error"),
                findings=len(findings),
            )

            if result.get("error"):
                lines.append(f"{plugin.name}: error: {result['error']}")
                continue

            if not findings:
                lines.append(f"{plugin.name}: clean")
                continue

            for raw in findings:
                finding = self._coerce(plugin.name, round_id, raw)
                self.battery.add_finding(finding)
                worst = max(worst, finding.severity, key=lambda s: SEVERITY_ORDER[s])
                lines.append(f"{finding.severity:6s} {plugin.name}: {finding.title}")

        self.battery.finish_round(round_id, worst, "; ".join(lines))
        self.audit.log("round.finish", round_id=round_id, severity=worst)
        return {"round_id": round_id, "severity": worst, "lines": lines}

    def _coerce(self, plugin_name: str, round_id: str, raw: Any) -> Finding:
        if not isinstance(raw, dict):
            raw = {"title": str(raw)}
        severity = raw.get("severity", "yellow")
        if severity not in SEVERITIES:
            severity = "yellow"
        return Finding(
            plugin=plugin_name,
            severity=severity,
            title=str(raw.get("title") or "untitled finding"),
            detail=str(raw.get("detail") or ""),
            evidence=raw.get("evidence") or {},
            subject=raw.get("subject") or {},
            round_id=round_id,
        )
