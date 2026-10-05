# Open questions (review wanted)

These are the design decisions we trust the least. If you work in security, your critique is worth more than your code right now. Comment here on GitHub or open an issue labeled `design-review`.

## 1. Plugin trust boundary

Jewels declare an action class in `plugin.toml`, and the Book of Oa blocks classes that are not allowed. But a jewel is arbitrary code: it can declare `read-only` and still do anything the user can. What is the right enforcement for a user-level plugin sandbox on Linux? bubblewrap, firejail, seccomp profiles, systemd sandboxing? What would you do first, and what would you not bother with?

## 2. Action classes: what is missing?

See [BOOK-OF-OA.md](BOOK-OF-OA.md). Classes A-D cover read-only, reversible, destructive and forbidden. What is wrong or missing? Consider network egress, setuid/capabilities, kernel surfaces, file-integrity baselines, package-manager actions.

## 3. Mogo: privileged read-only sensor

To see what a user cannot (`/root`, `/etc/shadow`, audit logs), we plan a root sensor that only reads and writes sanitized JSON to a user-readable spool. Narrow `NOPASSWD` sudoers with exact commands, or a root systemd unit? How would you harden the spool against output poisoning and TOCTOU?

## 4. Prompt injection in triage

Scanned content (file names, logs, file contents) reaches LLM triage. Our defense is output-side: the Ring validates schema and policy, and the model cannot execute anything. Is a small shield classifier at the ingest path worth it, or theater? Prior art from people running local LLM pipelines on untrusted data is very welcome.

## 5. False-positive strategy

Quarantine requires human confirmation. Before writing Phase 4, is there a better pattern from real SOC workflows we should adopt (severity + confidence split, staging areas, canary files, time-based quarantine)?

## 6. Corps link: trust and abuse model

We want opt-in mutual aid between pinned nodes (2-10 machines): signed distress beacons, audit-log witnesses, and intel proposals — never remote actions. What breaks? How would you design peer pairing, replay protection and eviction for a small trusted mesh? What should never cross the wire?

## 7. Everything else

If you only have fifteen minutes: read [ARCHITECTURE.md](ARCHITECTURE.md) and tell us which assumption breaks first.
