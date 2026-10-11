"""Offline native-outcome consumer proof, parity, rollback and latency measurement."""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from advisor.showdown_worker import ShowdownWorker
from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_showdown_simulation import simulate_detached_showdown
from llm.advisor_showdown_outcome_evidence import build_native_selected_action_outcome
from llm.advisor_runtime_d0_direct_heal_execution_authority import freeze_runtime_d0_direct_heal_execution_authority
from llm.advisor_detached_selected_action_execution_result import materialize_detached_selected_action_execution_result
from scripts.verify_showdown_integration import fixture_scenarios, snapshot_from_state


def consumer_fixture(bridge, *, hp=100, hp_points=2, status="", seed=None, opponent="move 2", ability="Marvel Scale"):
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
    metadata = {"move_id": "recover", "category": "status", "target": "self", "priority": 0, "accuracy": None, "power": None}
    action = {"action_id": "attack:recover", "action_type": "attack", "identity": "recover",
        "move_metadata_authority": {"status": "resolved", "metadata": metadata}}
    row = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=bridge)["scenarios"][0]
    assert row["status"] == "simulated", row
    return {"strategy_d0": d0, "runtime_snapshot": snapshot, "action": action, "actor": d0["active_owners"]["self"],
        "target": d0["active_owners"]["opponent"], "move_metadata": metadata,
        "checkpoint": row["root_checkpoint"], "bridge": bridge, "choices": scenario["choices"]}


def execute(args, evidence=None):
    authority = freeze_runtime_d0_direct_heal_execution_authority(**{k: args[k] for k in ("strategy_d0", "runtime_snapshot", "action", "actor")})
    return materialize_detached_selected_action_execution_result(**{k: args[k] for k in
        ("strategy_d0", "runtime_snapshot", "action", "actor", "target", "move_metadata")},
        family_authorities={"direct_heal_execution_authority": authority, "native_direct_heal_outcome": evidence})


def verify(checkout, iterations=30):
    start = perf_counter()
    with ShowdownWorker(checkout) as bridge:
        args = consumer_fixture(bridge)
        cold = (perf_counter() - start) * 1000
        source = deepcopy({k: v for k, v in args.items() if k != "bridge"})
        legacy = execute(args)
        timings, results = [], []
        for _ in range(iterations):
            start = perf_counter()
            evidence = build_native_selected_action_outcome(**args)
            result = execute(args, evidence)
            timings.append((perf_counter() - start) * 1000)
            assert result["status"] == "resolved", result
            assert result["paths"][0]["post_action_runtime_snapshot"] == legacy["paths"][0]["post_action_runtime_snapshot"]
            results.append(evidence["native_outcome"]["after"])
        assert all(value == results[0] for value in results)
        assert {k: v for k, v in args.items() if k != "bridge"} == source
        assert execute(args) == legacy  # Reversible backend seam.
        process = bridge._process
    assert process.poll() is not None
    return {"engine_commit": SHOWDOWN_COMMIT, "format_id": FORMAT_ID, "status": "verified",
        "evidence_class": evidence["evidence_class"], "probability_scope": evidence["probability_scope"],
        "native_proof": evidence["native_outcome"]["determinism_proof"],
        "heal": result["paths"][0]["action_consequence"]["heal"],
        "repeated_outputs_equal": True, "runtime_unchanged": True, "rollback_equal": True, "worker_closed": True,
        "performance_ms": {"worker_and_fixture_first_call": cold, "iterations": iterations,
            "native_proof_and_compatible_consumer_p50": statistics.median(timings),
            "native_proof_and_compatible_consumer_p95": sorted(timings)[max(0, int(.95 * len(timings)) - 1)]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--showdown-checkout", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 1000:
        parser.error("iterations must be between 1 and 1000")
    print(json.dumps(verify(args.showdown_checkout, args.iterations), ensure_ascii=False, indent=2))
