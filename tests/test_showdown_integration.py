"""Real native-engine tests are opt-in; pure boundary tests are always offline."""
from copy import deepcopy
import os
import subprocess

import pytest

from advisor.showdown_bridge import SHOWDOWN_COMMIT, ShowdownBridge, ShowdownBridgeError
from llm.advisor_showdown_simulation import resume_detached_showdown, simulate_detached_showdown
from scripts.verify_showdown_integration import fixture_scenarios, fixture_snapshot, snapshot_from_state, verify


class UnusedBridge:
    def run(self, request):
        pytest.fail("invalid or incomplete authority must not start a simulator")


@pytest.fixture
def native_bridge():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout:
        pytest.skip("set POKEADVICE_SHOWDOWN_CHECKOUT to the external pinned build")
    return ShowdownBridge(checkout)


@pytest.mark.parametrize("mutation,reason", [
    (lambda s: s.update(session_id="foreign"), "invalid_runtime_snapshot_binding"),
    (lambda s: s.update(state_fingerprint="stale"), "invalid_runtime_snapshot_binding"),
    (lambda s: s.update(status="ready"), "invalid_runtime_snapshot"),
])
def test_invalid_binding_does_not_execute(mutation, reason):
    snapshot = fixture_snapshot()
    mutation(snapshot)
    assert simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=fixture_scenarios(), bridge=UnusedBridge()) == {"status": "rejected", "reason": reason}


def test_unknown_hp_and_final_stats_never_get_fabricated():
    state = fixture_snapshot()["state"]
    state["opponent_side"]["pokemon"][0]["current_hp"] = {"knowledge": "unknown"}
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=fixture_scenarios(), bridge=UnusedBridge())
    assert result["reason"] == "observed_active_hp_required"
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][0]["current_final_stats"] = {"attack": {"value": 100, "provenance": {"event_kind": "current_final_combat_stat_observed", "trust": "user_confirmed_observation", "turn_number": 1}}}
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=fixture_scenarios(), bridge=UnusedBridge())
    assert result["reason"] == "observed_final_stats_adapter_required"


def test_assumptions_and_singles_are_required():
    scenarios = fixture_scenarios()
    scenarios[0]["assumptions"] = []
    result = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=scenarios, bridge=UnusedBridge())
    assert result["reason"] == "explicit_scenario_assumptions_required"
    state = fixture_snapshot()["state"]
    state["field"]["battle_format"] = "doubles"
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=fixture_scenarios(), bridge=UnusedBridge())
    assert result["reason"] == "observed_singles_format_required"


def test_missing_legacy_fields_are_not_promoted_to_known_absence():
    class CaptureBridge:
        def run(self, request):
            self.request = deepcopy(request)
            return {"scenarios": []}
    bridge = CaptureBridge()
    state = fixture_snapshot()["state"]
    del state["opponent_side"]["pokemon"][0]["known_item"]
    del state["opponent_side"]["pokemon"][0]["condition"]
    del state["field"]["weather"]
    simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=fixture_scenarios(), bridge=bridge)
    assert "item" not in bridge.request["observed_active"]["opponent"]
    assert "condition" not in bridge.request["observed_active"]["opponent"]
    assert "weather" not in bridge.request["observed_field"]


def test_unmapped_known_mechanics_fail_closed_with_field_paths():
    state = fixture_snapshot()["state"]
    state["self_side"]["side_conditions"] = []
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=fixture_scenarios(), bridge=UnusedBridge())
    assert result == {"status": "rejected", "reason": "unmapped_runtime_mechanics", "fields": ["self_side.side_conditions"]}
    state = fixture_snapshot()["state"]
    state["self_side"]["pokemon"][1] = {"pokemon_id": "garchomp", "current_hp": 50, "max_hp": 183, "fainted": False}
    result = simulate_detached_showdown(runtime_snapshot=snapshot_from_state(state), scenarios=fixture_scenarios(), bridge=UnusedBridge())
    assert result["reason"] == "unmapped_runtime_mechanics"
    assert "self_side.pokemon.1.current_hp" in result["fields"]


def test_unavailable_bridge_is_a_sanitized_local_failure():
    class MissingBridge:
        def run(self, request):
            raise ShowdownBridgeError("showdown_timeout")
    result = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=fixture_scenarios(), bridge=MissingBridge())
    assert result == {"status": "unavailable", "reason": "showdown_timeout"}


def test_transport_rejects_wrong_or_dirty_pin_without_launching_node(monkeypatch, tmp_path):
    calls = []
    def wrong_pin(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="wrong" if "rev-parse" in command else "", stderr="")
    monkeypatch.setattr(subprocess, "run", wrong_pin)
    with pytest.raises(ShowdownBridgeError, match="revision_or_tracked_sources_mismatch"):
        ShowdownBridge(tmp_path).run({})
    assert all(command[0] == "git" for command in calls)


def test_transport_does_not_echo_child_output(monkeypatch, tmp_path):
    def child(command, **kwargs):
        if "rev-parse" in command:
            return subprocess.CompletedProcess(command, 0, stdout=SHOWDOWN_COMMIT, stderr="")
        if "status" in command:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(command, 1, stdout="private-input-value", stderr="private-input-value")
    monkeypatch.setattr(subprocess, "run", child)
    with pytest.raises(ShowdownBridgeError) as error:
        ShowdownBridge(tmp_path).run({})
    assert "private-input-value" not in str(error.value)


def test_executable_mc_vertical_slice(native_bridge):
    report = verify(native_bridge, iterations=2)
    assert report["scenario_hp"]["sash"] == [116, 1]
    assert report["native_proof"]["complete_battle"]["restored_each_decision"]
    assert report["native_proof"]["seeded_accuracy_samples"]["miss"] > 0
    assert report["native_proof"]["native_freeze_timer_restore"]


def test_checkpoint_branches_are_independent_and_stale_sources_rejected(native_bridge):
    snapshot = fixture_snapshot()
    scenarios = fixture_scenarios()[1:2]
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=scenarios, bridge=native_bridge)
    checkpoint = result["scenarios"][0]["root_checkpoint"]
    before = deepcopy((snapshot, checkpoint, scenarios))
    attack = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=checkpoint, choices=scenarios[0]["choices"], bridge=native_bridge)
    protect = resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=checkpoint, choices={"self": "move 3", "opponent": "move 2"}, bridge=native_bridge)
    assert attack["scenarios"][0]["after"]["sides"]["opponent"]["pokemon"][0]["hp"] == 1
    assert protect["scenarios"][0]["after"]["sides"]["opponent"]["pokemon"][0]["hp"] == 147
    assert (snapshot, checkpoint, scenarios) == before
    state = deepcopy(snapshot["state"])
    state["last_applied_observation_sequence"] = 1
    assert resume_detached_showdown(runtime_snapshot=snapshot_from_state(state), checkpoint=checkpoint, choices=scenarios[0]["choices"], bridge=UnusedBridge())["status"] == "rejected"
    corrupt = deepcopy(checkpoint)
    corrupt["native_state"]["turn"] += 1
    assert resume_detached_showdown(runtime_snapshot=snapshot, checkpoint=corrupt, choices=scenarios[0]["choices"], bridge=UnusedBridge())["status"] == "rejected"


@pytest.mark.parametrize("field,value,reason", [
    ("item", "Leftovers", "observed_item_conflict"),
    ("max_hp", 999, "observed_max_hp_or_lifecycle_mismatch"),
    ("condition", "burn", "observed_condition_conflict"),
    ("known_move_ids", ["thunderbolt"], "observed_move_conflict"),
])
def test_known_observations_override_hypothesis_eligibility(native_bridge, field, value, reason):
    state = fixture_snapshot()["state"]
    state["opponent_side"]["pokemon"][0]["known_item" if field == "item" else field] = value
    snapshot = snapshot_from_state(state)
    before = deepcopy(snapshot)
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=fixture_scenarios(), bridge=native_bridge)
    assert result["status"] == "rejected"
    assert all(row["reason"] == reason for row in result["scenarios"])
    assert snapshot == before


@pytest.mark.parametrize("mutation,reason", [
    (lambda s: s["choices"].update(self="move 99"), "illegal_choice"),
    (lambda s: s["choices"].update(self=""), "missing_choice"),
    (lambda s: s["teams"]["self"][0].update(evs={"spa": 252}), "invalid_mc_team"),
    (lambda s: s["teams"]["self"][0].update(species="Mewtwo"), "invalid_mc_team"),
    (lambda s: s.update(seed=[1, 2, 3, 65536]), "invalid_seed"),
])
def test_invalid_scenario_is_isolated(native_bridge, mutation, reason):
    scenarios = fixture_scenarios()[1:3]
    mutation(scenarios[0])
    result = simulate_detached_showdown(runtime_snapshot=fixture_snapshot(), scenarios=scenarios, bridge=native_bridge)
    assert result["status"] == "simulated"
    assert result["scenarios"][0]["reason"] == reason
    assert result["scenarios"][1]["status"] == "simulated"
