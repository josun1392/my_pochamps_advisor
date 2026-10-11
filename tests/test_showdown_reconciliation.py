"""Native reconstruction with observed roster facts and explicit hidden history."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_bridge import ShowdownBridge
from llm.advisor_showdown_simulation import simulate_detached_showdown
from llm.advisor_showdown_simulation import reconcile_detached_showdown
from llm.advisor_observation_replay_runtime import ObservationReplayRuntime
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, snapshot_from_state


@pytest.fixture
def bridge():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned Showdown required")
    return ShowdownBridge(checkout)


def execute(bridge, state, scenario):
    before = deepcopy((state, scenario))
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=[scenario], bridge=bridge)
    assert (state, scenario) == before
    return result["scenarios"][0]


def test_bench_hp_faint_count_and_final_stats_are_reconciled(bridge):
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][1] = {"pokemon_id": "garchomp", "current_hp": 50, "max_hp": 185, "fainted": False}
    state["self_side"]["pokemon"][2] = {"pokemon_id": "rotom-wash", "current_hp": 0, "max_hp": 127, "fainted": True}
    state["self_side"]["pokemon"][0]["current_final_stats"] = {"special-attack": {"value": 177, "provenance": {"event_kind": "current_final_combat_stat_observed", "trust": "user_confirmed_observation", "turn_number": 1}}}
    scenario = fixture_scenarios()[1]
    row = execute(bridge, state, scenario)
    assert row["status"] == "simulated", row
    assert [p["hp"] for p in row["before"]["sides"]["self"]["pokemon"]] == [155, 50, 0]
    assert row["root_checkpoint"]["native_state"]["sides"][0]["pokemonLeft"] == 2
    state["self_side"]["pokemon"][0]["current_final_stats"]["special-attack"]["value"] = 176
    assert execute(bridge, state, scenario)["reason"] == "observed_final_stat_conflict"


def test_active_slot_identity_survives_native_switch_reordering(bridge):
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][1] = {"pokemon_id": "garchomp", "current_hp": 150, "max_hp": 185, "fainted": False}
    state["self_side"]["active_slot_index"] = 1
    scenario = fixture_scenarios()[1]
    scenario["history"] = [{"self": "switch 2", "opponent": "move 2"}]
    scenario["choices"] = {"self": "move 2", "opponent": "move 3"}
    row = execute(bridge, state, scenario)
    assert row["status"] == "simulated", row
    assert row["before"]["sides"]["self"]["pokemon"][0]["slot_index"] == 1
    scenario["history"] = []
    assert execute(bridge, state, scenario)["reason"] == "active_slot_mismatch"


@pytest.mark.parametrize("effect,target,identifier,field,value", [
    ("weather", "field", "rain", "weather", "rain"),
    ("terrain", "field", "electricterrain", "terrain", "electric"),
    ("pseudo", "field", "trickroom", "trick_room_status", "active"),
    ("pseudo", "field", "magicroom", "magic_room_status", "active"),
    ("pseudo", "field", "gravity", "gravity_status", "active"),
    ("side", "self", "tailwind", "tailwind_status", "active"),
    ("side", "self", "reflect", "side_conditions", ["reflect"]),
])
def test_native_field_conditioning_and_observation_validation(bridge, effect, target, identifier, field, value):
    state = fixture_snapshot()["state"]
    state["field" if target == "field" else "self_side"][field] = value
    # Runtime field toggles need trusted provenance.
    if field.endswith("_status") and target == "field":
        state["field"][field + "_provenance"] = {"event_kind": field.replace("_status", "_observed"), "trust": "user_confirmed_observation", "turn_number": 1}
        if field == "gravity_status": state["field"][field + "_provenance"].update(event_kind="gravity_field_observed", source="user_confirmed_gravity")
    scenario = fixture_scenarios()[1]
    scenario["conditioning"] = [{"target": target, "effect": effect, "id": "raindance" if identifier == "rain" else identifier, "remaining": 2}]
    scenario["choices"] = {"self": "move 3", "opponent": "move 2"}
    row = execute(bridge, state, scenario)
    assert row["status"] == "simulated", row
    if field == "weather": assert row["after"]["field"]["weather_duration"] == 1
    scenario["conditioning"] = []
    assert execute(bridge, state, scenario)["status"] == "rejected"


def test_native_status_conditioning_and_checkpoint_timer(bridge):
    state = fixture_snapshot()["state"]
    state["opponent_side"]["pokemon"][0]["condition"] = "freeze"
    scenario = fixture_scenarios()[1]
    scenario["conditioning"] = [{"target": "opponent", "effect": "status", "id": "frz"}]
    scenario["choices"] = {"self": "move 3", "opponent": "move 2"}
    row = execute(bridge, state, scenario)
    assert row["status"] == "simulated", row
    assert row["root_checkpoint"]["native_state"]["sides"][1]["pokemon"][0]["statusState"]["time"] == 3


def test_invalid_conditioning_never_enters_native_prediction(bridge):
    scenario = fixture_scenarios()[1]
    scenario["conditioning"] = [{"target": "field", "effect": "pseudo", "id": "invented", "remaining": 99}]
    assert execute(bridge, fixture_snapshot()["state"], scenario)["status"] == "rejected"


def test_new_reducer_observation_reconditions_old_hypothesis_without_writeback(bridge):
    initial = fixture_snapshot()
    scenario = fixture_scenarios()[1]
    saved = simulate_detached_showdown(runtime_snapshot=initial, scenarios=[scenario], bridge=bridge)["scenarios"][0]["root_checkpoint"]
    owner = ObservationReplayRuntime.create(initial["state"])["runtime"]
    event = {"session_id": initial["session_id"], "observation_id": "actual-hp", "observation_sequence": 1,
        "event_kind": "exact_hp_transition_observed", "reducer_eligibility": "candidate", "side": "self",
        "slot_index": 0, "pokemon_id": "charizard", "hp_before": 155, "hp_after": 60,
        "payload": {"hp_before": 155, "hp_after": 60}}
    assert owner.apply({"status": "ready", "session_id": initial["session_id"], "ordered_observations": [event]})["status"] == "applied"
    current = snapshot_from_state(owner.read_state()["state"])
    before = deepcopy((owner.read_state(), owner.read_applied_ledger(), saved))
    result = reconcile_detached_showdown(runtime_snapshot=current, checkpoint=saved, scenario=scenario, observed_history=[], bridge=bridge)
    assert result["status"] == "simulated", result
    assert result["reconciled_from_runtime_fingerprint"] == initial["state_fingerprint"]
    assert result["source_runtime_fingerprint"] == current["state_fingerprint"]
    assert result["scenarios"][0]["before"]["sides"]["self"]["pokemon"][0]["hp"] == 60
    assert (owner.read_state(), owner.read_applied_ledger(), saved) == before
    foreign = fixture_snapshot(session_id="foreign")
    assert reconcile_detached_showdown(runtime_snapshot=foreign, checkpoint=saved, scenario=scenario, observed_history=[], bridge=bridge)["status"] == "rejected"


def test_preview_excluded_identity_is_verified_but_not_simulated(bridge):
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][3] = {"pokemon_id": "tyranitar"}
    row = execute(bridge, state, fixture_scenarios()[1])
    assert row["status"] == "simulated", row
    state["self_side"]["pokemon"][3]["current_hp"] = 100
    assert execute(bridge, state, fixture_scenarios()[1])["reason"] == "observed_unselected_roster_mechanics"
