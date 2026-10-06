# Formal model of the round protocol

These are design artifacts, not production code: the round protocol of
Sector 2814 expressed as workflow nets and machine-checked with
[petrinet-lab](https://github.com/Polifemu/Petrinet-Lab). The goal is to
catch protocol-level flaws (deadlocks, bypasses, missing joins) before
they are baked into the Crown.

## Models

| Model | File | What it captures |
|---|---|---|
| Patrol round | `models/round-patrol.pnml` | deterministic sweep, LLM triage, policy gate, human approval, reversible quarantine |
| Deep round | `models/round-deep.pnml` | patrol + mandatory independent verification before the policy gate |
| Emergency dispatch | `models/emergency-dispatch.pnml` | all Lanterns in parallel, AND-join on every return |
| Triage deadline | `models/triage-deadline.pnml` | timed fail-safe: if the LLM does not answer within 30s, the hard deadline closes the round report-only |

The P/T models are exported to PNML. The timed model carries its firing
intervals in `verify.py`: `d_llm_triage [0,30]`, `d_hard_deadline [30,30]`.

## What is verified

For each round model, `verify.py` checks:

- workflow net: single source and sink, every node on a source-sink path
- conservative and 1-safe (a minimal P-invariant covers every place)
- deadlock-free with proper completion: every deadlock is exactly the sink
- option to complete: from every reachable marking the sink is reachable
- no dead transitions: every transition fires in some complete sequence
- the approval invariant: `p_approved` has exactly one producer
  (`t_human_mint_token`, the human) and one consumer (`t_quarantine`);
  over all complete firing sequences, no `t_quarantine` occurs without a
  prior human-minted token
- non-vacuity: the guarded mutation path occurs in at least one sequence

Emergency adds: the join preset equals every Lantern return place, and
all 6 return interleavings reach the same final marking.

The timed model adds: no time-lock class, the only terminal class is the
closed round, firing bounds `(0,30)` and `(30,30)`, both outcomes
reachable, and the deadline fires in simulation.

Negative controls (deliberately broken nets) are analysed too:

- approval bypass (`p_proposal -> t_quarantine`): the invariant checker
  reports the violating sequence
- emergency join that forgets one Lantern: the round closes with work in
  flight, and the checker reports the incomplete final marking

Result on 2026-10-06: **32/32 checks pass**.

## How to run

```bash
PYTHONPATH=/path/to/petrinet-lab/src python3 formal/verify.py
```

petrinet-lab needs `networkx` and `numpy` (its own venv is fine). The
script regenerates `formal/models/*.pnml` and exits non-zero on any
failure.

## Caveats

- The nets model the protocol, not the implementation: passing checks
  here does not prove that `src/sector2814/` refines the net. The audit
  log in the Central Battery is the reference event log for a future
  conformance check (token replay / alignments with petrinet-lab).
- LLM behaviour enters as an outcome-coloured choice (benign/suspicious,
  confirm/dismiss): safety holds for every outcome, including wrong ones.
- Policy-file tampering, host compromise and rootkits are out of scope
  (see `docs/ARCHITECTURE.md`); the net assumes an honest engine.
- The 30 second deadline is an example; real windows come from config.
