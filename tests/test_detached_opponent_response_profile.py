from copy import deepcopy

from llm.advisor_detached_opponent_response_profile import materialize_detached_opponent_response_profile
from llm.advisor_exact_equal_speed_action_order_branching import materialize_exact_equal_speed_action_order_branches
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
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
    metadata = {"move_id": move, "category": "special" if move in {"water-gun", "thunderbolt"} else "physical", "power": 90 if move == "thunderbolt" else 40, "type": "electric" if move == "thunderbolt" else "water" if move == "water-gun" else "normal", "accuracy": 100, "priority": 0}
    if move == "thunderbolt":
        metadata.update(target="selected-pokemon", effect_chance=10, ailment="paralysis")
    return {"status": "resolved", "schema_version": METADATA_SCHEMA_VERSION, "move_id": move, "metadata": metadata, "provenance": "repository_normalized_move_metadata_v1"}


def _complete_state(state):
    opponent = _owner(state, "opponent")
    usability = {move: {"status": "known_usable", "reason": None} if move in {"tackle", "water-gun"} else {"status": "known_unusable", "reason": "disabled"} for move in MOVES}
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [{"observation_id": "responses", "observation_sequence": 1, "planned_effect": "set_current_opponent_response_set", "trust": "user_confirmed_observation", **opponent, "move_ids": list(MOVES), "move_usability": usability, "turn_number": 1}]}
    result = project_atomic_transition(state, plan, state["session_id"])
    assert result["status"] == "ready_with_projected_state"
    return result["projected_state"]


def _inputs(*, equal_speed=False, own_hp=100, opponent_hp=100, own_move="tackle"):
    state = _complete_state(_state())
    state["self_side"]["pokemon"][0]["current_hp"] = own_hp
    state["opponent_side"]["pokemon"][0]["current_hp"] = opponent_hp
    if equal_speed:
        state["opponent_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"] = 100
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = _owner(state, "self")
    own_metadata = _metadata(own_move) | {"candidate_id": f"attack:{own_move}", "active_attacker": own, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    own_action = {"action_id": f"attack:{own_move}", "action_type": "attack", "identity": own_move, "move_metadata_authority": own_metadata}
    known = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities={move: _metadata(move) for move in MOVES})
    response_set = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=known)
    orders = {action_id: {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": "own_first", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "own_action_id": own_action["action_id"], "opponent_action_id": action_id, "own_actor": _owner(state, "self"), "opponent_actor": _owner(state, "opponent")} for action_id in response_set["selectable_response_action_ids"]}
    return state, snapshot, d0, own_action, response_set, orders


def _equal_speed_order(d0, own_action, opponent_action):
    return {
        "status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1",
        "order": "unresolved_tie", "order_engine": {"status": "speed_tie"},
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"],
        "own_action_id": own_action["action_id"], "opponent_action_id": opponent_action["action_id"],
        "own_actor": d0["active_owners"]["self"], "opponent_actor": d0["active_owners"]["opponent"],
    }


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


def test_combined_universe_dispatches_move_and_switch_entries_exactly_once(monkeypatch):
    _, snapshot, d0, own_action, move_set, orders = _inputs()
    move = deepcopy(move_set["actions"][0]) | {"response_kind": "move"}
    switch_id = "opponent_switch:response-profile:1:bench"
    switch = {"action_id": switch_id, "action_type": "manual_switch", "acting_side": "opponent", "target_side": "self", "selectability": "selectable", "availability": "alive", "response_kind": "switch", "target_owner": {"session_id": d0["session_id"], "side": "opponent", "slot_index": 1, "pokemon_id": "bench"}}
    combined = {
        "status": "resolved", "schema_version": "runtime-d0-combined-opponent-response-universe-authority-v1",
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "opponent_actor": d0["active_owners"]["opponent"], "target_owner": d0["active_owners"]["self"],
        "universe_state": "complete_with_selectable_responses", "response_action_ids": (move["action_id"], switch_id), "selectable_response_action_ids": (move["action_id"], switch_id), "actions": (move, switch), "source_switch_response_authority": {"status": "resolved"},
    }
    calls = []
    monkeypatch.setattr("llm.advisor_detached_opponent_response_profile.materialize_immediate_move_vs_move_action_pair", lambda **kwargs: calls.append(("move", kwargs["opponent_action"]["action_id"])) or {"status": "evaluable"})
    monkeypatch.setattr("llm.advisor_detached_opponent_response_profile.materialize_immediate_attack_vs_opponent_switch_action_pair", lambda **kwargs: calls.append(("switch", kwargs["selected_switch_response_action_id"])) or {"status": "evaluable"})
    monkeypatch.setattr("llm.advisor_detached_opponent_response_profile.normalize_exact_immediate_action_pair_outcome_ledger", lambda **_: {"status": "evaluable"})
    monkeypatch.setattr("llm.advisor_detached_opponent_response_profile.project_exact_immediate_action_pair_descriptive_metrics", lambda **_: {"status": "resolved"})

    result = materialize_detached_opponent_response_profile(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, response_set_authority=combined, action_order_authorities={move["action_id"]: orders[move["action_id"]]})
    assert result["status"] == "evaluable"
    assert calls == [("move", move["action_id"]), ("switch", switch_id)]
    assert [(row["opponent_response_action_id"], row["response_kind"]) for row in result["response_entries"]] == [(move["action_id"], "move"), (switch_id, "switch")]

    zero = deepcopy(combined) | {"universe_state": "complete_zero_response_universe", "selectable_response_action_ids": ()}
    unavailable = materialize_detached_opponent_response_profile(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, response_set_authority=zero, action_order_authorities={})
    assert unavailable["status"] == "incomplete" and unavailable["reason"] == "combined_response_universe_has_zero_selectable_responses"


def test_exact_equal_speed_branches_execute_both_orders_with_exact_mass_and_cancellation():
    _, snapshot, d0, own_action, response_set, _ = _inputs(equal_speed=True, own_hp=1, opponent_hp=1)
    opponent_action = response_set["actions"][0]
    order = _equal_speed_order(d0, own_action, opponent_action)
    assert order["status"] == "resolved" and order["order"] == "unresolved_tie"
    branching = materialize_exact_equal_speed_action_order_branches(action_order_authority=order)
    assert branching["status"] == "resolved"
    assert [(row["order"], row["conditional_probability"]) for row in branching["order_branches"]] == [
        ("own_first", {"numerator": 1, "denominator": 2}),
        ("opponent_first", {"numerator": 1, "denominator": 2}),
    ]

    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action,
        opponent_action=opponent_action, action_order_authority=order,
    )
    assert pair["status"] == "evaluable"
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert {row["action_order"] for row in pair["terminal_branches"]} == {"own_first", "opponent_first"}
    assert {row["action_order_conditional_probability"]["denominator"] for row in pair["terminal_branches"]} == {2}
    cancelled_orders = {
        row["action_order"] for row in pair["terminal_branches"]
        if row["second_action"]["state"] == "cancelled_due_to_faint"
    }
    assert cancelled_orders == {"own_first", "opponent_first"}
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"

    _, deterministic_snapshot, deterministic_d0, deterministic_own, deterministic_set, _ = _inputs()
    deterministic_order = {
        **_equal_speed_order(deterministic_d0, deterministic_own, deterministic_set["actions"][0]),
        "order": "own_first", "order_engine": {"status": "acts_first"},
    }
    deterministic_pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=deterministic_d0, runtime_snapshot=deterministic_snapshot,
        own_action=deterministic_own, opponent_action=deterministic_set["actions"][0],
        action_order_authority=deterministic_order,
    )
    assert deterministic_order["order"] == "own_first"
    assert deterministic_pair["status"] == "evaluable"
    assert "exact_equal_speed_order_branches" not in deterministic_pair


def test_equal_speed_branching_never_promotes_unknown_unsupported_or_mismatched_order():
    _, snapshot, d0, own_action, response_set, _ = _inputs(equal_speed=True)
    resolved = _equal_speed_order(d0, own_action, response_set["actions"][0])
    unknown = deepcopy(resolved) | {"status": "incomplete", "reason": "order_unknown"}
    assert materialize_exact_equal_speed_action_order_branches(action_order_authority=unknown)["status"] == "incomplete"
    unsupported = deepcopy(resolved) | {"status": "unsupported", "reason": "lagging_tail"}
    assert materialize_exact_equal_speed_action_order_branches(action_order_authority=unsupported)["status"] == "unsupported"
    malformed = deepcopy(resolved) | {"order_engine": {"status": "acts_first"}}
    assert materialize_exact_equal_speed_action_order_branches(action_order_authority=malformed)["status"] == "rejected"
    stale = deepcopy(resolved) | {"source_runtime_fingerprint": "stale"}
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action,
        opponent_action=response_set["actions"][0], action_order_authority=stale,
    )
    assert pair["status"] == "rejected"


def test_exact_first_action_paralysis_branches_second_action_without_current_condition_mutation(monkeypatch):
    state, snapshot, d0, own_action, response_set, orders = _inputs()
    opponent_action = response_set["actions"][0]

    def leaf(*, strategy_d0, actor, target, **_):
        first = actor == d0["active_owners"]["self"]
        return {
            "status": "evaluable", "terminal_leaves": ({
                "leaf_id": "first:paralysis" if first else "second:ordinary",
                "candidate_id": "attack:tackle", "action_type": "attack",
                "branch_path": ({"branch": "hit", "conditional_probability": {"numerator": 1, "denominator": 1}},),
                "probability": {"numerator": 1, "denominator": 1}, "hit_state": "hit",
                "critical_state": "non_critical", "damage_roll": {"roll_index": 0, "random_factor_percent": 85, "damage": 1},
                "consequences": {"damage": 1, "own_final_hp": 99, "target_final_hp": 99, "target_ko": False, "self_fainted": False,
                    "secondary": {"branch": "effect", "hypothetical_target_condition": {"resulting_condition": "paralysis"}} if first else None},
                "provenance": {"session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": strategy_d0["decision_owner"], "attacker": actor, "target": target, "move_id": "tackle"},
            },),
        }

    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._normal_formula_ledger", leaf)
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action,
        opponent_action=opponent_action, action_order_authority=orders[opponent_action["action_id"]],
    )
    assert pair["status"] == "evaluable"
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    states = {row["second_action"]["state"] for row in pair["terminal_branches"]}
    assert states == {"executed", "cancelled_due_to_paralysis"}
    assert any(row["second_action"].get("execution_conditional_probability") == {"numerator": 1, "denominator": 4} for row in pair["terminal_branches"] if row["second_action"]["state"] == "cancelled_due_to_paralysis")
    assert any(row["second_action"].get("execution_conditional_probability") == {"numerator": 3, "denominator": 4} for row in pair["terminal_branches"] if row["second_action"]["state"] == "executed")
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
    assert snapshot["state"]["opponent_side"]["pokemon"][0]["condition"] == "none"


def test_real_thunderbolt_first_action_reaches_crit_and_paralysis_second_action_path():
    state, _, _, _, _, _ = _inputs()
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = _owner(state, "self")
    own_metadata = _metadata("thunderbolt") | {"candidate_id": "attack:thunderbolt", "active_attacker": own, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    own_action = {"action_id": "attack:thunderbolt", "action_type": "attack", "identity": "thunderbolt", "move_metadata_authority": own_metadata}
    known = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities={move: _metadata(move) for move in MOVES})
    response_set = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=known)
    opponent_action = response_set["actions"][0]
    order = {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": "own_first", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "own_action_id": own_action["action_id"], "opponent_action_id": opponent_action["action_id"], "own_actor": own, "opponent_actor": _owner(state, "opponent")}
    pair = materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action,
        opponent_action=opponent_action, action_order_authority=order,
    )
    assert pair["status"] == "evaluable"
    assert pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert any(row["first_action_leaf"]["critical_state"] == "critical" for row in pair["terminal_branches"])
    assert {row["second_action"]["state"] for row in pair["terminal_branches"]} >= {"executed", "cancelled_due_to_paralysis"}
    assert any(row["second_action"].get("execution_conditional_probability") == {"numerator": 1, "denominator": 4} for row in pair["terminal_branches"] if row["second_action"]["state"] == "cancelled_due_to_paralysis")
    assert any(row["second_action"].get("execution_conditional_probability") == {"numerator": 3, "denominator": 4} for row in pair["terminal_branches"] if row["second_action"]["state"] == "executed")
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
    assert snapshot["state"]["opponent_side"]["pokemon"][0]["condition"] == "none"
