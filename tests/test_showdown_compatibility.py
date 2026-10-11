"""Semantic compatibility: old meaning survives, native counters are versioned."""
from copy import deepcopy
from fractions import Fraction
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_champions_sleep_freeze_action_gate import resolve_gate_branches, classify_status_move
from llm.advisor_champions_status_progression import valid_progression
from llm.advisor_observation_replay_runtime import ObservationReplayRuntime
from llm.advisor_showdown_simulation import (simulate_detached_showdown, resume_detached_showdown,
    reconcile_detached_showdown, evaluate_native_status_gate, _checkpoint_fingerprint)
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios, snapshot_from_state


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker: yield worker


@pytest.mark.parametrize("key,container,native", [("known_item", "opponent", "item"), ("condition", "opponent", "condition"),
    ("weather", "field", "weather"), ("terrain", "field", "terrain")])
def test_unconfirmed_legacy_none_is_unknown_in_native_projection(key, container, native):
    class Capture:
        def run(self, request): self.request = request; return {"scenarios": []}
    state = fixture_snapshot()["state"]
    target = state["field"] if container == "field" else state[f"{container}_side"]["pokemon"][0]
    target[key] = None
    before = deepcopy(state)
    bridge = Capture()
    simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=fixture_scenarios(), bridge=bridge)
    observed = bridge.request["observed_field"] if container == "field" else bridge.request["observed_active"][container]
    assert native not in observed
    assert bridge.request["observation_schema_version"] == "showdown-observed-projection-v2"
    assert state == before


@pytest.mark.parametrize("kind", ["item", "condition", "weather", "terrain"])
def test_confirmed_absence_rejects_conflicting_hypothesis(worker, kind):
    state, scenario = fixture_snapshot()["state"], fixture_scenarios()[1]
    provenance = {"trust": "user_confirmed_observation", "turn_number": 1}
    if kind == "item":
        state["opponent_side"]["pokemon"][0].update(known_item=None, known_item_provenance={**provenance,
            "event_kind": "current_item_observed", "status": "known_absent"})
    elif kind == "condition":
        state["opponent_side"]["pokemon"][0].update(condition=None, condition_provenance={**provenance,
            "event_kind": "current_condition_observed", "condition": "none"})
        scenario["conditioning"] = [{"effect": "status", "target": "opponent", "id": "frz"}]
    else:
        state["field"].update({kind: "none", kind + "_provenance": {**provenance, "event_kind": f"current_{kind}_observed"}})
        scenario["conditioning"] = [{"effect": kind, "target": "field", "id": "raindance" if kind == "weather" else "electricterrain"}]
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=[scenario], bridge=worker)
    assert result["scenarios"][0]["reason"] == f"observed_{kind}_conflict"


def status_inputs(condition="sleep", prior=0, duration=3, early_bird=True, adjusted=False):
    state, scenario = fixture_snapshot()["state"], fixture_scenarios()[1]
    if early_bird:
        state["self_side"]["pokemon"][0].update(pokemon_id="kangaskhan", current_hp=182, max_hp=182)
        scenario["teams"]["self"][0] = {"species": "Kangaskhan", "ability": "Early Bird", "nature": "Adamant", "level": 50,
            "moves": ["Crunch", "Rest", "Sleep Talk", "Protect"], "evs": {"atk": 32, "spe": 32, "hp": 2}}
    pokemon = state["self_side"]["pokemon"][0]
    owner = {"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": pokemon["pokemon_id"]}
    observation = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1,
        "condition": condition, "source_observation_id": "actual-condition", "source_sequence": 1}
    row = {"schema_version": "champions-sleep-freeze-progression-v1", "owner": owner, "condition": condition,
        "origin_id": "actual-condition:episode", "established_turn": 1, "prior_attempts": prior,
        "sleep_duration": duration if condition == "sleep" else None, "condition_observation": observation,
        "observed_turn": 1, "provenance": "observed_champions_status_progression_v1"}
    if adjusted:
        row.update(adjusted_duration=1, duration_adjustment={"status": "resolved", "early_bird_active": True,
            "holder": owner, "session_id": state["session_id"], "source_runtime_fingerprint": "historical-runtime",
            "source_branch_fingerprint": "historical-branch", "path": ["historical"], "ability_id": "early-bird",
            "abilities": {"self": "early-bird", "opponent": "technician"}, "suppressed": False})
    assert valid_progression(row, owner)
    pokemon.update(condition=condition, condition_provenance=observation, champions_status_progression=row)
    scenario["conditioning"] = [{"effect": "status", "target": "self", "id": "slp" if condition == "sleep" else "frz",
        "counter_state": {"schema_version": "showdown-status-counter-v1", "start_time": duration,
            "remaining_time": duration if prior == 0 else duration - prior}}]
    scenario["choices"] = {"self": "move 1", "opponent": "move 2"}
    return snapshot_from_state(state), scenario


def simulated(worker, snapshot, scenario):
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)
    assert result["status"] == "simulated", result
    return result["scenarios"][0]


def test_early_bird_native_version_preserves_legacy_adjustment_and_replay(worker):
    snapshot, scenario = status_inputs(adjusted=True)
    runtime = ObservationReplayRuntime.create(snapshot["state"])["runtime"]
    before = deepcopy((snapshot, runtime.export_envelope()))
    row = simulated(worker, snapshot, scenario)
    native = row["after"]["sides"]["self"]["pokemon"][0]
    assert native["status"] == "slp" and native["status_counter"]["remaining_time"] == 1
    gate = evaluate_native_status_gate(runtime_snapshot=snapshot, checkpoint=row["root_checkpoint"], side="self", move="crunch", bridge=worker)
    assert gate["scenarios"][0]["status_gate"]["branches"][0]["executes_status_gate"] is False
    legacy = snapshot["state"]["self_side"]["pokemon"][0]["champions_status_progression"]
    old = resolve_gate_branches(condition="sleep", progression=legacy, ability={"status": "resolved", "early_bird_active": True}, move_authority=classify_status_move("crunch"))
    assert old[0]["kind"] == "wakes_and_executes" and legacy["adjusted_duration"] == 1
    continued = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=row["checkpoint"], choices=scenario["choices"], bridge=worker)
    assert continued["scenarios"][0]["after"]["sides"]["self"]["pokemon"][0]["status"] == ""
    assert (snapshot, runtime.export_envelope()) == before


def test_early_bird_prior_attempt_requires_native_episode_history(worker):
    snapshot, scenario = status_inputs(prior=1)
    # A decremented timer alone cannot certify the count of observed attempts.
    scenario["conditioning"][0]["counter_state"]["remaining_time"] = 1
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)
    assert result["scenarios"][0]["reason"] == "legacy_status_requires_matching_native_attempt_history"
    scenario["initial_conditioning"] = deepcopy(scenario.pop("conditioning"))
    scenario["initial_conditioning"][0]["counter_state"]["remaining_time"] = 3
    scenario["history"] = [deepcopy(scenario["choices"])]
    row = simulated(worker, snapshot, scenario)
    assert row["before"]["sides"]["self"]["pokemon"][0]["status_counter"]["remaining_time"] == 1
    assert row["after"]["sides"]["self"]["pokemon"][0]["status"] == ""


@pytest.mark.parametrize("remaining", [1, 2, 3])
def test_native_freeze_callback_exact_weights_and_compatible_observed_attempts(worker, remaining):
    snapshot, scenario = status_inputs("freeze", prior=3 - remaining, early_bird=False)
    row = simulated(worker, snapshot, scenario)
    result = evaluate_native_status_gate(runtime_snapshot=snapshot, checkpoint=row["root_checkpoint"], side="self", move="air-slash", bridge=worker)
    gate = result["scenarios"][0]["status_gate"]
    assert gate["scope"] == "native_status_before_move_callback_only"
    branches = gate["branches"]
    assert sum(Fraction(**b["probability"]) for b in branches) == 1
    execution = sum(Fraction(**b["probability"]) for b in branches if b["executes_status_gate"])
    assert execution == (1 if remaining == 1 else Fraction(1, 4))


def test_native_sleep_exception_and_suppressed_early_bird(worker):
    snapshot, scenario = status_inputs()
    row = simulated(worker, snapshot, scenario)
    result = evaluate_native_status_gate(runtime_snapshot=snapshot, checkpoint=row["root_checkpoint"], side="self", move="sleep-talk", bridge=worker)
    branch = result["scenarios"][0]["status_gate"]["branches"][0]
    assert branch["executes_status_gate"] is True and branch["remaining_time"] == 1
    scenario["conditioning"].append({"effect": "volatile", "target": "self", "id": "gastroacid"})
    row = simulated(worker, snapshot, scenario)
    assert row["after"]["sides"]["self"]["pokemon"][0]["status_counter"]["remaining_time"] == 2
    assert row["before"]["sides"]["self"]["pokemon"][0]["status_counter"]["early_bird_active"] is False


def test_pre_projection_v2_checkpoint_fails_closed(worker):
    snapshot, scenario = fixture_snapshot(), fixture_scenarios()[1]
    saved = simulated(worker, snapshot, scenario)["root_checkpoint"]
    saved.pop("observation_schema_version")
    saved.pop("checkpoint_fingerprint")
    saved["checkpoint_fingerprint"] = _checkpoint_fingerprint(saved)
    result = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=saved, choices=scenario["choices"], bridge=worker)
    assert result["scenarios"][0]["reason"] == "checkpoint_binding_mismatch"


@pytest.mark.parametrize("duration,early_bird,awake", [(2, True, True), (3, True, False), (2, False, False), (3, False, False)])
def test_native_initial_counter_is_not_number_of_cancelled_moves(worker, duration, early_bird, awake):
    snapshot, scenario = status_inputs(duration=duration, early_bird=early_bird)
    row = simulated(worker, snapshot, scenario)
    assert (row["after"]["sides"]["self"]["pokemon"][0]["status"] == "") is awake


def test_native_rest_early_bird_timing_uses_real_move_callback(worker):
    snapshot, scenario = status_inputs()
    state = deepcopy(snapshot["state"])
    state["self_side"]["pokemon"][0].update(current_hp=100, condition=None)
    state["self_side"]["pokemon"][0].pop("condition_provenance")
    state["self_side"]["pokemon"][0].pop("champions_status_progression")
    snapshot = snapshot_from_state(state)
    scenario.pop("conditioning")
    scenario["choices"] = {"self": "move 2", "opponent": "move 2"}
    row = simulated(worker, snapshot, scenario)
    assert row["after"]["sides"]["self"]["pokemon"][0]["status_counter"]["start_time"] == 3
    first = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=row["checkpoint"],
        choices={"self": "move 1", "opponent": "move 2"}, bridge=worker)["scenarios"][0]
    assert first["after"]["sides"]["self"]["pokemon"][0]["status"] == "slp"
    second = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=first["checkpoint"],
        choices={"self": "move 1", "opponent": "move 2"}, bridge=worker)["scenarios"][0]
    assert second["after"]["sides"]["self"]["pokemon"][0]["status"] == ""
