"""Formal verification of the round orchestration as a workflow net.

The protocol of a round (Patrol / Deep) and the Emergency dispatch are
built with petrinet-lab and checked for workflow-net soundness,
1-safety, deadlock-freedom, proper completion, and the safety invariant
that no mutation can fire without a human-minted approval token.

Negative controls (deliberately broken variants) are analysed too, to
show that the checks above are not vacuous.

Usage:
    PYTHONPATH=/path/to/petrinet-lab/src python3 formal/verify.py

Generated PNML models are written to formal/models/. Exit code is
non-zero if any check fails.
"""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

try:
    from petrinet_lab.core.invariants import structural_properties
    from petrinet_lab.core.model import PetriNet
    from petrinet_lab.core.pnml import save_pnml
    from petrinet_lab.core.reachability import ReachabilityGraph, build_reachability_graph
    from petrinet_lab.core.temporal import (
        TimePetriNet,
        build_state_class_graph,
        simulate_timed,
    )
except ImportError as error:
    raise SystemExit(
        "petrinet-lab is required: run with PYTHONPATH=/path/to/petrinet-lab/src"
    ) from error

MODELS_DIR = Path(__file__).resolve().parent / "models"
ROUND_SINK = "p_reported"
LANTERNS = ("hal", "john", "kyle")


def build_round_net(
    with_verifier: bool,
    bypass_approval: bool = False,
) -> PetriNet:
    """Workflow net of one round.

    with_verifier=True models a Deep round (Kilowog mandatory before the
    policy gate); False models a Patrol round. bypass_approval=True is a
    negative control where quarantine can fire straight from the
    proposal, with no human-minted token.
    """
    name = "round-deep" if with_verifier else "round-patrol"
    if bypass_approval:
        name += "-mutant-bypass"
    net = PetriNet(name)

    net.add_place("p_start", "round triggered", initial=1)
    net.add_place("p_swept", "deterministic sweep done")
    net.add_place("p_triaged", "LLM triage verdict (advisory)")
    net.add_place("p_policy", "policy gate (Book of Oa)")
    net.add_place("p_proposal", "action proposed")
    net.add_place("p_awaiting", "waiting for a human")
    net.add_place("p_approved", "human-minted approval token")
    net.add_place("p_quarantined", "reversible quarantine executed")
    net.add_place(ROUND_SINK, "round closed")
    if with_verifier:
        net.add_place("p_verified", "independent verification done")

    net.add_transition("t_sweep", "deterministic sweep (Lanterns)")
    net.add_transition("t_sweep_clean", "sweep clean: close round")
    net.add_transition("t_triage", "LLM triage (models propose)")
    net.add_transition("t_triage_benign", "triage: benign")
    net.add_transition("t_escalate", "triage: escalate")
    if with_verifier:
        net.add_transition("t_kilowog_confirm", "verifier confirms")
        net.add_transition("t_kilowog_dismiss", "verifier dismisses")
    net.add_transition("t_policy_allow", "policy allows (disposes)")
    net.add_transition("t_policy_veto", "policy vetoes")
    net.add_transition("t_request_approval", "propose action to the human")
    net.add_transition("t_human_mint_token", "human mints approval token")
    net.add_transition("t_human_deny", "human denies")
    net.add_transition("t_quarantine", "quarantine (reversible, audited)")
    net.add_transition("t_report", "close round after mutation")

    net.add_arc("p_start", "t_sweep")
    net.add_arc("t_sweep", "p_swept")
    net.add_arc("p_swept", "t_sweep_clean")
    net.add_arc("t_sweep_clean", ROUND_SINK)
    net.add_arc("p_swept", "t_triage")
    net.add_arc("t_triage", "p_triaged")
    net.add_arc("p_triaged", "t_triage_benign")
    net.add_arc("t_triage_benign", ROUND_SINK)
    net.add_arc("p_triaged", "t_escalate")
    if with_verifier:
        net.add_arc("t_escalate", "p_verified")
        net.add_arc("p_verified", "t_kilowog_confirm")
        net.add_arc("t_kilowog_confirm", "p_policy")
        net.add_arc("p_verified", "t_kilowog_dismiss")
        net.add_arc("t_kilowog_dismiss", ROUND_SINK)
    else:
        net.add_arc("t_escalate", "p_policy")
    net.add_arc("p_policy", "t_policy_allow")
    net.add_arc("t_policy_allow", "p_proposal")
    net.add_arc("p_policy", "t_policy_veto")
    net.add_arc("t_policy_veto", ROUND_SINK)
    net.add_arc("p_proposal", "t_request_approval")
    net.add_arc("t_request_approval", "p_awaiting")
    net.add_arc("p_awaiting", "t_human_mint_token")
    net.add_arc("t_human_mint_token", "p_approved")
    net.add_arc("p_awaiting", "t_human_deny")
    net.add_arc("t_human_deny", ROUND_SINK)
    net.add_arc("p_proposal" if bypass_approval else "p_approved", "t_quarantine")
    net.add_arc("t_quarantine", "p_quarantined")
    net.add_arc("p_quarantined", "t_report")
    net.add_arc("t_report", ROUND_SINK)
    return net


def build_emergency_net(drop_kyle_join: bool = False) -> PetriNet:
    """Emergency round: all Lanterns dispatched in parallel, join on all.

    drop_kyle_join=True is a negative control where the join no longer
    waits for one Lantern: the round can close with work still in flight.
    """
    name = "emergency-dispatch-mutant" if drop_kyle_join else "emergency-dispatch"
    net = PetriNet(name)
    net.add_place("e_start", "emergency raised", initial=1)
    for lantern in LANTERNS:
        net.add_place(f"e_flight_{lantern}", f"{lantern} in flight")
        net.add_place(f"e_back_{lantern}", f"{lantern} reported")
    net.add_place("e_joined", "all reports gathered")
    net.add_place("e_done", "emergency round closed")

    net.add_transition("e_dispatch", "dispatch all Lanterns in parallel")
    for lantern in LANTERNS:
        net.add_transition(f"e_{lantern}_back", f"{lantern} returns")
    net.add_transition("e_join", "join: wait for every Lantern")
    net.add_transition("e_report", "close emergency round")

    net.add_arc("e_start", "e_dispatch")
    for lantern in LANTERNS:
        net.add_arc("e_dispatch", f"e_flight_{lantern}")
        net.add_arc(f"e_flight_{lantern}", f"e_{lantern}_back")
        net.add_arc(f"e_{lantern}_back", f"e_back_{lantern}")
        if drop_kyle_join and lantern == "kyle":
            continue
        net.add_arc(f"e_back_{lantern}", "e_join")
    net.add_arc("e_join", "e_joined")
    net.add_arc("e_joined", "e_report")
    net.add_arc("e_report", "e_done")
    return net


def build_deadline_net() -> TimePetriNet:
    """Timed triage: if the LLM has not answered by t=30, the hard
    deadline fires and the round closes report-only (fail-safe)."""
    net = PetriNet("triage-deadline")
    net.add_place("d_request", "triage requested", initial=1)
    net.add_place("d_triaged", "LLM answered")
    net.add_place("d_timeout", "deadline expired")
    net.add_place("d_done", "round closed")

    net.add_transition("d_llm_triage", "LLM triage (window 0-30s)")
    net.add_transition("d_hard_deadline", "hard deadline (t=30s)")
    net.add_transition("d_finalize_triaged", "close with triage")
    net.add_transition("d_finalize_timeout", "close report-only")

    net.add_arc("d_request", "d_llm_triage")
    net.add_arc("d_llm_triage", "d_triaged")
    net.add_arc("d_request", "d_hard_deadline")
    net.add_arc("d_hard_deadline", "d_timeout")
    net.add_arc("d_triaged", "d_finalize_triaged")
    net.add_arc("d_finalize_triaged", "d_done")
    net.add_arc("d_timeout", "d_finalize_timeout")
    net.add_arc("d_finalize_timeout", "d_done")
    return TimePetriNet(net, {"d_llm_triage": (0, 30), "d_hard_deadline": (30, 30)})


def final_marking(net: PetriNet, sink: str) -> dict[str, int]:
    return {pid: 1 if pid == sink else 0 for pid in net.place_ids}


def options_to_complete(graph: ReachabilityGraph) -> bool:
    deadlocks = [
        state for state in range(len(graph.states)) if not graph.successor_edges(state)
    ]
    reverse: dict[int, list[int]] = {}
    for edge in graph.edges:
        reverse.setdefault(edge.target, []).append(edge.source)
    seen = set(deadlocks)
    queue = deque(deadlocks)
    while queue:
        state = queue.popleft()
        for predecessor in reverse.get(state, []):
            if predecessor not in seen:
                seen.add(predecessor)
                queue.append(predecessor)
    return len(seen) == len(graph.states)


def complete_sequences(graph: ReachabilityGraph) -> list[list[str]]:
    """Every firing sequence from the initial state to a deadlock."""
    sequences: list[list[str]] = []

    def walk(state: int, fired: list[str]) -> None:
        edges = graph.successor_edges(state)
        if not edges:
            sequences.append(fired)
            return
        for edge in edges:
            walk(edge.target, fired + [edge.transition])

    walk(0, [])
    return sequences


def approval_bypass_sequences(
    net: PetriNet,
    graph: ReachabilityGraph,
    mint: str = "t_human_mint_token",
    mutation: str = "t_quarantine",
) -> list[list[str]]:
    violations: list[list[str]] = []
    for sequence in complete_sequences(graph):
        if mutation not in sequence:
            continue
        if mint not in sequence or sequence.index(mint) > sequence.index(mutation):
            violations.append(sequence)
    return violations


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def check(self, label: str, passed: bool, detail: str = "") -> None:
        self.checks += 1
        suffix = f" ({detail})" if detail else ""
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{suffix}")
        if not passed:
            self.failures.append(label)


def analyse_round(report: Report, label: str, net: PetriNet) -> None:
    print(f"\n== {label} ==")
    summary = net.summary()
    report.check("workflow net (one source, one sink, all nodes on a path)",
                 bool(summary["workflow_net"]))
    properties = structural_properties(net)
    report.check("conservative (P-invariant covers every place)",
                 bool(properties["conservative"]),
                 f"{len(properties['p_invariants'])} minimal invariant(s)")
    graph = build_reachability_graph(net)
    bounds = graph.token_bounds()
    report.check("1-safe (no place above one token)",
                 all(value <= 1 for value in bounds.values()),
                 f"{len(graph.states)} markings, max token {max(bounds.values())}")
    deadlocks = graph.deadlock_markings()
    expected = final_marking(net, ROUND_SINK)
    report.check("proper completion (every deadlock is exactly the sink)",
                 len(deadlocks) == 1 and deadlocks[0] == expected,
                 f"{len(deadlocks)} deadlock(s)")
    report.check("option to complete (every marking reaches the sink)",
                 options_to_complete(graph))
    report.check("no dead transitions",
                 not graph.dead_transitions(),
                 ",".join(graph.dead_transitions()) or "all transitions fire")
    report.check("liveness: every transition reachable in some path",
                 all(graph.liveness_level(t) >= 2 for t in net.transition_ids))
    producers = set(net.input_transitions("p_approved"))
    consumers = set(net.output_transitions("p_approved"))
    report.check("approval token has a single producer (human) and consumer (mutation)",
                 producers == {"t_human_mint_token"} and consumers == {"t_quarantine"},
                 f"producers={sorted(producers)}, consumers={sorted(consumers)}")
    sequences = complete_sequences(graph)
    violations = approval_bypass_sequences(net, graph)
    exercised = sum(1 for sequence in sequences if "t_quarantine" in sequence)
    report.check("no mutation without a prior human-minted token",
                 not violations,
                 f"{len(sequences)} complete sequences, {exercised} with mutation")
    report.check("the guarded path is non-vacuous (mutation actually occurs)",
                 exercised > 0)
    save_pnml(net, MODELS_DIR / f"{net.name}.pnml")


def analyse_emergency(report: Report) -> None:
    print("\n== emergency-dispatch ==")
    net = build_emergency_net()
    graph = build_reachability_graph(net)
    sequences = complete_sequences(graph)
    expected = final_marking(net, "e_done")
    deadlocks = graph.deadlock_markings()
    join_inputs = set(net.preset("e_join"))
    required = {f"e_back_{lantern}" for lantern in LANTERNS}
    report.check("join waits for every Lantern",
                 join_inputs == required,
                 f"join preset={sorted(join_inputs)}")
    report.check("deadlock-free with proper completion",
                 len(deadlocks) == 1 and deadlocks[0] == expected,
                 f"{len(deadlocks)} deadlock(s)")
    report.check("all 6 return interleavings reach the same final marking",
                 len(sequences) == 6 and all(sequence.count("e_join") == 1 for sequence in sequences),
                 f"{len(sequences)} interleavings")
    save_pnml(net, MODELS_DIR / f"{net.name}.pnml")

    print("\n== negative control: emergency join without one Lantern ==")
    mutant = build_emergency_net(drop_kyle_join=True)
    mutant_graph = build_reachability_graph(mutant)
    mutant_deadlocks = mutant_graph.deadlock_markings()
    leftover = [marking for marking in mutant_deadlocks if marking != final_marking(mutant, "e_done")]
    report.check("completed-with-work-in-flight is detected",
                 bool(leftover),
                 f"{len(leftover)} incomplete final marking(s)")


def analyse_deadline(report: Report) -> None:
    print("\n== triage-deadline (timed) ==")
    timed = build_deadline_net()
    graph = build_state_class_graph(timed)
    report.check("no time-lock class (time always advances or something fires)",
                 not graph.time_lock_classes(),
                 f"{len(graph.classes)} state classes")
    final_key = tuple(1 if pid == "d_done" else 0 for pid in timed.net.place_ids)
    premature = [cls for cls in graph.deadlock_classes() if cls.marking != final_key]
    report.check("no deadlock before completion (only the closed round is terminal)",
                 not premature,
                 f"{len(graph.deadlock_classes())} terminal class(es)")
    report.check("LLM window is [0, 30]",
                 graph.firing_time_bounds("d_llm_triage") == (0, 30))
    report.check("hard deadline fires exactly at t=30",
                 graph.firing_time_bounds("d_hard_deadline") == (30, 30))
    place_index = {pid: i for i, pid in enumerate(timed.net.place_ids)}
    markings = graph.reachable_markings()
    triaged = any(marking[place_index["d_triaged"]] for marking in markings)
    timed_out = any(marking[place_index["d_timeout"]] for marking in markings)
    done = any(marking[place_index["d_done"]] for marking in markings)
    report.check("both outcomes reachable (triage and timeout) and every run closes",
                 triaged and timed_out and done)
    earliest = simulate_timed(timed, steps=4, policy="earliest")
    report.check("earliest-policy trace fires triage at t=0 then closes",
                 [event.transition for event in earliest] == ["d_llm_triage", "d_finalize_triaged"],
                 f"times={[float(event.time) for event in earliest]}")
    timeout_seed = next(
        (seed for seed in range(200)
         if any(event.transition == "d_hard_deadline" for event in simulate_timed(timed, steps=4, seed=seed))),
        None,
    )
    trace = simulate_timed(timed, steps=4, seed=timeout_seed) if timeout_seed is not None else []
    trace_detail = ", ".join(f"{event.transition}@{float(event.time)}" for event in trace)
    report.check("deadline path can actually fire in simulation",
                 timeout_seed is not None,
                 f"seed={timeout_seed}, trace=[{trace_detail}]" if trace else "")
    save_pnml(timed.net, MODELS_DIR / f"{timed.net.name}.pnml")


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    report = Report()

    analyse_round(report, "round-patrol", build_round_net(with_verifier=False))
    analyse_round(report, "round-deep", build_round_net(with_verifier=True))

    print("\n== negative control: approval bypass ==")
    mutant = build_round_net(with_verifier=True, bypass_approval=True)
    mutant_graph = build_reachability_graph(mutant)
    violations = approval_bypass_sequences(mutant, mutant_graph)
    report.check("mutation from proposal without a token is detected",
                 bool(violations),
                 f"{len(violations)} violating sequence(s)")

    analyse_emergency(report)
    analyse_deadline(report)

    print(f"\n{report.checks - len(report.failures)}/{report.checks} checks passed")
    for failure in report.failures:
        print(f"FAILED: {failure}")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
