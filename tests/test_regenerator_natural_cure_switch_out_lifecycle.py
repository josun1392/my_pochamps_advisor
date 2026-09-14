"""Exact reducer switch-out lifecycle for Regenerator and Natural Cure."""
from copy import deepcopy

import pytest

from llm.advisor_ability_interaction_authority import build_ability_applicability_context
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import project_atomic_transition


def _state(*, ability="pressure", hp=30, maximum=90, condition=None, applicability="applicable"):
    state = create_unknown_bootstrap_battle_state("switch-out-abilities", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        active = state[f"{side}_side"]["pokemon"][0]
        active.update(current_hp=hp, max_hp=maximum, fainted=hp == 0, known_item="leftovers")
        bench = deepcopy(active)
        bench["pokemon_id"] = f"{side}-b"
        state[f"{side}_side"]["pokemon"][1] = bench
    active = state["self_side"]["pokemon"][0]
    active["current_ability"] = ability
    active["current_ability_provenance"] = {
        "event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1,
    }
    active["condition"] = condition
    if condition is not None:
        active["condition_provenance"] = {
            "event_kind": "current_condition_observed", "trust": "user_confirmed_observation",
            "turn_number": 1, "condition": condition,
        }
    if ability in {"regenerator", "natural-cure"} and applicability is not None:
        state["ability_applicability_context"] = build_ability_applicability_context(
            session_id=state["session_id"],
            source={"side": "self", "slot_index": 0, "pokemon_id": "self-a"},
            ability_id=ability, status=applicability,
        )
    return state


def _switch_plan(state, *, side="self", sequence=1, observation_id="switch"):
    roster = state[f"{side}_side"]["pokemon"]
    return {
        "session_id": state["session_id"], "status": "planned", "conflicts": [],
        "ordered_steps": [{
            "observation_id": observation_id, "observation_sequence": sequence,
            "planned_effect": "switch_active", "trust": "user_confirmed_observation",
            "side": side, "switch_out_slot_index": 0,
            "switch_out_pokemon_id": roster[0]["pokemon_id"],
            "switch_in_slot_index": 1, "switch_in_pokemon_id": roster[1]["pokemon_id"],
        }],
    }


def _switch(state, **kwargs):
    return project_atomic_transition(state, _switch_plan(state, **kwargs), state["session_id"])


@pytest.mark.parametrize(("hp", "maximum", "expected"), [(30, 90, 60), (80, 90, 90), (90, 90, 90), (1, 100, 34)])
def test_regenerator_recovers_exact_floor_one_third_and_caps(hp, maximum, expected):
    result = _switch(_state(ability="regenerator", hp=hp, maximum=maximum))
    assert result["status"] == "ready_with_projected_state"
    outgoing = result["projected_state"]["self_side"]["pokemon"][0]
    assert outgoing["current_hp"] == expected and outgoing["max_hp"] == maximum


def test_regenerator_ignores_healing_prevented_and_does_not_revive_or_heal_other_abilities():
    state = _state(ability="regenerator", hp=30)
    state["self_side"]["pokemon"][0].update(
        healing_prevented_status="active",
        healing_prevented_status_provenance={
            "event_kind": "current_healing_prevented_observed", "trust": "user_confirmed_observation",
            "status": "active", "turn_number": 1, "source_observation_id": "noise", "source_sequence": 1,
        },
    )
    assert _switch(state)["projected_state"]["self_side"]["pokemon"][0]["current_hp"] == 60

    fainted = _state(ability="regenerator", hp=0)
    fainted["self_side"]["pokemon"][1].update(current_hp=100, max_hp=100, fainted=False)
    result = _switch(fainted)
    assert result["status"] == "ready_with_projected_state"
    assert result["projected_state"]["self_side"]["pokemon"][0]["current_hp"] == 0

    ordinary = _switch(_state(ability="pressure", hp=30))
    assert ordinary["projected_state"]["self_side"]["pokemon"][0]["current_hp"] == 30


@pytest.mark.parametrize("ability", ["regenerator", "natural-cure"])
def test_unknown_or_explicitly_not_applicable_outgoing_ability_never_assumes_activation(ability):
    unknown = _switch(_state(ability=ability, condition="burn", applicability=None))
    assert unknown["status"] == "blocked_by_semantic_conflict"
    assert unknown["projected_state"] is None

    inactive = _switch(_state(ability=ability, condition="burn", applicability="not_applicable"))
    assert inactive["status"] == "ready_with_projected_state"
    outgoing = inactive["projected_state"]["self_side"]["pokemon"][0]
    assert outgoing["current_hp"] == 30
    assert outgoing["condition"] == "burn"


@pytest.mark.parametrize("condition", ["burn", "paralysis", "sleep", "poison", "toxic", "freeze"])
def test_natural_cure_clears_each_major_condition_with_switch_out_provenance(condition):
    result = _switch(_state(ability="natural-cure", condition=condition))
    assert result["status"] == "ready_with_projected_state"
    outgoing = result["projected_state"]["self_side"]["pokemon"][0]
    assert outgoing["condition"] is None
    assert outgoing["condition_provenance"]["event_kind"] == "condition_removed_observed"
    assert outgoing["condition_provenance"]["source"] == "natural_cure_switch_out"


def test_natural_cure_leaves_no_condition_and_confusion_to_the_existing_switch_lifecycle():
    none = _switch(_state(ability="natural-cure", condition=None))
    assert none["status"] == "ready_with_projected_state"
    assert none["projected_state"]["self_side"]["pokemon"][0]["condition"] is None

    state = _state(ability="natural-cure", condition=None)
    state["self_side"]["pokemon"][0]["current_confusion"] = "confused"
    confused = _switch(state)
    outgoing = confused["projected_state"]["self_side"]["pokemon"][0]
    assert outgoing["condition"] is None
    assert outgoing["confusion_provenance"]["event_kind"] == "confusion_cleared_on_switch"


def test_natural_cure_unknown_condition_fails_closed_and_non_natural_cure_preserves_condition():
    unknown = _switch(_state(ability="natural-cure", condition={"knowledge": "unknown"}))
    assert unknown["status"] == "blocked_by_semantic_conflict"
    ordinary = _switch(_state(ability="pressure", condition="burn"))
    assert ordinary["status"] == "ready_with_projected_state"
    assert ordinary["projected_state"]["self_side"]["pokemon"][0]["condition"] == "burn"


def test_outgoing_effect_precedes_ability_retirement_and_other_side_switch_does_not_trigger_it():
    state = _state(ability="regenerator", hp=30)
    source_before = deepcopy(state)
    result = _switch(state)
    outgoing = result["projected_state"]["self_side"]["pokemon"][0]
    assert outgoing["current_hp"] == 60
    assert outgoing["current_ability"] == {"knowledge": "unknown"}
    assert "current_ability_provenance" not in outgoing
    assert state == source_before

    other = _switch(_state(ability="regenerator", hp=30), side="opponent")
    assert other["status"] == "ready_with_projected_state"
    assert other["projected_state"]["self_side"]["pokemon"][0]["current_hp"] == 30


def test_replayed_switch_remains_safe_after_outgoing_ability_lifecycle():
    state = _state(ability="regenerator", hp=30)
    first = _switch(state)
    switched = first["projected_state"]
    replay = _switch(switched)
    assert replay["status"] == "blocked_by_semantic_conflict"
    assert replay["projected_state"] is None
