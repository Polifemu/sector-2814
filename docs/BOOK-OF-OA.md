# The Book of Oa

The policy that every Lantern obeys. If it is not written here, it is not allowed.

## Severity spectrum

| Level | Name | Meaning |
|---|---|---|
| Green | clean | nothing to do |
| Yellow | suspicious | verify and report |
| Red | active threat | escalate, propose action |
| Black | compromise suspected | page the human, suspend mutations |

## Action classes

### Class A — Read-only (autonomous)

Safe to run without asking:

- scanning, hashing, listing, inspecting, reading metadata
- querying local endpoints
- writing to the Central Battery (findings, logs)

### Class B — Reversible mutation (confirmation required by default)

Touching the system in a way that can be undone:

- moving a file to the quarantine vault
- disabling a unit, blocking a connection temporarily

Default: propose, then execute only after human confirmation.
Opt-in configuration may allow auto-quarantine after a confirmed verdict, never for paths on the protected list.

### Class C — Destructive (always confirmation, explicit warning)

- killing a process
- deleting anything (the vault is the closest thing to deletion that exists)
- editing firewall rules or security settings

Always requires an approval token minted by an interactive human session.

### Class D — Forbidden

Never, under any circumstances:

- exfiltrating data or contacting external services
- disabling the Corps itself, its logging, or its policy
- modifying its own policy or digest pins
- escalating privileges on its own
- deleting vault contents

## Escalation matrix

| Severity | Autonomous | Needs confirmation | Forbidden |
|---|---|---|---|
| Green | logging | — | mutations |
| Yellow | verify, dedup, report | quarantine | Class C, D |
| Red | verifier pass, evidence capture | quarantine, kill | Class D |
| Black | freeze mutations, alert | everything | Class D |

## Allowlist rules

Every entry requires:

- the exact subject (path, hash, process, connection, unit)
- a reason
- an expiry date

Expired entries are removed automatically and reported in the next round.

## Amendments

Changes to this document require a human commit. The running Corps watches its hash; any change triggers a policy reload and a yellow finding in the audit log.
