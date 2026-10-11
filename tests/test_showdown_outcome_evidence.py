"""Exact native attempt proofs are conditional, never promoted seeded samples."""
from copy import deepcopy
import os
import pytest

from advisor.showdown_worker import ShowdownWorker
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_showdown_simulation import simulate_detached_showdown, progress_native_showdown
from llm.advisor_showdown_outcome_evidence import (
    build_native_selected_action_outcome, validate_native_selected_action_outcome, evidence_fingerprint,
)
from llm.advisor_detached_selected_action_execution_result import _base
from llm.advisor_detached_selected_action_execution_result import materialize_detached_selected_action_execution_result
from llm.advisor_runtime_d0_direct_heal_execution_authority import freeze_runtime_d0_direct_heal_execution_authority
from llm.advisor_champions_gated_selected_action_execution import execute_gated_selected_action
from scripts.verify_showdown_integration import fixture_scenarios, snapshot_from_state


@pytest.fixture(scope="module")
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as bridge:
        yield bridge


def inputs(worker, *, hp=100, hp_points=2, status="", ability="Marvel Scale", seed=None, opponent="move 2"):
    scenario = fixture_scenarios()[1]
    scenario["teams"]["self"][0] = {"species": "Milotic", "ability": ability, "level": 50,
        "moves": ["Recover", "Protect"], "nature": "Timid", "evs": {"spa": 32, "spe": 32, "hp": hp_points}}
    scenario["seed"] = seed or [1, 2, 3, 4]
    scenario["choices"] = {"self": "move 1", "opponent": opponent}
    if status:
        scenario["conditioning"] = [{"target": "self", "effect": "status", "id": status}]
    state = create_unknown_bootstrap_battle_state("native-outcome-proof", "milotic", "scizor",
        battle_format={"battle_format": "singles", "source": "user_confirmed_battle_format"})["state"]
    state["self_side"]["pokemon"][0].update(current_hp=hp, max_hp=170 + hp_points, fainted=False)
    state["opponent_side"]["pokemon"][0].update(current_hp=147, max_hp=147, fainted=False)
    snapshot = snapshot_from_state(state)
    owner = {"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": "milotic"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    assert d0["status"] == "resolved", d0
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    metadata = {"move_id": "recover", "category": "status", "target": "self", "priority": 0, "accuracy": None, "power": None}
    action = {"action_id": "attack:recover", "action_type": "attack", "identity": "recover",
              "move_metadata_authority": {"status": "resolved", "metadata": metadata}}
    row = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)["scenarios"][0]
    assert row["status"] == "simulated", row
    return {"strategy_d0": d0, "runtime_snapshot": snapshot, "action": action, "actor": actor,
            "target": target, "move_metadata": metadata, "checkpoint": row["root_checkpoint"],
            "bridge": worker, "choices": scenario["choices"]}


def test_constant_rng_is_complete_only_for_one_conditional_attempt(worker):
    for seed in ([1, 2, 3, 4], [50, 1, 8, 9], [255, 11, 2, 6]):
        args = inputs(worker, seed=seed)
        before = deepcopy({k: v for k, v in args.items() if k != "bridge"})
        evidence = build_native_selected_action_outcome(**args)
        assert evidence["status"] == "resolved", evidence
        assert evidence["evidence_class"] == "native_conditional_exact"
        assert evidence["probability_mass"] == {"numerator": 1, "denominator": 1}
        assert len(evidence["branches"]) == 1
        row = evidence["native_outcome"]
        assert row["after"]["sides"]["self"]["pokemon"][0]["hp"] == 172
        assert row["determinism_proof"]["stochastic_draws"] == 0
        assert row["native_progression"]["stopped_at"] == "paused_native_queue"
        assert row["after"]["decision_phase"]["queued_actions"]
        assert evidence["hypothetical_provenance"]["interpretation"].endswith("never_observed_truth")
        assert {k: v for k, v in args.items() if k != "bridge"} == before
        drained = progress_native_showdown(runtime_snapshot=args["runtime_snapshot"], checkpoint=row["checkpoint"],
            bridge=worker, stop_after_move=False)
        assert drained["scenarios"][0]["status"] == "simulated"


def test_stochastic_gate_does_not_supply_partial_exact_mass(worker):
    evidence = build_native_selected_action_outcome(**inputs(worker, status="frz"))
    assert evidence["status"] == "unsupported", evidence
    assert evidence["reason"] == "native_stochastic_rng_required"
    assert "probability_mass" not in evidence and "branches" not in evidence


def test_native_action_order_identity_rejects_other_first_action(worker):
    evidence = build_native_selected_action_outcome(**inputs(worker, opponent="move 1"))
    assert evidence["status"] == "unsupported"  # Bullet Punch requires unproven native RNG first.
    args = inputs(worker, status="par")
    evidence = build_native_selected_action_outcome(**args)
    assert evidence["status"] == "rejected"
    assert evidence["reason"] == "native_outcome_selected_action_phase_mismatch"


def test_seeded_success_cannot_be_reclassified_as_exact(worker):
    args = inputs(worker)
    evidence = build_native_selected_action_outcome(**args, require_deterministic=False)
    assert evidence["status"] == "resolved", evidence
    assert evidence["evidence_class"] == "native_seeded_execution"
    assert "probability_mass" not in evidence
    base = _base(args["strategy_d0"], args["runtime_snapshot"], args["action"], args["actor"], args["target"], args["move_metadata"])
    for change in ({"evidence_class": "native_conditional_exact"},
                   {"probability_mass": {"numerator": 1, "denominator": 1}},
                   {"evidence_class": "legacy_guaranteed_exact"}):
        bad = {**deepcopy(evidence), **change}
        bad["evidence_fingerprint"] = evidence_fingerprint(bad)
        assert validate_native_selected_action_outcome(evidence=bad, base=base, runtime_snapshot=args["runtime_snapshot"])["status"] == "rejected"


@pytest.mark.parametrize("kind", ["mass", "branch", "checkpoint", "session", "phase", "hypothesis"])
def test_exact_evidence_rejects_incomplete_or_wrong_source_even_with_new_digest(worker, kind):
    args = inputs(worker)
    evidence = build_native_selected_action_outcome(**args)
    assert evidence["status"] == "resolved", evidence
    if kind == "mass": evidence["probability_mass"]["numerator"] = 0
    elif kind == "branch": evidence["branches"] = []
    elif kind == "checkpoint": evidence["native_outcome"]["checkpoint"]["native_state"]["turn"] += 1
    elif kind == "session": evidence["session_id"] = "another-session"
    elif kind == "phase": evidence["source_native_phase"]["turn"] += 1
    else: evidence["hypothetical_provenance"]["assumptions"] = ["unbound hypothesis"]
    evidence["evidence_fingerprint"] = evidence_fingerprint(evidence)
    base = _base(args["strategy_d0"], args["runtime_snapshot"], args["action"], args["actor"], args["target"], args["move_metadata"])
    assert validate_native_selected_action_outcome(evidence=evidence, base=base, runtime_snapshot=args["runtime_snapshot"])["status"] == "rejected"


def execute(args, native=None):
    authority = freeze_runtime_d0_direct_heal_execution_authority(**{k: args[k] for k in ("strategy_d0", "runtime_snapshot", "action", "actor")})
    return materialize_detached_selected_action_execution_result(**{k: args[k] for k in
        ("strategy_d0", "runtime_snapshot", "action", "actor", "target", "move_metadata")},
        family_authorities={"direct_heal_execution_authority": authority, "native_direct_heal_outcome": native})


@pytest.mark.parametrize("hp,points", [(1, 1), (50, 1), (100, 1), (170, 1), (171, 1), (1, 2), (100, 2), (172, 2)])
def test_native_heal_replaces_only_hp_calculation_with_legacy_projection_parity(worker, hp, points):
    args = inputs(worker, hp=hp, hp_points=points)
    original = deepcopy(args["runtime_snapshot"])
    native = build_native_selected_action_outcome(**args)
    result = execute(args, native)
    legacy = execute(args)
    assert result["status"] == "resolved", result
    assert result["evidence_class"] == "native_conditional_exact"
    assert result["paths"][0]["post_action_runtime_snapshot"] == legacy["paths"][0]["post_action_runtime_snapshot"]
    assert result["paths"][0]["probability"] == legacy["paths"][0]["probability"]
    consequence = result["paths"][0]["action_consequence"]
    assert consequence["schema_version"] == "showdown-compatible-direct-heal-v1"
    assert "nominal_heal" not in consequence["heal"]  # No duplicate half-HP formula.
    assert consequence["native_outcome_evidence"] == native
    assert args["runtime_snapshot"] == original
    assert "evidence_class" not in legacy


def test_gated_consumer_selects_opt_in_native_evidence_by_action_id(worker):
    args = inputs(worker)
    native = build_native_selected_action_outcome(**args)
    authority = freeze_runtime_d0_direct_heal_execution_authority(**{k: args[k] for k in ("strategy_d0", "runtime_snapshot", "action", "actor")})
    result = execute_gated_selected_action(**{k: args[k] for k in ("strategy_d0", "runtime_snapshot", "action", "actor", "target")},
        metadata_authority=args["action"]["move_metadata_authority"],
        extension_authorities={"direct_heal_execution_authorities": {args["action"]["action_id"]: authority},
            "native_direct_heal_outcomes": {args["action"]["action_id"]: native}})
    assert result["status"] == "resolved", result
    assert result["execution_result"]["evidence_class"] == "native_conditional_exact"
    assert result["paths"][0]["final_hp"]["self"] == 172


def test_unsupported_stochastic_proof_keeps_compatible_legacy_consumer(worker):
    args = inputs(worker, status="frz")
    native = build_native_selected_action_outcome(**args)
    result = execute(args, native)
    legacy = execute(args)
    assert result["status"] == "resolved", result
    assert result["paths"] == legacy["paths"]
    assert result["native_fallback_reason"] == "native_stochastic_rng_required"
    # The gate consumer still owns whether this legacy action is permitted.
    assert "evidence_class" not in result


def test_native_cancellation_or_seeded_execution_never_becomes_healing(worker):
    args = inputs(worker, status="slp")
    native = build_native_selected_action_outcome(**args)
    assert native["status"] == "resolved", native
    assert execute(args, native)["reason"] == "native_direct_heal_action_was_cancelled"
    args = inputs(worker)
    native = build_native_selected_action_outcome(**args, require_deterministic=False)
    assert execute(args, native)["reason"] == "native_direct_heal_requires_conditional_exact"


def test_native_proof_is_not_reused_after_a_detached_gate_transition(worker):
    args = inputs(worker)
    native = build_native_selected_action_outcome(**args)
    args["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["current_hp"] = 90
    args["runtime_snapshot"] = snapshot_from_state(args["runtime_snapshot"]["state"])
    args["strategy_d0"] = freeze_runtime_strategy_d0(runtime_snapshot=args["runtime_snapshot"], decision_owner=args["actor"])
    assert execute(args, native)["reason"] == "native_outcome_consumer_binding_mismatch"


def test_summary_cannot_contradict_native_checkpoint(worker):
    args = inputs(worker)
    native = build_native_selected_action_outcome(**args)
    native["native_outcome"]["after"]["sides"]["self"]["pokemon"][0]["hp"] = 160
    native["evidence_fingerprint"] = evidence_fingerprint(native)
    assert execute(args, native)["reason"] == "native_direct_heal_summary_checkpoint_contradiction"
