"""Real JSON restart boundary, with no live source owner after loading."""
import json
import hashlib
from copy import deepcopy

import pytest

from llm.advisor_c6_production_battle_export import (
    materialize_c6_production_battle_export, write_c6_production_battle_export,
)
from llm.advisor_c6_production_decision_capture import ProductionDecisionCapture
from llm.advisor_c6_production_transition_capture import ProductionObservedTransitionCapture
from llm.advisor_c6_durable_archive_offline_ingestion import load_c6_production_battle_export
from llm.advisor_offline_strategy_choice_outcome_example import (
    materialize_offline_strategy_choice_outcome_example_from_archive,
)
from llm.advisor_offline_strategy_evaluation_split import materialize_offline_strategy_evaluation_split
from llm.advisor_offline_strategy_model_feature_semantics import (
    materialize_offline_strategy_model_feature_semantics_from_archive,
)
from llm.advisor_offline_strategy_train_only_numeric_encoding import fit_train_only_numeric_encoder, encode_semantic_feature_record
from llm.advisor_offline_strategy_linear_terminal_outcome_baseline import fit_offline_linear_terminal_outcome_baseline
from llm.advisor_offline_strategy_linear_terminal_outcome_evaluation import materialize_offline_linear_terminal_outcome_evaluation
from llm.advisor_offline_decision_point_provenance import _canonical
from llm.advisor_session_battle_terminal_outcome_evidence import SessionBoundBattleTerminalOutcomeEvidenceSource
from tests.test_c6_production_transition_capture import _attach, _attempt
from tests.test_offline_strategy_transition_replay import _attack_case
from tests.test_session_actor_private_decision_information import _snapshot as private_snapshot
from tests.test_session_decision_public_battle_information import snapshot as public_snapshot


def _written_archive(tmp_path, *, command=True, legal=None, private=None, cause="all_fainted"):
    case = _attack_case()
    actor = case["feature_contract"]["provenance"]["decision_owner"]
    decision = ProductionDecisionCapture.create(
        session_id="replay", battle_id="replay", actor=actor,
        source_id="production:replay:self")["source"]
    public = public_snapshot()
    for row in public["active"].values():
        row["session_id"] = "replay"
    admitted = decision.begin_decision_capture(
        captured_session_id="replay", captured_battle_id="replay", actor=actor,
        opportunity_id="turn:1:kind:turn_start:runtime:" + case["decision_runtime_snapshot"]["state_fingerprint"],
        decision_kind="turn_start", turn_number=1, simultaneity_group_id="turn:1",
        context_reference={"ruleset_id": "rules-a", "mechanics_version": "mechanics-a",
                           "protocol_version": "protocol-a", "battle_format_id": "format-a"},
        legal_action_set=legal or {"status": "exact", "action_ids": ["attack:shadow-ball", "attack:protect"]},
        public_snapshot=public, private_snapshot=private or private_snapshot())
    assert admitted["status"] == "captured", admitted
    boundary = admitted["opportunity"]["certificate"]["boundary_id"]
    transition = ProductionObservedTransitionCapture(decision)
    assert transition.retain_decision_anchor(
        opportunity_record=admitted["opportunity"],
        decision_runtime_snapshot=case["decision_runtime_snapshot"], decision_turn_number=1)["status"] == "retained"
    _attach(transition, boundary, case)
    if command:
        submitted = decision.confirm_submitted_command(
            captured_session_id="replay", captured_battle_id="replay", boundary_id=boundary,
            actor=actor, confirmation_event_id="direct-choice-1",
            command_payload={"kind": "attack", "move_slot": 1})
        assert submitted["status"] == "admitted"
    assert _attempt(transition, boundary, case)["status"] == "resolved"
    terminal = SessionBoundBattleTerminalOutcomeEvidenceSource.create(
        session_id="replay", battle_id="replay", source_id="production:replay:first-person-terminal",
        source_kind="first_person_battle_stream")["source"]
    assert terminal.admit_final_declaration(
        captured_session_id="replay", captured_battle_id="replay",
        declaring_source_id=terminal.source_id, source_terminal_event_id="final-1",
        source_event_sequence=10, declared_result="self", termination_cause=cause,
        turn_number=1, source_cause_event_id="cause-1")["status"] == "admitted"
    archive = materialize_c6_production_battle_export(
        session_id="replay", battle_id="replay", decision_captures=(decision,),
        transition_captures=(transition,), terminal_source=terminal, competition_context="unknown")
    assert archive["status"] == "materialized", archive
    path = tmp_path / "battle.json"
    assert write_c6_production_battle_export(export_bundle=archive, output_path=path)["status"] == "written"
    return path, boundary


def test_saved_archive_restarts_into_split_choice_semantics_and_encoder(tmp_path):
    path, boundary = _written_archive(tmp_path)
    # The post-restart half receives only a path, boundary string, and detached records.
    ingested = load_c6_production_battle_export(input_path=path)
    assert ingested["status"] == "validated", ingested
    target = ingested["terminal_target"]
    split = materialize_offline_strategy_evaluation_split(
        target_records=[target], manifest={target["target_record_id"]: "train"})
    assert split["status"] == "validated"
    choice = materialize_offline_strategy_choice_outcome_example_from_archive(
        ingestion=ingested, boundary_id=boundary, evaluation_split=split)
    assert choice["status"] == "materialized", choice
    assert choice["example_availability"] == {"availability": "available"}
    semantic = materialize_offline_strategy_model_feature_semantics_from_archive(
        ingestion=ingested, boundary_id=boundary, choice_example=choice, evaluation_split=split)
    assert semantic["status"] == "materialized", semantic
    assert semantic["feature_availability"] == {"availability": "available"}
    fitted = fit_train_only_numeric_encoder([semantic])
    assert fitted["status"] == "fitted", fitted
    encoded = encode_semantic_feature_record(encoder=fitted, semantic_record=semantic)
    assert encoded["status"] == "encoded", encoded
    model = fit_offline_linear_terminal_outcome_baseline([encoded])
    assert model["status"] == "fitted", model
    evaluation = materialize_offline_linear_terminal_outcome_evaluation(model=model, encoded_records=[encoded])
    assert evaluation["status"] == "materialized", evaluation


@pytest.mark.parametrize("field,value", [("schema_version", "wrong"), ("session_id", "foreign")])
def test_changed_archive_identity_or_schema_rejected(tmp_path, field, value):
    path, _ = _written_archive(tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw[field] = value
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_c6_production_battle_export(input_path=path)["status"] == "rejected"


def test_missing_direct_command_stays_missing_after_restart(tmp_path):
    path, boundary = _written_archive(tmp_path, command=False)
    ingested = load_c6_production_battle_export(input_path=path)
    assert ingested["status"] == "validated"
    assert ingested["boundaries"][0]["choice_availability"]["reason"] == "direct_command_not_observed"
    target = ingested["terminal_target"]
    split = materialize_offline_strategy_evaluation_split(
        target_records=[target], manifest={target["target_record_id"]: "train"})
    assert materialize_offline_strategy_choice_outcome_example_from_archive(
        ingestion=ingested, boundary_id=boundary, evaluation_split=split)["reason"] == "direct_command_not_observed"


def _rewrite_with_current_export_id(path, mutate):
    raw = json.loads(path.read_text(encoding="utf-8"))
    mutate(raw)
    raw["export_id"] = "c6-production-export:" + hashlib.sha256(
        _canonical({key: value for key, value in raw.items() if key != "export_id"})).hexdigest()
    path.write_text(json.dumps(raw), encoding="utf-8")


@pytest.mark.parametrize("location", ["command", "public", "private", "terminal", "duplicate_public"])
def test_rehashed_cross_link_tamper_still_rejected(tmp_path, location):
    path, _ = _written_archive(tmp_path)
    def mutate(raw):
        capture = raw["decision_capture_snapshots"][0]
        if location == "command":
            capture["submitted_commands"]["command_evidence"][0]["boundary_id"] = "foreign-boundary"
        elif location == "public":
            capture["public_information"]["evidence"][0]["boundary_id"] = "foreign-boundary"
        elif location == "private":
            capture["private_information"]["evidence"][0]["boundary_id"] = "foreign-boundary"
        elif location == "terminal":
            raw["terminal_learning_target"]["battle_id"] = "foreign-battle"
        else:
            capture["public_information"]["evidence"].append(
                deepcopy(capture["public_information"]["evidence"][0]))
    _rewrite_with_current_export_id(path, mutate)
    assert load_c6_production_battle_export(input_path=path)["status"] == "rejected"


def test_incomplete_private_and_unavailable_target_never_upgraded(tmp_path):
    incomplete = private_snapshot()
    incomplete["own_roster"][0].pop("known_item")
    path, boundary = _written_archive(tmp_path, private=incomplete)
    ingested = load_c6_production_battle_export(input_path=path)
    assert ingested["status"] == "validated", ingested
    target = ingested["terminal_target"]
    split = materialize_offline_strategy_evaluation_split(
        target_records=[target], manifest={target["target_record_id"]: "train"})
    choice = materialize_offline_strategy_choice_outcome_example_from_archive(
        ingestion=ingested, boundary_id=boundary, evaluation_split=split)
    assert choice["example_availability"]["reason"] == "actor_private_incomplete"
    path2 = tmp_path / "excluded"
    path2.mkdir()
    file2, boundary2 = _written_archive(path2, cause="forfeit_opponent")
    ingested2 = load_c6_production_battle_export(input_path=file2)
    target2 = ingested2["terminal_target"]
    split2 = materialize_offline_strategy_evaluation_split(
        target_records=[target2], manifest={target2["target_record_id"]: "test"})
    choice2 = materialize_offline_strategy_choice_outcome_example_from_archive(
        ingestion=ingested2, boundary_id=boundary2, evaluation_split=split2)
    assert choice2["example_availability"]["reason"] == "terminal_target_unavailable"


def test_partial_legality_and_missing_split_membership_fail_closed(tmp_path):
    path, boundary = _written_archive(tmp_path, legal={"status": "partial", "action_ids": ["attack:shadow-ball"]})
    ingested = load_c6_production_battle_export(input_path=path)
    target = ingested["terminal_target"]
    split = materialize_offline_strategy_evaluation_split(
        target_records=[target], manifest={target["target_record_id"]: "train"})
    choice = materialize_offline_strategy_choice_outcome_example_from_archive(
        ingestion=ingested, boundary_id=boundary, evaluation_split=split)
    assert choice["example_availability"]["reason"] == "legal_action_set_not_exact"
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    other_path, _ = _written_archive(other_dir, cause="rules_based")
    other_target = load_c6_production_battle_export(input_path=other_path)["terminal_target"]
    other_split = materialize_offline_strategy_evaluation_split(
        target_records=[other_target], manifest={other_target["target_record_id"]: "train"})
    assert materialize_offline_strategy_choice_outcome_example_from_archive(
        ingestion=ingested, boundary_id=boundary, evaluation_split=other_split)["reason"] == "target_partition_membership_invalid"
