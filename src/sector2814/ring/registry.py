"""The Ring: the only component allowed to touch the system.

Every tool declares its action class. The policy engine decides whether
that class is allowed. Every call is audited. Failures never crash a round.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

ToolFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    action: str
    fn: ToolFn


class Ring:
    def __init__(self, audit: Any = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._audit = audit

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list(self) -> list[Tool]:
        return sorted(self._tools.values(), key=lambda t: t.name)

    def run(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"unknown tool: {name}"}
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return {"error": "arguments must be a JSON object"}

        try:
            result = tool.fn(args)
            ok = "error" not in result
        except Exception as exc:  # noqa: BLE001 - the ring must never crash a round
            result = {"error": f"{type(exc).__name__}: {exc}"}
            ok = False

        if self._audit is not None:
            self._audit.log("ring.tool", tool=name, action=tool.action, args=args, ok=ok)
        return result
