# Security Policy

## Reporting a vulnerability

Do not open a public issue for security problems. Use GitHub private vulnerability reporting on this repository, or contact the maintainers directly.

Please include:

- what the issue is and where
- how to reproduce it
- what a malicious actor could achieve
- any suggested fix

## Scope

We are especially interested in these classes of issues:

- **Prompt injection** — scanned content influencing agent behavior beyond its advisory role
- **Policy bypass** — model output or crafted input leading the Ring past the Book of Oa
- **Privilege escalation** — anything letting the Corps act outside the user it runs as
- **Unwanted egress** — any code path that sends data off the host
- **Supply chain** — tampered models, container images, or engine artifacts that pass digest checks incorrectly
- **Vault escape** — quarantine contents executed, leaked, or silently deleted

## Project promises

- Local-first: no telemetry, no phone-home, no cloud dependency.
- Reversible: no deletion of user data, ever.
- Transparent: every action is auditable in the Central Battery.
- Fail-safe: ambiguity resolves to inaction.

## Threat model

The full threat model lives in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). In short: we defend against commodity malware, stalkerware, leaked secrets, anomalous network activity, and supply-chain tampering on a personal workstation. We do not claim coverage against kernel implants, physical access, or full network intrusion detection.
