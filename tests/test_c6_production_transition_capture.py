"""Production anchors use the settled strict transition replay unchanged."""
from copy import deepcopy
from types import MappingProxyType

import pytest
import ui.main_window as main_window_module

from llm.advisor_c6_production_decision_capture import ProductionDecisionCapture
from llm.advisor_c6_production_transition_capture import ProductionObservedTransitionCapture
from llm.advisor_exact_outcome_descriptive_metrics import project_exact_outcome_descriptive_metrics
from tests.test_offline_strategy_transition_replay import _attack_case, _switch_case
from tests.test_v36_main_window_session_lifecycle_wiring import _Harness
from tests.test_production_pokemon_switch_observation_wiring import _manager as switch_manager
from llm.advisor_pokemon_switch_observation import admit_pokemon_switch_observation
from ui.main_window import MainWindow


def _owners(kwargs, *, turn):
    feature = kwargs["feature_contract"]
    actor = feature["provenance"]["decision_owner"]
    session = actor["session_id"]
    capture = ProductionDecisionCapture.create(
        session_id=session, battle_id=session, actor=actor, source_id=f"production:{session}:self")
    assert capture["status"] == "source_ready"
    capture = capture["source"]
    state = kwargs["decision_runtime_snapshot"]["state"]
    opponent = state["opponent_side"]
    opponent_slot = opponent["active_slot_index"]
    opportunity = capture.begin_decision_capture(
        captured_session_id=session, captured_battle_id=session, actor=actor,
        opportunity_id=f"turn-{turn}", decision_kind="turn_start", turn_number=turn,
        simultaneity_group_id=f"turn-{turn}",
        context_reference={"ruleset_id": "explicit-rules", "mechanics_version": "explicit-mechanics",
                           "protocol_version": "explicit-protocol", "battle_format_id": "explicit-singles"},
        legal_action_set={"status": "unknown", "action_ids": []},
        public_snapshot={
            "active": {"self": {"session_id": session, "slot_index": actor["slot_index"],
                                "pokemon_id": actor["pokemon_id"]},
                       "opponent": {"session_id": session, "slot_index": opponent_slot,
                                    "pokemon_id": opponent["pokemon"][opponent_slot]["pokemon_id"]}},
            "field": {}, "sides": {"self": {}, "opponent": {}},
            "opponent_revealed_moves": {"status": "unknown", "move_ids": []}},
        private_snapshot={"roster_scope": {"status": "partial", "slot_indices": [actor["slot_index"]]},
                          "own_roster": [{"slot_index": actor["slot_index"], "pokemon_id": actor["pokemon_id"]}]})
    assert opportunity["status"] == "captured", opportunity
    transition = ProductionObservedTransitionCapture(capture)
    anchored = transition.retain_decision_anchor(
        opportunity_record=opportunity["opportunity"],
        decision_runtime_snapshot=kwargs["decision_runtime_snapshot"], decision_turn_number=turn)
    assert anchored["status"] == "retained", anchored
    return capture, transition, opportunity["opportunity"]["certificate"]["boundary_id"]


def _attach(transition, boundary_id, kwargs, *, with_binding=True):
    feature = kwargs["feature_contract"]
    row = feature["rows"][0]
    candidate_id = row["candidate_id"]
    ledger = kwargs.get("predictive_ledger")
    if ledger is None:
        candidate = {"schema_version": "deterministic-strategy-candidate-evidence-v1",
                     "candidate_id": candidate_id, "action_type": "manual_switch",
                     "evidence_class": "incomplete"}
        ledgers, metrics, bundles = {}, {}, {}
    else:
        candidate = {"schema_version": "deterministic-strategy-candidate-evidence-v1",
                     "candidate_id": candidate_id, "action_type": "attack",
                     "evidence_class": "exact_outcome", "execution_readiness": "complete"}
        ledgers = {candidate_id: ledger}
        metrics = {candidate_id: project_exact_outcome_descriptive_metrics(ledger=ledger)}
        bundles = ({candidate_id: {"binding": kwargs["historical_binding"], "ledger": ledger}}
                   if with_binding else {})
    strategy = {"status": "incomplete_comparison_set",
                "schema_version": "deterministic-strategy-orchestration-result-v1",
                "session_id": feature["provenance"]["session_id"],
                "decision_branch_fingerprint": feature["provenance"]["source_branch_fingerprint"],
                "decision_owner": feature["provenance"]["decision_owner"],
                "candidates": [candidate]}
    result = transition.retain_strategy_evidence(
        boundary_id=boundary_id, strategy_result=strategy,
        exact_outcome_ledgers=ledgers, descriptive_metrics=metrics,
        historical_attack_bundles=bundles)
    assert result["status"] == "retained", result


def _attempt(owner, boundary_id, kwargs):
    return owner.attempt_observed_transition(
        boundary_id=boundary_id, observation_snapshot=kwargs["observation_snapshot"],
        next_runtime_snapshot=kwargs["next_runtime_snapshot"])


def test_attack_retains_pre_execution_snapshot_and_strict_replay_resolves():
    kwargs = _attack_case()
    before = deepcopy(kwargs["next_runtime_snapshot"])
    _, owner, boundary_id = _owners(kwargs, turn=1)
    anchor = owner.read_snapshot(captured_session_id="replay", captured_battle_id="replay")["pending_anchors"][0]
    assert anchor["decision_runtime_snapshot"] == kwargs["decision_runtime_snapshot"]
    assert anchor["feature_contract"] is None
    assert owner.attempt_observed_transition(
        boundary_id=boundary_id, observation_snapshot={"status": "ready", "session_id": "replay",
                                                    "ordered_observations": []},
        next_runtime_snapshot=kwargs["decision_runtime_snapshot"])["status"] == "incomplete"
    _attach(owner, boundary_id, kwargs)
    result = _attempt(owner, boundary_id, kwargs)
    assert result["status"] == "resolved", result
    assert result["schema_version"] == "offline-strategy-transition-replay-v1"
    assert result["action_identity_semantics"] == "observed_executed_action"
    assert result["executed_action"]["execution_identity"]["kind"] == "historical_action_link"
    assert kwargs["next_runtime_snapshot"] == before
    saved = owner.read_snapshot(captured_session_id="replay", captured_battle_id="replay")
    assert saved["resolved_transitions"] == (result,)
    with pytest.raises(TypeError):
        saved["resolved_transitions"][0]["next_state"]["turn_number"] = 9


def test_submitted_command_alone_never_resolves_transition():
    kwargs = _attack_case()
    capture, owner, boundary_id = _owners(kwargs, turn=1)
    opportunity = capture.opportunity_source.read_snapshot(captured_session_id="replay")["opportunities"][0]
    command = capture.confirm_submitted_command(
        captured_session_id="replay", captured_battle_id="replay", boundary_id=boundary_id,
        actor=opportunity["certificate"]["actor"], confirmation_event_id="direct-command",
        command_payload={"kind": "attack", "move_id": "shadow-ball"})
    assert command["status"] == "admitted"
    assert owner.attempt_observed_transition(
        boundary_id=boundary_id,
        observation_snapshot={"status": "ready", "session_id": "replay", "ordered_observations": []},
        next_runtime_snapshot=kwargs["decision_runtime_snapshot"])["status"] == "incomplete"
    assert owner.read_snapshot(captured_session_id="replay", captured_battle_id="replay")["resolved_transitions"] == ()


def test_missing_attack_binding_incomplete_and_mismatched_execution_rejected():
    kwargs = _attack_case()
    _, owner, boundary_id = _owners(kwargs, turn=1)
    _attach(owner, boundary_id, kwargs, with_binding=False)
    assert _attempt(owner, boundary_id, kwargs)["reason"] == "historical_action_binding_unavailable"
    kwargs = _attack_case()
    _, owner, boundary_id = _owners(kwargs, turn=1)
    _attach(owner, boundary_id, kwargs)
    altered = {**kwargs, "observation_snapshot": deepcopy(kwargs["observation_snapshot"])}
    altered["observation_snapshot"]["ordered_observations"][0]["payload"]["source_action_id"] = "foreign"
    assert _attempt(owner, boundary_id, altered)["status"] == "rejected"


def test_manual_switch_uses_direct_switch_observation_without_attack_binding():
    kwargs = _switch_case()
    _, owner, boundary_id = _owners(kwargs, turn=4)
    _attach(owner, boundary_id, kwargs)
    result = _attempt(owner, boundary_id, kwargs)
    assert result["status"] == "resolved", result
    assert result["executed_action"]["execution_identity"]["kind"] == "switch_observation"


def test_stale_or_same_state_and_foreign_evidence_fail_closed():
    kwargs = _attack_case()
    _, owner, boundary_id = _owners(kwargs, turn=1)
    _attach(owner, boundary_id, kwargs)
    assert owner.attempt_observed_transition(
        boundary_id=boundary_id, observation_snapshot=kwargs["observation_snapshot"],
        next_runtime_snapshot=kwargs["decision_runtime_snapshot"])["status"] == "rejected"
    foreign = deepcopy(kwargs["next_runtime_snapshot"])
    foreign["session_id"] = "foreign"
    assert owner.attempt_observed_transition(
        boundary_id=boundary_id, observation_snapshot=kwargs["observation_snapshot"],
        next_runtime_snapshot=foreign)["status"] == "rejected"


def test_missing_next_observation_is_incomplete_and_foreign_opportunity_rejected():
    kwargs = _attack_case()
    capture, owner, boundary_id = _owners(kwargs, turn=1)
    _attach(owner, boundary_id, kwargs)
    missing = deepcopy(kwargs["observation_snapshot"])
    missing["ordered_observations"] = missing["ordered_observations"][:1]
    result = owner.attempt_observed_transition(
        boundary_id=boundary_id, observation_snapshot=missing,
        next_runtime_snapshot=kwargs["next_runtime_snapshot"])
    assert result["status"] == "incomplete" and result["reason"] == "next_state_observation_unavailable"
    retained = capture.opportunity_source.read_snapshot(captured_session_id="replay")["opportunities"][0]
    forged = MappingProxyType({**retained, "certificate": MappingProxyType({
        **retained["certificate"], "actor": {"session_id": "replay", "side": "opponent",
                                                "slot_index": 0, "pokemon_id": "opponent-a"}})})
    assert owner.retain_decision_anchor(
        opportunity_record=forged, decision_runtime_snapshot=kwargs["decision_runtime_snapshot"],
        decision_turn_number=1)["status"] == "rejected"


def test_second_decision_retains_distinct_boundary_anchor():
    kwargs = _attack_case()
    capture, owner, first = _owners(kwargs, turn=1)
    actor = capture.opportunity_source.actor
    second = capture.begin_decision_capture(
        captured_session_id="replay", captured_battle_id="replay", actor=actor,
        opportunity_id="turn-2", decision_kind="turn_start", turn_number=2,
        simultaneity_group_id="turn-2",
        context_reference={"ruleset_id": "explicit-rules", "mechanics_version": "explicit-mechanics",
                           "protocol_version": "explicit-protocol", "battle_format_id": "explicit-singles"},
        legal_action_set={"status": "unknown", "action_ids": []},
        public_snapshot={"active": {"self": {"session_id": "replay", "slot_index": 0, "pokemon_id": "self-a"},
                                    "opponent": {"session_id": "replay", "slot_index": 0, "pokemon_id": "opponent-a"}},
                         "field": {}, "sides": {"self": {}, "opponent": {}},
                         "opponent_revealed_moves": {"status": "unknown", "move_ids": []}},
        private_snapshot={"roster_scope": {"status": "partial", "slot_indices": [0]},
                          "own_roster": [{"slot_index": 0, "pokemon_id": "self-a"}]})
    assert second["status"] == "captured"
    result = owner.retain_decision_anchor(
        opportunity_record=second["opportunity"],
        decision_runtime_snapshot=kwargs["decision_runtime_snapshot"], decision_turn_number=2)
    assert result["status"] == "retained"
    snapshot = owner.read_snapshot(captured_session_id="replay", captured_battle_id="replay")
    assert len(snapshot["pending_anchors"]) == 2
    assert len({row["boundary_id"] for row in snapshot["pending_anchors"]}) == 2
    assert first != result["anchor"]["boundary_id"]
    assert snapshot == owner.read_snapshot(captured_session_id="replay", captured_battle_id="replay")


def test_main_window_decision_capture_retains_transition_anchor_without_execution():
    window = _Harness()
    window._c6_decision_capture_owners = {}
    window._c6_transition_capture_owners = {}
    window._c6_explicit_context_reference = {
        "ruleset_id": "explicit-rules", "mechanics_version": "explicit-mechanics",
        "protocol_version": "explicit-protocol", "battle_format_id": "explicit-singles"}
    window._current_trusted_turn_number = 1
    manager = window._observation_runtime_session_manager
    before = manager.read_state()
    captured = MainWindow.begin_c6_decision_capture(
        window, runtime_snapshot=manager.capture_runtime_state_snapshot("ui-session-0"))
    assert captured["status"] == "captured"
    snapshot = MainWindow.read_c6_observed_transition_snapshot(window)
    assert snapshot["status"] == "ready"
    assert len(snapshot["actor_transitions"][0]["pending_anchors"]) == 1
    assert snapshot["actor_transitions"][0]["resolved_transitions"] == ()
    assert manager.read_state() == before
    with pytest.raises(TypeError):
        snapshot["actor_transitions"][0]["pending_anchors"][0]["decision_turn_number"] = 8


def test_main_window_refresh_resolves_observed_manual_switch_without_command_inference():
    window = _Harness()
    window._observation_runtime_session_manager = switch_manager()
    window._c6_decision_capture_owners = {}
    window._c6_transition_capture_owners = {}
    window._c6_explicit_context_reference = {
        "ruleset_id": "explicit-rules", "mechanics_version": "explicit-mechanics",
        "protocol_version": "explicit-protocol", "battle_format_id": "explicit-singles"}
    window._current_trusted_turn_number = 4
    manager = window._observation_runtime_session_manager
    captured = MainWindow.begin_c6_decision_capture(
        window, runtime_snapshot=manager.capture_runtime_state_snapshot("s"))
    assert captured["status"] == "captured", captured
    owner = window._c6_transition_capture_owners[(0, "pikachu")]
    boundary_id = captured["opportunity"]["certificate"]["boundary_id"]
    _attach(owner, boundary_id, _switch_case())
    assert MainWindow.read_c6_decision_capture_snapshot(window)["actor_captures"][0]["submitted_commands"]["command_evidence"] == ()
    switched = admit_pokemon_switch_observation(
        runtime_session_manager=manager, captured_session_id="s", side="self",
        switch_in_slot_index=1, switch_in_pokemon_id="raichu", turn_number=4)
    assert switched["status"] == "resolved"
    MainWindow._refresh_c6_observed_transitions(window)
    snapshot = MainWindow.read_c6_observed_transition_snapshot(window)
    assert snapshot["actor_transitions"][0]["resolved_transitions"][0]["schema_version"] == "offline-strategy-transition-replay-v1"
    assert MainWindow.read_c6_decision_capture_snapshot(window)["actor_captures"][0]["submitted_commands"]["command_evidence"] == ()


def test_main_window_strategy_result_attaches_features_at_same_runtime_revision(monkeypatch):
    window = _Harness()
    window._observation_runtime_session_manager = switch_manager()
    window._c6_decision_capture_owners = {}
    window._c6_transition_capture_owners = {}
    window._c6_explicit_context_reference = {
        "ruleset_id": "explicit-rules", "mechanics_version": "explicit-mechanics",
        "protocol_version": "explicit-protocol", "battle_format_id": "explicit-singles"}
    window._current_trusted_turn_number = 4
    fixture = _switch_case()
    feature = fixture["feature_contract"]
    candidate_id = feature["rows"][0]["candidate_id"]
    strategy = {"status": "incomplete_comparison_set",
                "schema_version": "deterministic-strategy-orchestration-result-v1",
                "session_id": "s",
                "decision_branch_fingerprint": feature["provenance"]["source_branch_fingerprint"],
                "decision_owner": feature["provenance"]["decision_owner"],
                "candidates": [{"schema_version": "deterministic-strategy-candidate-evidence-v1",
                                "candidate_id": candidate_id, "action_type": "manual_switch",
                                "evidence_class": "incomplete"}]}
    bridge_result = {"status": "resolved",
                     "source_runtime_fingerprint": feature["provenance"]["source_runtime_fingerprint"],
                     "orchestration": strategy, "exact_outcome_ledgers": {},
                     "descriptive_metrics": {}, "explanation": {"status": "resolved"}}
    monkeypatch.setattr(main_window_module, "run_current_ui_detached_strategy", lambda **_: bridge_result)
    window._historical_predictive_action_bindings = {}
    window._install_historical_predictive_action_bindings = lambda _result: None
    window.panel.set_strategy_explanation = lambda _value: None
    MainWindow._start_deterministic_strategy_analysis(window)
    captured = MainWindow.read_c6_observed_transition_snapshot(window)
    assert len(captured["actor_transitions"][0]["pending_anchors"]) == 1
    assert captured["actor_transitions"][0]["pending_anchors"][0]["feature_contract"]["status"] == "resolved"
