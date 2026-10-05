# Roadmap

## Phase 0 — Foundation

- [ ] Build llama.cpp for the target GPU (CUDA, flash-attn, KV cache q8_0)
- [ ] Install llama-swap as a user service
- [ ] Import existing GGUF models into the Corps store (hardlink when possible)
- [ ] Tiering config: always-warm tiny models + on-demand medium models
- [ ] Deploy the TensorRT-LLM container (digest-pinned) and cache the Guardian engine
- [ ] First Book of Oa draft: model/image digests, allowlists, ports

Stretch: put a prompt-injection shield model in the ingest path from day one.

## Phase 1 — The Ring (read-only)

- [x] Crown v0: round runner, JSON plugin protocol, example jewel
- [x] Policy engine (Book of Oa parser) + structured audit log
- [x] Central Battery schema (SQLite) and finding model
- [x] Tool schemas: `hash_file`, `list_connections`, `check_perms` (v0)
- [ ] Remaining tools: `scan_file`, `search_secrets`, `list_units`
- [ ] Install the deterministic arsenal (antivirus, YARA, file-integrity, audit tooling)

## Phase 2 — Lanterns (on demand)

- [ ] Agent definitions with per-agent model routing
- [ ] Hal (malware/download), John (network), Kyle (privacy) first pass
- [ ] Kilowog verification pass with a different model family
- [ ] Salaak dedup and round reports
- [ ] Targeted-round mode: one Lantern on one artifact

## Phase 3 — Patrol daemon

- [ ] Deterministic sweep script
- [ ] systemd timer + anomaly-triggered triage
- [ ] Token budget per round and kill switch
- [ ] Baseline snapshot to suppress known-good noise

## Phase 4 — Atrocitus (response)

- [ ] Vault with manifests and one-command restore
- [ ] Approval flow: token minted only by an interactive human session
- [ ] Allowlist entries with expiry and required reason
- [ ] Dry-run mode for every mutating action

## Phase 5 — Hardening the Corps

- [ ] Integrity monitor for models, images, engines (digest pinning enforced)
- [ ] Prompt-injection shield integrated end to end
- [ ] Book of Oa hash-watched by the Corps itself
- [ ] Optional: LoRA specialization trained on labeled findings from the Central Battery
