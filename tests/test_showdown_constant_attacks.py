"""Native fixed damage proves whole attempts without enumerating custom mechanics."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_showdown_simulation import simulate_detached_showdown, progress_native_showdown
from llm.advisor_showdown_outcome_evidence import build_native_selected_action_outcome
from llm.advisor_detached_selected_action_execution_result import materialize_detached_selected_action_execution_result
from llm.advisor_champions_gated_selected_action_execution import execute_gated_selected_action
from scripts.verify_showdown_integration import fixture_scenarios, snapshot_from_state


@pytest.fixture(scope="module")
def worker():
    if not os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT"):
        pytest.skip("external pinned engine required")
    with ShowdownWorker(os.environ["POKEADVICE_SHOWDOWN_CHECKOUT"]) as bridge:
        yield bridge


def attack_inputs(worker, hp=147, move="Night Shade", seed=None):
    scenario = fixture_scenarios()[1]
    scenario["teams"]["opponent"][0]["moves"].append("X-Scissor")
    scenario["teams"]["self"][-1] = deepcopy(scenario["teams"]["self"][0])
    toss = move == "Seismic Toss"
    species, ability, maximum = ("Machamp", "No Guard", 167) if toss else ("Gengar", "Cursed Body", 137)
    if toss:
        scenario["teams"]["opponent"][0]["evs"]["spe"] = 31  # Distinct native speeds; no unproven tie draw.
    scenario["teams"]["self"][0] = {"species": species, "ability": ability, "level": 50,
        "moves": [move, "Protect"], "nature": "Timid", "evs": {"spa": 32, "spe": 32, "hp": 2}}
    scenario["choices"] = {"self": "move 1", "opponent": "move 2"}
    scenario["seed"] = seed or [1, 2, 3, 4]
    state = create_unknown_bootstrap_battle_state("native-attack-proof", species.lower(), "scizor",
        battle_format={"battle_format": "singles", "source": "user_confirmed_battle_format"})["state"]
    state["self_side"]["pokemon"][0].update(current_hp=maximum, max_hp=maximum, fainted=False)
    state["opponent_side"]["pokemon"][0].update(current_hp=hp, max_hp=147, fainted=False)
    snapshot = snapshot_from_state(state)
    owner = {"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": species.lower()}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    move_id = move.lower().replace(" ", "-")
    metadata = {"move_id": move_id, "category": "physical" if toss else "special", "target": "selected-pokemon", "priority": 0, "accuracy": 100, "damage": "level"}
    action = {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id,
        "move_metadata_authority": {"status": "resolved", "metadata": metadata}}
    row = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)["scenarios"][0]
    assert row["status"] == "simulated", row
    return {"strategy_d0": d0, "runtime_snapshot": snapshot, "action": action, "actor": d0["active_owners"]["self"],
        "target": d0["active_owners"]["opponent"], "move_metadata": metadata, "checkpoint": row["root_checkpoint"],
        "bridge": worker, "choices": scenario["choices"]}, row


@pytest.mark.parametrize("hp", [147, 50, 40, 1])
@pytest.mark.parametrize("seed", [[1, 2, 3, 4], [50, 11, 4, 8]])
def test_native_fixed_damage_faint_and_pending_queue_semantics(worker, hp, seed):
    args, full = attack_inputs(worker, hp, seed=seed)
    original = deepcopy(args["runtime_snapshot"])
    result = build_native_selected_action_outcome(**args)
    assert result["status"] == "resolved", result
    assert result["probability_mass"] == {"numerator": 1, "denominator": 1}
    row = result["native_outcome"]
    assert row["after"]["sides"]["opponent"]["pokemon"][0]["hp"] == max(0, hp - 50)
    assert row["determinism_proof"]["constant_draws"] == [{"kind": "constant_bernoulli", "numerator": 100, "denominator": 100}]
    drained = progress_native_showdown(runtime_snapshot=args["runtime_snapshot"], checkpoint=row["checkpoint"], bridge=worker, stop_after_move=False)["scenarios"][0]
    assert drained["after"] == full["after"]
    if hp <= 50:
        assert drained["after"]["request_state"] == "switch"
        assert not any(line.startswith("|move|p2") for line in drained["events"])
        assert drained["after"]["sides"]["opponent"]["pokemon"][0]["moves"][1]["pp"] == row["before"]["sides"]["opponent"]["pokemon"][0]["moves"][1]["pp"]
    assert args["runtime_snapshot"] == original


@pytest.mark.parametrize("hp", [147, 50, 40, 1])
@pytest.mark.parametrize("move", ["Night Shade", "Seismic Toss"])
def test_selected_and_gated_fixed_damage_consumers_use_native_post_hp(worker, hp, move):
    args, _ = attack_inputs(worker, hp, move)
    source = deepcopy(args["runtime_snapshot"])
    evidence = build_native_selected_action_outcome(**args)
    result = materialize_detached_selected_action_execution_result(**{k: args[k] for k in
        ("strategy_d0", "runtime_snapshot", "action", "actor", "target", "move_metadata")},
        family_authorities={"native_attack_outcome": evidence})
    assert result["status"] == "resolved", result
    assert result["execution_family"] == "native_fixed_damage_attempt"
    assert result["paths"][0]["post_action_runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]["current_hp"] == max(0, hp - 50)
    assert result["paths"][0]["action_consequence"]["native_outcome_evidence"] == evidence
    gated = execute_gated_selected_action(**{k: args[k] for k in
        ("strategy_d0", "runtime_snapshot", "action", "actor", "target")}, metadata_authority=args["action"]["move_metadata_authority"],
        extension_authorities={"native_attack_outcomes": {args["action"]["action_id"]: evidence}})
    assert gated["status"] == "resolved", gated
    assert gated["paths"][0]["final_hp"] == {"self": args["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["current_hp"], "opponent": max(0, hp - 50)}
    assert args["runtime_snapshot"] == source
    if hp <= 50:
        projected = result["paths"][0]["post_action_runtime_snapshot"]["state"]
        assert projected["opponent_side"]["active_slot_index"] == 0
        assert projected["opponent_side"]["pokemon"][0]["fainted"] is True
        assert evidence["native_outcome"]["after"]["sides"]["opponent"]["pokemon"][0]["active"] is False


def test_seeded_attack_cannot_supply_selected_exact_paths(worker):
    args, _ = attack_inputs(worker)
    evidence = build_native_selected_action_outcome(**args, require_deterministic=False)
    result = materialize_detached_selected_action_execution_result(**{k: args[k] for k in
        ("strategy_d0", "runtime_snapshot", "action", "actor", "target", "move_metadata")},
        family_authorities={"native_attack_outcome": evidence})
    assert result["status"] == "rejected" and result["reason"] == "native_attack_requires_conditional_exact"


def test_native_set_knowledge_remains_hypothetical_in_compatible_hp_view(worker):
    args, _ = attack_inputs(worker)
    native = build_native_selected_action_outcome(**args)
    result = materialize_detached_selected_action_execution_result(**{k: args[k] for k in
        ("strategy_d0", "runtime_snapshot", "action", "actor", "target", "move_metadata")}, family_authorities={"native_attack_outcome": native})
    post = result["paths"][0]["post_action_runtime_snapshot"]["state"]
    for side in ("self", "opponent"):
        original = args["runtime_snapshot"]["state"][f"{side}_side"]["pokemon"][0]
        for key in ("known_item", "current_ability", "condition", "current_type"):
            assert post[f"{side}_side"]["pokemon"][0][key] == original[key]


def test_known_pp_record_keeps_its_compatible_consumer(worker):
    args, full = attack_inputs(worker)
    state = args["runtime_snapshot"]["state"]
    pokemon = state["opponent_side"]["pokemon"][0]
    native_moves = full["before"]["sides"]["opponent"]["pokemon"][0]["moves"]
    moves = ["bullet-punch", "swords-dance", "protect", "x-scissor"]
    pokemon["known_move_ids"] = moves
    pokemon["current_opponent_response_set"] = {"moveset_completeness": "complete", "move_ids": moves,
        "provenance": {"event_kind": "current_opponent_response_set_observed", "trust": "user_confirmed_observation", "turn_number": 1, "source_sequence": 1},
        "move_pp_slots": [{"slot_index": i, "move_id": move, "current_pp": native_moves[i]["pp"], "max_pp": native_moves[i]["max_pp"]} for i, move in enumerate(moves)]}
    args["runtime_snapshot"] = snapshot_from_state(state)
    args["strategy_d0"] = freeze_runtime_strategy_d0(runtime_snapshot=args["runtime_snapshot"], decision_owner=args["actor"])
    cp = args["checkpoint"]
    scenario = {**cp["model_definition"], "scenario_id": cp["scenario_id"], "assumptions": cp["assumptions"],
        "seed": [1, 2, 3, 4], "history": [], "choices": args["choices"]}
    response = simulate_detached_showdown(runtime_snapshot=args["runtime_snapshot"], scenarios=[scenario], bridge=worker)
    assert response["status"] == "simulated", response
    row = response["scenarios"][0]
    args["checkpoint"] = row["root_checkpoint"]
    native = build_native_selected_action_outcome(**args)
    assert native["status"] == "resolved", native
    result = materialize_detached_selected_action_execution_result(**{k: args[k] for k in
        ("strategy_d0", "runtime_snapshot", "action", "actor", "target", "move_metadata")}, family_authorities={"native_attack_outcome": native})
    assert result["status"] == "unsupported" and result["reason"] == "native_attack_known_pp_projection_unsupported"
