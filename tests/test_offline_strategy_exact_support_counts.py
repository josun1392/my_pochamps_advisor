"""Exact descriptive coverage of detached episode population records."""
import pytest

from llm.advisor_offline_decision_point_provenance import _freeze
from llm.advisor_offline_strategy_episode_dataset import materialize_offline_strategy_episode
from llm.advisor_offline_strategy_episode_terminal_binding import (
    materialize_offline_strategy_episode_terminal_binding as bind,
)
from llm.advisor_offline_strategy_exact_support_counts import (
    materialize_offline_strategy_exact_support_counts as count,
    project_exact_context_support as query,
)
from tests.test_offline_strategy_episode_dataset import _chain, _editable
from tests.test_offline_strategy_episode_population_context import RULES, _attach
from tests.test_offline_strategy_episode_terminal_binding import _episode, _final, _source


ALT_RULES = {**RULES, "battle_format_id": "singles-other"}


def _records():
    first_episode, first_source = _episode(), _source()
    first_terminal = bind(
        episode=first_episode, terminal_source=first_source,
        terminal_evidence=_final(first_source, "self"),
    )
    first = _attach(first_terminal, first_source, {
        "collection_mode": "first_person_capture", "competition_context": "ladder",
        "self_rating": 1500, "source_dataset_id": "corpus-1",
    })

    second_episode, second_source = _episode(gap=True), _source("s")
    second_terminal = bind(
        episode=second_episode, terminal_source=second_source,
        terminal_evidence=_final(second_source, "opponent"),
    )
    second = _attach(second_terminal, second_source, {
        "collection_mode": "simulator_self_generated", "competition_context": "self_play",
        "team_cluster_id": "team-1",
    })

    third_episode = materialize_offline_strategy_episode(list(_chain()))
    assert third_episode["status"] == "resolved"
    third_source = _source("s")
    third_terminal = bind(episode=third_episode, terminal_source=third_source)
    third = _attach(third_terminal, third_source, {
        "collection_mode": "spectator_auxiliary", "competition_context": "tournament",
    }, ALT_RULES)
    assert all(row["status"] in {"resolved", "incomplete"} for row in (first, second, third))
    return first, second, third


def test_one_valid_record_and_zero_match_query():
    first = _records()[0]
    inventory = count([first])
    assert inventory["status"] == "materialized"
    assert inventory["total_records"] == 1
    assert inventory["collection_mode_counts"]["first_person_capture"] == 1
    assert inventory["rules_context_buckets"][0]["record_count"] == 1
    zero = query(inventory, rules_context=ALT_RULES)
    assert zero["status"] == "projected"
    assert zero["matching_record_count"] == 0
    assert zero["matching_context_binding_ids"] == ()
    assert "unsupported" not in zero


def test_exact_rules_modes_competition_status_and_terminal_counts():
    first, second, third = _records()
    inventory = count([third, first, second])
    assert inventory["status"] == "materialized"
    assert inventory["total_records"] == 3
    assert (inventory["resolved_records"], inventory["incomplete_records"]) == (1, 2)
    assert inventory["base_episode_status_counts"] == {"resolved": 2, "incomplete": 1}
    assert sorted(bucket["record_count"] for bucket in inventory["rules_context_buckets"]) == [1, 2]
    assert {bucket["rules_context"]["battle_format_id"] for bucket in inventory["rules_context_buckets"]} == {
        "singles-custom", "singles-other",
    }
    assert inventory["collection_mode_counts"] == {
        "first_person_capture": 1, "simulator_self_generated": 1,
        "spectator_auxiliary": 1, "unknown": 0,
    }
    assert inventory["competition_context_counts"]["ladder"] == 1
    assert inventory["competition_context_counts"]["self_play"] == 1
    assert inventory["competition_context_counts"]["tournament"] == 1
    assert inventory["competition_context_counts"]["direct_challenge"] == 0
    assert inventory["terminal_availability_counts"] == {"available": 2, "unavailable": 1}
    assert inventory["declared_result_counts"] == {"self": 1, "opponent": 1, "tie": 0}
    availability = inventory["optional_metadata_availability_counts"]
    assert availability["self_rating"] == {"available": 1, "unavailable": 2}
    assert availability["team_cluster_id"] == {"available": 1, "unavailable": 2}
    assert availability["set_id"] == {"available": 0, "unavailable": 3}
    assert third["sampling_context"]["set_id"] == {"availability": "unavailable"}


def test_exact_query_filters_predeclared_context_only():
    first, second, third = _records()
    inventory = count([first, second, third])
    assert query(inventory, rules_context=RULES)["matching_record_count"] == 2
    mode = query(inventory, collection_mode="spectator_auxiliary")
    assert mode["matching_context_binding_ids"] == (third["context_binding_id"],)
    competition = query(inventory, competition_context="self_play")
    assert competition["matching_context_binding_ids"] == (second["context_binding_id"],)
    combined = query(inventory, rules_context=RULES, collection_mode="first_person_capture", competition_context="ladder")
    assert combined["matching_context_binding_ids"] == (first["context_binding_id"],)
    assert query(inventory, collection_mode="bad")["reason"] == "collection_mode_invalid"
    with pytest.raises(TypeError):
        query(inventory, declared_result="self")
    assert not {"sufficient", "confidence", "score", "threshold", "abstain"} & set(mode)


def test_duplicate_and_conflicting_episode_context_rejected():
    first = _records()[0]
    assert count([first, first])["reason"] == "duplicate_context_binding_id"
    binding = first["base_terminal_binding"]
    source = _source()
    _final(source, "self")
    conflicting = _attach(binding, source, {
        "collection_mode": "simulator_self_generated", "competition_context": "fixture",
    })
    assert conflicting["status"] == "resolved"
    assert count([first, conflicting])["reason"] == "conflicting_episode_context"


def test_tie_is_counted_only_with_direct_terminal_declaration():
    episode, source = _episode(), _source()
    terminal = bind(episode=episode, terminal_source=source, terminal_evidence=_final(source, "tie"))
    record = _attach(terminal, source)
    inventory = count([record])
    assert inventory["declared_result_counts"] == {"self": 0, "opponent": 0, "tie": 1}


def test_conflicting_final_declarations_for_one_battle_rejected():
    _, second, _ = _records()
    episode = materialize_offline_strategy_episode(list(_chain()))
    source = _source("s")
    terminal = bind(episode=episode, terminal_source=source, terminal_evidence=_final(source, "self"))
    other = _attach(terminal, source, rules=ALT_RULES)
    assert count([second, other])["reason"] == "conflicting_battle_terminal_evidence"


def test_fabricated_identity_fingerprint_and_availability_rejected():
    first = _records()[0]
    assert count([_editable(first)])["reason"] == "record_invalid"
    changed_id = _editable(first)
    changed_id["context_binding_id"] = "offline-episode-population-context:" + "0" * 64
    assert count([_freeze(changed_id)])["reason"] == "record_invalid"
    changed_fp = _editable(first)
    changed_fp["rules_context_fingerprint"] = "0" * 64
    assert count([_freeze(changed_fp)])["reason"] == "record_invalid"
    changed_nested = _editable(first)
    changed_nested["episode_terminal_binding_id"] = "foreign"
    assert count([_freeze(changed_nested)])["reason"] == "record_invalid"
    malformed_availability = _editable(first)
    malformed_availability["sampling_context"]["set_id"] = {"availability": "unavailable", "value": "fake"}
    assert count([_freeze(malformed_availability)])["reason"] == "record_invalid"


def test_order_independence_deterministic_id_and_deep_immutability():
    records = list(_records())
    before = [_editable(row) for row in records]
    first = count(records)
    second = count(list(reversed(records)))
    assert first == second and first["inventory_id"] == second["inventory_id"]
    assert [_editable(row) for row in records] == before
    assert first["limitation"] == "episode_population_coverage_only_not_state_action_support"
    assert not {"reward", "target", "train_eligible", "confidence", "score", "threshold", "abstain"} & set(first)
    with pytest.raises(TypeError):
        first["collection_mode_counts"]["first_person_capture"] = 0
    with pytest.raises(TypeError):
        first["rules_context_buckets"][0]["rules_context"]["ruleset_id"] = "foreign"
    with pytest.raises(TypeError):
        first["records"][0]["sampling_context"]["set_id"] = {"availability": "available", "value": "fake"}
    corrupted_inventory = _editable(first)
    corrupted_inventory["total_records"] = 99
    assert query(_freeze(corrupted_inventory))["reason"] == "inventory_revalidation_failed"


def test_empty_inventory_stays_descriptive():
    inventory = count([])
    assert inventory["total_records"] == 0
    assert query(inventory, rules_context=RULES)["matching_record_count"] == 0
