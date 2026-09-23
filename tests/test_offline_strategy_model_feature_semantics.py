"""Semantic inputs exclude terminal labels, partition, and provenance artifacts."""
from copy import deepcopy
from types import MappingProxyType

import pytest

from llm.advisor_offline_strategy_choice_outcome_example import (
    materialize_offline_strategy_choice_outcome_example as assemble,
)
from llm.advisor_offline_strategy_evaluation_split import materialize_offline_strategy_evaluation_split as split
from llm.advisor_offline_strategy_model_feature_semantics import (
    materialize_offline_strategy_model_feature_semantics as materialize,
)
from llm.advisor_offline_strategy_terminal_learning_target import (
    materialize_offline_strategy_terminal_learning_target as target,
)
from llm.advisor_session_actor_private_decision_information import SessionBoundActorPrivateDecisionInformationSource
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource
from llm.advisor_session_decision_public_battle_information import SessionBoundDecisionPublicBattleInformationSource
from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource
from tests.test_offline_strategy_choice_outcome_example import RULES
from tests.test_offline_strategy_terminal_learning_target import _case as target_case
from tests.test_session_actor_private_decision_information import _snapshot as private_snapshot
from tests.test_session_decision_public_battle_information import snapshot as public_snapshot


def case(*, channel="actor_first_person", result="self", cause="all_fainted", partition="train",
         command=None, legal=None, public=None, private=None):
    actor = {"session_id": "replay", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    opportunity_source = SessionBoundDecisionOpportunityBoundarySource.create(
        session_id="replay", battle_id="battle-1", source_id="opportunity-input-1",
        channel=channel, actor=actor)["source"]
    opportunity = opportunity_source.capture_opportunity(
        captured_session_id="replay", opportunity_id="request-1", actor=actor,
        decision_kind="turn_start", turn_number=1, simultaneity_group_id="turn-1",
        context_reference=RULES, legal_action_set=legal or {
            "status": "exact", "action_ids": ["attack:shadow-ball", "attack:protect", "manual_switch:bench-a"],
        })
    assert opportunity["status"] == "captured"
    command_source = SessionBoundSubmittedCommandEvidenceSource.create(
        opportunity_source=opportunity_source, source_id="direct-input-1")["source"]
    private_source = SessionBoundActorPrivateDecisionInformationSource.create(
        opportunity_source=opportunity_source, command_source=command_source, source_id="private-input-1")["source"]
    public_source = SessionBoundDecisionPublicBattleInformationSource.create(
        opportunity_source=opportunity_source, command_source=command_source, source_id="public-input-1")["source"]
    raw_private = private_snapshot() if private is None else private
    admitted_private = private_source.admit_private_snapshot(
        captured_session_id="replay", captured_battle_id="battle-1", opportunity_record=opportunity,
        actor=actor, source_private_event_id="private-1", private_snapshot=raw_private)
    assert admitted_private["status"] == "admitted", admitted_private
    raw_public = public_snapshot() if public is None else public
    for row in raw_public["active"].values():
        row["session_id"] = "replay"
    admitted_public = public_source.admit_public_snapshot(
        captured_session_id="replay", captured_battle_id="battle-1", opportunity_record=opportunity,
        actor=actor, source_public_event_id="public-1", public_snapshot=raw_public)
    assert admitted_public["status"] == "admitted", admitted_public
    submitted = command_source.admit_submitted_command(
        captured_session_id="replay", opportunity_record=opportunity, actor=actor,
        source_command_id="command-1", command_payload=command or {"kind": "attack", "move_slot": 1})
    assert submitted["status"] == "admitted", submitted
    context, terminal_source = target_case(result, cause)
    terminal_target = target(population_context=context, terminal_source=terminal_source)
    evaluation = split(target_records=[terminal_target], manifest={terminal_target["target_record_id"]: partition})
    inputs = dict(opportunity_record=opportunity, opportunity_source=opportunity_source,
                  private_information=admitted_private["evidence"], private_source=private_source,
                  submitted_command=submitted["evidence"], command_source=command_source,
                  terminal_target=terminal_target, terminal_source=terminal_source, evaluation_split=evaluation)
    example = assemble(**inputs)
    assert example["status"] == "materialized", example
    args = dict(choice_example=example, public_information=admitted_public["evidence"],
                public_source=public_source, private_source=private_source,
                terminal_source=terminal_source, evaluation_split=evaluation)
    return args, raw_public


@pytest.mark.parametrize("channel", ["actor_first_person", "simulator_input"])
def test_semantic_families_and_decision_time_values(channel):
    args, _ = case(channel=channel)
    row = materialize(**args)
    assert row["status"] == "materialized", row
    assert row["feature_availability"] == {"availability": "available"}
    features = row["model_features"]
    assert features["rules_and_decision"] == {**RULES, "decision_kind": "turn_start", "turn_number": 1}
    public = features["public_battle"]
    assert public["active"]["self"]["current_hp"] == {"availability": "available", "value": 51}
    assert public["active"]["opponent"]["current_hp"] == {"availability": "available", "value": 36}
    assert public["active"]["self"]["fainted"] == {"availability": "available", "value": False}
    assert public["active"]["self"]["condition"] == {"availability": "available", "value": "none"}
    assert public["active"]["self"]["stat_stages"]["attack"] == {"availability": "available", "value": 0}
    assert public["active"]["self"]["stat_stages"]["evasion"] == {"availability": "unavailable"}
    assert public["field"]["weather"]["value"] == "rain"
    assert public["field"]["terrain"]["value"] == "electric"
    assert public["field"]["trick_room"]["value"] is False
    assert public["sides"]["self"]["tailwind"]["value"] is True
    assert public["opponent_revealed_moves"] == {"status": "partial", "move_ids": ("protect", "shadow-ball")}
    private = {entry["pokemon_id"]: entry for entry in features["actor_private"]["own_roster"]}
    assert set(private) == {"self-a", "bench-a"}
    assert any(move["move_id"]["value"] == "shadow-ball" and move["current_pp"]["value"] == 0
               for move in private["self-a"]["moves"])
    assert private["self-a"]["known_item"]["value"] == "life-orb"
    assert private["bench-a"]["known_item"] == {"availability": "available", "value": None}
    assert private["self-a"]["current_ability"]["value"] == "static"
    assert private["self-a"]["current_level"]["value"] == 50
    assert private["self-a"]["current_final_stats"]["speed"]["value"] == 105
    assert "slot_index" not in repr(features) and "move_slot" not in repr(features)
    assert features["exact_legal_actions"]["status"] == "exact"
    assert features["selected_action"] == {"kind": "attack", "move_id": "shadow-ball"}
    assert "session_id" not in public["active"]["self"]
    assert "session_id" not in public["active"]["opponent"]
    assert "predictive_strategy_feature_join_not_proven" in row["audit"]["limitations"]


def test_switch_is_semantic_without_command_slot_or_provenance():
    args, _ = case(command={"kind": "switch", "incoming_slot_index": 1})
    features = materialize(**args)["model_features"]
    assert features["selected_action"] == {"kind": "switch", "incoming_pokemon_id": "bench-a"}
    assert "incoming_slot_index" not in features["selected_action"]
    assert "command_id" not in repr(features)


@pytest.mark.parametrize("result,expected", [("self", 1), ("tie", 0), ("opponent", -1)])
@pytest.mark.parametrize("partition", ["train", "validation", "test"])
def test_labels_and_partitions_are_outside_label_blind_features(result, expected, partition):
    args, _ = case(result=result, partition=partition)
    row = materialize(**args)
    assert row["label"]["value"] == expected
    assert row["evaluation_partition"] == partition
    features = row["model_features"]
    assert "label" not in features and "evaluation_partition" not in features
    assert "target" not in repr(features) and "terminal" not in repr(features)
    assert "session_id" not in repr(features) and "battle_id" not in repr(features)
    assert "boundary_id" not in repr(features) and "command_id" not in repr(features)
    assert "collection_mode" not in repr(features) and "team_cluster_id" not in repr(features)
    assert "evaluation_split_id" not in repr(features)


def test_fingerprint_ignores_outcome_and_partition_but_changes_with_input():
    base, _ = case()
    baseline = materialize(**base)
    for result, partition in (("tie", "train"), ("opponent", "test"), ("self", "validation")):
        args, _ = case(result=result, partition=partition)
        assert materialize(**args)["semantic_feature_fingerprint"] == baseline["semantic_feature_fingerprint"]
    changed = public_snapshot()
    changed["active"]["self"]["current_hp"]["value"] = 50
    hp_args, _ = case(public=changed)
    assert materialize(**hp_args)["semantic_feature_fingerprint"] != baseline["semantic_feature_fingerprint"]
    action_args, _ = case(command={"kind": "attack", "move_slot": 2})
    assert materialize(**action_args)["semantic_feature_fingerprint"] != baseline["semantic_feature_fingerprint"]


def test_partial_public_information_is_kept_without_numeric_fill():
    public = public_snapshot()
    public["active"]["opponent"].pop("current_hp")
    public["active"]["opponent"].pop("condition")
    public["field"].pop("weather")
    args, _ = case(public=public)
    row = materialize(**args)
    assert row["feature_availability"] == {"availability": "available"}
    facts = row["model_features"]["public_battle"]
    assert facts["active"]["opponent"]["current_hp"] == {"availability": "unavailable"}
    assert facts["active"]["opponent"]["condition"] == {"availability": "unavailable"}
    assert facts["field"]["weather"] == {"availability": "unavailable"}


@pytest.mark.parametrize("kwargs,reason", [
    ({"legal": {"status": "partial", "action_ids": ["attack:shadow-ball"]}}, "legal_action_set_not_exact"),
    ({"legal": {"status": "unknown", "action_ids": []}}, "legal_action_set_not_exact"),
    ({"legal": {"status": "exact", "action_ids": ["attack:shadow-ball"]}}, "no_free_choice"),
    ({"cause": "forfeit_opponent"}, "terminal_target_unavailable"),
])
def test_unavailable_example_cannot_become_trainable(kwargs, reason):
    args, _ = case(**kwargs)
    row = materialize(**args)
    assert row["feature_availability"] == {"availability": "unavailable", "reason": reason}
    assert row["model_features"] is None and row["semantic_feature_fingerprint"] is None
    if reason == "terminal_target_unavailable":
        assert row["label"]["availability"] == "unavailable" and "value" not in row["label"]


def test_incomplete_private_information_stays_unavailable():
    private = private_snapshot()
    private["own_roster"][0].pop("current_ability")
    args, _ = case(private=private)
    row = materialize(**args)
    assert row["feature_availability"]["reason"] == "actor_private_incomplete"
    assert row["model_features"] is None


def test_fabricated_foreign_and_mismatched_public_evidence_fail_closed():
    args, _ = case()
    assert materialize(**{**args, "public_information": dict(args["public_information"])})["reason"] == "public_information_not_authenticated"
    foreign, _ = case()
    assert materialize(**{**args, "public_source": foreign["public_source"]})["reason"] == "choice_example_reauthentication_failed"
    assert materialize(**{**args, "public_information": foreign["public_information"]})["reason"] == "public_information_not_authenticated"
    changed = public_snapshot()
    changed["active"]["self"]["current_hp"]["value"] = 1
    other, _ = case(public=changed)
    assert materialize(**{**args, "public_information": other["public_information"]})["reason"] == "public_information_not_authenticated"
    tampered = MappingProxyType({**args["choice_example"], "battle_id": "foreign"})
    assert materialize(**{**args, "choice_example": tampered})["reason"] == "choice_example_reauthentication_failed"


def test_public_active_identity_must_match_actor_and_private_roster():
    changed = public_snapshot()
    changed["active"]["self"]["slot_index"] = 1
    source, _ = case()
    public_source = source["public_source"]
    # The public owner itself refuses a self identity foreign to its retained actor.
    opportunity = source["choice_example"]["evidence"]["opportunity"]
    actor = source["choice_example"]["actor"]
    assert public_source.admit_public_snapshot(
        captured_session_id="replay", captured_battle_id="battle-1",
        opportunity_record=opportunity, actor=actor, source_public_event_id="different",
        public_snapshot=changed)["reason"] == "public_snapshot_invalid"


def test_determinism_immutability_and_no_encoder_fields():
    args, raw = case()
    original = deepcopy(raw)
    before_public = args["public_source"].read_snapshot(captured_session_id="replay")
    row = materialize(**args)
    assert materialize(**args) == row
    assert raw == original
    assert args["public_source"].read_snapshot(captured_session_id="replay") == before_public
    raw["active"]["self"]["current_hp"]["value"] = 0
    assert row["model_features"]["public_battle"]["active"]["self"]["current_hp"]["value"] == 51
    with pytest.raises(TypeError):
        row["model_features"]["public_battle"]["active"]["self"]["current_hp"]["value"] = 0
    assert not {"vector", "vocabulary", "scaler", "model", "embedding", "gamma"} & set(row)
