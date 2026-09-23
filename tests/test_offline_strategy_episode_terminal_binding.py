"""Strict, detached binding of observed battle endings to offline episodes."""
from types import MappingProxyType

import pytest

from llm.advisor_offline_strategy_episode_dataset import materialize_offline_strategy_episode
from llm.advisor_offline_strategy_episode_terminal_binding import (
    materialize_offline_strategy_episode_terminal_binding as bind,
)
from llm.advisor_session_battle_terminal_outcome_evidence import (
    SessionBoundBattleTerminalOutcomeEvidenceSource,
)
from tests.test_offline_strategy_episode_dataset import _chain, _editable
from tests.test_offline_strategy_transition_replay import _attack_case, _run


def _episode(*, gap=False):
    transitions = _chain(gap=True) if gap else (_run(_attack_case()),)
    episode = materialize_offline_strategy_episode(list(transitions))
    assert episode["status"] == ("incomplete" if gap else "resolved")
    return episode


def _source(session="replay"):
    result = SessionBoundBattleTerminalOutcomeEvidenceSource.create(
        session_id=session, battle_id="battle-1", source_id="stream-1",
        source_kind="first_person_battle_stream",
    )
    assert result["status"] == "source_ready"
    return result["source"]


def _final(source, result="self", cause="all_fainted", turn=8):
    admitted = source.admit_final_declaration(
        captured_session_id=source.session_id, captured_battle_id=source.battle_id,
        declaring_source_id=source.source_id, source_terminal_event_id="end-1",
        source_event_sequence=1, declared_result=result, termination_cause=cause,
        turn_number=turn, source_cause_event_id="end-1" if cause != "unknown" else None,
    )
    assert admitted["status"] == "admitted"
    return admitted["evidence"]


@pytest.mark.parametrize("result,cause", [
    ("self", "all_fainted"), ("opponent", "forfeit_self"), ("tie", "unknown"),
])
def test_direct_outcome_preserves_raw_dimensions_without_reward(result, cause):
    episode, source = _episode(), _source()
    evidence = _final(source, result, cause)
    bound = bind(episode=episode, terminal_source=source, terminal_evidence=evidence)
    assert bound["status"] == "resolved"
    assert bound["terminal_outcome"]["availability"] == "available"
    assert bound["terminal_outcome"]["declared_result"] == result
    assert bound["terminal_outcome"]["termination_cause"] == cause
    assert bound["terminal_outcome"]["evidence_completeness"] == "final_declaration_observed"
    assert bound["terminal_outcome"]["evidence_id"] == evidence["evidence_id"]
    assert bound["terminal_outcome"]["evidence"] == evidence
    assert bound["battle_id"] == "battle-1" and "battle_id" not in episode
    assert bound["binding_basis"] == "session_scoped_terminal_source"
    assert not {"reward", "utility", "return", "numeric_target"} & set(_editable(bound))
    assert episode["terminal_status"] == {
        "availability": "unavailable", "reason": "battle_terminality_not_observed",
    }


def test_stream_end_and_absent_evidence_are_explicitly_nonterminal():
    episode, source = _episode(), _source()
    absent = bind(episode=episode, terminal_source=source)
    assert absent["status"] == "incomplete"
    assert absent["terminal_outcome"]["reason"] == "terminal_declaration_not_observed"
    end = source.record_stream_end_without_declaration(
        captured_session_id="replay", captured_battle_id="battle-1",
        declaring_source_id="stream-1", source_stream_end_event_id="eof-1",
        source_event_sequence=2,
    )["evidence"]
    truncated = bind(episode=episode, terminal_source=source, terminal_evidence=end)
    assert truncated["status"] == "incomplete"
    assert truncated["terminal_outcome"]["availability"] == "unavailable"
    assert truncated["terminal_outcome"]["reason"] == "stream_ended_without_declaration"
    assert truncated["terminal_outcome"]["evidence"] == end
    assert "declared_result" not in truncated["terminal_outcome"]


def test_foreign_session_and_unretained_or_fabricated_evidence_rejected():
    episode, source = _episode(), _source()
    evidence = _final(source)
    assert bind(episode=episode, terminal_source=_source("foreign"))["reason"] == "foreign_session"
    assert bind(episode=episode, terminal_source=_source(), terminal_evidence=evidence)["reason"] == "terminal_evidence_not_authenticated"
    fabricated = _editable(evidence)
    fabricated["declared_result"] = "opponent"
    assert bind(episode=episode, terminal_source=source, terminal_evidence=fabricated)["reason"] == "terminal_evidence_not_authenticated"
    assert bind(episode=episode, terminal_source=source, terminal_evidence=MappingProxyType(fabricated))["reason"] == "terminal_evidence_not_authenticated"


def test_known_earlier_terminal_turn_rejected_and_unknown_preserved():
    episode = _episode(gap=True)
    source = _source("s")
    early = _final(source, turn=4)
    assert bind(episode=episode, terminal_source=source, terminal_evidence=early)["reason"] == "terminal_before_episode_final_turn"
    episode = _episode()
    unknown_source = _source()
    unknown = _final(unknown_source, turn=None)
    bound = bind(episode=episode, terminal_source=unknown_source, terminal_evidence=unknown)
    assert bound["status"] == "resolved"
    assert bound["terminal_outcome"]["turn_number"] is None


def test_incomplete_episode_keeps_lineage_gap_with_attached_declaration():
    episode = _episode(gap=True)
    source = _source("s")
    evidence = _final(source, turn=5)
    bound = bind(episode=episode, terminal_source=source, terminal_evidence=evidence)
    assert bound["status"] == "incomplete"
    assert bound["base_episode_status"] == "incomplete"
    assert bound["continuity_gaps"] == episode["continuity_gaps"]
    assert bound["terminal_outcome"]["availability"] == "available"


def test_binding_determinism_detachment_and_source_immutability():
    episode, source = _episode(), _source()
    evidence = _final(source)
    episode_before, evidence_before = _editable(episode), _editable(evidence)
    binding = bind(episode=episode, terminal_source=source, terminal_evidence=evidence)
    repeated = bind(episode=episode, terminal_source=source, terminal_evidence=evidence)
    assert binding == repeated and binding["binding_id"] == repeated["binding_id"]
    assert _editable(episode) == episode_before
    assert _editable(evidence) == evidence_before
    assert binding["base_episode"]["transitions"] == episode["transitions"]
    assert source.read_snapshot(captured_session_id="replay", captured_battle_id="battle-1")["terminal_evidence"] == evidence
    with pytest.raises(TypeError):
        binding["terminal_outcome"]["declared_result"] = "opponent"
    with pytest.raises(TypeError):
        binding["base_episode"]["status"] = "resolved"
    with pytest.raises(TypeError):
        binding["base_episode"]["transitions"][0]["status"] = "incomplete"


def test_rejects_arbitrary_episode_mapping():
    episode = _episode()
    assert bind(episode=_editable(episode), terminal_source=_source())["reason"] == "episode_invalid"
