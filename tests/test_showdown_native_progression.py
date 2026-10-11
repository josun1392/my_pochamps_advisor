"""Native action stepping preserves queue, RNG, callbacks and truth isolation."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_showdown_simulation import (
    simulate_detached_showdown, progress_native_showdown, resume_detached_showdown,
    evaluate_native_damage_rolls, evaluate_native_status_gate,
)
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, snapshot_from_state


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker:
        yield worker


def semantic_native(checkpoint):
    state = deepcopy(checkpoint["native_state"])
    meaningful = lambda line: bool(line) and line != "|" and not line.startswith("|t:|")
    for key in ("lastMoveLine", "sentLogPos"):
        state[key] = sum(meaningful(line) for line in state["log"][:state[key]])
    state["log"] = [line for line in state["log"] if meaningful(line)]
    return state


def progress(worker, checkpoint, *, snapshot=None, **kwargs):
    result = progress_native_showdown(runtime_snapshot=snapshot or fixture_snapshot(), checkpoint=checkpoint, bridge=worker, **kwargs)
    return result["scenarios"][0] if "scenarios" in result else result


@pytest.mark.parametrize("move,status,opponent", [
    ("Flamethrower", "", "move 1"), ("Air Slash", "", "move 2"),
    ("Fire Blast", "", "move 1"), ("Scale Shot", "", "move 2"),
    ("Rest", "", "move 2"), ("Flamethrower", "slp", "move 2"),
    ("Air Slash", "frz", "move 2"), ("Protect", "", "move 1"),
])
@pytest.mark.parametrize("item", [0, 1, 2, 3])
def test_native_stepping_and_full_execution_are_equivalent(worker, move, status, opponent, item):
    scenario = fixture_scenarios()[item]
    scenario["teams"]["self"][0]["moves"] = [move, "Protect"] if move != "Protect" else ["Protect", "Flamethrower"]
    if status:
        scenario["conditioning"] = [{"target": "self", "effect": "status", "id": status}]
    scenario["choices"] = {"self": "move 1", "opponent": opponent}
    snapshot = fixture_snapshot()
    original = deepcopy((snapshot, scenario))
    full = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)["scenarios"][0]
    assert full["status"] == "simulated", full
    checkpoint = full["root_checkpoint"]
    frozen = deepcopy(checkpoint)
    row = progress(worker, checkpoint, choices=scenario["choices"])
    assert row["status"] == "simulated", row
    assert len(row["native_progression"]["move_attempts"]) == 1
    assert "runAction" not in row["checkpoint"]["native_state"]
    assert checkpoint == frozen
    attempts = list(row["native_progression"]["move_attempts"])
    for _ in range(3):
        if row["native_progression"]["stopped_at"] != "paused_native_queue":
            break
        row = progress(worker, row["checkpoint"])
        assert row["status"] == "simulated", row
        assert len(row["native_progression"]["move_attempts"]) <= 1
        attempts.extend(row["native_progression"]["move_attempts"])
    assert row["native_progression"]["stopped_at"] in {"native_request", "battle_end"}
    assert semantic_native(row["checkpoint"]) == semantic_native(full["checkpoint"])
    assert row["after"] == full["after"]
    assert (snapshot, scenario) == original
    assert row["native_progression"]["interpretation"].endswith("not_exact_probability")


def test_inflight_queue_rejects_new_choices_and_conditional_root_queries(worker):
    scenario = fixture_scenarios()[1]
    root = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=[scenario], bridge=worker)["scenarios"][0]["root_checkpoint"]
    first = progress(worker, root, choices=scenario["choices"])
    assert first["native_progression"]["move_attempts"][0]["side"] == "opponent"
    queued = first["checkpoint"]
    assert queued["native_state"]["midTurn"] and queued["native_state"]["queue"]
    assert progress(worker, queued, choices=scenario["choices"])["reason"] == "native_progression_phase_mismatch"
    assert progress(worker, root)["reason"] == "native_progression_phase_mismatch"
    resumed = resume_detached_showdown(runtime_snapshot=fixture_snapshot(), checkpoint=queued, choices={"self": "", "opponent": ""}, bridge=worker)
    assert resumed["scenarios"][0]["reason"] == "native_choice_boundary_required"
    for query, kwargs in ((evaluate_native_damage_rolls, {"critical": False}), (evaluate_native_status_gate, {})):
        result = query(runtime_snapshot=fixture_snapshot(), checkpoint=queued, side="self", move="flamethrower", bridge=worker, **kwargs)
        assert result["scenarios"][0]["reason"] == "native_move_boundary_required"
    drained = progress(worker, queued, stop_after_move=False)
    full = resume_detached_showdown(runtime_snapshot=fixture_snapshot(), checkpoint=root, choices=scenario["choices"], bridge=worker)["scenarios"][0]
    assert semantic_native(drained["checkpoint"]) == semantic_native(full["checkpoint"])


def test_pivot_keeps_request_and_pending_opponent_action(worker):
    scenario = fixture_scenarios()[1]
    scenario["teams"]["self"][0], scenario["teams"]["self"][2] = scenario["teams"]["self"][2], scenario["teams"]["self"][0]
    scenario["teams"]["self"][0]["moves"] = ["Volt Switch", "Protect"]
    scenario["choices"] = {"self": "move 1", "opponent": "move 2"}
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][0] = {"pokemon_id": "rotom-wash", "current_hp": 127, "max_hp": 127, "fainted": False}
    snapshot = snapshot_from_state(state)
    full = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)["scenarios"][0]
    assert full["status"] == "simulated", full
    row = progress(worker, full["root_checkpoint"], snapshot=snapshot, choices=scenario["choices"])
    assert row["native_progression"]["stopped_at"] == "native_request"
    assert row["after"]["decision_phase"]["requesting_sides"] == ["self"]
    assert semantic_native(row["checkpoint"]) == semantic_native(full["checkpoint"])
    choice = {"self": "switch slot:1", "opponent": ""}
    switched = progress(worker, row["checkpoint"], snapshot=snapshot, choices=choice)
    assert switched["native_progression"]["move_attempts"] == [{"side": "opponent", "slot_index": 0, "queued_move": "swordsdance"}]
    assert switched["after"]["sides"]["self"]["pokemon"][0]["species"] == "garchomp"
    finished = progress(worker, switched["checkpoint"], snapshot=snapshot, stop_after_move=False)
    direct = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=full["checkpoint"], choices=choice, bridge=worker)["scenarios"][0]
    assert semantic_native(finished["checkpoint"]) == semantic_native(direct["checkpoint"])


def test_manual_switch_runs_native_entry_callbacks_before_next_move(worker):
    scenario = fixture_scenarios()[1]
    choice = {"self": "switch slot:1", "opponent": "move 1"}
    scenario["choices"] = choice
    full = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=[scenario], bridge=worker)["scenarios"][0]
    row = progress(worker, full["root_checkpoint"], choices=choice)
    assert row["native_progression"]["move_attempts"][0]["side"] == "opponent"
    active = row["after"]["sides"]["self"]["pokemon"][0]
    assert active["species"] == "garchomp" and active["hp"] < active["max_hp"]
    assert any("Rough Skin" in event for event in row["events"])
    finished = progress(worker, row["checkpoint"], stop_after_move=False)
    assert semantic_native(finished["checkpoint"]) == semantic_native(full["checkpoint"])


def test_progression_rejects_stale_and_tampered_checkpoint(worker):
    scenario = fixture_scenarios()[1]
    root = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=[scenario], bridge=worker)["scenarios"][0]["root_checkpoint"]
    assert progress_native_showdown(runtime_snapshot=fixture_snapshot(hp=100), checkpoint=root, choices=scenario["choices"], bridge=worker)["status"] == "rejected"
    root["native_state"]["queue"] = []
    root["native_state"]["turn"] += 1
    assert progress(worker, root, choices=scenario["choices"])["status"] == "rejected"
