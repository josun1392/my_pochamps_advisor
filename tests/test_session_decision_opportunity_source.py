from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from llm.advisor_offline_decision_point_provenance import materialize_offline_decision_point
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource


def _inputs(*, channel="actor_first_person"):
    actor = {"session_id": "session-a", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    source = SessionBoundDecisionOpportunityBoundarySource.create(
        session_id="session-a", battle_id="battle-a", source_id="first-person-a",
        channel=channel, actor=actor,
    )
    assert source["status"] == "source_ready"
    return source["source"], actor, {
        "ruleset_id": "rules-a", "mechanics_version": "mechanics-a",
        "protocol_version": "protocol-a", "battle_format_id": "format-a",
    }, {"status": "unknown", "action_ids": []}


def _capture(source, actor, context, legal, *, opportunity_id="request-1", kind="turn_start", turn=1):
    return source.capture_opportunity(
        captured_session_id="session-a", opportunity_id=opportunity_id,
        actor=actor, decision_kind=kind, turn_number=turn,
        simultaneity_group_id=f"group-{turn}",
        context_reference=context, legal_action_set=legal,
    )


def _decision(record):
    return materialize_offline_decision_point(
        boundary_certificate=record["certificate"], channel_source=record["channel_source"],
        context_reference=record["context_reference"], legal_action_set=record["legal_action_set"],
        post_boundary_end_sequence=record["certificate"]["after_event_sequence"],
    )


def test_turn_start_opportunity_exists_before_execution_or_choice():
    source, actor, context, legal = _inputs()
    result = _capture(source, actor, context, legal)
    assert result["status"] == "captured", result
    certificate = result["certificate"]
    assert certificate["schema_version"] == "decision-opportunity-boundary-certificate-v1"
    assert certificate["sequence_domain"] == "channel_event_sequence"
    assert certificate["after_event_sequence"] == certificate["prefix_event_count"] == 0
    assert certificate["certified_runtime_fingerprint"] is None
    assert not any("choice" in key or "command" in key or "execution" in key for key in certificate)
    decision = _decision(result)
    assert decision["status"] == "contract_validated", decision
    assert decision["post_boundary"]["selected_choice_evidence"] == {"status": "none", "selected_choice": None}
    assert decision["post_boundary"]["execution_replay_link"] is None
    assert decision["pre_boundary"]["choice_opportunity"] == "unknown"
    snapshot = source.read_snapshot(captured_session_id="session-a")
    assert snapshot["opportunity_scope"] == "admitted_to_this_source_only"
    assert len(snapshot["opportunities"]) == 1


def test_mid_turn_boundary_pins_existing_channel_prefix_and_accepts_later_events():
    source, actor, context, legal = _inputs(channel="simulator_input")
    first = source.admit_channel_event(
        captured_session_id="session-a", source_event_id="stream-1", source_event_fingerprint="a" * 64,
    )
    assert first["status"] == "admitted"
    record = _capture(source, actor, context, legal, kind="mid_turn_replacement", turn=2)
    assert record["status"] == "captured", record
    assert record["certificate"]["after_event_sequence"] == 1
    assert record["certificate"]["decision_kind"] == "mid_turn_replacement"
    assert source.admit_channel_event(
        captured_session_id="session-a", source_event_id="stream-2", source_event_fingerprint="b" * 64,
    )["status"] == "admitted"
    assert _decision(record)["status"] == "contract_validated"
    full = source.read_snapshot(captured_session_id="session-a")["channel_source"]
    as_of_full = materialize_offline_decision_point(
        boundary_certificate=record["certificate"], channel_source=full,
        context_reference=record["context_reference"], legal_action_set=record["legal_action_set"],
        post_boundary_end_sequence=2,
    )
    assert as_of_full["pre_boundary"] == _decision(record)["pre_boundary"]
    assert len(record["channel_source"]["events"]) == 1
    assert len(full["events"]) == 2


def test_exact_legal_set_is_pinned_and_choice_opportunity_is_derived():
    source, actor, context, _ = _inputs()
    legal = {"status": "exact", "action_ids": ["attack:a"]}
    before = deepcopy(legal)
    record = _capture(source, actor, context, legal)
    assert record["status"] == "captured"
    assert legal == before
    assert record["legal_action_set"] == {"status": "exact", "action_ids": ("attack:a",)}
    assert _decision(record)["pre_boundary"]["choice_opportunity"] == "no_free_choice"
    legal["action_ids"].append("attack:b")
    assert record["legal_action_set"]["action_ids"] == ("attack:a",)
    assert _decision(record)["pre_boundary"]["legal_action_set"]["action_ids"] == ("attack:a",)


def test_duplicate_is_idempotent_and_conflicting_identity_fails_closed():
    source, actor, context, legal = _inputs()
    first = _capture(source, actor, context, legal)
    repeated = _capture(source, actor, context, legal)
    assert repeated["status"] == "duplicate"
    assert repeated["certificate"] == first["certificate"]
    changed = deepcopy(context)
    changed["ruleset_id"] = "other-rules"
    assert _capture(source, actor, changed, legal)["reason"] == "conflicting_opportunity"
    assert _capture(source, actor, context, {"status": "partial", "action_ids": ["attack:a"]})["reason"] == "conflicting_opportunity"
    assert _capture(source, actor, context, legal, kind="forced_replacement")["reason"] == "conflicting_opportunity"
    assert len(source.read_snapshot(captured_session_id="session-a")["opportunities"]) == 1


def test_legal_alternative_order_does_not_change_certificate_identity():
    source, actor, context, _ = _inputs()
    first = _capture(source, actor, context, {"status": "exact", "action_ids": ["attack:b", "attack:a"]})
    second = _capture(source, actor, context, {"status": "exact", "action_ids": ["attack:a", "attack:b"]})
    assert first["status"] == "captured"
    assert second["status"] == "duplicate"
    assert first["certificate"] == second["certificate"]
    assert first["legal_action_set"]["action_ids"] == ("attack:a", "attack:b")


def test_prefix_change_for_same_opportunity_is_conflict():
    source, actor, context, legal = _inputs()
    first = _capture(source, actor, context, legal)
    assert source.admit_channel_event(
        captured_session_id="session-a", source_event_id="stream-1", source_event_fingerprint="a" * 64,
    )["status"] == "admitted"
    assert _capture(source, actor, context, legal)["reason"] == "conflicting_opportunity"
    assert first["certificate"]["after_event_sequence"] == 0


def test_stale_session_foreign_actor_and_invalid_source_fail_closed():
    source, actor, context, legal = _inputs()
    assert source.capture_opportunity(
        captured_session_id="foreign", opportunity_id="request-1", actor=actor,
        decision_kind="turn_start", turn_number=1, simultaneity_group_id="group-1",
        context_reference=context, legal_action_set=legal,
    )["reason"] == "stale_or_foreign_session"
    assert source.admit_channel_event(
        captured_session_id="foreign", source_event_id="event-1", source_event_fingerprint="a" * 64,
    )["reason"] == "stale_or_foreign_session"
    assert source.read_snapshot(captured_session_id="foreign")["reason"] == "stale_or_foreign_session"
    wrong = deepcopy(actor)
    wrong["pokemon_id"] = "foreign"
    assert _capture(source, wrong, context, legal)["reason"] == "foreign_actor"
    assert SessionBoundDecisionOpportunityBoundarySource.create(
        session_id="session-a", battle_id="battle-a", source_id="source-a",
        channel="spectator", actor=actor,
    )["reason"] == "source_channel_invalid"
    with pytest.raises(FrozenInstanceError):
        source.session_id = "foreign"
    with pytest.raises(TypeError):
        source.actor["pokemon_id"] = "foreign"


@pytest.mark.parametrize("field,value,reason", [
    ("context", {"ruleset_id": ""}, "context_reference_invalid"),
    ("legal", {"status": "exact", "action_ids": []}, "legal_action_set_invalid"),
    ("kind", "invalid", "opportunity_boundary_invalid"),
    ("turn", 0, "opportunity_boundary_invalid"),
])
def test_malformed_opportunity_input_rejected(field, value, reason):
    source, actor, context, legal = _inputs()
    args = {"source": source, "actor": actor, "context": context, "legal": legal, "kind": "turn_start", "turn": 1}
    if field == "context":
        context.update(value)
    elif field == "legal":
        args["legal"] = value
    else:
        args[field] = value
    assert _capture(**args)["reason"] == reason


def test_malformed_channel_reference_and_event_duplicate_rejected():
    source, _, _, _ = _inputs()
    assert source.admit_channel_event(
        captured_session_id="session-a", source_event_id="event-1", source_event_fingerprint="bad",
    )["reason"] == "source_event_reference_invalid"
    first = source.admit_channel_event(
        captured_session_id="session-a", source_event_id="event-1", source_event_fingerprint="a" * 64,
    )
    assert first["status"] == "admitted"
    assert source.admit_channel_event(
        captured_session_id="session-a", source_event_id="event-1", source_event_fingerprint="a" * 64,
    )["status"] == "duplicate"
    assert source.admit_channel_event(
        captured_session_id="session-a", source_event_id="event-1", source_event_fingerprint="b" * 64,
    )["reason"] == "conflicting_source_event"
    assert len(source.read_snapshot(captured_session_id="session-a")["channel_source"]["events"]) == 1


def test_equivalent_sources_emit_identical_certificates_and_ordered_snapshots():
    first_source, first_actor, first_context, first_legal = _inputs()
    second_source, second_actor, second_context, second_legal = _inputs()
    first = _capture(first_source, first_actor, first_context, first_legal)
    second = _capture(second_source, second_actor, second_context, second_legal)
    assert first["certificate"] == second["certificate"]
    assert _decision(first) == _decision(second)
    _capture(first_source, first_actor, first_context, first_legal, opportunity_id="request-2", turn=2)
    snapshot = first_source.read_snapshot(captured_session_id="session-a")
    ids = tuple(item["certificate"]["boundary_id"] for item in snapshot["opportunities"])
    assert ids == tuple(sorted(ids))
    with pytest.raises(TypeError):
        snapshot["opportunities"][0]["certificate"]["turn_number"] = 999


def test_caller_mutation_never_rewrites_captured_boundary():
    source, actor, context, legal = _inputs()
    inputs_before = deepcopy((actor, context, legal))
    record = _capture(source, actor, context, legal)
    assert (actor, context, legal) == inputs_before
    actor["pokemon_id"] = "changed-after-capture"
    context["ruleset_id"] = "changed-after-capture"
    legal["status"] = "exact"
    legal["action_ids"] = ["attack:a"]
    assert record["certificate"]["actor"]["pokemon_id"] == "self-a"
    assert record["context_reference"]["ruleset_id"] == "rules-a"
    assert record["legal_action_set"]["status"] == "unknown"
    assert _decision(record)["status"] == "contract_validated"
