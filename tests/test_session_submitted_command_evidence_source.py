from copy import deepcopy

import pytest

from llm.advisor_offline_decision_point_provenance import (
    fingerprint_decision_channel_prefix, materialize_offline_decision_point,
)
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource
from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource
from tests.test_offline_strategy_transition_replay import _attack_case, _run
from tests.test_offline_decision_point_provenance import _case as _replay_boundary_case
from tests.test_session_decision_opportunity_source import _capture, _inputs


def _case(*, kind="turn_start", legal=None, channel="actor_first_person"):
    opportunity_source, actor, context, default_legal = _inputs(channel=channel)
    legal = default_legal if legal is None else legal
    opportunity = _capture(opportunity_source, actor, context, legal, kind=kind)
    assert opportunity["status"] == "captured", opportunity
    command_created = SessionBoundSubmittedCommandEvidenceSource.create(
        opportunity_source=opportunity_source, source_id="direct-command-log-a",
    )
    assert command_created["status"] == "source_ready"
    return opportunity_source, command_created["source"], opportunity, actor


def _admit(source, opportunity, actor, command, *, command_id="input-1", session="session-a"):
    return source.admit_submitted_command(
        captured_session_id=session, opportunity_record=opportunity,
        actor=actor, source_command_id=command_id, command_payload=command,
    )


def _decision(opportunity, *, evidence=None, source=None, execution_replay=None):
    return materialize_offline_decision_point(
        boundary_certificate=opportunity["certificate"],
        channel_source=opportunity["channel_source"],
        context_reference=opportunity["context_reference"],
        legal_action_set=opportunity["legal_action_set"],
        post_boundary_end_sequence=opportunity["certificate"]["after_event_sequence"],
        selected_choice_evidence=evidence, submitted_command_source=source,
        execution_replay=execution_replay,
    )


def test_direct_attack_survives_without_execution_and_only_enters_post_boundary():
    opportunity_source, source, opportunity, actor = _case()
    before_opportunity = opportunity_source.read_snapshot(captured_session_id="session-a")
    result = _admit(source, opportunity, actor, {"kind": "attack", "move_slot": 2})
    assert result["status"] == "admitted", result
    evidence = result["evidence"]
    assert evidence["command_payload"] == {"kind": "attack", "move_slot": 2}
    assert "move_id" not in evidence["command_payload"]
    decision = _decision(opportunity, evidence=evidence, source=source)
    assert decision["status"] == "contract_validated", decision
    assert decision["post_boundary"]["selected_choice_evidence"]["status"] == "direct"
    assert decision["post_boundary"]["selected_choice_evidence"]["selected_choice"] == {"kind": "attack", "move_slot": 2}
    assert decision["post_boundary"]["execution_replay_link"] is None
    assert "selected_choice" not in decision["pre_boundary"]
    assert decision["pre_boundary"] == _decision(opportunity)["pre_boundary"]
    assert decision["pre_boundary"]["actor_completeness"] == "unknown"
    assert decision["pre_boundary"]["legal_action_set"]["status"] == "unknown"
    assert opportunity_source.read_snapshot(captured_session_id="session-a") == before_opportunity


def test_direct_replacement_switch_is_not_an_executed_switch():
    _, source, opportunity, actor = _case(kind="forced_replacement", channel="simulator_input")
    result = _admit(source, opportunity, actor, {"kind": "switch", "incoming_slot_index": 1})
    assert result["status"] == "admitted"
    decision = _decision(opportunity, evidence=result["evidence"], source=source)
    assert decision["status"] == "contract_validated"
    assert decision["post_boundary"]["selected_choice_evidence"]["selected_choice"] == {
        "kind": "switch", "incoming_slot_index": 1,
    }
    assert decision["post_boundary"]["execution_replay_link"] is None


def test_exact_legal_set_stays_exact_without_legality_inference():
    legal = {"status": "exact", "action_ids": ["attack:shadow-ball", "manual_switch:other"]}
    _, source, opportunity, actor = _case(legal=legal)
    result = _admit(source, opportunity, actor, {"kind": "attack", "move_slot": 2})
    decision = _decision(opportunity, evidence=result["evidence"], source=source)
    assert decision["status"] == "contract_validated"
    assert decision["pre_boundary"]["legal_action_set"]["status"] == "exact"
    assert decision["pre_boundary"]["legal_action_set"]["action_ids"] == (
        "attack:shadow-ball", "manual_switch:other",
    )
    assert decision["pre_boundary"]["choice_opportunity"] == "free"
    assert "legal" not in decision["post_boundary"]["selected_choice_evidence"]


def test_exact_duplicate_and_conflicting_second_command():
    _, source, opportunity, actor = _case()
    command = {"kind": "attack", "move_id": "shadow-ball"}
    first = _admit(source, opportunity, actor, command)
    repeated = _admit(source, opportunity, actor, command)
    assert first["status"] == "admitted"
    assert repeated["status"] == "duplicate"
    assert repeated["evidence"] == first["evidence"]
    assert _admit(source, opportunity, actor, {"kind": "attack", "move_id": "other"})["reason"] == "conflicting_submitted_command"
    assert _admit(source, opportunity, actor, command, command_id="input-2")["reason"] == "conflicting_submitted_command"
    assert len(source.read_snapshot(captured_session_id="session-a")["command_evidence"]) == 1


def test_deterministic_command_identity_and_detached_caller_input():
    _, first_source, first_opportunity, first_actor = _case()
    _, second_source, second_opportunity, second_actor = _case()
    command = {"kind": "attack", "move_slot": 1, "move_id": "shadow-ball"}
    before = deepcopy(command)
    first = _admit(first_source, first_opportunity, first_actor, command)["evidence"]
    second = _admit(second_source, second_opportunity, second_actor, command)["evidence"]
    assert command == before
    assert first == second
    assert first["command_id"] == second["command_id"]
    command["move_id"] = "changed-later"
    assert first["command_payload"]["move_id"] == "shadow-ball"
    with pytest.raises(TypeError):
        first["command_payload"]["move_id"] = "changed"


def test_stale_session_actor_and_source_scope_fail_closed():
    opportunity_source, source, opportunity, actor = _case()
    command = {"kind": "attack", "move_slot": 1}
    assert _admit(source, opportunity, actor, command, session="foreign")["reason"] == "stale_or_foreign_session"
    wrong_actor = deepcopy(actor)
    wrong_actor["pokemon_id"] = "foreign"
    assert _admit(source, opportunity, wrong_actor, command)["reason"] == "foreign_actor"
    assert source.read_snapshot(captured_session_id="foreign")["reason"] == "stale_or_foreign_session"
    other_source, other_actor, other_context, other_legal = _inputs(channel="simulator_input")
    other = _capture(other_source, other_actor, other_context, other_legal)
    assert _admit(source, other, actor, command)["reason"] == "opportunity_not_retained_by_source"
    foreign_battle = SessionBoundDecisionOpportunityBoundarySource.create(
        session_id="session-a", battle_id="foreign-battle", source_id="foreign-source",
        channel="actor_first_person", actor=actor,
    )["source"]
    foreign = _capture(foreign_battle, actor, other_context, other_legal)
    assert _admit(source, foreign, actor, command)["reason"] == "opportunity_not_retained_by_source"
    assert opportunity_source.read_snapshot(captured_session_id="session-a")["opportunities"][0]["certificate"] == opportunity["certificate"]


def test_nonexistent_or_handcrafted_boundary_rejected():
    _, source, opportunity, actor = _case()
    command = {"kind": "attack", "move_slot": 1}
    fabricated = {key: value for key, value in opportunity.items()}
    fabricated["certificate"] = {**opportunity["certificate"], "boundary_id": "foreign"}
    assert _admit(source, fabricated, actor, command)["reason"] == "opportunity_not_retained_by_source"
    assert _admit(source, {"certificate": opportunity["certificate"]}, actor, command)["reason"] == "opportunity_not_retained_by_source"


@pytest.mark.parametrize("kind,decision_kind,reason", [
    ({"kind": "attack"}, "turn_start", "submitted_command_payload_invalid"),
    ({"kind": "attack", "move_slot": 0}, "turn_start", "submitted_command_payload_invalid"),
    ({"kind": "attack", "move_slot": True}, "turn_start", "submitted_command_payload_invalid"),
    ({"kind": "attack", "move_slot": 1, "target": "opponent"}, "turn_start", "submitted_command_payload_invalid"),
    ({"kind": "switch"}, "forced_replacement", "submitted_command_payload_invalid"),
    ({"kind": "switch", "incoming_slot_index": -1}, "forced_replacement", "submitted_command_payload_invalid"),
    ({"kind": "switch", "incoming_pokemon_id": ""}, "forced_replacement", "submitted_command_payload_invalid"),
    ({"kind": "attack", "move_slot": 1}, "forced_replacement", "submitted_command_payload_invalid"),
])
def test_malformed_or_incompatible_command_rejected(kind, decision_kind, reason):
    _, source, opportunity, actor = _case(kind=decision_kind)
    assert _admit(source, opportunity, actor, kind)["reason"] == reason


def test_direct_materialization_rejects_arbitrary_claims_and_foreign_owner():
    _, source, opportunity, actor = _case()
    evidence = _admit(source, opportunity, actor, {"kind": "attack", "move_slot": 1})["evidence"]
    assert _decision(opportunity, evidence={"status": "direct", "selected_choice": {"kind": "attack", "move_slot": 1}}, source=source)["reason"] == "direct_choice_authentication_invalid"
    assert _decision(opportunity, evidence=evidence)["reason"] == "direct_choice_producer_unavailable"
    other_source, other_actor, other_context, other_legal = _inputs()
    other_opportunity = _capture(other_source, other_actor, other_context, other_legal, opportunity_id="request-foreign")
    assert _decision(other_opportunity, evidence=evidence, source=source)["reason"] == "direct_choice_authentication_invalid"


def test_command_snapshot_keeps_command_unknown_opportunities():
    opportunity_source, source, opportunity, actor = _case()
    context = dict(opportunity["context_reference"])
    legal = {"status": "unknown", "action_ids": []}
    second = _capture(opportunity_source, actor, context, legal, opportunity_id="request-2", turn=2)
    evidence = _admit(source, opportunity, actor, {"kind": "attack", "move_slot": 1})["evidence"]
    snapshot = source.read_snapshot(captured_session_id="session-a")
    assert tuple(item["command_id"] for item in snapshot["command_evidence"]) == (evidence["command_id"],)
    assert snapshot["command_unknown_boundary_ids"] == (second["certificate"]["boundary_id"],)
    with pytest.raises(TypeError):
        snapshot["command_evidence"][0]["command_payload"]["move_slot"] = 3


def test_execution_replay_alone_remains_distinct_from_direct_command():
    replay = _run(_attack_case())
    assert replay["status"] == "resolved" and replay["action_identity_semantics"] == "observed_executed_action"
    _, source, opportunity, actor = _case()
    assert _decision(opportunity)["post_boundary"]["selected_choice_evidence"]["status"] == "none"
    evidence = _admit(source, opportunity, actor, {"kind": "attack", "move_slot": 1})["evidence"]
    direct = _decision(opportunity, evidence=evidence, source=source)
    assert direct["post_boundary"]["selected_choice_evidence"]["status"] == "direct"
    assert direct["post_boundary"]["execution_replay_link"] is None
    assert _decision(opportunity, evidence=evidence, source=source, execution_replay=replay)["reason"] == "execution_replay_binding_invalid"


def test_valid_execution_link_alone_still_has_no_direct_selected_choice():
    replay = _run(_attack_case())
    args = _replay_boundary_case(cutoff=0)
    args["channel_source"]["events"] = []
    args["boundary_certificate"]["prefix_fingerprint"] = fingerprint_decision_channel_prefix([])
    args["boundary_certificate"]["decision_kind"] = "turn_start"
    args["boundary_certificate"]["sequence_domain"] = "runtime_observation_sequence"
    args["channel_source"]["sequence_domain"] = "runtime_observation_sequence"
    args["boundary_certificate"]["certified_runtime_fingerprint"] = replay["decision_provenance"]["source_runtime_fingerprint"]
    args["post_boundary_end_sequence"] = replay["executed_action"]["observation_sequence"]
    args["execution_replay"] = replay
    decision = materialize_offline_decision_point(**args)
    assert decision["status"] == "contract_validated", decision
    assert decision["post_boundary"]["execution_replay_link"]["transition_id"] == replay["transition_id"]
    assert decision["post_boundary"]["selected_choice_evidence"]["status"] == "none"
