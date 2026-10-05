# Architecture

## Goals

- Detect and triage security and privacy threats on a personal Linux workstation.
- Keep all inference local. Nothing sensitive leaves the host by default.
- Never let an autonomous agent perform an irreversible action unattended.

## Non-goals

- Replacing an enterprise EDR or a full IDS/IPS.
- Guaranteeing detection of kernel-level rootkits (we can surface symptoms, not promise coverage).
- Any form of offensive counter-hacking.

## Design principles

1. **Deterministic before probabilistic** — scanners and rules first; LLMs only triage, investigate, and explain.
2. **Least privilege** — the Corps runs as the user, never root. The Ring exposes the smallest possible toolset.
3. **Reversibility** — quarantine moves files to a vault with a manifest; restore is one command. Deletion does not exist as an action.
4. **Human in the loop** — system-mutating tools require an approval token. The daemon cannot mint tokens.
5. **Propose vs dispose** — model output is advisory. The Ring validates schema and policy before any effect.
6. **Auditability** — every finding, verdict, and action is logged.
7. **Fail-safe** — any crash, timeout, or ambiguous state resolves to "do nothing and report".

## Layers

```
                           +---------------------------+
                           |        Oa / Guardian      |   orchestration, policy
                           +-------------+-------------+
                                         |
              +--------------------------+--------------------------+
              |                          |                          |
        [ Hal ] [ John ]            [ Kilowog ]                [ Salaak ]
        [ Kyle ]  malware           independent                scribe,
         network  privacy           verification               memory
              |                          |                          |
              +--------------------------+--------------------------+
                                         |
                                  +------+------+
                                  |  THE RING   |   capability layer
                                  +------+------+   (least privilege, audited)
                                         |
                        +----------------+----------------+
                        |                                 |
                 filesystem / network              CENTRAL BATTERY
                 scanners, tools                   findings + audit log

                        policy enforced from: BOOK OF OA
```

## Round types

| Round | Trigger | Cost | What runs |
|---|---|---|---|
| Patrol | systemd timer (e.g. every few hours) | low | deterministic sweep; LLM triage only on yellow+ |
| Deep | weekly or on demand | medium | full sweep + Kilowog verification, Salaak report |
| Emergency | human or black finding | high | all Lanterns in parallel, Guardian escalated |
| Targeted | human | low | one Lantern on one artifact (a download, a process, a file) |

## Model routing

| Role | Model class | Residency |
|---|---|---|
| Shield (prompt-injection filter) | tiny classifier (~86M–2B) | always warm |
| Triage (green/yellow/red) | 4B instruct, JSON-schema constrained | always warm |
| Memory / dedup | embedding model | always warm |
| Verifier (Kilowog) | 12–27B, **different family** from the analyst models | on demand |
| Guardian | 30B MoE class (TensorRT-LLM) | on demand / scheduled |
| Escalation (black only) | 120B MoE class, optional | manual |

Hard rule: the verifier is never the same model that produced the finding.

## Engine stack

| Part | Engine | Notes |
|---|---|---|
| Swarm | llama.cpp built for the target GPU (CUDA, flash-attn, KV cache q8_0, mmap) | one process per model |
| Routing | llama-swap | single OpenAI-compatible endpoint, warm/cold tiers, TTL, API key, loopback only |
| Guardian | TensorRT-LLM in a digest-pinned NGC container | engine cached once; fallback to the 30B MoE on llama.cpp if unavailable |
| Existing GraphRAG | Ollama | separate store and port; never part of the Corps' policy surface |

## Runtime layout (reference)

```
~/.local/share/lantern-corps/
  models/*.gguf          # swarm GGUFs (hardlinked from existing local stores when possible)
  trt-engines/           # TensorRT-LLM engine cache
  vault/                 # reversible quarantine, with manifests
  findings.db            # Central Battery (SQLite)
  book-of-oa.yaml        # policy
```

- All Corps endpoints bind to `127.0.0.1` and require an API key.
- The patrol script talks directly to the local endpoints (no agent-harness overhead).
- The orchestrator swarm runs on demand inside opencode for deep investigations.

## Threat model

In scope:

- Commodity malware and suspicious downloads.
- Stalkerware and unwanted telemetry.
- Leaked secrets in plaintext, weak file permissions, exposed services.
- Anomalous network activity and attempted exfiltration.
- Supply chain: model files, container images, engine artifacts.
- Prompt injection through scanned content.

Out of scope (for now):

- Physical access, firmware implants, hypervisor-level attacks.
- Full packet-level IDS.
- Multi-user or server-grade deployments.

## Security of the Corps itself

- **Digest pinning** — every model, image, and engine artifact is identified by hash in the Book of Oa; a changed hash raises a black finding.
- **Ring validation** — the Ring parses tool calls structurally and checks policy; it never trusts free-form model output.
- **Approval tokens** — destructive tools need a token minted only by an interactive human session, never by the daemon.
- **No egress by default** — Lanterns have no network privileges except read-only inspection. The only network service is the local inference endpoint.
- **Vault manifests** — every quarantine action writes source path, hash, reason, and finding id; restore is verifiable.

## Failure modes

| Failure | Behavior |
|---|---|
| LLM endpoint down | deterministic sweep continues; anomalies queued |
| Verifier disagrees | finding stays proposed; human decides |
| Guardian container broken | fall back to local 30B MoE; log engine degradation |
| Policy file modified | black finding; patrol suspends mutations |
| Budget exceeded | round stops; partial report delivered |
