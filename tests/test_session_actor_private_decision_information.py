"""Direct own-side facts retained before a submitted command."""
from copy import deepcopy

import pytest

from llm.advisor_session_actor_private_decision_information import (
    PRIVATE_SURFACE_VERSION,
    SessionBoundActorPrivateDecisionInformationSource,
)
from llm.advisor_session_battle_terminal_outcome_evidence import (
    SessionBoundBattleTerminalOutcomeEvidenceSource,
)
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource
from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource
from tests.test_session_decision_opportunity_source import _capture, _inputs
from tests.test_session_submitted_command_evidence_source import _admit, _case


STATS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")


def _available(value):
    return {"availability": "available", "value": value}


def _roster_row(slot, pokemon_id, *, item):
    return {
        "slot_index": slot, "pokemon_id": pokemon_id,
        "move_scope": {"status": "exact", "move_slots": [1, 2]},
        "moves": [
            {"move_slot": 1, "move_id": "shadow-ball", "current_pp": 0},
            {"move_slot": 2, "move_id": "protect", "current_pp": 16},
        ],
        "known_item": _available(item), "current_ability": _available("static"),
        "current_level": _available(50),
        "current_final_stats": {stat: _available(100 + index) for index, stat in enumerate(STATS)},
    }


def _snapshot():
    return {
        "roster_scope": {"status": "exact", "slot_indices": [0, 1]},
        "own_roster": [_roster_row(0, "self-a", item="life-orb"),
                       _roster_row(1, "bench-a", item=None)],
    }


def _source(*, channel="actor_first_person"):
    opportunity_source, command_source, opportunity, actor = _case(channel=channel)
    created = SessionBoundActorPrivateDecisionInformationSource.create(
        opportunity_source=opportunity_source, command_source=command_source,
        source_id="private-input-a",
    )
    assert created["status"] == "source_ready"
    return created["source"], opportunity_source, command_source, opportunity, actor


def _admit_private(source, opportunity, actor, snapshot=None, *, event_id="private-1", session="session-a", battle="battle-a"):
    return source.admit_private_snapshot(
        captured_session_id=session, captured_battle_id=battle,
        opportunity_record=opportunity, actor=actor,
        source_private_event_id=event_id,
        private_snapshot=_snapshot() if snapshot is None else snapshot,
    )


@pytest.mark.parametrize("channel", ["actor_first_person", "simulator_input"])
def test_complete_snapshot_preserves_own_roster_moves_pp_item_ability_level_and_stats(channel):
    source, _, _, opportunity, actor = _source(channel=channel)
    admitted = _admit_private(source, opportunity, actor)
    assert admitted["status"] == "admitted", admitted
    evidence = admitted["evidence"]
    assert evidence["completeness"] == "complete_for_v1_supported_private_surface"
    assert evidence["private_surface_version"] == PRIVATE_SURFACE_VERSION
    assert evidence["channel"] == channel
    assert evidence["boundary_id"] == opportunity["certificate"]["boundary_id"]
    rows = evidence["private_snapshot"]["own_roster"]
    assert tuple((row["slot_index"], row["pokemon_id"]) for row in rows) == ((0, "self-a"), (1, "bench-a"))
    assert rows[0]["moves"][0]["move_slot"] == 1
    assert rows[0]["moves"][0]["move_id"] == _available("shadow-ball")
    assert rows[0]["moves"][0]["current_pp"] == _available(0)
    assert rows[0]["known_item"] == _available("life-orb")
    assert rows[1]["known_item"] == _available(None)
    assert rows[0]["current_ability"] == _available("static")
    assert rows[0]["current_level"] == _available(50)
    assert rows[0]["current_final_stats"]["special-attack"] == _available(103)
    assert source.authenticates(evidence, opportunity)
    assert not {"command", "execution", "result", "reward", "target"} & set(evidence["private_snapshot"])


@pytest.mark.parametrize("change", [
    lambda value: value["own_roster"][0].pop("current_ability"),
    lambda value: value["own_roster"][0]["moves"][0].pop("current_pp"),
    lambda value: value["own_roster"][0]["current_final_stats"].pop("speed"),
    lambda value: value["own_roster"][0].pop("known_item"),
    lambda value: value["own_roster"][0].pop("current_level"),
    lambda value: value["own_roster"].pop(),
    lambda value: value["own_roster"][0].pop("move_scope"),
])
def test_missing_required_private_category_is_incomplete_without_default(change):
    source, _, _, opportunity, actor = _source()
    raw = _snapshot()
    change(raw)
    result = _admit_private(source, opportunity, actor, raw)
    assert result["status"] == "admitted", result
    evidence = result["evidence"]
    assert evidence["completeness"] == "incomplete"
    assert evidence["private_snapshot"]["roster_scope"]["status"] == "exact"
    assert "opponent" not in evidence["private_snapshot"]
    if "current_ability" not in raw["own_roster"][0]:
        assert evidence["private_snapshot"]["own_roster"][0]["current_ability"] == {"availability": "unavailable"}


def test_unknown_roster_scope_never_claims_complete():
    source, _, _, opportunity, actor = _source()
    raw = _snapshot()
    raw["roster_scope"]["status"] = "unknown"
    result = _admit_private(source, opportunity, actor, raw)
    assert result["status"] == "admitted"
    assert result["evidence"]["completeness"] == "incomplete"


def test_spectator_and_opponent_actor_cannot_create_private_complete_source():
    actor = {"session_id": "session-a", "side": "self", "slot_index": 0, "pokemon_id": "self-a"}
    spectator = SessionBoundDecisionOpportunityBoundarySource.create(
        session_id="session-a", battle_id="battle-a", source_id="spectator-a",
        channel="spectator", actor=actor,
    )
    assert spectator["reason"] == "source_channel_invalid"
    foreign_actor = dict(actor, side="opponent")
    created = SessionBoundDecisionOpportunityBoundarySource.create(
        session_id="session-a", battle_id="battle-a", source_id="opponent-a",
        channel="actor_first_person", actor=foreign_actor,
    )
    assert created["status"] == "source_ready"
    command = SessionBoundSubmittedCommandEvidenceSource.create(
        opportunity_source=created["source"], source_id="command-a",
    )["source"]
    assert SessionBoundActorPrivateDecisionInformationSource.create(
        opportunity_source=created["source"], command_source=command, source_id="private-a",
    )["reason"] == "foreign_actor_side"


def test_stale_foreign_and_unretained_opportunities_fail_closed():
    source, _, _, opportunity, actor = _source()
    assert _admit_private(source, opportunity, actor, session="foreign")["reason"] == "stale_or_foreign_session"
    assert _admit_private(source, opportunity, actor, battle="foreign")["reason"] == "foreign_battle"
    assert _admit_private(source, opportunity, dict(actor, pokemon_id="foreign"))["reason"] == "foreign_actor"
    other_source, other_actor, context, legal = _inputs()
    foreign_opportunity = _capture(other_source, other_actor, context, legal, opportunity_id="foreign-request")
    assert _admit_private(source, foreign_opportunity, actor)["reason"] == "opportunity_not_retained_by_source"
    assert not source.authenticates({"completeness": "complete_for_v1_supported_private_surface"}, opportunity)


def test_private_admission_is_before_command_and_at_exact_opportunity_prefix():
    source, opportunity_source, command_source, opportunity, actor = _source()
    command = _admit(command_source, opportunity, actor, {"kind": "attack", "move_slot": 1})
    assert command["status"] == "admitted"
    assert _admit_private(source, opportunity, actor)["reason"] == "command_already_admitted"

    fresh, opportunity_source, _, opportunity, actor = _source()
    advanced = opportunity_source.admit_channel_event(
        captured_session_id="session-a", source_event_id="later-reveal",
        source_event_fingerprint="a" * 64,
    )
    assert advanced["status"] == "admitted"
    assert _admit_private(fresh, opportunity, actor)["reason"] == "opportunity_prefix_advanced"


def test_later_command_and_terminal_result_cannot_rewrite_private_snapshot():
    source, _, command_source, opportunity, actor = _source()
    admitted = _admit_private(source, opportunity, actor)
    before = source.read_snapshot(captured_session_id="session-a")
    assert _admit(command_source, opportunity, actor, {"kind": "attack", "move_slot": 1})["status"] == "admitted"
    terminal = SessionBoundBattleTerminalOutcomeEvidenceSource.create(
        session_id="session-a", battle_id="battle-a", source_id="terminal-a",
        source_kind="first_person_battle_stream",
    )["source"]
    terminal.admit_final_declaration(
        captured_session_id="session-a", captured_battle_id="battle-a",
        declaring_source_id="terminal-a", source_terminal_event_id="end-a",
        source_event_sequence=1, declared_result="opponent", termination_cause="unknown",
    )
    assert source.read_snapshot(captured_session_id="session-a") == before
    assert source.authenticates(admitted["evidence"], opportunity)
    assert _admit_private(source, opportunity, actor)["status"] == "duplicate"


def test_exact_duplicate_conflict_determinism_detachment_and_no_caller_mutation():
    source, _, _, opportunity, actor = _source()
    raw = _snapshot()
    before = deepcopy(raw)
    admitted = _admit_private(source, opportunity, actor, raw)
    evidence = admitted["evidence"]
    assert raw == before
    assert _admit_private(source, opportunity, actor, raw)["status"] == "duplicate"
    altered = deepcopy(raw)
    altered["own_roster"][0]["moves"][0]["current_pp"] = 9
    assert _admit_private(source, opportunity, actor, altered)["reason"] == "conflicting_private_snapshot"
    assert _admit_private(source, opportunity, actor, raw, event_id="other-event")["reason"] == "conflicting_private_snapshot"
    raw["own_roster"][0]["moves"][0]["current_pp"] = 99
    assert evidence["private_snapshot"]["own_roster"][0]["moves"][0]["current_pp"] == _available(0)
    second, _, _, second_opportunity, second_actor = _source()
    equivalent = _admit_private(second, second_opportunity, second_actor)["evidence"]
    assert evidence == equivalent and evidence["private_information_id"] == equivalent["private_information_id"]
    with pytest.raises(TypeError):
        evidence["private_snapshot"]["own_roster"][0]["moves"][0]["current_pp"]["value"] = 7
    with pytest.raises(TypeError):
        source.read_snapshot(captured_session_id="session-a")["evidence"][0]["completeness"] = "incomplete"


def test_malformed_or_hindsight_payload_rejected_without_knowledge_inference():
    source, _, _, opportunity, actor = _source()
    bad = _snapshot()
    bad["selected_command"] = {"kind": "attack", "move_slot": 1}
    assert _admit_private(source, opportunity, actor, bad)["reason"] == "private_snapshot_invalid"
    bad = _snapshot()
    bad["own_roster"][0]["current_final_stats"]["speed"] = _available(0)
    assert _admit_private(source, opportunity, actor, bad)["reason"] == "private_snapshot_invalid"
    bad = _snapshot()
    bad["own_roster"][0]["pokemon_id"] = "later-revealed-opponent"
    assert _admit_private(source, opportunity, actor, bad)["reason"] == "private_snapshot_invalid"
    bad = _snapshot()
    bad["roster_scope"]["status"] = []
    assert _admit_private(source, opportunity, actor, bad)["reason"] == "private_snapshot_invalid"
    assert source.read_snapshot(captured_session_id="session-a")["evidence"] == ()
