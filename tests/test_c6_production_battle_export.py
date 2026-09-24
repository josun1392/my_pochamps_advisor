"""Strict production terminal ingestion and durable pre-split battle archive."""
import json
from types import MappingProxyType

import pytest

from llm.advisor_c6_production_battle_export import (
    materialize_c6_production_battle_export, write_c6_production_battle_export,
)
from llm.advisor_c6_production_decision_capture import ProductionDecisionCapture
from llm.advisor_session_battle_terminal_outcome_evidence import SessionBoundBattleTerminalOutcomeEvidenceSource
from tests.test_c6_production_transition_capture import _attach, _attempt, _owners
from tests.test_offline_strategy_transition_replay import _attack_case
from tests.test_v36_main_window_session_lifecycle_wiring import _Harness
from ui.main_window import MainWindow


def _case(*, resolved=True, command=False, result=None, cause="all_fainted", stream_end=False):
    kwargs = _attack_case()
    decision, transition, boundary = _owners(kwargs, turn=1)
    if command:
        admitted = decision.confirm_submitted_command(
            captured_session_id="replay", captured_battle_id="replay", boundary_id=boundary,
            actor=decision.opportunity_source.actor, confirmation_event_id="direct-choice",
            command_payload={"kind": "attack", "move_id": "shadow-ball"})
        assert admitted["status"] == "admitted"
    if resolved:
        # The command, if any, is independent of the strict observed replay.
        if command:
            # Strategy evidence is retained before a direct command in production.
            raise AssertionError("attach strategy before command in this fixture")
        _attach(transition, boundary, kwargs)
        assert _attempt(transition, boundary, kwargs)["status"] == "resolved"
    source = SessionBoundBattleTerminalOutcomeEvidenceSource.create(
        session_id="replay", battle_id="replay", source_id="first-person:replay",
        source_kind="first_person_battle_stream")["source"]
    if result is not None:
        admitted = source.admit_final_declaration(
            captured_session_id="replay", captured_battle_id="replay",
            declaring_source_id=source.source_id, source_terminal_event_id="final-1",
            source_event_sequence=10, declared_result=result, termination_cause=cause,
            turn_number=1, source_cause_event_id="cause-1")
        assert admitted["status"] == "admitted", admitted
    if stream_end:
        assert source.record_stream_end_without_declaration(
            captured_session_id="replay", captured_battle_id="replay",
            declaring_source_id=source.source_id, source_stream_end_event_id="eof-1",
            source_event_sequence=10)["status"] == "admitted"
    return decision, transition, source, boundary, kwargs


def _export(case, *, competition="unknown", metadata=None):
    decision, transition, source, _, _ = case
    return materialize_c6_production_battle_export(
        session_id="replay", battle_id="replay", decision_captures=(decision,),
        transition_captures=(transition,), terminal_source=source,
        competition_context=competition, optional_population_metadata=metadata)


@pytest.mark.parametrize("result,value", [("self", 1), ("opponent", -1), ("tie", 0)])
@pytest.mark.parametrize("cause", ["all_fainted", "rules_based"])
def test_direct_terminal_result_reuses_episode_binding_context_and_target(result, value, cause):
    bundle = _export(_case(result=result, cause=cause))
    assert bundle["offline_episode"]["schema_version"] == "offline-strategy-episode-v1"
    assert bundle["terminal_binding"]["terminal_outcome"]["declared_result"] == result
    assert bundle["terminal_binding"]["terminal_outcome"]["termination_cause"] == cause
    assert bundle["population_context"]["sampling_context"]["collection_mode"] == "first_person_capture"
    assert bundle["population_context"]["sampling_context"]["competition_context"] == "unknown"
    assert bundle["terminal_learning_target"]["target"] == {
        "availability": "available", "value": value,
        "semantics": "terminal_outcome_self_perspective"}
    assert "evaluation_partition" not in bundle
    assert "evaluation_split_id" not in bundle


@pytest.mark.parametrize("cause", ["forfeit_opponent", "inactivity_opponent", "administrative"])
def test_excluded_cause_preserves_raw_result_without_target(cause):
    bundle = _export(_case(result="self", cause=cause))
    assert bundle["terminal_binding"]["terminal_outcome"]["declared_result"] == "self"
    assert bundle["terminal_learning_target"]["target"] == {
        "availability": "unavailable", "reason": "termination_cause_not_admitted_v1"}


@pytest.mark.parametrize("stream_end,reason", [(False, "terminal_declaration_not_observed"),
                                                  (True, "stream_ended_without_declaration")])
def test_missing_or_stream_end_never_fabricates_result_or_target(stream_end, reason):
    bundle = _export(_case(stream_end=stream_end))
    assert bundle["terminal_binding"]["terminal_outcome"]["reason"] == reason
    assert bundle["terminal_learning_target"]["target"] == {"availability": "unavailable", "reason": reason}
    assert bundle["terminal_evidence_snapshot"]["terminal_evidence"] is None


def test_pending_decision_is_not_an_episode_and_direct_command_has_separate_coverage():
    decision, transition, source, boundary, _ = _case(resolved=False, command=True)
    bundle = _export((decision, transition, source, boundary, None))
    assert bundle["episode_availability"] == {
        "availability": "unavailable", "reason": "no_resolved_observed_transitions"}
    assert bundle["offline_episode"] is None and bundle["terminal_learning_target"] is None
    assert bundle["coverage"]["command_without_transition_boundary_ids"] == (boundary,)
    assert bundle["coverage"]["resolved_transition_count"] == 0


def test_resolved_transition_without_direct_command_remains_auditable():
    bundle = _export(_case(result="self"))
    boundary = bundle["coverage"]["opportunity_boundary_ids"][0]
    assert bundle["coverage"]["transition_without_command_boundary_ids"] == (boundary,)
    assert bundle["transition_capture_snapshots"][0]["resolved_transition_records"][0]["boundary_id"] == boundary
    assert bundle["coverage"]["direct_command_count"] == 0


def test_direct_command_and_resolved_transition_are_counted_independently():
    kwargs = _attack_case()
    decision, transition, boundary = _owners(kwargs, turn=1)
    _attach(transition, boundary, kwargs)
    admitted = decision.confirm_submitted_command(
        captured_session_id="replay", captured_battle_id="replay", boundary_id=boundary,
        actor=decision.opportunity_source.actor, confirmation_event_id="direct-choice",
        command_payload={"kind": "attack", "move_id": "shadow-ball"})
    assert admitted["status"] == "admitted"
    assert _attempt(transition, boundary, kwargs)["status"] == "resolved"
    source = SessionBoundBattleTerminalOutcomeEvidenceSource.create(
        session_id="replay", battle_id="replay", source_id="first-person:replay",
        source_kind="first_person_battle_stream")["source"]
    bundle = _export((decision, transition, source, boundary, kwargs))
    assert bundle["coverage"]["direct_command_count"] == 1
    assert bundle["coverage"]["resolved_transition_count"] == 1
    assert bundle["coverage"]["command_without_transition_boundary_ids"] == ()
    assert bundle["coverage"]["transition_without_command_boundary_ids"] == ()


def test_conflicting_decision_rules_context_rejected():
    case = _case(result="self")
    decision, _, _, _, _ = case
    actor = decision.opportunity_source.actor
    additional = decision.begin_decision_capture(
        captured_session_id="replay", captured_battle_id="replay", actor=actor,
        opportunity_id="different-rules", decision_kind="turn_start", turn_number=2,
        simultaneity_group_id="turn-2",
        context_reference={"ruleset_id": "other-rules", "mechanics_version": "explicit-mechanics",
                           "protocol_version": "explicit-protocol", "battle_format_id": "explicit-singles"},
        legal_action_set={"status": "unknown", "action_ids": []},
        public_snapshot={
            "active": {"self": {"session_id": "replay", "slot_index": 0, "pokemon_id": "self-a"},
                       "opponent": {"session_id": "replay", "slot_index": 0, "pokemon_id": "opponent-a"}},
            "field": {}, "sides": {"self": {}, "opponent": {}},
            "opponent_revealed_moves": {"status": "unknown", "move_ids": []}},
        private_snapshot={"roster_scope": {"status": "partial", "slot_indices": [0]},
                          "own_roster": [{"slot_index": 0, "pokemon_id": "self-a"}]})
    assert additional["status"] == "captured"
    assert _export(case)["reason"] == "conflicting_battle_rules_context"


def test_foreign_source_and_context_conflict_fail_closed():
    case = _case(result="self")
    decision, transition, _, _, _ = case
    foreign = SessionBoundBattleTerminalOutcomeEvidenceSource.create(
        session_id="foreign", battle_id="foreign", source_id="foreign",
        source_kind="first_person_battle_stream")["source"]
    assert materialize_c6_production_battle_export(
        session_id="replay", battle_id="replay", decision_captures=(decision,),
        transition_captures=(transition,), terminal_source=foreign,
        competition_context="unknown")["status"] == "rejected"
    assert _export(case, metadata={"competition_context": "ladder"})["status"] == "rejected"


def test_deterministic_durable_json_idempotence_and_conflict(tmp_path):
    case = _case(result="self")
    first = _export(case)
    second = _export(case)
    assert first == second and first["export_id"] == second["export_id"]
    assert isinstance(first, MappingProxyType)
    with pytest.raises(TypeError):
        first["coverage"]["opportunity_count"] = 0
    path = tmp_path / "battle.json"
    receipt = write_c6_production_battle_export(export_bundle=first, output_path=path)
    assert receipt["status"] == "written" and receipt["write_disposition"] == "created"
    assert json.loads(path.read_text(encoding="utf-8"))["export_id"] == first["export_id"]
    assert write_c6_production_battle_export(export_bundle=first, output_path=path)["write_disposition"] == "identical_existing"
    assert write_c6_production_battle_export(
        export_bundle=first, output_path=tmp_path / "other.json")["export_id"] == first["export_id"]
    path.write_text("foreign content", encoding="utf-8")
    assert write_c6_production_battle_export(export_bundle=first, output_path=path)["reason"] == "destination_content_conflict"


def test_caller_owner_order_and_source_evidence_are_stable():
    case = _case(result="self")
    decision, transition, source, _, _ = case
    other = ProductionDecisionCapture.create(
        session_id="replay", battle_id="replay", actor=decision.opportunity_source.actor,
        source_id="production:replay:second-owner")["source"]
    before = source.read_snapshot(captured_session_id="replay", captured_battle_id="replay")
    first = materialize_c6_production_battle_export(
        session_id="replay", battle_id="replay", decision_captures=(decision, other),
        transition_captures=(transition,), terminal_source=source,
        competition_context="unknown")
    reversed_order = materialize_c6_production_battle_export(
        session_id="replay", battle_id="replay", decision_captures=(other, decision),
        transition_captures=(transition,), terminal_source=source,
        competition_context="unknown")
    assert first == reversed_order and first["export_id"] == reversed_order["export_id"]
    assert source.read_snapshot(captured_session_id="replay", captured_battle_id="replay") == before


def test_main_window_terminal_ingress_and_new_battle_reset_preserve_written_archive(tmp_path):
    window = _Harness()
    window._c6_decision_capture_owners = {}
    window._c6_transition_capture_owners = {}
    session = MainWindow._active_session_id(window)
    source = MainWindow._c6_battle_terminal_source(window)
    assert source.session_id == session
    empty = MainWindow.materialize_c6_battle_export(window, competition_context="unknown")
    assert empty["terminal_evidence_snapshot"]["outcome_evidence"] is None
    assert empty["offline_episode"] is None
    event = MainWindow.admit_c6_terminal_declaration(
        window, captured_session_id=session, captured_battle_id=session,
        declaring_source_id=source.source_id, source_terminal_event_id="first-person-final",
        source_event_sequence=1, declared_result="self", termination_cause="rules_based",
        source_cause_event_id="first-person-cause")
    assert event["status"] == "admitted"
    saved = MainWindow.save_c6_battle_export(
        window, output_path=tmp_path / "production.json", competition_context="unknown")
    assert saved["status"] == "written"
    assert MainWindow.begin_new_battle(window) == "ui-session-1"
    assert window._c6_terminal_outcome_source is None
    assert (tmp_path / "production.json").is_file()
    new_export = MainWindow.materialize_c6_battle_export(window, competition_context="unknown")
    assert new_export["terminal_evidence_snapshot"]["outcome_evidence"] is None
    assert new_export["export_id"] != empty["export_id"]
