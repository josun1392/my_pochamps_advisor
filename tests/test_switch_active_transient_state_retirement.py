"""Reducer switch-out retirement for facts that only exist while active."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import make_unknown_battle_fact, project_atomic_transition


_STATS = (
    "attack", "defense", "special-attack", "special-defense",
    "speed", "accuracy", "evasion",
)


def _state():
    state = create_unknown_bootstrap_battle_state("switch-transients", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        active = state[f"{side}_side"]["pokemon"][0]
        active.update(current_hp=73, max_hp=100, fainted=False, known_item="leftovers")
        bench = deepcopy(active)
        bench["pokemon_id"] = f"{side}-b"
        state[f"{side}_side"]["pokemon"][1] = bench
    return state


def _plan(state, *, side, out_slot, in_slot, sequence, observation_id):
    roster = state[f"{side}_side"]["pokemon"]
    return {
        "session_id": state["session_id"], "status": "planned", "conflicts": [],
        "ordered_steps": [{
            "observation_id": observation_id, "observation_sequence": sequence,
            "planned_effect": "switch_active", "trust": "user_confirmed_observation",
            "side": side, "switch_out_slot_index": out_slot,
            "switch_out_pokemon_id": roster[out_slot]["pokemon_id"],
            "switch_in_slot_index": in_slot,
            "switch_in_pokemon_id": roster[in_slot]["pokemon_id"],
        }],
    }


def _apply(state, **kwargs):
    result = project_atomic_transition(state, _plan(state, **kwargs), state["session_id"])
    assert result["status"] == "ready_with_projected_state"
    return result["projected_state"]


def _active_only_observations(pokemon):
    pokemon["stat_stages"] = dict(zip(_STATS, (3, -2, 1, -1, 5, 2, -3)))
    pokemon["stat_stages_provenance"] = {"event_kind": "current_stat_stage_observed"}
    pokemon["current_type"] = ["water"]
    pokemon["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    pokemon["current_ability"] = "levitate"
    pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    pokemon["healing_prevented_status"] = "active"
    pokemon["healing_prevented_status_provenance"] = {
        "event_kind": "current_healing_prevented_observed", "trust": "user_confirmed_observation",
        "status": "active", "turn_number": 1, "source_observation_id": "noise", "source_sequence": 1,
    }
    pokemon["current_crit_volatiles"] = ["focus-energy"]
    pokemon["current_crit_volatiles_provenance"] = {"event_kind": "current_crit_volatiles_observed", "trust": "user_confirmed_observation", "turn_number": 1}


def test_switch_out_and_reentry_retire_only_active_transient_state():
    state = _state()
    outgoing = state["self_side"]["pokemon"][0]
    _active_only_observations(outgoing)
    persistent = {field: deepcopy(outgoing[field]) for field in ("pokemon_id", "current_hp", "max_hp", "fainted", "known_item")}
    unrelated = deepcopy(state["opponent_side"]["pokemon"])
    source_before = deepcopy(state)

    switched = _apply(state, side="self", out_slot=0, in_slot=1, sequence=1, observation_id="switch-out")
    returned = _apply(switched, side="self", out_slot=1, in_slot=0, sequence=2, observation_id="switch-back")
    outgoing = returned["self_side"]["pokemon"][0]

    assert outgoing["stat_stages"] == {stat: 0 for stat in _STATS}
    assert "stat_stages_provenance" not in outgoing
    for field in ("current_type", "current_ability", "healing_prevented_status", "current_crit_volatiles"):
        assert outgoing[field] == make_unknown_battle_fact()
        assert f"{field}_provenance" not in outgoing
    assert {field: outgoing[field] for field in persistent} == persistent
    assert returned["opponent_side"]["pokemon"] == unrelated
    assert state == source_before


def test_replayed_switch_observation_rejects_without_reapplying_transient_retirement():
    state = _state()
    _active_only_observations(state["self_side"]["pokemon"][0])
    plan_kwargs = dict(side="self", out_slot=0, in_slot=1, sequence=1, observation_id="switch-out")
    switched = _apply(state, **plan_kwargs)
    before_replay = deepcopy(switched)
    replay = project_atomic_transition(switched, _plan(switched, **plan_kwargs), switched["session_id"])

    assert replay["status"] == "blocked_by_semantic_conflict"
    assert replay["projected_state"] is None
    assert switched == before_replay


def test_switching_the_other_side_does_not_retire_this_active_pokemon_state():
    state = _state()
    _active_only_observations(state["self_side"]["pokemon"][0])
    before = deepcopy(state["self_side"]["pokemon"][0])

    switched = _apply(state, side="opponent", out_slot=0, in_slot=1, sequence=1, observation_id="opponent-switch")

    assert switched["self_side"]["pokemon"][0] == before
