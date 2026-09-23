from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from llm.advisor_session_battle_terminal_outcome_evidence import (
    SessionBoundBattleTerminalOutcomeEvidenceSource,
)
from tests.test_offline_strategy_transition_replay import _attack_case


def _source(kind="first_person_battle_stream"):
    created = SessionBoundBattleTerminalOutcomeEvidenceSource.create(
        session_id="session-a", battle_id="battle-a", source_id="final-stream-a", source_kind=kind,
    )
    assert created["status"] == "source_ready"
    return created["source"]


def _final(source, result="self", cause="all_fainted", **changes):
    args = {
        "captured_session_id": "session-a", "captured_battle_id": "battle-a",
        "declaring_source_id": "final-stream-a", "source_terminal_event_id": "final-5",
        "source_event_sequence": 5, "declared_result": result,
        "termination_cause": cause, "turn_number": 8,
        "source_cause_event_id": "final-5" if cause != "unknown" else None,
    }
    args.update(changes)
    return source.admit_final_declaration(**args)


def _end(source, **changes):
    args = {
        "captured_session_id": "session-a", "captured_battle_id": "battle-a",
        "declaring_source_id": "final-stream-a", "source_stream_end_event_id": "stream-end-5",
        "source_event_sequence": 5,
    }
    args.update(changes)
    return source.record_stream_end_without_declaration(**args)


@pytest.mark.parametrize("result", ["self", "opponent", "tie"])
def test_direct_final_declaration_preserves_result_without_reward(result):
    source = _source()
    initial = source.read_snapshot(captured_session_id="session-a", captured_battle_id="battle-a")
    assert initial["outcome_evidence"] is None
    assert initial["terminality_availability"] == "unavailable"
    admitted = _final(source, result=result, cause="unknown", turn_number=None)
    assert admitted["status"] == "admitted", admitted
    evidence = admitted["evidence"]
    assert evidence["declared_result"] == result
    assert evidence["termination_cause"] == "unknown"
    assert evidence["evidence_completeness"] == "final_declaration_observed"
    assert evidence["authority"] == "direct_final_declaration"
    assert evidence["source_terminal_event_id"] == "final-5"
    assert evidence["turn_number"] is None
    assert evidence["battle_terminal"] is True
    assert "reward" not in evidence and "utility" not in evidence and "score" not in evidence
    snapshot = source.read_snapshot(captured_session_id="session-a", captured_battle_id="battle-a")
    assert snapshot["terminal_evidence"] == evidence
    assert snapshot["outcome_evidence"] == evidence
    assert snapshot["terminality_availability"] == "observed"
    assert snapshot["stream_end_evidence"] is None


@pytest.mark.parametrize("result,cause", [
    ("self", "all_fainted"),
    ("opponent", "forfeit_self"),
    ("self", "forfeit_opponent"),
    ("opponent", "inactivity_self"),
    ("self", "inactivity_opponent"),
    ("tie", "rules_based"),
    ("opponent", "administrative"),
    ("tie", "server_error"),
    ("self", "unrecognized"),
])
def test_direct_termination_cause_is_independent_of_declared_result(result, cause):
    source = _source(kind="simulator_output")
    evidence = _final(source, result=result, cause=cause, raw_termination_cause=cause)["evidence"]
    assert evidence["declared_result"] == result
    assert evidence["termination_cause"] == cause
    assert evidence["raw_termination_cause"] == cause
    assert evidence["source_cause_event_id"] == "final-5"
    assert evidence["source_kind"] == "simulator_output"


def test_inactivity_raw_token_is_preserved_without_disconnect_inference():
    evidence = _final(_source(), result="opponent", cause="inactivity_self", raw_termination_cause="timeout")
    assert evidence["status"] == "admitted"
    assert evidence["evidence"]["termination_cause"] == "inactivity_self"
    assert evidence["evidence"]["raw_termination_cause"] == "timeout"
    assert "disconnect" not in evidence["evidence"]


def test_stream_end_without_final_declaration_is_nonterminal_and_fail_closed():
    source = _source()
    end = _end(source)
    assert end["status"] == "admitted"
    evidence = end["evidence"]
    assert evidence["declared_result"] == "none_observed"
    assert evidence["termination_cause"] == "unknown"
    assert evidence["evidence_completeness"] == "stream_ended_without_declaration"
    assert evidence["battle_terminal"] is False
    assert evidence["source_stream_end_event_id"] == "stream-end-5"
    snapshot = source.read_snapshot(captured_session_id="session-a", captured_battle_id="battle-a")
    assert snapshot["terminal_evidence"] is None
    assert snapshot["outcome_evidence"] == evidence
    assert snapshot["terminality_availability"] == "unavailable"
    assert _final(source)["reason"] == "declaration_after_stream_end"
    assert _end(source)["status"] == "duplicate"
    assert _end(source, source_stream_end_event_id="different-end")["reason"] == "conflicting_stream_end_evidence"


def test_exact_duplicate_and_conflicting_final_declarations():
    source = _source()
    first = _final(source, result="self", cause="all_fainted")
    assert first["status"] == "admitted"
    assert _final(source, result="self", cause="all_fainted")["status"] == "duplicate"
    assert _final(source, result="opponent", cause="all_fainted")["reason"] == "conflicting_final_declaration"
    assert _final(source, result="tie", cause="all_fainted")["reason"] == "conflicting_final_declaration"
    assert _final(source, result="self", cause="forfeit_opponent")["reason"] == "conflicting_final_declaration"
    assert _final(source, result="self", cause="all_fainted", source_terminal_event_id="other-final")["reason"] == "conflicting_final_declaration"
    assert source.read_snapshot(captured_session_id="session-a", captured_battle_id="battle-a")["terminal_evidence"] == first["evidence"]
    assert _end(source)["reason"] == "final_declaration_already_observed"


@pytest.mark.parametrize("change,reason", [
    ({"captured_session_id": "foreign"}, "stale_or_foreign_session"),
    ({"captured_battle_id": "foreign"}, "foreign_battle"),
    ({"declaring_source_id": "foreign"}, "foreign_declaring_source"),
    ({"declared_result": "none_observed"}, "declared_result_invalid"),
    ({"declared_result": "winner"}, "declared_result_invalid"),
    ({"termination_cause": "disconnect"}, "termination_cause_invalid"),
    ({"source_cause_event_id": None}, "direct_cause_provenance_missing"),
    ({"source_terminal_event_id": ""}, "final_declaration_provenance_invalid"),
    ({"source_event_sequence": 0}, "final_declaration_provenance_invalid"),
    ({"turn_number": True}, "final_declaration_provenance_invalid"),
])
def test_foreign_or_malformed_final_declaration_rejected(change, reason):
    assert _final(_source(), **change)["reason"] == reason


def test_stream_end_scope_and_source_kind_validation():
    source = _source()
    assert _end(source, captured_session_id="foreign")["reason"] == "stale_or_foreign_session"
    assert _end(source, captured_battle_id="foreign")["reason"] == "foreign_battle"
    assert _end(source, declaring_source_id="foreign")["reason"] == "foreign_declaring_source"
    assert SessionBoundBattleTerminalOutcomeEvidenceSource.create(
        session_id="session-a", battle_id="battle-a", source_id="final-stream-a", source_kind="prediction",
    )["reason"] == "source_kind_invalid"
    with pytest.raises(FrozenInstanceError):
        source.battle_id = "foreign"


def test_deterministic_detached_evidence_and_no_runtime_or_ledger_mutation():
    first_source, second_source = _source(), _source()
    replay_inputs = _attack_case()
    runtime_before = deepcopy(replay_inputs["decision_runtime_snapshot"])
    ledger_before = deepcopy(replay_inputs["predictive_ledger"])
    args = {
        "captured_session_id": "session-a", "captured_battle_id": "battle-a",
        "declaring_source_id": "final-stream-a", "source_terminal_event_id": "final-5",
        "source_event_sequence": 5, "declared_result": "opponent",
        "termination_cause": "forfeit_self", "turn_number": 8,
        "source_cause_event_id": "final-5",
    }
    before = deepcopy(args)
    first = first_source.admit_final_declaration(**args)["evidence"]
    second = second_source.admit_final_declaration(**args)["evidence"]
    assert first == second and first["evidence_id"] == second["evidence_id"]
    assert args == before
    args["declared_result"] = "self"
    assert first["declared_result"] == "opponent"
    assert replay_inputs["decision_runtime_snapshot"] == runtime_before
    assert replay_inputs["predictive_ledger"] == ledger_before
    with pytest.raises(TypeError):
        first["declared_result"] = "self"
    with pytest.raises(TypeError):
        first_source.read_snapshot(captured_session_id="session-a", captured_battle_id="battle-a")["terminal_evidence"]["termination_cause"] = "unknown"
