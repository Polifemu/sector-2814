from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from sector2814 import policy as policy_mod
from sector2814.audit import Audit
from sector2814.battery import Battery, Finding
from sector2814.config import Config
from sector2814.guardian import Guardian
from sector2814.plugins import discover, run
from sector2814.ring.builtin import build_default_ring


def make_config(root: Path, plugin_dirs: tuple[Path, ...]) -> Config:
    return Config(
        home=root,
        data_dir=root / "data",
        config_dir=root / "config",
        plugin_dirs=plugin_dirs,
        battery_path=root / "data" / "battery.db",
        audit_path=root / "data" / "audit.jsonl",
        book_path=root / "config" / "book-of-oa.toml",
    )


class PolicyTest(unittest.TestCase):
    def test_defaults_deny_mutations(self):
        policy = policy_mod.Policy()
        self.assertEqual(policy.allows_actions(["read-only"]), (True, "ok"))
        self.assertFalse(policy.allows_actions(["reversible"])[0])
        self.assertFalse(policy.allows_actions(["destructive"])[0])

    def test_unknown_action_rejected(self):
        self.assertFalse(policy_mod.Policy().allows_actions(["sudo"])[0])


class BatteryTest(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            battery = Battery(Path(tmp) / "battery.db")
            battery.start_round("r1")
            battery.add_finding(
                Finding(plugin="t", severity="yellow", title="x", round_id="r1")
            )
            battery.finish_round("r1", "yellow", "done")
            rows = battery.recent()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["severity"], "yellow")
            self.assertEqual(rows[0]["title"], "x")


class PluginTest(unittest.TestCase):
    def test_example_detector_flags_world_writable(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            bad = target / "bad.txt"
            bad.write_text("x")
            os.chmod(bad, 0o666)

            plugins = discover((REPO / "plugins",))
            plugin = next(p for p in plugins if p.name == "example-detector")
            result = run(
                plugin,
                {"protocol": 1, "round_id": "t", "config": {"directory": str(target)}},
            )
            self.assertNotIn("error", result)
            self.assertTrue(any("bad.txt" in f["title"] for f in result["findings"]))


class RingTest(unittest.TestCase):
    def test_hash_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hello"
            path.write_text("hello")
            out = build_default_ring().run("hash_file", {"path": str(path)})
            self.assertEqual(out["size"], 5)
            self.assertEqual(len(out["sha256"]), 64)

    def test_unknown_tool(self):
        self.assertIn("error", build_default_ring().run("nope", {}))


class GuardianTest(unittest.TestCase):
    def test_patrol_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root, (REPO / "plugins",))
            audit = Audit(config.audit_path)
            battery = Battery(config.battery_path)
            guardian = Guardian(config, policy_mod.Policy(), battery, audit)

            summary = guardian.patrol()
            self.assertIn(summary["severity"], ("green", "yellow"))
            self.assertTrue(config.audit_path.is_file())

    def test_policy_blocks_destructive_jewel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jewel = root / "plugins" / "bad"
            jewel.mkdir(parents=True)
            (jewel / "plugin.toml").write_text(
                '[plugin]\nname = "bad"\nversion = "0"\nkind = "detector"\n'
                'entry = "run.sh"\n\n[safety]\nactions = ["destructive"]\n'
            )
            (jewel / "run.sh").write_text('#!/bin/sh\necho \'{"findings": []}\'\n')

            config = make_config(root, (root / "plugins",))
            guardian = Guardian(
                config,
                policy_mod.Policy(),
                Battery(config.battery_path),
                Audit(config.audit_path),
            )
            summary = guardian.patrol()
            self.assertIn("blocked bad", "\n".join(summary["lines"]))


if __name__ == "__main__":
    unittest.main()
