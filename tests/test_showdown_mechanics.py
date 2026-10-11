"""Native interactions exercised through the actual Python simulation bridge."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_showdown_simulation import simulate_detached_showdown, resume_detached_showdown
from llm.advisor_showdown_simulation import reconcile_detached_showdown
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, snapshot_from_state
from scripts.compare_showdown_legacy import compare


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker: yield worker


def run(worker, scenario, snapshot=None):
    result = simulate_detached_showdown(runtime_snapshot=snapshot or fixture_snapshot(), scenarios=[scenario], bridge=worker)
    assert result["status"] == "simulated", result
    return result["scenarios"][0]


def test_mc_representative_conditional_roll_parity(worker):
    report = compare(worker.checkout)
    assert report["all_matched"], report
    assert len(report["cases"]) == 12


def test_native_stealth_rock_switch_damage_and_toxic_spikes(worker):
    scenario = fixture_scenarios()[1]
    scenario["conditioning"] = [{"target": "self", "effect": "side", "id": "stealthrock"}, {"target": "self", "effect": "side", "id": "toxicspikes"}]
    scenario["choices"] = {"self": "switch slot:1", "opponent": "move 2"}
    row = run(worker, scenario)
    incoming = row["after"]["sides"]["self"]["pokemon"][0]
    assert incoming["species"] == "garchomp"
    assert incoming["hp"] == 151  # native Rock entry damage then poison residual
    assert incoming["status"] == "psn"
    assert any("Stealth Rock" in line for line in row["events"])


def test_native_levitate_ground_immunity_after_switch(worker):
    state = fixture_snapshot()["state"]
    state["opponent_side"]["pokemon"][1] = {"pokemon_id": "garchomp", "current_hp": 185, "max_hp": 185, "fainted": False}
    state["opponent_side"]["active_slot_index"] = 1
    scenario = fixture_scenarios()[1]
    scenario["preview"]["opponent"] = [2, 1, 3]
    scenario["choices"] = {"self": "switch slot:2", "opponent": "move 1"}
    row = run(worker, scenario, snapshot_from_state(state))
    assert row["after"]["sides"]["self"]["pokemon"][0]["hp"] == 127
    assert any("-immune" in line for line in row["events"])


def test_native_mega_evolution_and_checkpoint_restore(worker):
    scenario = fixture_scenarios()[1]
    scenario["teams"]["self"][0]["item"] = "Charizardite X"
    scenario["choices"] = {"self": "move 2 mega", "opponent": "move 2"}
    row = run(worker, scenario)
    own = row["after"]["sides"]["self"]["pokemon"][0]
    assert own["species"] == "charizardmegax"
    assert own["ability"] == "toughclaws"
    assert own["types"] == ["Fire", "Dragon"]
    resumed = resume_detached_showdown(runtime_snapshot=fixture_snapshot(), checkpoint=row["checkpoint"], choices={"self": "move 3", "opponent": "move 2"}, bridge=worker)
    assert resumed["scenarios"][0]["before"] == row["after"]
    current = fixture_snapshot()["state"]
    current["self_side"]["pokemon"][0].update(current_ability="tough-claws", current_ability_provenance={
        "event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 2})
    scenario["choices"] = {"self": "move 3", "opponent": "move 2"}
    reconciled = reconcile_detached_showdown(runtime_snapshot=snapshot_from_state(current), checkpoint=row["checkpoint"],
        scenario=scenario, observed_history=[], bridge=worker)
    assert reconciled["status"] == "simulated", reconciled
    assert reconciled["scenarios"][0]["before"]["sides"]["self"]["pokemon"][0]["species"] == "charizardmegax"


def test_native_pivot_requires_explicit_human_replacement(worker):
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][0] = {"pokemon_id": "rotom-wash", "current_hp": 127, "max_hp": 127, "fainted": False}
    scenario = fixture_scenarios()[1]
    scenario["teams"]["self"][0], scenario["teams"]["self"][2] = scenario["teams"]["self"][2], scenario["teams"]["self"][0]
    scenario["teams"]["self"][0]["moves"] = ["Volt Switch", "Hydro Pump", "Protect"]
    scenario["choices"] = {"self": "move 1", "opponent": "move 2"}
    snapshot = snapshot_from_state(state)
    row = run(worker, scenario, snapshot)
    assert row["after"]["request_state"] == "switch"
    assert row["after"]["sides"]["self"]["request"]["forceSwitch"] == [True]
    continued = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=row["checkpoint"], choices={"self": "switch slot:1", "opponent": ""}, bridge=worker)
    assert continued["status"] == "simulated"
    assert continued["scenarios"][0]["after"]["turn"] == 2


@pytest.mark.parametrize("item", ["Choice Band", "Choice Specs"])
def test_native_mc_validator_excludes_items_not_available_in_champions(worker, item):
    scenario = fixture_scenarios()[1]
    scenario["teams"]["self"][0]["item"] = item
    result = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=[scenario], bridge=worker)
    assert result["scenarios"][0]["reason"] == "invalid_mc_team"


def test_early_bird_sleep_duration_three_differs_from_legacy_exact_gate(worker):
    from llm.advisor_champions_sleep_freeze_action_gate import resolve_gate_branches, classify_status_move
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][0] = {"pokemon_id": "kangaskhan", "current_hp": 182, "max_hp": 182, "fainted": False}
    scenario = fixture_scenarios()[1]
    scenario["teams"]["self"][0] = {"species": "Kangaskhan", "ability": "Early Bird", "nature": "Adamant", "level": 50,
        "moves": ["Crunch", "Protect"], "evs": {"atk": 32, "spe": 32, "hp": 2}}
    scenario["conditioning"] = [{"target": "self", "effect": "status", "id": "slp"}]
    scenario["choices"] = {"self": "move 1", "opponent": "move 2"}
    native = None
    for n in range(16):
        scenario["seed"] = [7, 11, 17, n]
        row = run(worker, scenario, snapshot_from_state(state))
        if row["root_checkpoint"]["native_state"]["sides"][0]["pokemon"][0]["statusState"]["startTime"] == 3:
            native = row
            break
    assert native is not None
    assert native["after"]["sides"]["self"]["pokemon"][0]["status"] == "slp"
    legacy = resolve_gate_branches(condition="sleep", progression={"prior_attempts": 0, "sleep_duration": 3, "origin_id": "proof"},
        ability={"status": "resolved", "early_bird_active": True}, move_authority=classify_status_move("crunch"))
    assert len(legacy) == 1 and legacy[0]["kind"] == "wakes_and_executes"
    # This discrepancy is deliberately not converted into an exact ranking fact.


def test_actual_faint_reconciles_at_native_replacement_boundary(worker):
    scenario = fixture_scenarios()[0]
    row = run(worker, scenario)
    assert row["after"]["request_state"] == "switch"
    current = fixture_snapshot()["state"]
    current["opponent_side"]["pokemon"][0].update(current_hp=0, fainted=True)
    scenario["choices"] = {"self": "", "opponent": "switch slot:1"}
    snapshot = snapshot_from_state(current)
    before = deepcopy(snapshot)
    result = reconcile_detached_showdown(runtime_snapshot=snapshot, checkpoint=row["checkpoint"],
        scenario=scenario, observed_history=[], bridge=worker)
    assert result["status"] == "simulated", result
    assert result["scenarios"][0]["before"]["request_state"] == "switch"
    assert result["scenarios"][0]["after"]["sides"]["opponent"]["pokemon"][0]["slot_index"] == 1
    assert snapshot == before
    scenario["history"] = [{"self": "move 1", "opponent": "move 1"}]
    fresh = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)
    assert fresh["status"] == "simulated", fresh
    assert fresh["scenarios"][0]["after"] == result["scenarios"][0]["after"]
    scenario["history"] = []
    rejected = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)
    assert rejected["scenarios"][0]["reason"] == "observed_faint_requires_matching_native_history"


def test_pivot_reconciliation_retains_queued_opponent_action(worker):
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][0] = {"pokemon_id": "rotom-wash", "current_hp": 127, "max_hp": 127, "fainted": False}
    scenario = fixture_scenarios()[1]
    scenario["teams"]["self"][0], scenario["teams"]["self"][2] = scenario["teams"]["self"][2], scenario["teams"]["self"][0]
    scenario["teams"]["self"][0]["moves"] = ["Volt Switch", "Hydro Pump", "Protect"]
    scenario["teams"]["opponent"][0]["moves"].append("X-Scissor")
    scenario["choices"] = {"self": "move 1", "opponent": "move 4"}
    original = snapshot_from_state(state)
    row = run(worker, scenario, original)
    assert row["after"]["request_state"] == "switch"
    state["opponent_side"]["pokemon"][0]["current_hp"] = row["after"]["sides"]["opponent"]["pokemon"][0]["hp"]
    scenario["choices"] = {"self": "switch slot:1", "opponent": ""}
    snapshot = snapshot_from_state(state)
    result = reconcile_detached_showdown(runtime_snapshot=snapshot, checkpoint=row["checkpoint"], scenario=scenario,
        observed_history=[], bridge=worker)
    assert result["status"] == "simulated", result
    after = result["scenarios"][0]["after"]
    assert after["turn"] == 2
    assert after["sides"]["self"]["pokemon"][0]["hp"] < 185
    continued = resume_detached_showdown(runtime_snapshot=original,
        checkpoint=row["checkpoint"], choices=scenario["choices"], bridge=worker)
    assert continued["scenarios"][0]["after"] == after
