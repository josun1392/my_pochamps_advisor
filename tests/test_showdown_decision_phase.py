"""Observed phase authority, historical replay and native queue boundaries."""
from copy import deepcopy
import os
import pytest
from advisor.showdown_worker import ShowdownWorker
from llm.advisor_battle_decision_phase import KEY, KIND, SCHEMA, SOURCE, admit_battle_decision_phase_observation, valid_payload
from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, USER_TRUST
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_showdown_simulation import simulate_detached_showdown, reconcile_detached_showdown
from llm.advisor_current_condition_observation import admit_current_condition_observation
from scripts.verify_showdown_integration import fixture_snapshot, fixture_scenarios


def manager(state=None):
    state = deepcopy(state or fixture_snapshot()["state"])
    created = BattleObservationRuntimeSessionManager.create(state["session_id"], state)
    assert created["status"] == "session_ready", created
    return created["manager"]


def capture(owner, *, phase="move_selection", sides=None, turn=1):
    result = admit_battle_decision_phase_observation(runtime_session_manager=owner, captured_session_id=fixture_snapshot()["session_id"],
        phase=phase, requesting_sides=sides if sides is not None else ["self", "opponent"], turn_number=turn)
    assert result["status"] == "resolved", result
    return result["runtime_snapshot"]


@pytest.fixture
def worker():
    checkout = os.environ.get("POKEADVICE_SHOWDOWN_CHECKOUT")
    if not checkout: pytest.skip("external pinned engine required")
    with ShowdownWorker(checkout) as worker: yield worker


def test_phase_observation_uses_reducer_and_preserves_legacy_records(tmp_path):
    owner = manager()
    initial = owner.capture_runtime_state_snapshot(fixture_snapshot()["session_id"])
    assert KEY not in initial["state"]
    snapshot = capture(owner)
    assert snapshot["state"][KEY]["schema_version"] == SCHEMA
    assert len(owner.read_applied_ledger()) == 1
    assert owner.read_collection_snapshot()["ordered_observations"][0]["event_kind"] == KIND
    assert capture(owner) == snapshot  # Idempotent, no new observation or sequence.
    path = tmp_path / "new-session.json"
    assert owner.save(snapshot["session_id"], path)["status"] == "save_complete"
    loaded = owner.load(snapshot["session_id"], path)
    assert loaded["status"] == "load_ready", loaded
    assert loaded["envelope"]["store"]["state"] == snapshot["state"]
    assert owner.restore(snapshot["session_id"], loaded, snapshot["state_fingerprint"])["status"] == "restore_complete"
    # An old session with no new contract is still admitted unchanged.
    old = manager(initial["state"])
    assert old.capture_runtime_state_snapshot(initial["session_id"]) == initial


@pytest.mark.parametrize("payload", [{}, {"schema_version": SCHEMA, "phase": {}, "requesting_sides": [], "participants": {}},
    {"schema_version": SCHEMA, "phase": "move_selection", "requesting_sides": [{}], "participants": {}}])
def test_invalid_versioned_phase_payload_fails_closed(payload):
    assert valid_payload(payload) is False


def test_prediction_source_and_stale_session_cannot_admit_phase():
    owner = manager()
    payload = {"schema_version": SCHEMA, "phase": "move_selection", "requesting_sides": ["self", "opponent"],
        "participants": {"self": {"slot_index": 0, "pokemon_id": "charizard"}, "opponent": {"slot_index": 0, "pokemon_id": "scizor"}}}
    result = LifecycleConfirmationBoundary(fixture_snapshot()["session_id"], {}).confirm(event_kind=KIND, payload=payload,
        session_id=fixture_snapshot()["session_id"], source="showdown_prediction", trust=USER_TRUST, confirmed=True, turn_number=1)
    assert result["status"] == "invalid_provenance"
    assert admit_battle_decision_phase_observation(runtime_session_manager=owner, captured_session_id="old-session",
        phase="move_selection", requesting_sides=["self", "opponent"], turn_number=1)["status"] == "rejected"
    assert owner.read_applied_ledger() == {}


def test_observed_turn_requests_and_recapture_freshness(worker):
    owner, scenario = manager(), fixture_scenarios()[1]
    snapshot = capture(owner)
    result = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)
    assert result["scenarios"][0]["status"] == "simulated", result
    changed = capture(owner, turn=2)
    conflict = simulate_detached_showdown(runtime_snapshot=changed, scenarios=[scenario], bridge=worker)
    assert conflict["scenarios"][0]["reason"] == "observed_decision_phase_conflict"
    condition = admit_current_condition_observation(runtime_session_manager=owner, captured_session_id=snapshot["session_id"],
        side="self", condition="none", turn_number=2)
    assert condition["status"] == "resolved", condition
    stale = owner.capture_runtime_state_snapshot(snapshot["session_id"])
    assert simulate_detached_showdown(runtime_snapshot=stale, scenarios=[scenario], bridge=worker)["reason"] == "stale_observed_decision_phase"
    fresh = capture(owner, turn=2)
    scenario["history"] = [{"self": "move 3", "opponent": "move 2"}]
    assert simulate_detached_showdown(runtime_snapshot=fresh, scenarios=[scenario], bridge=worker)["scenarios"][0]["status"] == "simulated"
    rejected = admit_battle_decision_phase_observation(runtime_session_manager=owner, captured_session_id=snapshot["session_id"],
        phase="move_selection", requesting_sides=["self", "opponent"], turn_number=1)
    assert rejected["status"] == "rejected"


def test_faint_replacement_phase_requires_native_faint_and_preserves_queue(worker):
    original, scenario = fixture_snapshot(), fixture_scenarios()[0]
    first = simulate_detached_showdown(runtime_snapshot=original, scenarios=[scenario], bridge=worker)["scenarios"][0]
    state = deepcopy(original["state"])
    state["opponent_side"]["pokemon"][0].update(current_hp=0, fainted=True)
    owner = manager(state)
    snapshot = capture(owner, phase="faint_replacement", sides=["opponent"])
    scenario["choices"] = {"self": "", "opponent": "switch slot:1"}
    result = reconcile_detached_showdown(runtime_snapshot=snapshot, checkpoint=first["checkpoint"], scenario=scenario,
        observed_history=[], bridge=worker)
    assert result["scenarios"][0]["status"] == "simulated", result
    assert result["scenarios"][0]["before"]["request_state"] == "switch"
    assert result["scenarios"][0]["after"]["sides"]["opponent"]["pokemon"][0]["species"] == "garchomp"
    wrong = capture(owner, phase="pivot_replacement", sides=["opponent"])
    conflict = reconcile_detached_showdown(runtime_snapshot=wrong, checkpoint=first["checkpoint"], scenario=scenario,
        observed_history=[], bridge=worker)
    assert conflict["scenarios"][0]["reason"] == "observed_replacement_reason_conflict"


def test_observed_pivot_preserves_native_queued_opponent_action(worker):
    state, scenario = fixture_snapshot()["state"], fixture_scenarios()[1]
    state["self_side"]["pokemon"][0] = {"pokemon_id": "rotom-wash", "current_hp": 127, "max_hp": 127, "fainted": False}
    scenario["teams"]["self"][0], scenario["teams"]["self"][2] = scenario["teams"]["self"][2], scenario["teams"]["self"][0]
    scenario["teams"]["self"][0]["moves"] = ["Volt Switch", "Hydro Pump", "Protect"]
    scenario["choices"] = {"self": "move 1", "opponent": "move 2"}
    owner = manager(state)
    snapshot = capture(owner)
    first = simulate_detached_showdown(runtime_snapshot=snapshot, scenarios=[scenario], bridge=worker)["scenarios"][0]
    assert first["status"] == "simulated", first
    snapshot = capture(owner, phase="pivot_replacement", sides=["self"])
    scenario["choices"] = {"self": "switch slot:1", "opponent": ""}
    frozen = deepcopy((snapshot, first["checkpoint"]))
    result = reconcile_detached_showdown(runtime_snapshot=snapshot, checkpoint=first["checkpoint"], scenario=scenario,
        observed_history=[], bridge=worker)["scenarios"][0]
    assert result["status"] == "simulated", result
    assert result["before"]["decision_phase"]["queued_actions"] == first["after"]["decision_phase"]["queued_actions"]
    assert any(a["choice"] == "move" and a["side"] == "p2" for a in result["before"]["decision_phase"]["queued_actions"])
    assert result["after"]["sides"]["opponent"]["pokemon"][0]["boosts"]["atk"] == 2
    assert result["after"]["turn"] == 2
    assert (snapshot, first["checkpoint"]) == frozen
