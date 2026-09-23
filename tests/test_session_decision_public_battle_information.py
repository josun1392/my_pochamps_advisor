"""Direct public facts captured before a submitted decision command."""
from copy import deepcopy
import pytest

from llm.advisor_session_decision_public_battle_information import (
    PUBLIC_SURFACE_VERSION, SessionBoundDecisionPublicBattleInformationSource,
)
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource
from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource
from tests.test_session_submitted_command_evidence_source import _admit, _case


def available(value):
    return {"availability": "available", "value": value}


def snapshot():
    return {
        "active": {
            "self": {
                "session_id": "session-a", "slot_index": 0, "pokemon_id": "self-a",
                "current_hp": available(51), "max_hp": available(100),
                "fainted": available(False), "condition": available("none"),
                "stat_stages": {"attack": available(0), "defense": available(-6), "speed": available(6)},
            },
            "opponent": {
                "session_id": "session-a", "slot_index": 0, "pokemon_id": "opponent-a",
                "current_hp": available(36), "max_hp": available(100),
                "fainted": available(False), "condition": available("burn"),
            },
        },
        "field": {"weather": available("rain"), "terrain": available("electric"),
                  "trick_room": available(False)},
        "sides": {"self": {"tailwind": available(True)}, "opponent": {"tailwind": available(False)}},
        "opponent_revealed_moves": {"status": "partial", "move_ids": ["protect", "shadow-ball"]},
    }


def case(channel="actor_first_person"):
    opportunity_source, command_source, opportunity, actor = _case(channel=channel)
    created = SessionBoundDecisionPublicBattleInformationSource.create(
        opportunity_source=opportunity_source, command_source=command_source, source_id="public-input-a")
    assert created["status"] == "source_ready"
    return created["source"], opportunity_source, command_source, opportunity, actor


def admit(source, opportunity, actor, value=None, **overrides):
    args = dict(captured_session_id="session-a", captured_battle_id="battle-a",
                opportunity_record=opportunity, actor=actor, source_public_event_id="public-1",
                public_snapshot=snapshot() if value is None else value)
    args.update(overrides)
    return source.admit_public_snapshot(**args)


@pytest.mark.parametrize("channel", ["actor_first_person", "simulator_input"])
def test_direct_public_snapshot_preserves_facts_and_availability(channel):
    source, _, _, opportunity, actor = case(channel)
    result = admit(source, opportunity, actor)
    assert result["status"] == "admitted", result
    evidence = result["evidence"]
    assert evidence["public_surface_version"] == PUBLIC_SURFACE_VERSION
    assert evidence["channel"] == channel
    assert evidence["session_id"] == "session-a" and evidence["battle_id"] == "battle-a"
    assert evidence["actor"] == actor
    assert evidence["boundary_id"] == opportunity["certificate"]["boundary_id"]
    assert evidence["prefix_fingerprint"] == opportunity["certificate"]["prefix_fingerprint"]
    assert evidence["context_fingerprint"] == opportunity["certificate"]["context_fingerprint"]
    public = evidence["public_snapshot"]
    assert public["active"]["self"]["pokemon_id"] == "self-a"
    assert public["active"]["opponent"]["pokemon_id"] == "opponent-a"
    assert public["active"]["opponent"]["current_hp"] == available(36)
    assert public["active"]["self"]["fainted"] == available(False)
    assert public["active"]["self"]["condition"] == available("none")
    assert public["active"]["opponent"]["condition"] == available("burn")
    assert public["active"]["self"]["stat_stages"]["attack"] == available(0)
    assert public["active"]["self"]["stat_stages"]["defense"] == available(-6)
    assert public["active"]["self"]["stat_stages"]["speed"] == available(6)
    assert public["active"]["self"]["stat_stages"]["evasion"] == {"availability": "unavailable"}
    assert public["field"]["weather"] == available("rain")
    assert public["field"]["terrain"] == available("electric")
    assert public["field"]["trick_room"] == available(False)
    assert public["sides"]["self"]["tailwind"] == available(True)
    assert public["opponent_revealed_moves"] == {"status": "partial", "move_ids": ("protect", "shadow-ball")}
    assert evidence["scope_limitation"] == "v1_supported_public_surface_only"
    assert evidence["directness_limitation"] == "external_actor_visibility_not_independently_verified"
    assert source.authenticates(evidence, opportunity)
    assert source.authenticates(source.read_snapshot(captured_session_id="session-a")["evidence"][0], opportunity)


def test_missing_values_are_unavailable_and_not_defaults():
    source, _, _, opportunity, actor = case()
    raw = snapshot()
    raw["active"]["opponent"].pop("current_hp")
    raw["active"]["opponent"].pop("max_hp")
    raw["active"]["opponent"].pop("fainted")
    raw["active"]["opponent"].pop("condition")
    raw["active"]["self"].pop("stat_stages")
    raw["field"] = {}
    raw["sides"]["self"] = {}
    raw["opponent_revealed_moves"] = {"status": "unknown", "move_ids": []}
    public = admit(source, opportunity, actor, raw)["evidence"]["public_snapshot"]
    unavailable = {"availability": "unavailable"}
    for key in ("current_hp", "max_hp", "fainted", "condition"):
        assert public["active"]["opponent"][key] == unavailable
    assert public["active"]["self"]["stat_stages"]["attack"] == unavailable
    assert public["field"]["weather"] == unavailable
    assert public["field"]["terrain"] == unavailable
    assert public["field"]["trick_room"] == unavailable
    assert public["sides"]["self"]["tailwind"] == unavailable
    assert public["opponent_revealed_moves"] == {"status": "unknown", "move_ids": ()}


@pytest.mark.parametrize("change", [
    lambda x: x["active"]["opponent"].update(held_item=available("leftovers")),
    lambda x: x["active"]["opponent"].update(ability=available("levitate")),
    lambda x: x["active"]["opponent"].update(stat_stages={"attack": available(7)}),
    lambda x: x["active"]["self"]["stat_stages"].update(defense=available(-7)),
    lambda x: x["active"]["opponent"].update(current_hp=available(120)),
    lambda x: x["active"]["opponent"].update(pokemon_id=""),
    lambda x: x["active"]["self"].update(pokemon_id="other-self"),
    lambda x: x["active"]["opponent"].update(session_id="foreign"),
    lambda x: x["field"].update(weather=available("unknown")),
    lambda x: x["opponent_revealed_moves"].update(move_ids=["protect", "protect"]),
    lambda x: x.update(terminal_result="self"),
    lambda x: x.update(command={"kind": "attack"}),
])
def test_malformed_or_hidden_and_post_boundary_fields_fail_closed(change):
    source, _, _, opportunity, actor = case()
    raw = snapshot()
    change(raw)
    assert admit(source, opportunity, actor, raw)["reason"] == "public_snapshot_invalid"


def test_stale_foreign_and_unretained_opportunity_fail_closed():
    source, _, _, opportunity, actor = case()
    assert admit(source, opportunity, actor, captured_session_id="foreign")["reason"] == "stale_or_foreign_session"
    assert admit(source, opportunity, actor, captured_battle_id="foreign")["reason"] == "foreign_battle"
    assert admit(source, opportunity, {**actor, "pokemon_id": "foreign"})["reason"] == "foreign_actor"
    other, foreign_source, _, _, foreign_actor = case()
    foreign_opportunity = foreign_source.capture_opportunity(
        captured_session_id="session-a", opportunity_id="distinct-opportunity",
        actor=foreign_actor, decision_kind="turn_start", turn_number=2,
        simultaneity_group_id="turn-2", context_reference=opportunity["context_reference"],
        legal_action_set=opportunity["legal_action_set"],
    )
    assert foreign_opportunity["status"] == "captured"
    assert other is not source
    assert admit(source, foreign_opportunity, foreign_actor)["reason"] == "opportunity_not_retained_by_source"
    assert source.read_snapshot(captured_session_id="foreign")["reason"] == "stale_or_foreign_session"


def test_spectator_and_opponent_side_cannot_create_canonical_public_source():
    spectator = SessionBoundDecisionOpportunityBoundarySource.create(
        session_id="session-a", battle_id="battle-a", source_id="spectator-a", channel="spectator",
        actor={"session_id": "session-a", "side": "self", "slot_index": 0, "pokemon_id": "self-a"},
    )
    assert spectator["reason"] == "source_channel_invalid"
    opponent = SessionBoundDecisionOpportunityBoundarySource.create(
        session_id="session-a", battle_id="battle-a", source_id="opponent-a", channel="simulator_input",
        actor={"session_id": "session-a", "side": "opponent", "slot_index": 0, "pokemon_id": "opponent-a"},
    )["source"]
    command = SessionBoundSubmittedCommandEvidenceSource.create(
        opportunity_source=opponent, source_id="command-a")["source"]
    created = SessionBoundDecisionPublicBattleInformationSource.create(
        opportunity_source=opponent, command_source=command, source_id="public-a")
    assert created["reason"] == "foreign_actor_side"


def test_late_admission_rejected_after_command_or_prefix_advance():
    source, opportunity_source, command_source, opportunity, actor = case()
    assert _admit(command_source, opportunity, actor, {"kind": "attack", "move_slot": 1})["status"] == "admitted"
    assert admit(source, opportunity, actor)["reason"] == "command_already_admitted"
    source2, opportunity_source2, _, opportunity2, actor2 = case()
    assert opportunity_source2.admit_channel_event(
        captured_session_id="session-a", source_event_id="later-reveal",
        source_event_fingerprint="a" * 64)["status"] == "admitted"
    assert admit(source2, opportunity2, actor2)["reason"] == "opportunity_prefix_advanced"


def test_duplicate_conflict_determinism_detachment_and_no_runtime_mutation():
    source, opportunity_source, command_source, opportunity, actor = case()
    raw = snapshot()
    before_opportunity = opportunity_source.read_snapshot(captured_session_id="session-a")
    before_command = command_source.read_snapshot(captured_session_id="session-a")
    original = deepcopy(raw)
    result = admit(source, opportunity, actor, raw)
    assert raw == original
    evidence = result["evidence"]
    assert admit(source, opportunity, actor, raw)["status"] == "duplicate"
    raw["active"]["self"]["current_hp"]["value"] = 0
    assert evidence["public_snapshot"]["active"]["self"]["current_hp"] == available(51)
    assert admit(source, opportunity, actor, raw)["reason"] == "conflicting_public_snapshot"
    assert opportunity_source.read_snapshot(captured_session_id="session-a") == before_opportunity
    assert command_source.read_snapshot(captured_session_id="session-a") == before_command
    assert len(source.read_snapshot(captured_session_id="session-a")["evidence"]) == 1
    assert not source.authenticates({**evidence}, opportunity)
    with pytest.raises(TypeError):
        evidence["public_snapshot"]["active"]["self"]["current_hp"]["value"] = 0
    other, _, _, other_opportunity, other_actor = case()
    assert admit(other, other_opportunity, other_actor)["evidence"]["public_information_id"] == evidence["public_information_id"]
    assert not {"reward", "target", "terminal", "result", "execution", "command"} & set(evidence["public_snapshot"])
