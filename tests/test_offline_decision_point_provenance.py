from copy import deepcopy

import pytest

from llm.advisor_offline_decision_point_provenance import (
    BOUNDARY_SCHEMA, CHANNEL_SOURCE_SCHEMA,
    fingerprint_decision_channel_prefix, fingerprint_decision_contract_reference,
    materialize_offline_decision_point,
    materialize_offline_decision_point_collection,
)
from tests.test_offline_strategy_transition_replay import _attack_case, _run


def _case(*, channel="actor_first_person", cutoff=2):
    actor = {"session_id": "replay", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    events = [
        {"sequence": 1, "available_at_sequence": 1, "session_id": "replay", "channel": channel,
         "event_kind": "public_turn_event", "payload": {"turn": 1}},
        {"sequence": 2, "available_at_sequence": 2, "session_id": "replay", "channel": channel,
         "event_kind": "public_opponent_action", "payload": {"move": "observed-before-replacement"}},
        {"sequence": 3, "available_at_sequence": 3, "session_id": "replay", "channel": channel,
         "event_kind": "later_item_reveal", "payload": {"item": "revealed-later"}},
    ]
    source = {
        "schema_version": CHANNEL_SOURCE_SCHEMA, "source_id": "fixture-channel", "session_id": "replay",
        "battle_id": "battle-1", "channel": channel,
        "sequence_domain": "channel_event_sequence",
        "channel_actor": None if channel == "spectator" else deepcopy(actor), "events": events,
    }
    context = {
        "ruleset_id": "fixture-rules", "mechanics_version": "fixture-mechanics",
        "protocol_version": "fixture-protocol", "battle_format_id": "fixture-format",
    }
    legal = {"status": "unknown", "action_ids": []}
    boundary = {
        "schema_version": BOUNDARY_SCHEMA, "source_id": "fixture-channel", "session_id": "replay",
        "battle_id": "battle-1", "boundary_id": "decision-1", "simultaneity_group_id": "group-1",
        "channel": channel, "actor": actor, "decision_kind": "mid_turn_replacement", "turn_number": 1,
        "sequence_domain": "channel_event_sequence", "certified_runtime_fingerprint": None,
        "after_event_sequence": cutoff,
        "prefix_event_count": cutoff,
        "prefix_fingerprint": fingerprint_decision_channel_prefix(events[:cutoff]),
        "context_fingerprint": fingerprint_decision_contract_reference(context),
        "legal_action_set_fingerprint": fingerprint_decision_contract_reference(legal),
    }
    return {
        "boundary_certificate": boundary, "channel_source": source,
        "context_reference": context,
        "legal_action_set": legal,
        "post_boundary_end_sequence": 3,
    }


def _materialize(kwargs):
    return materialize_offline_decision_point(**kwargs)


def test_pre_boundary_equals_physical_truncation_and_ignores_later_reveal():
    args = _case()
    original = deepcopy(args)
    full = _materialize(args)
    assert full["status"] == "contract_validated", full
    truncated = deepcopy(args)
    truncated["channel_source"]["events"] = truncated["channel_source"]["events"][:2]
    assert full["pre_boundary"] == _materialize(truncated)["pre_boundary"]
    args["channel_source"]["events"][2]["payload"]["item"] = "different-later-reveal"
    assert full["pre_boundary"] == _materialize(args)["pre_boundary"]
    assert original["channel_source"]["events"][0] == args["channel_source"]["events"][0]
    assert full["pre_boundary"]["prefix_events"][1]["event_kind"] == "public_opponent_action"
    assert all(row["event_kind"] != "later_item_reveal" for row in full["pre_boundary"]["prefix_events"])


def test_unknown_choice_survives_without_observed_execution_on_spectator_channel():
    args = _case(channel="spectator")
    row = _materialize(args)
    assert row["status"] == "contract_validated"
    assert row["pre_boundary"]["actor_completeness"] == "not_complete"
    assert row["pre_boundary"]["opportunity_completeness"] == "unproven_without_boundary_producer"
    assert row["post_boundary"]["selected_choice_evidence"] == {"status": "none", "selected_choice": None}
    assert row["post_boundary"]["execution_replay_link"] is None
    assert "post_boundary" not in row["pre_boundary"]


def test_legal_set_and_choice_opportunity_are_derived_without_defaulting_unknown():
    args = _case()
    assert _materialize(args)["pre_boundary"]["choice_opportunity"] == "unknown"
    args["legal_action_set"] = {"status": "partial", "action_ids": ["attack:a"]}
    args["boundary_certificate"]["legal_action_set_fingerprint"] = fingerprint_decision_contract_reference(args["legal_action_set"])
    assert _materialize(args)["pre_boundary"]["choice_opportunity"] == "unknown"
    args["legal_action_set"] = {"status": "exact", "action_ids": ["attack:a"]}
    args["boundary_certificate"]["legal_action_set_fingerprint"] = fingerprint_decision_contract_reference(args["legal_action_set"])
    assert _materialize(args)["pre_boundary"]["choice_opportunity"] == "no_free_choice"
    args["legal_action_set"] = {"status": "exact", "action_ids": ["manual_switch:b", "attack:a"]}
    args["boundary_certificate"]["legal_action_set_fingerprint"] = fingerprint_decision_contract_reference(args["legal_action_set"])
    row = _materialize(args)
    assert row["pre_boundary"]["choice_opportunity"] == "free"
    assert row["pre_boundary"]["legal_action_set"]["action_ids"] == ("attack:a", "manual_switch:b")


def test_observed_execution_links_only_post_boundary_and_never_authenticates_choice():
    replay = _run(_attack_case())
    assert replay["status"] == "resolved"
    args = _case(cutoff=0)
    args["channel_source"]["events"] = []
    args["boundary_certificate"]["prefix_fingerprint"] = fingerprint_decision_channel_prefix([])
    args["boundary_certificate"]["prefix_event_count"] = 0
    args["boundary_certificate"]["decision_kind"] = "turn_start"
    args["boundary_certificate"]["sequence_domain"] = "runtime_observation_sequence"
    args["channel_source"]["sequence_domain"] = "runtime_observation_sequence"
    args["boundary_certificate"]["certified_runtime_fingerprint"] = replay["decision_provenance"]["source_runtime_fingerprint"]
    args["execution_replay"] = replay
    args["post_boundary_end_sequence"] = replay["executed_action"]["observation_sequence"]
    row = _materialize(args)
    assert row["status"] == "contract_validated", row
    assert row["post_boundary"]["execution_replay_link"]["transition_id"] == replay["transition_id"]
    assert row["post_boundary"]["execution_replay_link"]["action_identity_semantics"] == "observed_executed_action"
    assert row["post_boundary"]["selected_choice_evidence"]["selected_choice"] is None
    assert replay["action_identity_semantics"] == "observed_executed_action"
    assert "executed_action" not in row["pre_boundary"]


def test_execution_link_requires_same_sequence_domain_and_decision_fingerprint():
    replay = _run(_attack_case())
    args = _case(cutoff=0)
    args["channel_source"]["events"] = []
    args["boundary_certificate"]["prefix_fingerprint"] = fingerprint_decision_channel_prefix([])
    args["execution_replay"] = replay
    args["post_boundary_end_sequence"] = replay["executed_action"]["observation_sequence"]
    assert _materialize(args)["reason"] == "execution_replay_binding_invalid"
    args["boundary_certificate"]["sequence_domain"] = "runtime_observation_sequence"
    args["channel_source"]["sequence_domain"] = "runtime_observation_sequence"
    args["boundary_certificate"]["certified_runtime_fingerprint"] = "0" * 64
    assert _materialize(args)["reason"] == "execution_replay_binding_invalid"


@pytest.mark.parametrize("change,reason", [
    (lambda x: x["channel_source"].update(session_id="other"), "channel_source_or_actor_mismatch"),
    (lambda x: x["channel_source"]["channel_actor"].update(pokemon_id="wrong"), "channel_source_or_actor_mismatch"),
    (lambda x: x["boundary_certificate"].update(after_event_sequence=-1), "boundary_certificate_invalid"),
    (lambda x: x["context_reference"].update(protocol_version=""), "context_reference_invalid"),
    (lambda x: x["boundary_certificate"].update(channel="invalid"), "boundary_certificate_invalid"),
    (lambda x: x["boundary_certificate"].update(prefix_fingerprint="0" * 64), "prefix_fingerprint_mismatch"),
    (lambda x: x["boundary_certificate"].update(context_fingerprint="0" * 64), "boundary_reference_fingerprint_mismatch"),
    (lambda x: x["boundary_certificate"].update(legal_action_set_fingerprint="0" * 64), "boundary_reference_fingerprint_mismatch"),
    (lambda x: x["channel_source"]["events"][1].update(available_at_sequence=3), "future_or_foreign_event_in_pre_boundary"),
    (lambda x: x["legal_action_set"].update(status="unknown", action_ids=["attack:a"]), "legal_action_set_invalid"),
])
def test_malformed_or_foreign_input_fails_closed(change, reason):
    args = _case()
    change(args)
    assert _materialize(args)["reason"] == reason


def test_direct_choice_cannot_be_claimed_without_a_command_producer():
    args = _case()
    args["selected_choice_evidence"] = {"status": "direct", "selected_choice": "attack:a"}
    assert _materialize(args)["reason"] == "direct_choice_producer_unavailable"
    args["selected_choice_evidence"] = {"status": "not_applicable"}
    assert _materialize(args)["reason"] == "not_applicable_choice_unproven"
    args["selected_choice_evidence"] = {}
    assert _materialize(args)["reason"] == "selected_choice_evidence_invalid"


def test_determinism_detachment_and_boundary_identity_conflicts():
    args = _case()
    before = deepcopy(args)
    first = _materialize(args)
    second = _materialize(args)
    assert first == second and args == before
    with pytest.raises(TypeError):
        first["pre_boundary"]["prefix_events"][0]["payload"]["turn"] = 99
    args["channel_source"]["events"][0]["payload"]["turn"] = 99
    assert first["pre_boundary"]["prefix_events"][0]["payload"]["turn"] == 1
    assert materialize_offline_decision_point_collection([first, second])["reason"] == "duplicate_decision_id"
    changed = _case()
    changed["context_reference"]["ruleset_id"] = "other-rules"
    changed["boundary_certificate"]["context_fingerprint"] = fingerprint_decision_contract_reference(changed["context_reference"])
    conflicting = _materialize(changed)
    assert conflicting["decision_id"] != first["decision_id"]
    assert materialize_offline_decision_point_collection([first, conflicting])["reason"] == "conflicting_decision_boundary"
