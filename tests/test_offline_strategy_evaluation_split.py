"""Explicit episode split manifests and exact population leakage checks."""
from copy import deepcopy

import pytest

from llm.advisor_current_state_runtime_admission import admit_current_state_observation
from llm.advisor_detached_observed_rng_reconciliation import materialize_historical_predictive_action_binding
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_offline_decision_point_provenance import _freeze
from llm.advisor_offline_strategy_episode_dataset import materialize_offline_strategy_episode
from llm.advisor_offline_strategy_episode_terminal_binding import (
    materialize_offline_strategy_episode_terminal_binding as bind,
)
from llm.advisor_offline_strategy_evaluation_split import (
    materialize_offline_strategy_evaluation_split as split,
)
from llm.advisor_offline_strategy_terminal_learning_target import (
    materialize_offline_strategy_terminal_learning_target as target,
)
from llm.advisor_offline_strategy_transition_replay import materialize_offline_strategy_transition
from llm.advisor_previous_action_history_observation import admit_previous_action_history_observation
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_session_battle_terminal_outcome_evidence import (
    SessionBoundBattleTerminalOutcomeEvidenceSource,
)
from tests.test_observed_scalar_attack_rng_reconciliation import _ledger as scalar_ledger
from tests.test_offline_strategy_episode_dataset import _chain, _editable
from tests.test_offline_strategy_episode_population_context import RULES, _attach
from tests.test_offline_strategy_episode_terminal_binding import _episode, _final, _source
from tests.test_offline_strategy_transition_replay import _features


ALT_RULES = {**RULES, "battle_format_id": "singles-other"}


def _third_episode():
    """Construct another genuine strict transition in a separate session."""
    session = "third-session"
    state = create_unknown_bootstrap_battle_state(session, "self-a", "opponent-a")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    manager = BattleObservationRuntimeSessionManager.create(session, state)["manager"]
    decision = manager.capture_runtime_state_snapshot(session)
    owner = {"session_id": session, "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    opponent = {"session_id": session, "side": "opponent", "slot_index": 0, "pokemon_id": "opponent-a"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=decision, decision_owner=owner)
    assert d0["status"] == "resolved"
    ledger = scalar_ledger(critical=False)
    bindings = {
        "session_id": session, "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": owner, "attacker": owner, "target": opponent, "move_id": "shadow-ball",
    }
    ledger["bindings"] = deepcopy(bindings)
    for leaf in ledger["terminal_leaves"]:
        leaf["provenance"] = deepcopy(bindings)
    features = _features(decision, d0, "attack:shadow-ball", "attack", ledger)
    history = materialize_historical_predictive_action_binding(predictive_ledger=ledger, turn_number=1)
    assert history["status"] == "resolved"
    executed = admit_previous_action_history_observation(
        runtime_session_manager=manager, captured_session_id=session, side="self",
        execution_move_id="shadow-ball", selected_move_id="shadow-ball",
        source_action_id=history["source_action_id"], result_class="success", turn_number=1,
    )
    hp = admit_current_state_observation(
        runtime_session_manager=manager, captured_session_id=session,
        event_kind="exact_hp_transition_observed",
        payload={"hp_before": 100, "hp_after": 80}, side="self", turn_number=1,
    )
    transition = materialize_offline_strategy_transition(
        feature_contract=features, candidate_id="attack:shadow-ball",
        decision_runtime_snapshot=decision, decision_turn_number=1,
        observation_snapshot=manager.read_collection_snapshot(),
        executed_observation_id=executed["observations"][0]["observation_id"],
        next_runtime_snapshot=manager.capture_runtime_state_snapshot(session),
        next_state_observation_id=hp["observation"]["observation_id"],
        historical_binding=history, predictive_ledger=ledger,
    )
    assert transition["status"] == "resolved", transition
    episode = materialize_offline_strategy_episode([transition])
    assert episode["status"] == "resolved"
    return episode


def _third_source():
    created = SessionBoundBattleTerminalOutcomeEvidenceSource.create(
        session_id="third-session", battle_id="battle-third", source_id="stream-third",
        source_kind="simulator_output",
    )
    assert created["status"] == "source_ready"
    return created["source"]


def _record(episode, source, *, result="self", cause="all_fainted", sampling=None, rules=None):
    admitted = source.admit_final_declaration(
        captured_session_id=source.session_id, captured_battle_id=source.battle_id,
        declaring_source_id=source.source_id, source_terminal_event_id="end-1",
        source_event_sequence=1, declared_result=result, termination_cause=cause,
        turn_number=8, source_cause_event_id="end-1" if cause != "unknown" else None,
    )
    assert admitted["status"] == "admitted"
    evidence = admitted["evidence"]
    binding = bind(episode=episode, terminal_source=source, terminal_evidence=evidence)
    context = _attach(binding, source, sampling, rules)
    record = target(population_context=context, terminal_source=source)
    assert record["status"] == "materialized", record
    return record


def _three():
    first = _record(
        _episode(), _source(), result="self",
        sampling={"collection_mode": "first_person_capture", "competition_context": "ladder"},
    )
    second = _record(
        _episode(gap=True), _source("s"), result="opponent",
        sampling={"collection_mode": "simulator_self_generated", "competition_context": "self_play"},
    )
    third = _record(
        _third_episode(), _third_source(), result="tie",
        sampling={"collection_mode": "spectator_auxiliary", "competition_context": "tournament"},
        rules=ALT_RULES,
    )
    return first, second, third


def _manifest(*records):
    return {record["target_record_id"]: partition for record, partition in zip(records, ("train", "validation", "test"))}


def test_valid_explicit_three_partition_manifest_and_descriptive_counts():
    first, second, third = _three()
    protocol = split(target_records=[third, first, second], manifest=_manifest(first, second, third))
    assert protocol["status"] == "validated"
    assert protocol["manifest_authority"] == "explicit_external_evaluation_manifest"
    assert protocol["partitions"]["train"]["target_record_ids"] == (first["target_record_id"],)
    assert protocol["partitions"]["validation"]["target_record_ids"] == (second["target_record_id"],)
    assert protocol["partitions"]["test"]["target_record_ids"] == (third["target_record_id"],)
    assert protocol["partitions"]["train"]["target_availability_counts"] == {"available": 1, "unavailable": 0}
    assert protocol["partitions"]["validation"]["target_availability_counts"] == {"available": 0, "unavailable": 1}
    assert protocol["partitions"]["test"]["collection_mode_counts"]["spectator_auxiliary"] == 1
    assert protocol["partitions"]["train"]["collection_mode_counts"]["first_person_capture"] == 1
    assert protocol["partitions"]["validation"]["collection_mode_counts"]["simulator_self_generated"] == 1
    assert protocol["partitions"]["test"]["rules_context_buckets"][0]["rules_context"] == ALT_RULES
    assert protocol["partitions"]["train"]["rules_context_buckets"][0]["rules_context"] == RULES
    assert protocol["partitions"]["test"]["record_count"] == 1
    assert "split_is_not_training_admission" in protocol["limitations"]
    assert "external_manifest_label_blindness_not_proven" in protocol["limitations"]
    assert "collection_time_not_chronological_authority" in protocol["limitations"]
    assert "self_and_opponent_player_clusters_checked_in_separate_namespaces" in protocol["limitations"]


def test_distinct_rules_contexts_remain_separate_within_one_partition():
    first, second, third = _three()
    manifest = {
        first["target_record_id"]: "train",
        second["target_record_id"]: "validation",
        third["target_record_id"]: "train",
    }
    protocol = split(target_records=[first, second, third], manifest=manifest)
    assert protocol["status"] == "validated"
    buckets = protocol["partitions"]["train"]["rules_context_buckets"]
    assert len(buckets) == 2
    assert {bucket["rules_context"]["battle_format_id"] for bucket in buckets} == {
        "singles-custom", "singles-other",
    }


def test_ordering_independence_determinism_and_no_input_mutation():
    records = list(_three())
    before = [_editable(row) for row in records]
    manifest = _manifest(*records)
    manifest_before = dict(manifest)
    first = split(target_records=records, manifest=manifest)
    second = split(target_records=list(reversed(records)), manifest=dict(reversed(list(manifest.items()))))
    assert first == second
    assert first["evaluation_split_id"] == second["evaluation_split_id"]
    assert first["manifest_fingerprint"] == second["manifest_fingerprint"]
    assert [_editable(row) for row in records] == before and manifest == manifest_before
    with pytest.raises(TypeError):
        first["partitions"]["train"]["record_count"] = 9
    with pytest.raises(TypeError):
        first["partitions"]["test"]["rules_context_buckets"][0]["rules_context"]["ruleset_id"] = "foreign"
    assert not {"accuracy", "loss", "auc", "random_seed", "split_ratio", "train_eligible"} & set(first)


def test_manifest_exact_coverage_and_partition_vocabulary():
    records = _three()
    manifest = _manifest(*records)
    missing = dict(manifest)
    missing.pop(records[0]["target_record_id"])
    assert split(target_records=list(records), manifest=missing)["reason"] == "missing_manifest_assignment"
    extra = {**manifest, "unknown-record": "train"}
    assert split(target_records=list(records), manifest=extra)["reason"] == "extra_manifest_assignment"
    invalid = {**manifest, records[0]["target_record_id"]: "holdout"}
    assert split(target_records=list(records), manifest=invalid)["reason"] == "partition_invalid"
    assert split(target_records=[records[0], records[0]], manifest={records[0]["target_record_id"]: "train"})["reason"] == "duplicate_target_record_id"


def test_same_episode_or_battle_cannot_cross_partitions():
    first = _three()[0]
    population = first["base_population_context"]
    source = _source()
    _final(source, "self")
    alternate_context = _attach(
        population["base_terminal_binding"], source,
        {"collection_mode": "simulator_self_generated", "competition_context": "fixture"},
    )
    alternate = target(population_context=alternate_context, terminal_source=source)
    assert split(target_records=[first, alternate], manifest={
        first["target_record_id"]: "train", alternate["target_record_id"]: "test",
    })["reason"] == "cross_partition_episode_terminal_binding_id"

    episode = _episode()
    no_final_source = _source()
    no_final = target(
        population_context=_attach(bind(episode=episode, terminal_source=no_final_source), no_final_source),
        terminal_source=no_final_source,
    )
    assert split(target_records=[first, no_final], manifest={
        first["target_record_id"]: "train", no_final["target_record_id"]: "test",
    })["reason"] == "cross_partition_episode_id"

    later_episode = materialize_offline_strategy_episode(list(_chain()))
    later_source = _source("s")
    later = target(
        population_context=_attach(bind(episode=later_episode, terminal_source=later_source), later_source),
        terminal_source=later_source,
    )
    second = _three()[1]
    assert split(target_records=[second, later], manifest={
        second["target_record_id"]: "train", later["target_record_id"]: "test",
    })["reason"] == "cross_partition_session_battle"


@pytest.mark.parametrize("field", [
    "set_id", "team_cluster_id", "self_player_cluster_id", "opponent_player_cluster_id",
])
def test_explicit_optional_identity_cannot_cross_partitions(field):
    first = _record(
        _episode(), _source(),
        sampling={"collection_mode": "first_person_capture", "competition_context": "ladder", field: "shared-17"},
    )
    second = _record(
        _episode(gap=True), _source("s"),
        sampling={"collection_mode": "simulator_self_generated", "competition_context": "self_play", field: "shared-17"},
    )
    result = split(target_records=[first, second], manifest={
        first["target_record_id"]: "train", second["target_record_id"]: "test",
    })
    assert result["reason"] == "cross_partition_" + field


def test_unavailable_ids_do_not_collide_and_player_roles_stay_separate():
    first = _record(
        _episode(), _source(),
        sampling={"collection_mode": "first_person_capture", "competition_context": "ladder",
                  "self_player_cluster_id": "shared-player", "source_dataset_id": "same-corpus",
                  "collection_time": "later-token"},
    )
    second = _record(
        _episode(gap=True), _source("s"),
        sampling={"collection_mode": "simulator_self_generated", "competition_context": "self_play",
                  "opponent_player_cluster_id": "shared-player", "source_dataset_id": "same-corpus",
                  "collection_time": "earlier-token"},
    )
    result = split(target_records=[first, second], manifest={
        first["target_record_id"]: "train", second["target_record_id"]: "test",
    })
    assert result["status"] == "validated"
    assert first["base_population_context"]["sampling_context"]["set_id"] == {"availability": "unavailable"}
    assert second["base_population_context"]["sampling_context"]["set_id"] == {"availability": "unavailable"}


def test_malformed_detached_target_and_label_independent_assignment():
    first, second, third = _three()
    assert split(target_records=[_editable(first)], manifest={first["target_record_id"]: "train"})["reason"] == "target_record_invalid"
    forged = _editable(first)
    forged["target_record_id"] = "offline-terminal-learning-target:" + "0" * 64
    assert split(target_records=[_freeze(forged)], manifest={first["target_record_id"]: "train"})["reason"] == "target_record_invalid"

    alternate = _record(_episode(), _source(), result="opponent")
    original = split(target_records=[first, second, third], manifest=_manifest(first, second, third))
    changed = split(target_records=[alternate, second, third], manifest=_manifest(alternate, second, third))
    assert original["partitions"]["train"]["target_record_ids"] == (first["target_record_id"],)
    assert changed["partitions"]["train"]["target_record_ids"] == (alternate["target_record_id"],)
    assert original["partitions"]["validation"]["target_record_ids"] == changed["partitions"]["validation"]["target_record_ids"]
    assert original["partitions"]["test"]["target_record_ids"] == changed["partitions"]["test"]["target_record_ids"]
