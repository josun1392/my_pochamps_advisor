"""Factual, detached rules and sampling metadata for terminal-bound episodes."""
from copy import deepcopy

import pytest

from llm.advisor_offline_decision_point_provenance import (
    _freeze,
    fingerprint_decision_contract_reference,
)
from llm.advisor_offline_strategy_episode_population_context import (
    materialize_offline_strategy_episode_population_context as attach,
)
from llm.advisor_offline_strategy_episode_terminal_binding import (
    materialize_offline_strategy_episode_terminal_binding as bind,
)
from tests.test_offline_strategy_episode_terminal_binding import _episode, _final, _source
from tests.test_offline_strategy_episode_dataset import _editable


RULES = {
    "ruleset_id": "gen9-custom", "mechanics_version": "gen9-v1",
    "protocol_version": "showdown-v1", "battle_format_id": "singles-custom",
}


def _bound(*, gap=False):
    episode = _episode(gap=gap)
    source = _source("s" if gap else "replay")
    evidence = _final(source, turn=8)
    binding = bind(episode=episode, terminal_source=source, terminal_evidence=evidence)
    assert binding["status"] == ("incomplete" if gap else "resolved")
    return binding, source


def _attach(binding, source, sampling=None, rules=None, **scope):
    return attach(
        terminal_binding=binding, terminal_source=source,
        session_id=scope.get("session_id", binding["session_id"]),
        battle_id=scope.get("battle_id", binding["battle_id"]),
        rules_context=RULES if rules is None else rules,
        sampling_context={"collection_mode": "first_person_capture", "competition_context": "ladder"}
        if sampling is None else sampling,
    )


@pytest.mark.parametrize("mode,competition", [
    ("first_person_capture", "ladder"),
    ("simulator_self_generated", "self_play"),
    ("spectator_auxiliary", "tournament"),
])
def test_explicit_collection_modes_and_exact_rules_are_preserved(mode, competition):
    binding, source = _bound()
    result = _attach(binding, source, {
        "collection_mode": mode, "competition_context": competition,
        "collection_time": "2026-09-23T00:00:00Z", "self_rating": 1500,
        "source_dataset_id": "corpus-a",
    })
    assert result["status"] == "resolved"
    assert result["rules_context"] == RULES
    assert result["rules_context_fingerprint"] == fingerprint_decision_contract_reference(RULES)
    assert result["sampling_context"]["collection_mode"] == mode
    assert result["sampling_context"]["competition_context"] == competition
    assert result["sampling_context"]["self_rating"] == {"availability": "available", "value": 1500}
    assert result["sampling_context"]["opponent_rating"] == {"availability": "unavailable"}
    assert result["sampling_context"]["set_id"] == {"availability": "unavailable"}
    assert result["sampling_context"]["self_player_cluster_id"] == {"availability": "unavailable"}
    assert result["sampling_context"]["team_cluster_id"] == {"availability": "unavailable"}
    assert result["provenance"]["metadata_authority"] == "explicit_caller_supplied_unverified"
    assert result["provenance"]["decision_context_alignment"] == "not_proven_by_episode_transition_records"
    assert not {"train_eligible", "reward", "target", "support_score", "split"} & set(result)


def test_foreign_session_and_battle_fail_closed():
    binding, source = _bound()
    assert _attach(binding, source, session_id="foreign")["reason"] == "foreign_session"
    assert _attach(binding, source, battle_id="foreign")["reason"] == "foreign_battle"
    foreign_source = _source("foreign")
    assert _attach(binding, foreign_source)["reason"] == "foreign_session"


@pytest.mark.parametrize("rules", [
    {},
    {**RULES, "ruleset_id": ""},
    {**RULES, "mechanics_version": None},
    {**RULES, "extra": "unsupported"},
])
def test_malformed_rules_rejected(rules):
    binding, source = _bound()
    assert _attach(binding, source, rules=rules)["reason"] == "rules_context_invalid"


@pytest.mark.parametrize("sampling", [
    {},
    {"collection_mode": "actor", "competition_context": "ladder"},
    {"collection_mode": "first_person_capture", "competition_context": "ranked"},
    {"collection_mode": "first_person_capture", "competition_context": "ladder", "self_rating": float("nan")},
    {"collection_mode": "first_person_capture", "competition_context": "ladder", "self_rating": True},
    {"collection_mode": "first_person_capture", "competition_context": "ladder", "team_cluster_id": ""},
    {"collection_mode": "first_person_capture", "competition_context": "ladder", "unrecognized": "x"},
])
def test_malformed_sampling_rejected(sampling):
    binding, source = _bound()
    assert _attach(binding, source, sampling=sampling)["reason"] == "sampling_context_invalid"


def test_fabricated_or_stale_terminal_binding_rejected():
    binding, source = _bound()
    fabricated = _editable(binding)
    fabricated["terminal_outcome"]["declared_result"] = "opponent"
    assert _attach(fabricated, source)["reason"] == "terminal_binding_invalid"
    assert _attach(_freeze(fabricated), source)["reason"] == "terminal_binding_revalidation_failed"
    assert _attach(binding, _source())["reason"] == "terminal_binding_revalidation_failed"


def test_incomplete_base_and_raw_outcome_remain_unchanged():
    binding, source = _bound(gap=True)
    before = _editable(binding)
    result = _attach(binding, source)
    assert result["status"] == "incomplete"
    assert result["base_terminal_binding"]["continuity_gaps"] == binding["continuity_gaps"]
    assert result["base_terminal_binding"]["terminal_outcome"] == binding["terminal_outcome"]
    assert _editable(binding) == before
    assert binding["base_episode"]["terminal_status"]["availability"] == "unavailable"


def test_deterministic_detached_output_and_no_source_mutation():
    binding, source = _bound()
    rules = deepcopy(RULES)
    sampling = {
        "collection_mode": "first_person_capture", "competition_context": "direct_challenge",
        "opponent_rating": 1672.5, "set_id": "series-1",
    }
    rules_before, sampling_before, binding_before = deepcopy(rules), deepcopy(sampling), _editable(binding)
    first = _attach(binding, source, sampling, rules)
    second = _attach(binding, source, dict(reversed(list(sampling.items()))), dict(reversed(list(rules.items()))))
    assert first == second and first["context_binding_id"] == second["context_binding_id"]
    assert rules == rules_before and sampling == sampling_before and _editable(binding) == binding_before
    assert source.read_snapshot(captured_session_id="replay", captured_battle_id="battle-1")["terminal_evidence"] == binding["terminal_outcome"]["evidence"]
    rules["ruleset_id"] = "later-change"
    sampling["set_id"] = "later-change"
    assert first["rules_context"]["ruleset_id"] == "gen9-custom"
    assert first["sampling_context"]["set_id"]["value"] == "series-1"
    with pytest.raises(TypeError):
        first["rules_context"]["ruleset_id"] = "later-change"
    with pytest.raises(TypeError):
        first["sampling_context"]["set_id"]["value"] = "later-change"
