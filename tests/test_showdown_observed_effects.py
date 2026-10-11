"""High-value observed effects verified against native state, never reimplemented."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_showdown_simulation import simulate_detached_showdown
from llm.advisor_switch_hazard_authority import build_switch_hazard_context
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, snapshot_from_state


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker: yield worker


def execute(worker, state, scenario):
    before = deepcopy((state, scenario))
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=[scenario], bridge=worker)
    assert (state, scenario) == before
    return result["scenarios"][0]


def event_state(base_state, *, effect, side="self", **values):
    slot = base_state[f"{side}_side"]["active_slot_index"]
    event = {"planned_effect": effect, "observation_id": "actual-effect", "observation_sequence": 1,
        "trust": "user_confirmed_observation", "session_id": base_state["session_id"], "side": side, "slot_index": slot,
        "pokemon_id": base_state[f"{side}_side"]["pokemon"][slot]["pokemon_id"], "turn_number": 1, **values}
    result = project_atomic_transition(base_state, {"status": "planned", "session_id": base_state["session_id"], "conflicts": [], "ordered_steps": [event]}, base_state["session_id"])
    assert result["status"] == "ready_with_projected_state", result
    return result["projected_state"]


def test_observed_hazard_layers_drive_native_switch_and_unknowns_stay_unknown(worker):
    state, scenario = fixture_snapshot()["state"], fixture_scenarios()[1]
    state["switch_hazard_context"] = build_switch_hazard_context(session_id=state["session_id"], affected_side="self",
        stealth_rock="present", spikes_layers=3, toxic_spikes_layers=2, sticky_web="present")
    scenario["conditioning"] = [{"target": "self", "effect": "side", "id": identifier, **extra} for identifier, extra in
        [("stealthrock", {}), ("spikes", {"layers": 3}), ("toxicspikes", {"layers": 2}), ("stickyweb", {})]]
    scenario["choices"] = {"self": "switch slot:1", "opponent": "move 2"}
    row = execute(worker, state, scenario)
    assert row["status"] == "simulated", row
    target = row["after"]["sides"]["self"]["pokemon"][0]
    assert target["hp"] == 117 and target["status"] == "tox" and target["boosts"]["spe"] == -1
    state["switch_hazard_context"]["spikes_layers"] = 2
    assert execute(worker, state, scenario)["reason"] == "observed_hazard_conflict"
    # Legacy v1 never claimed anything about Toxic Spikes or Sticky Web.
    state["switch_hazard_context"] = {"schema_version": "switch-hazard-context-v1", "session_id": state["session_id"],
        "affected_side": "self", "stealth_rock": "present", "spikes_layers": 3}
    assert execute(worker, state, scenario)["status"] == "simulated"


@pytest.mark.parametrize("family,native", [("aqua_ring", "aquaring"), ("ingrain", "ingrain")])
def test_observed_persistent_recovery_and_native_switch_restriction(worker, family, native):
    state, scenario = fixture_snapshot(hp=60)["state"], fixture_scenarios()[1]
    state = event_state(state, effect=f"set_current_{family}_state", persistent_state="active")
    scenario["conditioning"] = [{"target": "self", "effect": "volatile", "id": native}]
    scenario["choices"] = {"self": "move 3", "opponent": "move 2"}
    row = execute(worker, state, scenario)
    assert row["status"] == "simulated", row
    assert row["after"]["sides"]["self"]["pokemon"][0]["hp"] == 69
    if family == "ingrain":
        scenario["choices"]["self"] = "switch slot:1"
        assert execute(worker, state, scenario)["reason"] == "illegal_choice"
    scenario["conditioning"] = []
    assert execute(worker, state, scenario)["reason"] == "observed_volatile_conflict"


def test_observed_leech_seed_source_uses_native_current_position(worker):
    state, scenario = fixture_snapshot(hp=60)["state"], fixture_scenarios()[1]
    state = event_state(state, effect="set_current_leech_seed_state", persistent_state="active", source_side="opponent", source_slot_index=0)
    scenario["conditioning"] = [{"target": "self", "effect": "volatile", "id": "leechseed", "source": "opponent"}]
    scenario["choices"] = {"self": "move 3", "opponent": "move 2"}
    row = execute(worker, state, scenario)
    assert row["status"] == "simulated", row
    assert row["after"]["sides"]["self"]["pokemon"][0]["hp"] == 41
    state["opponent_side"]["pokemon"][1] = {"pokemon_id": "garchomp"}
    state["current_persistent_effect_context"]["rows"][0]["source_slot"]["slot_index"] = 1
    assert execute(worker, state, scenario)["reason"] == "observed_leech_source_phase_conflict"


def test_legacy_taunt_future_turns_are_verified_not_assigned_as_native_truth(worker):
    state, scenario = fixture_snapshot()["state"], fixture_scenarios()[1]
    state = event_state(state, effect="apply_taunt_restriction", source_action_id="actual-taunt", source_move_id="taunt")
    scenario["conditioning"] = [{"target": "self", "effect": "volatile", "id": "taunt", "remaining": 3}]
    scenario["choices"] = {"self": "move 2", "opponent": "move 2"}
    row = execute(worker, state, scenario)
    assert row["status"] == "simulated", row
    scenario["choices"]["self"] = "move 3"
    assert execute(worker, state, scenario)["reason"] == "illegal_choice"
    state["current_taunt_restrictions"]["self"]["remaining_target_turns"] = 2
    assert execute(worker, state, scenario)["reason"] == "legacy_restriction_counter_conflict"


@pytest.mark.parametrize("kind,identifier", [("encore", "locked_move_id"), ("disable", "disabled_move_id")])
def test_observed_move_lock_and_last_execution_use_native_history(worker, kind, identifier):
    state, scenario = fixture_snapshot()["state"], fixture_scenarios()[1]
    state = event_state(state, effect="record_executed_move", move_id="protect", source_action_id="actual-protect", observation_id="actual-execution")
    state = event_state(state, effect=f"apply_{kind}_restriction", source_action_id=f"actual-{kind}", source_move_id=kind,
        **{identifier: "protect", "last_used_execution_id": "actual-execution"})
    scenario["history"] = [{"self": "move 3", "opponent": "move 2"}]
    scenario["conditioning"] = [{"target": "self", "effect": "volatile", "id": kind, "remaining": 3 if kind == "encore" else 4}]
    scenario["choices"] = {"self": "move 3" if kind == "encore" else "move 2", "opponent": "move 2"}
    row = execute(worker, state, scenario)
    assert row["status"] == "simulated", row
    scenario["choices"]["self"] = "move 2" if kind == "encore" else "move 3"
    assert execute(worker, state, scenario)["reason"] == "illegal_choice"


def test_observed_berry_consumption_requires_native_consumption_history(worker):
    state, scenario = fixture_snapshot()["state"], fixture_scenarios()[2]
    state = event_state(state, effect="set_berry_eaten_state", side="opponent", state="known_true",
        basis="observed_berry_consumption", item_id="sitrus-berry")
    scenario["history"] = [{"self": "move 2", "opponent": "move 2"}]
    scenario["choices"] = {"self": "move 3", "opponent": "move 3"}
    row = execute(worker, state, scenario)
    assert row["status"] == "simulated", row
    assert row["before"]["sides"]["opponent"]["pokemon"][0]["berry_eaten"] is True
    scenario["history"] = []
    assert execute(worker, state, scenario)["reason"] == "observed_berry_history_conflict"


def test_observed_qualifying_hit_count_requires_matching_native_history(worker):
    state, scenario = fixture_snapshot()["state"], fixture_scenarios()[1]
    state = event_state(state, effect="initialize_rage_fist_hit_count")
    state = event_state(state, effect="record_rage_fist_qualifying_hit", hit_outcome="successful_direct_hit")
    scenario["history"] = [{"self": "move 2", "opponent": "move 1"}]
    scenario["choices"] = {"self": "move 3", "opponent": "move 3"}
    row = execute(worker, state, scenario)
    assert row["status"] == "simulated", row
    assert row["before"]["sides"]["self"]["pokemon"][0]["received_hit_count"] == 1
    scenario["history"] = []
    assert execute(worker, state, scenario)["reason"] == "observed_received_hit_count_conflict"
