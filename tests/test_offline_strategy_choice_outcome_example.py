"""Canonical observational decision, direct choice, and terminal outcome joins."""
from copy import deepcopy

import pytest

from llm.advisor_offline_decision_point_provenance import _freeze
from llm.advisor_offline_strategy_choice_outcome_example import (
    materialize_offline_strategy_choice_outcome_example as assemble,
)
from llm.advisor_offline_strategy_evaluation_split import (
    materialize_offline_strategy_evaluation_split as split,
)
from llm.advisor_offline_strategy_terminal_learning_target import (
    materialize_offline_strategy_terminal_learning_target as target,
)
from llm.advisor_session_actor_private_decision_information import (
    SessionBoundActorPrivateDecisionInformationSource,
)
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource
from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource
from tests.test_offline_strategy_episode_dataset import _editable
from tests.test_offline_strategy_terminal_learning_target import _case as _target_case
from tests.test_session_actor_private_decision_information import _snapshot
from tests.test_offline_strategy_transition_replay import _attack_case, _run


RULES = {
    "ruleset_id": "rules-a", "mechanics_version": "mechanics-a",
    "protocol_version": "protocol-a", "battle_format_id": "format-a",
}


def _bundle(
    *, channel="actor_first_person", command=None, legal=None, private_snapshot=None,
    result="self", cause="all_fainted", partition="train",
    session="replay", battle="battle-1",
):
    actor = {"session_id": session, "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    opportunity_source = SessionBoundDecisionOpportunityBoundarySource.create(
        session_id=session, battle_id=battle, source_id="opportunity-input-1",
        channel=channel, actor=actor,
    )["source"]
    legal = legal if legal is not None else {
        "status": "exact", "action_ids": ["attack:shadow-ball", "attack:protect", "manual_switch:bench-a"],
    }
    opportunity = opportunity_source.capture_opportunity(
        captured_session_id=session, opportunity_id="request-1", actor=actor,
        decision_kind="turn_start", turn_number=1, simultaneity_group_id="turn-1",
        context_reference=RULES, legal_action_set=legal,
    )
    assert opportunity["status"] == "captured", opportunity
    command_source = SessionBoundSubmittedCommandEvidenceSource.create(
        opportunity_source=opportunity_source, source_id="direct-input-1",
    )["source"]
    private_source = SessionBoundActorPrivateDecisionInformationSource.create(
        opportunity_source=opportunity_source, command_source=command_source,
        source_id="private-input-1",
    )["source"]
    raw_private = _snapshot() if private_snapshot is None else private_snapshot
    private = private_source.admit_private_snapshot(
        captured_session_id=session, captured_battle_id=battle,
        opportunity_record=opportunity, actor=actor,
        source_private_event_id="private-1", private_snapshot=raw_private,
    )
    assert private["status"] == "admitted", private
    raw_command = {"kind": "attack", "move_slot": 1} if command is None else command
    submitted = command_source.admit_submitted_command(
        captured_session_id=session, opportunity_record=opportunity, actor=actor,
        source_command_id="command-1", command_payload=raw_command,
    )
    assert submitted["status"] == "admitted", submitted
    context, terminal_source = _target_case(result, cause)
    terminal_target = target(population_context=context, terminal_source=terminal_source)
    assert terminal_target["status"] == "materialized"
    evaluation = split(
        target_records=[terminal_target],
        manifest={terminal_target["target_record_id"]: partition},
    )
    assert evaluation["status"] == "validated"
    return {
        "opportunity_record": opportunity, "opportunity_source": opportunity_source,
        "private_information": private["evidence"], "private_source": private_source,
        "submitted_command": submitted["evidence"], "command_source": command_source,
        "terminal_target": terminal_target, "terminal_source": terminal_source,
        "evaluation_split": evaluation,
    }, raw_private, raw_command


@pytest.mark.parametrize("channel", ["actor_first_person", "simulator_input"])
def test_attack_slot_only_uses_direct_private_move_identity(channel):
    inputs, _, _ = _bundle(channel=channel)
    example = assemble(**inputs)
    assert example["status"] == "materialized"
    assert example["example_availability"] == {"availability": "available"}
    assert example["channel"] == channel
    assert example["selected_choice"]["canonical_action"] == {
        "kind": "attack", "action_id": "attack:shadow-ball",
        "move_slot": 1, "move_id": "shadow-ball", "move_slot_basis": "direct_command",
    }
    assert example["decision_information"]["actor_private_completeness"] == "complete_for_v1_supported_private_surface"
    assert example["decision_information"]["exact_legal_action_set"]["status"] == "exact"
    assert example["selected_choice"]["choice_opportunity"] == "free"


def test_attack_move_id_only_resolves_exact_slot_and_mismatch_rejects():
    inputs, _, _ = _bundle(command={"kind": "attack", "move_id": "protect"})
    example = assemble(**inputs)
    assert example["selected_choice"]["canonical_action"] == {
        "kind": "attack", "action_id": "attack:protect",
        "move_slot": 2, "move_id": "protect", "move_slot_basis": "actor_private_resolution",
    }
    mismatched, _, _ = _bundle(command={"kind": "attack", "move_slot": 1, "move_id": "protect"})
    assert assemble(**mismatched)["reason"] == "command_identity_mismatch"


def test_command_identity_must_be_unique_within_exact_private_scope():
    duplicate_moves = _snapshot()
    duplicate_moves["own_roster"][0]["moves"][1]["move_id"] = "shadow-ball"
    attack, _, _ = _bundle(
        command={"kind": "attack", "move_id": "shadow-ball"}, private_snapshot=duplicate_moves,
    )
    assert assemble(**attack)["reason"] == "ambiguous_command_identity"
    duplicate_roster = _snapshot()
    duplicate_roster["own_roster"][1]["pokemon_id"] = "self-a"
    switch, _, _ = _bundle(
        command={"kind": "switch", "incoming_pokemon_id": "self-a"},
        private_snapshot=duplicate_roster,
    )
    assert assemble(**switch)["reason"] == "ambiguous_command_identity"


def test_switch_slot_or_identity_resolves_exact_roster_and_mismatch_rejects():
    slot_only, _, _ = _bundle(command={"kind": "switch", "incoming_slot_index": 1})
    slot_action = assemble(**slot_only)["selected_choice"]["canonical_action"]
    assert slot_action == {
        "kind": "switch", "action_id": "manual_switch:bench-a",
        "incoming_slot_index": 1, "incoming_pokemon_id": "bench-a",
        "incoming_slot_basis": "direct_command",
    }
    id_only, _, _ = _bundle(command={"kind": "switch", "incoming_pokemon_id": "bench-a"})
    id_action = assemble(**id_only)["selected_choice"]["canonical_action"]
    assert id_action["action_id"] == "manual_switch:bench-a"
    assert id_action["incoming_slot_index"] == 1
    assert id_action["incoming_slot_basis"] == "actor_private_resolution"
    mismatched, _, _ = _bundle(command={
        "kind": "switch", "incoming_slot_index": 1, "incoming_pokemon_id": "self-a",
    })
    assert assemble(**mismatched)["reason"] == "command_identity_mismatch"


def test_exact_legality_and_no_free_choice_are_distinct():
    illegal, _, _ = _bundle(legal={"status": "exact", "action_ids": ["attack:protect", "manual_switch:bench-a"]})
    assert assemble(**illegal)["reason"] == "selected_action_not_legal"
    singleton, _, _ = _bundle(legal={"status": "exact", "action_ids": ["attack:shadow-ball"]})
    row = assemble(**singleton)
    assert row["status"] == "materialized"
    assert row["example_availability"] == {"availability": "unavailable", "reason": "no_free_choice"}
    assert row["selected_choice"]["choice_opportunity"] == "no_free_choice"
    assert row["selected_choice"]["canonical_action"]["action_id"] == "attack:shadow-ball"


@pytest.mark.parametrize("legal", [
    {"status": "partial", "action_ids": ["attack:shadow-ball"]},
    {"status": "unknown", "action_ids": []},
])
def test_nonexact_legal_set_does_not_become_choice_example(legal):
    inputs, _, _ = _bundle(legal=legal)
    row = assemble(**inputs)
    assert row["status"] == "materialized"
    assert row["example_availability"] == {
        "availability": "unavailable", "reason": "legal_action_set_not_exact",
    }
    assert row["decision_information"]["exact_legal_action_set"]["status"] == legal["status"]


def test_incomplete_private_evidence_is_unavailable_and_not_filled_from_command():
    raw = _snapshot()
    raw["own_roster"][0].pop("current_ability")
    inputs, _, _ = _bundle(private_snapshot=raw)
    row = assemble(**inputs)
    assert row["example_availability"] == {"availability": "unavailable", "reason": "actor_private_incomplete"}
    assert row["selected_choice"]["canonical_action"] is None
    assert row["decision_information"]["actor_private_snapshot"]["own_roster"][0]["current_ability"] == {
        "availability": "unavailable",
    }


def test_live_private_and_direct_command_authentication_cannot_be_bypassed():
    inputs, _, _ = _bundle()
    private_claim = dict(inputs, private_information={"completeness": "complete_for_v1_supported_private_surface"})
    assert assemble(**private_claim)["reason"] == "private_information_not_authenticated"
    command_claim = dict(inputs, submitted_command={"command_payload": {"kind": "attack", "move_slot": 1}})
    assert assemble(**command_claim)["reason"] == "submitted_command_not_authenticated"
    execution_claim = dict(inputs, submitted_command=_run(_attack_case()))
    assert assemble(**execution_claim)["reason"] == "submitted_command_not_authenticated"


@pytest.mark.parametrize("result,expected", [("self", 1), ("tie", 0), ("opponent", -1)])
def test_terminal_target_is_outcome_only_and_real_tie_zero(result, expected):
    inputs, _, _ = _bundle(result=result)
    row = assemble(**inputs)
    assert row["example_availability"] == {"availability": "available"}
    assert row["outcome"]["terminal_target"] == {
        "availability": "available", "value": expected,
        "semantics": "terminal_outcome_self_perspective",
    }
    information = _editable(row["decision_information"])
    assert "target" not in information and "winner" not in information
    assert "termination_cause" not in information
    assert "execution_replay_link" not in information
    assert row["evidence"]["decision_point"]["post_boundary"]["execution_replay_link"] is None


def test_unavailable_terminal_target_remains_unavailable_without_numeric_default():
    inputs, _, _ = _bundle(result="self", cause="forfeit_opponent")
    row = assemble(**inputs)
    assert row["example_availability"] == {"availability": "unavailable", "reason": "terminal_target_unavailable"}
    assert row["outcome"]["terminal_target"]["availability"] == "unavailable"
    assert "value" not in row["outcome"]["terminal_target"]


def test_foreign_session_or_battle_rejected():
    foreign_session, _, _ = _bundle(session="foreign")
    assert assemble(**foreign_session)["reason"] == "foreign_terminal_target"
    foreign_battle, _, _ = _bundle(battle="battle-other")
    assert assemble(**foreign_battle)["reason"] == "foreign_terminal_target"


@pytest.mark.parametrize("partition", ["train", "validation", "test"])
def test_fixed_partition_is_preserved_without_target_based_reassignment(partition):
    inputs, _, _ = _bundle(partition=partition)
    row = assemble(**inputs)
    assert row["evaluation"]["partition"] == partition
    other, _, _ = _bundle(partition=partition, result="opponent")
    assert assemble(**other)["evaluation"]["partition"] == partition


def test_fabricated_or_missing_target_split_membership_rejected():
    inputs, _, _ = _bundle()
    forged = _editable(inputs["evaluation_split"])
    forged["evaluation_split_id"] = "offline-evaluation-split:" + "0" * 64
    assert assemble(**dict(inputs, evaluation_split=_freeze(forged)))["reason"] == "evaluation_split_invalid"
    assert assemble(**dict(inputs, evaluation_split={"status": "validated"}))["reason"] == "evaluation_split_invalid"
    other_context, other_terminal = _target_case("opponent", "all_fainted")
    other_target = target(population_context=other_context, terminal_source=other_terminal)
    other_split = split(target_records=[other_target], manifest={other_target["target_record_id"]: "test"})
    assert assemble(**dict(inputs, evaluation_split=other_split))["reason"] == "target_partition_membership_invalid"


def test_deterministic_immutable_auditable_and_observational_only():
    inputs, raw_private, raw_command = _bundle()
    private_before, command_before = deepcopy(raw_private), deepcopy(raw_command)
    first = assemble(**inputs)
    second = assemble(**inputs)
    assert first == second and first["example_id"] == second["example_id"]
    assert raw_private == private_before and raw_command == command_before
    raw_private["own_roster"][0]["moves"][0]["move_id"] = "later-change"
    raw_command["move_slot"] = 2
    assert first["selected_choice"]["canonical_action"]["action_id"] == "attack:shadow-ball"
    assert first["decision_information"]["actor_private_snapshot"]["own_roster"][0]["moves"][0]["move_id"]["value"] == "shadow-ball"
    assert first["provenance"]["join_basis"] == "session_id_and_battle_id"
    assert "decision_to_episode_transition_membership_not_proven" in first["provenance"]["limitations"]
    assert "observational_terminal_outcome_not_causal_action_value" in first["provenance"]["limitations"]
    assert not {"gamma", "q_value", "advantage", "discount", "shaping", "transition_id"} & set(first)
    with pytest.raises(TypeError):
        first["selected_choice"]["canonical_action"]["move_id"] = "other"
    with pytest.raises(TypeError):
        first["outcome"]["terminal_target"]["value"] = 0
    with pytest.raises(TypeError):
        first["decision_information"]["public_pre_boundary"]["turn_number"] = 99
