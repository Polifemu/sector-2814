# Extending Sector 2814: the Crown and the Jewels

The project is split in two, and the halves have different rules.

## The Crown

`src/sector2814/` — orchestration, policy engine, Ring, audit, findings store.
This is the part everyone shares and nobody forks. Changes here are
security-sensitive: two reviewers, and a note on threat-model impact.
If it is not in the audit log, it did not happen.

The crown knows nothing about viruses or networks. It knows how to run a
round, enforce the Book of Oa, validate tool calls, and record findings.

## The Jewels

Everything else is a jewel: detectors, Lantern prompts, engine adapters,
reporters. A jewel is a directory with:

```
my-jewel/
  plugin.toml     # manifest
  entry           # executable in any language
```

Jewels ship in this repo (`plugins/`) or in separate repos installed into
`~/.config/sector2814/plugins/`. Maintainers give suggestions; they do not
dictate how a jewel works, as long as it respects the contract below.

## The contract

### Manifest (`plugin.toml`)

```toml
[plugin]
name = "my-jewel"          # lowercase, dashes
version = "0.1.0"
kind = "detector"          # detector | lantern | adapter | reporter
entry = "detect.py"        # relative to the jewel directory
description = "one line"
schedule = "daily"
timeout = 30               # seconds, enforced by the crown

[safety]
actions = ["read-only"]    # read-only | reversible | destructive

[config]
# free-form, passed to the jewel on every run
```

A jewel that declares `reversible` or `destructive` does not run unless the
Book of Oa allows that action class. With the default book, only `read-only`
jewels run.

### Runtime protocol (v1)

The crown starts `entry`, writes one JSON payload to stdin and waits for one
JSON object on stdout.

Payload:

```json
{
  "protocol": 1,
  "round_id": "a1b2c3d4e5f6",
  "plugin": "my-jewel",
  "config": { "...": "from plugin.toml" },
  "policy": {
    "actions": { "read_only": true, "reversible": false, "destructive": false },
    "escalate_at": "red"
  }
}
```

Response:

```json
{
  "findings": [
    {
      "severity": "yellow",
      "title": "world-writable file: notes.txt",
      "detail": "Any local user can modify this file.",
      "subject": { "type": "file", "value": "/home/user/notes.txt" },
      "evidence": { "mode": "0o666" }
    }
  ]
}
```

Rules:

- Exit code 0 and one JSON object on stdout. Anything else is logged as a
  plugin error and the round continues.
- Findings must match `schemas/finding.schema.json`. Unknown severity values
  are coerced to `yellow` by the crown, never trusted upward.
- Jewels are read-only at runtime unless the policy says otherwise. Leaving
  the machine without explicit human approval is a Class D violation
  (see `docs/BOOK-OF-OA.md`).
- A jewel never talks to the network. If it needs to, it is the wrong shape.

## Testing a jewel

```bash
echo '{"protocol": 1, "config": {}}' | ./plugins/my-jewel/entry
PYTHONPATH=src python3 -m sector2814 patrol --plugin my-jewel
```

The crown's own tests live in `tests/` and run with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
