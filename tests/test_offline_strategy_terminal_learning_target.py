"""Terminal-only episode targets; raw outcomes and replay remain untouched."""
import pytest

from llm.advisor_offline_decision_point_provenance import _freeze
from llm.advisor_offline_strategy_episode_terminal_binding import (
    materialize_offline_strategy_episode_terminal_binding as bind,
)
from llm.advisor_offline_strategy_terminal_learning_target import (
    materialize_offline_strategy_terminal_learning_target as target,
)
from tests.test_offline_strategy_episode_dataset import _editable
from tests.test_offline_strategy_episode_population_context import _attach
from tests.test_offline_strategy_episode_terminal_binding import _episode, _final, _source


def _case(result="self", cause="all_fainted", *, gap=False, mode="first_person_capture"):
    episode = _episode(gap=gap)
    source = _source("s" if gap else "replay")
    evidence = _final(source, result, cause)
    terminal = bind(episode=episode, terminal_source=source, terminal_evidence=evidence)
    context = _attach(terminal, source, {
        "collection_mode": mode, "competition_context": "fixture",
    })
    assert context["status"] in {"resolved", "incomplete"}
    return context, source


@pytest.mark.parametrize("result,cause,expected", [
    ("self", "all_fainted", 1),
    ("opponent", "all_fainted", -1),
    ("tie", "all_fainted", 0),
    ("self", "rules_based", 1),
    ("opponent", "rules_based", -1),
    ("tie", "rules_based", 0),
])
def test_approved_result_and_cause_mapping_only(result, cause, expected):
    context, source = _case(result, cause)
    record = target(population_context=context, terminal_source=source)
    assert record["status"] == "materialized"
    assert record["target"] == {
        "availability": "available", "value": expected,
        "semantics": "terminal_outcome_self_perspective",
    }
    assert record["target_policy_version"] == "terminal-only-self-perspective-v1"
    assert record["raw_terminal_outcome"]["declared_result"] == result
    assert record["raw_terminal_outcome"]["termination_cause"] == cause
    assert record["raw_terminal_outcome"]["evidence_completeness"] == "final_declaration_observed"
    assert record["raw_terminal_outcome"]["evidence_id"] == context["base_terminal_binding"]["terminal_outcome"]["evidence_id"]


@pytest.mark.parametrize("result,cause", [
    ("self", "forfeit_opponent"),
    ("opponent", "forfeit_self"),
    ("opponent", "inactivity_self"),
    ("self", "inactivity_opponent"),
    ("self", "administrative"),
    ("opponent", "server_error"),
    ("tie", "unrecognized"),
    ("tie", "unknown"),
])
def test_excluded_causes_keep_raw_outcome_without_numeric_target(result, cause):
    context, source = _case(result, cause)
    record = target(population_context=context, terminal_source=source)
    assert record["target"] == {
        "availability": "unavailable", "reason": "termination_cause_not_admitted_v1",
    }
    assert "value" not in record["target"]
    assert record["raw_terminal_outcome"]["declared_result"] == result
    assert record["raw_terminal_outcome"]["termination_cause"] == cause


def test_missing_declaration_and_truncated_stream_have_no_target():
    episode = _episode()
    missing_source = _source()
    missing_context = _attach(bind(episode=episode, terminal_source=missing_source), missing_source)
    missing = target(population_context=missing_context, terminal_source=missing_source)
    assert missing["target"] == {
        "availability": "unavailable", "reason": "terminal_declaration_not_observed",
    }
    assert missing["raw_terminal_outcome"]["evidence"] is None

    truncated_source = _source()
    end = truncated_source.record_stream_end_without_declaration(
        captured_session_id="replay", captured_battle_id="battle-1",
        declaring_source_id="stream-1", source_stream_end_event_id="eof-1",
        source_event_sequence=2,
    )["evidence"]
    truncated_binding = bind(episode=episode, terminal_source=truncated_source, terminal_evidence=end)
    truncated_context = _attach(truncated_binding, truncated_source)
    truncated = target(population_context=truncated_context, terminal_source=truncated_source)
    assert truncated["target"] == {
        "availability": "unavailable", "reason": "stream_ended_without_declaration",
    }
    assert "value" not in truncated["target"]
    assert truncated["raw_terminal_outcome"]["evidence"] == end


def test_incomplete_episode_keeps_direct_outcome_but_no_target():
    context, source = _case("self", "all_fainted", gap=True)
    record = target(population_context=context, terminal_source=source)
    assert record["target"] == {"availability": "unavailable", "reason": "episode_incomplete"}
    assert record["raw_terminal_outcome"]["declared_result"] == "self"
    assert record["base_population_context"]["base_terminal_binding"]["continuity_gaps"]
    assert "value" not in record["target"]


def test_tie_zero_is_distinct_from_unavailable():
    tie_context, tie_source = _case("tie", "all_fainted")
    excluded_context, excluded_source = _case("tie", "unknown")
    tie = target(population_context=tie_context, terminal_source=tie_source)
    excluded = target(population_context=excluded_context, terminal_source=excluded_source)
    assert tie["target"]["value"] == 0
    assert excluded["target"]["availability"] == "unavailable"
    assert "value" not in excluded["target"]


def test_foreign_or_unretained_source_and_fabricated_context_rejected():
    context, source = _case()
    assert target(population_context=context, terminal_source=None)["reason"] == "terminal_source_invalid"
    assert target(population_context=context, terminal_source=_source("foreign"))["reason"] == "foreign_session"
    fresh_source = _source()
    assert target(population_context=context, terminal_source=fresh_source)["reason"] == "population_context_reauthentication_failed"
    assert target(population_context=_editable(context), terminal_source=source)["reason"] == "population_context_invalid"
    altered = _editable(context)
    altered["context_binding_id"] = "offline-episode-population-context:" + "0" * 64
    assert target(population_context=_freeze(altered), terminal_source=source)["reason"] == "population_context_invalid"


def test_deterministic_detached_episode_level_record_without_shaping_or_propagation():
    context, source = _case("opponent", "rules_based", mode="spectator_auxiliary")
    context_before = _editable(context)
    source_before = source.read_snapshot(captured_session_id="replay", captured_battle_id="battle-1")
    first = target(population_context=context, terminal_source=source)
    second = target(population_context=context, terminal_source=source)
    assert first == second and first["target_record_id"] == second["target_record_id"]
    assert _editable(context) == context_before
    assert source.read_snapshot(captured_session_id="replay", captured_battle_id="battle-1") == source_before
    assert first["base_population_context"]["sampling_context"]["collection_mode"] == "spectator_auxiliary"
    assert first["raw_terminal_outcome"] == context["base_terminal_binding"]["terminal_outcome"]
    assert not {"gamma", "discount", "return", "hp_delta", "ko_value", "status_value", "shaping"} & set(first)
    episode = context["base_terminal_binding"]["base_episode"]
    for transition in episode["transitions"]:
        assert not {"target", "reward", "return"} & set(transition)
        assert not {"target", "reward", "return"} & set(transition["decision_feature_row"])
    with pytest.raises(TypeError):
        first["target"]["value"] = 0
    with pytest.raises(TypeError):
        first["raw_terminal_outcome"]["declared_result"] = "self"
    with pytest.raises(TypeError):
        first["base_population_context"]["rules_context"]["ruleset_id"] = "foreign"
