# AGENTS.md — Sector 2814

Local-first security patrol: deterministic scanners do the work, local LLM agents ("Lanterns") only triage/investigate/explain. Codename "Green Lantern Corps" is a fan homage; the repo is public (`github.com/Polifemu/sector-2814`, Apache-2.0).

## Non-negotiable design rules

Read `CONTRIBUTING.md` and `SECURITY.md` before touching the Crown or the Ring.

1. Deterministic before probabilistic — scanners first, LLMs only triage.
2. No destructive defaults — nothing deletes/kills/blocks without human confirmation; deletion does not exist as an action.
3. No egress — agents never send data anywhere.
4. Least privilege — runs as user, never root; the Ring exposes the smallest toolset.
5. Propose vs dispose — model output is advisory; schema + policy validation lives in the Ring, never in a prompt.
6. Everything logged — if it is not in the audit log, it did not happen.
7. Fail-safe — crash/timeout/ambiguity resolves to "do nothing and report".

## Layout

- `src/sector2814/` — **the Crown** (security-sensitive, two reviewers): `guardian.py` (orchestrator), `policy.py` (Book of Oa, only component with veto), `ring/` (capability layer: `registry.py`, `builtin.py`), `battery.py` (findings store), `audit.py`, `config.py`, `plugins.py`, `__main__.py` (CLI).
- `plugins/` — **the Jewels** (contribution-friendly): `plugin.toml` + executable speaking JSON over stdin/stdout, any language. Spec: `docs/EXTENDING.md`.
- `schemas/` — `finding.schema.json`, `plugin.schema.json`.
- `config/` — `book-of-oa.example.toml`, `llama-swap.example.yaml`.
- `docs/` — ARCHITECTURE.md (full design), BOOK-OF-OA.md, EXTENDING.md, OPEN-QUESTIONS.md, ROADMAP.md.
- `formal/` — round protocol as machine-checked workflow nets (petrinet-lab), PNML models in `formal/models/`; design artifacts, not production code.
- `tests/test_crown.py` — pytest suite.

## Commands

```bash
PYTHONPATH=src python3 -m sector2814 plugins      # list discovered jewels
PYTHONPATH=src python3 -m sector2814 patrol       # run one round
PYTHONPATH=src python3 -m sector2814 findings     # recent findings
PYTHONPATH=src python3 -m sector2814 tools list   # the Ring (read-only tools)
PYTHONPATH=src python3 -m sector2814 tools run hash_file --args '{"path": "/etc/hostname"}'
python3 -m pytest tests/                          # crown tests
python3 formal/verify.py                          # formal round-protocol checks (32 checks)
```

- Pure Python 3.11+, **no dependencies for the Crown** (stdlib only).
- Runtime data: `~/.local/share/sector2814/` (SQLite battery + audit log).
- Policy config: `~/.config/sector2814/book-of-oa.toml` (example in `config/`).
- New behavior goes in the Book of Oa before it goes in code.

## Conventions

- Keep the Crown stdlib-only; Jewels are isolated and may use anything.
- Findings and tool I/O are JSON validated against `schemas/`.
- Never commit real malware; test fixtures must be simulated findings.
- Commit identity: `198372504+Polifemu@users.noreply.github.com` (never personal emails).
- The formal models must stay in sync with the round protocol in the Crown; run `formal/verify.py` after protocol changes.
