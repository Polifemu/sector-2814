# Contributing

Thanks for wanting to join the Corps. This project is security-sensitive, so the rules are stricter than usual.

## Ground rules

1. **No destructive defaults.** Nothing the Corps does by default may delete, kill, or block without human confirmation.
2. **No egress.** Agents never send data anywhere. If your change needs the network, it needs a very good reason and a reviewer.
3. **Everything is logged.** If an action is not in the audit log, it did not happen.
4. **Least privilege.** New tools run as the user. Root is not available to the Ring.
5. **Policy first.** New behavior goes in the Book of Oa before it goes in code.
6. **Propose vs dispose.** Model output is advisory; validation lives in the Ring, never in a prompt.

## Crown and Jewels

The repo is split in two, and the halves have different rules:

- **The Crown** (`src/sector2814/`): orchestration, policy engine, tool registry, audit, findings store. Security-sensitive: two reviewers, and a note on threat-model impact.
- **The Jewels** (`plugins/`): detectors, Lantern prompts, engine adapters, reporters. Contribution-friendly: a jewel is a `plugin.toml` plus an executable that speaks JSON over stdin/stdout, in any language. Maintainers review for safety and give suggestions; they do not dictate style or scope. Spec: [docs/EXTENDING.md](docs/EXTENDING.md).

## Ways to contribute

- Lantern agent definitions and prompts
- Deterministic detectors and rules
- Engine and runtime configuration (llama.cpp, llama-swap, TensorRT-LLM)
- The Ring tool schemas and policy engine
- Documentation, threat research, taxonomy
- Test fixtures that simulate findings (never real malware committed to the repo)

## Development

- Target platform: Linux, ARM64 or x86_64, optional NVIDIA GPU.
- Models are never committed. Use your own local copies; the repo tracks digests, not weights.
- Keep PRs small and focused. Describe the threat-model impact of the change.
- Security-sensitive changes (Ring, policy engine, approval flow) need two reviewers.

## Commit style

Short imperative subject, a body when the "why" is not obvious. Example:

```
ring: reject tool calls with unknown schema fields

Free-form fields were passed through to the executor, which
allowed a model to smuggle arguments past policy checks.
```

## Reporting security issues

See [SECURITY.md](../SECURITY.md). Do not open a public issue for a bypass or a vulnerability.
