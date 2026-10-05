"""The Book of Oa: the only component with veto power.

Default policy is the safest one: read-only everywhere, no mutations,
no destructive actions. A missing Book means those defaults.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

ACTION_CLASSES = ("read-only", "reversible", "destructive")
PLUGIN_KINDS = ("detector", "lantern", "adapter", "reporter")


@dataclass(frozen=True)
class Policy:
    read_only: bool = True
    reversible: bool = False
    destructive: bool = False
    escalate_at: str = "red"
    allow_kinds: tuple[str, ...] = PLUGIN_KINDS
    source: str = "defaults (no Book of Oa found)"

    def allows_actions(self, actions: list[str]) -> tuple[bool, str]:
        for action in actions:
            if action not in ACTION_CLASSES:
                return False, f"unknown action class: {action}"
            if action == "read-only" and not self.read_only:
                return False, "read-only actions are disabled"
            if action == "reversible" and not self.reversible:
                return False, "reversible actions are disabled by the Book of Oa"
            if action == "destructive" and not self.destructive:
                return False, "destructive actions are disabled by the Book of Oa"
        return True, "ok"

    def allows_kind(self, kind: str) -> bool:
        return kind in self.allow_kinds


def load(path: Path) -> Policy:
    path = Path(path)
    if not path.is_file():
        return Policy()

    with path.open("rb") as fh:
        data = tomllib.load(fh)

    actions = data.get("actions", {})
    meta = data.get("policy", {})
    return Policy(
        read_only=bool(actions.get("read_only", True)),
        reversible=bool(actions.get("reversible", False)),
        destructive=bool(actions.get("destructive", False)),
        escalate_at=str(meta.get("escalate_at", "red")),
        source=str(path),
    )
