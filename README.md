# Sector 2814

A local-first agent swarm that patrols your machine for security and privacy threats — and counters what it finds.

> In brightest day, in blackest night,
> No evil shall escape my sight!
> Let those who worship evil's might,
> Beware my power — Green Lantern's light!
>
> — *The Green Lantern Oath*. The original wording (Alfred Bester, in *Green Lantern* #9) reads "in darkest night"; the modern Corps version uses "in blackest night".

**Green Lantern Corps** is the internal codename of this swarm. Agent names below are a fan homage, not branding.

## What it is

The Corps is a self-hosted defense system built from small, specialized local LLM agents coordinated by an orchestrator. Three ideas drive everything:

1. **Local-first** — inference runs on your hardware. No findings, logs, or file contents leave the host.
2. **Deterministic before probabilistic** — real scanners (ClamAV, YARA, rules) do the patrol. LLM agents wake only to triage anomalies, investigate, and explain.
3. **Reversible by default** — the Corps never deletes. Destructive actions require explicit human confirmation.

## The cast

| Entity | Role |
|---|---|
| **Oa / Guardian** | Orchestrator: dispatches Lanterns, aggregates findings, enforces the Book of Oa |
| **The Ring** | Capability layer: audited, least-privilege tools (scan, hash, inspect network, quarantine, ...) |
| **Hal Jordan** | Malware and download sentinel (ClamAV, YARA, hashes, pre-flight of downloaded files) |
| **John Stewart** | Network sentinel (listeners, connections, unusual outbound traffic) |
| **Kyle Rayner** | Privacy sentinel (permissions, leaked secrets, exposed services) |
| **Mogo** | Privileged read-only sensor: sees what a user cannot (audit logs, protected paths), never acts |
| **Kilowog** | Independent verifier: re-checks findings with a different model family; kills false positives |
| **Salaak** | Scribe: findings, deduplication, reports, memory between rounds |
| **Atrocitus** | Response: quarantine execution, after verification and human approval |
| **Central Battery** | Findings store and audit log |
| **Book of Oa** | Policy: allowlists, forbidden actions, escalation rules |

## Severity spectrum

| Level | Meaning | Response |
|---|---|---|
| Green | Clean | Log round summary |
| Yellow | Suspicious, needs triage | Verify, then report |
| Red | Active threat | Escalate to Guardian, propose action |
| Black | Compromise suspected | Page the human on duty |

## Engine stack

| Part | Engine | Why |
|---|---|---|
| Swarm (small/medium Lanterns) | llama.cpp + llama-swap | minimal overhead, one process per model, on-demand loading |
| Guardian (heavy reasoning) | TensorRT-LLM (NGC container) | maximum efficiency on Blackwell |
| Existing GraphRAG pipeline | Ollama | independent, untouched by the Corps |

## Quickstart (crown v0)

Pure Python 3.11+, no dependencies. From the repo:

```bash
PYTHONPATH=src python3 -m sector2814 plugins        # list discovered jewels
PYTHONPATH=src python3 -m sector2814 patrol         # run one round
PYTHONPATH=src python3 -m sector2814 findings       # recent findings
PYTHONPATH=src python3 -m sector2814 tools list     # the Ring (read-only tools)
PYTHONPATH=src python3 -m sector2814 tools run hash_file --args '{"path": "/etc/hostname"}'
```

Copy `config/book-of-oa.example.toml` to `~/.config/sector2814/book-of-oa.toml` to activate a policy. Data goes to `~/.local/share/sector2814/` (SQLite battery + audit log). To add a jewel, see [docs/EXTENDING.md](docs/EXTENDING.md).

## Status

**Design phase, crown v0 seeded.** See [docs/ROADMAP.md](docs/ROADMAP.md) for the build order, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design, and [docs/EXTENDING.md](docs/EXTENDING.md) to add a jewel.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first. This is security-sensitive software: read [SECURITY.md](SECURITY.md) before touching the Ring or the policy engine.

Not sure where to start? [docs/OPEN-QUESTIONS.md](docs/OPEN-QUESTIONS.md) lists the design decisions we trust the least — an expert critique is worth more than code right now.

## Disclaimer

Sector 2814 is an independent project. Agent codenames reference the Green Lantern Corps, a DC Comics property, as a fan homage. This project is not affiliated with or endorsed by DC Comics.

## License

Apache-2.0. See [LICENSE](LICENSE).
