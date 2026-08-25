from copy import deepcopy

from llm.advisor_detached_opponent_response_profile import materialize_detached_opponent_response_profile
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_complete_opponent_response_set_authority import freeze_runtime_d0_complete_opponent_response_set_authority
from llm.advisor_runtime_d0_opponent_action_authority import METADATA_SCHEMA_VERSION, freeze_runtime_d0_opponent_known_move_action_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_substitute import update_substitute_state_context


MOVES = ("tackle", "water-gun", "scratch", "pound")


def _state():
    state = create_unknown_bootstrap_battle_state("response-profile", "self-a", "opponent-a")["state"]
    for side, speed in (("self", 100), ("opponent", 90)):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False, current_level=50, stat_stages={name: 0 for name in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}, condition="none", current_ability="pressure", known_item=None, current_type=["normal"], current_crit_volatiles=[])
        pokemon["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "none"}
        pokemon["current_level_provenance"] = {"event_kind": "current_level_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known_absent"}
        pokemon["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_crit_volatiles_provenance"] = {"event_kind": "current_crit_volatiles_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_final_stats"] = {stat: {"value": speed if stat == "speed" else 100, "provenance": {"event_kind": "current_final_combat_stat_observed", "trust": "user_confirmed_observation", "turn_number": 1}} for stat in ("attack", "defense", "special-attack", "special-defense", "speed")}
        state[f"{side}_side"]["side_conditions"] = []
        state[f"{side}_side"]["side_conditions_provenance"] = {"event_kind": "current_side_conditions_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        state["substitute_state_context"] = update_substitute_state_context(context=state.get("substitute_state_context"), session_id=state["session_id"], owner=_owner(state, side), state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1")
    state["field"].update(weather="none", terrain="none", battle_format="singles")
    for field, event in (("weather", "current_weather_observed"), ("terrain", "current_terrain_observed"), ("battle_format", "current_battle_format_observed")):
        state["field"][f"{field}_provenance"] = {"event_kind": event, "trust": "user_confirmed_observation", "turn_number": 1}
    return state


def _owner(state, side):
    slot = state[f"{side}_side"]["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _metadata(move):
    return {"status": "resolved", "schema_version": METADATA_SCHEMA_VERSION, "move_id": move, "metadata": {"move_id": move, "category": "special" if move == "water-gun" else "physical", "power": 40, "type": "water" if move == "water-gun" else "normal", "accuracy": 100, "priority": 0}, "provenance": "repository_normalized_move_metadata_v1"}


def _complete_state(state):
    opponent = _owner(state, "opponent")
    usability = {move: {"status": "known_usable", "reason": None} if move in {"tackle", "water-gun"} else {"status": "known_unusable", "reason": "disabled"} for move in MOVES}
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [{"observation_id": "responses", "observation_sequence": 1, "planned_effect": "set_current_opponent_response_set", "trust": "user_confirmed_observation", **opponent, "move_ids": list(MOVES), "move_usability": usability, "turn_number": 1}]}
    result = project_atomic_transition(state, plan, state["session_id"])
    assert result["status"] == "ready_with_projected_state"
    return result["projected_state"]


def _inputs():
    state = _complete_state(_state()); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = _owner(state, "self")
    own_metadata = _metadata("tackle") | {"candidate_id": "attack:tackle", "active_attacker": own, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    own_action = {"action_id": "attack:tackle", "action_type": "attack", "identity": "tackle", "move_metadata_authority": own_metadata}
    known = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities={move: _metadata(move) for move in MOVES})
    response_set = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=known)
    orders = {action_id: {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": "own_first", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "own_action_id": own_action["action_id"], "opponent_action_id": action_id, "own_actor": _owner(state, "self"), "opponent_actor": _owner(state, "opponent")} for action_id in response_set["selectable_response_action_ids"]}
    return state, snapshot, d0, own_action, response_set, orders


def test_complete_response_set_materializes_all_exact_pairs_without_probabilities():
    state, snapshot, d0, own_action, response_set, orders = _inputs()
    result = materialize_detached_opponent_response_profile(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, response_set_authority=response_set, action_order_authorities=orders)

    assert result["status"] == "evaluable"
    assert tuple(row["opponent_response_action_id"] for row in result["response_entries"]) == response_set["selectable_response_action_ids"]
    assert all(row["pair"]["status"] == row["exact_pair_outcome_ledger"]["status"] == "evaluable" and row["descriptive_metrics"]["status"] == "resolved" for row in result["response_entries"])
    assert all(row["exact_pair_outcome_ledger"]["terminal_probability_mass"] == {"numerator": 1, "denominator": 1} for row in result["response_entries"])
    assert result["response_probability"] == "not_modeled" and result["ranking_influence"] == "none"
    state["opponent_side"]["pokemon"][0]["current_hp"] = 1
    assert len(result["response_entries"]) == 2


def test_unusable_excluded_incomplete_pair_blocks_and_binding_mismatch_rejects():
    _, snapshot, d0, own_action, response_set, orders = _inputs()
    response_set = deepcopy(response_set)
    response_set["actions"] = tuple({**row, "selectability": "not_selectable", "usability": {"status": "known_unusable", "reason": "disabled"}} if row["action_id"] == "opponent_attack:water-gun" else row for row in response_set["actions"])
    response_set["selectable_response_action_ids"] = tuple(action_id for action_id in response_set["selectable_response_action_ids"] if action_id != "opponent_attack:water-gun")
    orders.pop("opponent_attack:water-gun")
    resolved = materialize_detached_opponent_response_profile(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, response_set_authority=response_set, action_order_authorities=orders)
    assert resolved["status"] == "evaluable" and "opponent_attack:water-gun" not in resolved["selectable_response_action_ids"]

    _, snapshot, d0, own_action, response_set, orders = _inputs()
    first = next(iter(orders)); orders[first] = {**orders[first], "status": "incomplete", "reason": "order_unknown"}
    incomplete = materialize_detached_opponent_response_profile(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, response_set_authority=response_set, action_order_authorities=orders)
    assert incomplete["status"] == "incomplete"

    bad_orders = dict(orders); bad_orders["forged"] = bad_orders.pop(next(iter(bad_orders)))
    assert materialize_detached_opponent_response_profile(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, response_set_authority=response_set, action_order_authorities=bad_orders)["status"] == "rejected"

    stale = deepcopy(snapshot); stale["state"]["last_applied_observation_sequence"] = 2; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert materialize_detached_opponent_response_profile(strategy_d0=d0, runtime_snapshot=stale, own_action=own_action, response_set_authority=response_set, action_order_authorities=orders)["status"] == "rejected"
